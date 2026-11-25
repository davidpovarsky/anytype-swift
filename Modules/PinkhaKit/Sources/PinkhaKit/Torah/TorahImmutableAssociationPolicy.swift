import Foundation

/// Domain payload only. Native adapters still verify signatures, authors,
/// target reachability, current ACL and the account/Space lifetime.
public struct TorahImmutableAssociationContent: Sendable, Equatable {
    public let record: TorahStoredAssociationRecord
    public let envelopeUnknown: [String: TorahJSONValue]
    public let originalPayload: Data
    public let canonicalPayload: Data

    public init(payload: Data, location: TorahAssociationLocation,
                providerID: String, canonicalRef: String) throws {
        guard !payload.isEmpty, payload.count <= 65_536 else {
            throw TorahAssociationRepositoryError.malformedCanonicalData
        }
        let codec = TorahAssociationPayloadCodec()
        let decoded = try codec.decodeCanonicalDocument(payload, legacyLocation: location)
        try TorahSourceJSONGuard.validateCanonicalPayload(payload, decoded: decoded)
        guard decoded.records.count == 1, let record = decoded.records.first,
              TorahImmutableAssociationPolicy.sameLocation(record.location, location),
              !record.item.id.isEmpty, !providerID.isEmpty, !canonicalRef.isEmpty,
              TorahAuthorizedOperationReadContract.exact(record.item.providerID, providerID),
              TorahAuthorizedOperationReadContract.exact(
                record.item.canonicalKey.isEmpty ? record.item.externalID : record.item.canonicalKey,
                canonicalRef) else {
            throw TorahAssociationRepositoryError.malformedCanonicalData
        }
        let canonical = try codec.encodeCanonicalDocument(decoded)
        guard canonical.count <= 65_536 else {
            throw TorahAssociationRepositoryError.malformedCanonicalData
        }
        self.record = record
        envelopeUnknown = decoded.unknownFields
        originalPayload = payload
        canonicalPayload = canonical
    }
}

/// A native adapter supplies this value only after its own actual claim checks.
/// Constructing this shape is not independent native or signature verification.
public struct TorahImmutableAssociationClaim: Sendable, Equatable {
    public let claimID: String
    public let content: TorahImmutableAssociationContent

    public init(claimID: String, content: TorahImmutableAssociationContent) throws {
        guard TorahImmutableAssociationPolicy.validClaimID(claimID) else {
            throw TorahAssociationRepositoryError.malformedCanonicalData
        }
        self.claimID = claimID
        self.content = content
    }
}

public struct TorahImmutableAssociationConflict: Sendable, Equatable {
    public let claimIDs: [String]
    public let reason: String

    public init(claimIDs: [String], reason: String) {
        self.claimIDs = claimIDs
        self.reason = reason
    }
}

/// The default retains the existing Any behavior. Coalescing is an explicit
/// domain policy, and is permitted only for complete equal canonical payloads.
public enum TorahImmutableAssociationDuplicatePolicy: Sendable {
    case preserveVariants
    case coalesceEqualCanonicalFacts
}

public struct TorahImmutableAssociationEntry: Sendable, Equatable {
    public let content: TorahImmutableAssociationContent
    public let claims: [TorahImmutableAssociationClaim]
    public var record: TorahStoredAssociationRecord { content.record }
    public var observedClaimIDs: [String] { claims.map(\.claimID).sorted() }

    fileprivate init(claims: [TorahImmutableAssociationClaim]) {
        self.claims = claims
        content = claims[0].content
    }
}

public struct TorahImmutableAssociationState: Sendable {
    public let location: TorahAssociationLocation
    public let entries: [TorahImmutableAssociationEntry]
    public let conflicts: [TorahImmutableAssociationConflict]
    public let duplicatePolicy: TorahImmutableAssociationDuplicatePolicy

    fileprivate init(location: TorahAssociationLocation,
                     entries: [TorahImmutableAssociationEntry],
                     conflicts: [TorahImmutableAssociationConflict],
                     duplicatePolicy: TorahImmutableAssociationDuplicatePolicy) {
        self.location = location
        self.entries = entries
        self.conflicts = conflicts
        self.duplicatePolicy = duplicatePolicy
    }
}

/// Pure item-level intent. The engine adapter freezes its own operation ID,
/// author, signed bytes and lease before the first actual append. Exact retry
/// must reuse that whole frozen native operation, never re-run this planner.
public struct TorahImmutableAssociationMutation: Sendable, Equatable {
    public enum Kind: String, Sendable { case add, remove, replace }
    public let kind: Kind
    public let location: TorahAssociationLocation
    public let providerID: String
    public let canonicalRef: String
    public let payload: Data
    public let observed: [String]

    fileprivate init(kind: Kind, location: TorahAssociationLocation,
                     providerID: String = "", canonicalRef: String = "",
                     payload: Data = Data(), observed: [String] = []) throws {
        guard observed.count <= 256, Set(observed).count == observed.count,
              observed.allSatisfy(TorahImmutableAssociationPolicy.validClaimID) else {
            throw TorahAssociationRepositoryError.writeConflict("Observed association variants exceed the native bound")
        }
        self.kind = kind
        self.location = location
        self.providerID = providerID
        self.canonicalRef = canonicalRef
        self.payload = payload
        self.observed = observed.sorted()
    }
}

public struct TorahImmutableAssociationItemPlan: Sendable {
    public let item: TorahAssociationItem
    public let mutation: TorahImmutableAssociationMutation?

    fileprivate init(item: TorahAssociationItem, mutation: TorahImmutableAssociationMutation?) {
        self.item = item
        self.mutation = mutation
    }
}

public enum TorahImmutableAssociationPolicy {
    /// Native operation-ID conflicts and unresolved predecessors remain visible
    /// even when their parsed source facts happen to be canonically equal.
    public static func project(
        _ claims: [TorahImmutableAssociationClaim],
        at location: TorahAssociationLocation,
        nativeConflicts: [TorahImmutableAssociationConflict] = [],
        duplicates: TorahImmutableAssociationDuplicatePolicy = .preserveVariants
    ) throws -> TorahImmutableAssociationState {
        guard claims.count <= 10_000,
              Set(claims.map(\.claimID)).count == claims.count,
              claims.allSatisfy({ sameLocation($0.content.record.location, location) }),
              nativeConflicts.allSatisfy({
                  !$0.claimIDs.isEmpty && $0.claimIDs.allSatisfy(validClaimID) && !$0.reason.isEmpty
              }) else {
            throw TorahAssociationRepositoryError.malformedCanonicalData
        }
        var groups: [[TorahImmutableAssociationClaim]] = []
        switch duplicates {
        case .preserveVariants:
            groups = claims.map { [$0] }
        case .coalesceEqualCanonicalFacts:
            var indexes: [Data: Int] = [:]
            for claim in claims {
                let key = claim.content.canonicalPayload
                if let index = indexes[key] {
                    groups[index].append(claim)
                } else {
                    indexes[key] = groups.count
                    groups.append([claim])
                }
            }
        }
        let entries = groups.map(TorahImmutableAssociationEntry.init(claims:))
        var conflicts = nativeConflicts
        let semanticGroups = Dictionary(grouping: entries) {
            TorahAssociationIdentity(item: $0.record.item, location: location)
        }
        for group in semanticGroups.values where group.count > 1 {
            conflicts.append(.init(claimIDs: group.flatMap(\.observedClaimIDs).sorted(),
                                   reason: "concurrent live association variants"))
        }
        let idGroups = Dictionary(grouping: entries, by: { $0.record.item.id })
        for group in idGroups.values where group.count > 1 &&
            Set(group.map { TorahAssociationIdentity(item: $0.record.item, location: location) }).count > 1 {
            conflicts.append(.init(claimIDs: group.flatMap(\.observedClaimIDs).sorted(),
                                   reason: "stable association ID changed identity concurrently"))
        }
        return .init(location: location, entries: entries, conflicts: conflicts, duplicatePolicy: duplicates)
    }

    public static func plan(
        _ item: TorahAssociationItem,
        in state: TorahImmutableAssociationState,
        requireExisting: Bool
    ) throws -> TorahImmutableAssociationItemPlan {
        guard !item.id.isEmpty, !item.providerID.isEmpty,
              !item.canonicalKey.isEmpty || !item.externalID.isEmpty else {
            throw TorahAssociationRepositoryError.malformedCanonicalData
        }
        try requireNoConflicts(state)
        let identity = TorahAssociationIdentity(item: item, location: state.location)
        let matches = state.entries.filter {
            $0.record.item.id == item.id ||
                (!requireExisting && TorahAssociationIdentity(item: $0.record.item, location: state.location) == identity)
        }
        guard matches.count <= 1 else {
            throw TorahAssociationRepositoryError.writeConflict("Ambiguous association identity")
        }
        let existing = matches.first
        if requireExisting && existing == nil {
            throw TorahAssociationRepositoryError.associationNotFound(item.id)
        }
        let merged: TorahAssociationItem
        if let existing {
            let prior = [existing.record.item]
            let items = requireExisting
                ? try TorahAssociationCollectionPolicy.updating(item, in: prior)
                : TorahAssociationCollectionPolicy.upserting(item, into: prior, location: state.location)
            guard let value = items.first else {
                throw TorahAssociationRepositoryError.malformedCanonicalData
            }
            merged = value
        } else {
            merged = item
        }
        var record = existing?.record ?? TorahStoredAssociationRecord(location: state.location, item: merged)
        record.item = merged
        let payload = try TorahAssociationPayloadCodec().encodeCanonicalDocument(.init(
            records: [record], unknownFields: existing?.content.envelopeUnknown ?? [:]))
        guard payload.count <= 65_536 else {
            throw TorahAssociationRepositoryError.malformedCanonicalData
        }
        if let existing {
            let prior = switch state.duplicatePolicy {
            case .preserveVariants: existing.content.originalPayload
            case .coalesceEqualCanonicalFacts: existing.content.canonicalPayload
            }
            if payload == prior { return .init(item: merged, mutation: nil) }
        }
        let mutation = try TorahImmutableAssociationMutation(
            kind: existing == nil ? .add : .replace, location: state.location,
            providerID: merged.providerID,
            canonicalRef: merged.canonicalKey.isEmpty ? merged.externalID : merged.canonicalKey,
            payload: payload, observed: existing?.observedClaimIDs ?? [])
        return .init(item: merged, mutation: mutation)
    }

    public static func removing(
        associationID: String,
        from state: TorahImmutableAssociationState
    ) throws -> TorahImmutableAssociationMutation? {
        try requireNoConflicts(state)
        let matches = state.entries.filter { $0.record.item.id == associationID }
        guard !matches.isEmpty else { return nil }
        return try .init(kind: .remove, location: state.location,
                         observed: matches.flatMap(\.observedClaimIDs))
    }

    public static func requireNoConflicts(_ state: TorahImmutableAssociationState) throws {
        guard state.conflicts.isEmpty else {
            throw TorahAssociationRepositoryError.writeConflict("Concurrent association variants require explicit resolution")
        }
    }

    static func validClaimID(_ value: String) -> Bool {
        let parts = value.split(separator: "/", omittingEmptySubsequences: false)
        return parts.count == 2 && parts.allSatisfy {
            TorahAuthorizedOperationReadContract.hex(String($0), count: 64)
        }
    }

    static func sameLocation(_ left: TorahAssociationLocation, _ right: TorahAssociationLocation) -> Bool {
        TorahAuthorizedOperationReadContract.exact(left.spaceId, right.spaceId) &&
            TorahAuthorizedOperationReadContract.exact(left.target.objectId, right.target.objectId) &&
            sameOptional(left.target.blockId, right.target.blockId)
    }

    private static func sameOptional(_ left: String?, _ right: String?) -> Bool {
        switch (left, right) {
        case (nil, nil): true
        case let (left?, right?): TorahAuthorizedOperationReadContract.exact(left, right)
        default: false
        }
    }
}
