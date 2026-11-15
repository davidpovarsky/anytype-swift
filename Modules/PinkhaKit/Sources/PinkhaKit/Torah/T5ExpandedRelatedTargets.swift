import Foundation

public struct T5ExpandedRelatedTargets: Sendable {
    public enum Capability: Sendable {
        case unavailable
        case verified
    }

    public struct Target: Sendable {
        public let id: String
        public let document: T5IndexedDocument
        public let blockID: String?
        public let contextAssociationIDs: [String]
        public let sourceQuoteAssociationIDs: [String]

        public var canUnlink: Bool {
            blockID == nil && sourceQuoteAssociationIDs.isEmpty
                && !contextAssociationIDs.isEmpty && document.canUnlink
        }
    }

    public struct Snapshot: Sendable {
        public let targets: [Target]
        public let hasStaleCandidates: Bool
        public let isTruncated: Bool
        public let isCapabilityUnavailable: Bool
    }

    private struct Group: Sendable {
        let id: String
        let document: T5IndexedDocument
        let blockID: String?
        var contextIDs: Set<String> = []
        var quoteIDs: Set<String> = []

        var target: Target {
            Target(id: id, document: document, blockID: blockID,
                   contextAssociationIDs: contextIDs.sorted(), sourceQuoteAssociationIDs: quoteIDs.sorted())
        }
    }

    public let requestSpaceID: String
    public let source: T5SourceIdentity
    public let targetLimit: Int
    private let capability: Capability
    private var groups: [String: Group] = [:]
    private var stale = false
    private var truncated = false

    public init(requestSpaceID: String, source: T5SourceIdentity, capability: Capability, targetLimit: Int = 500) {
        self.requestSpaceID = requestSpaceID
        self.source = source
        self.capability = capability
        self.targetLimit = min(max(targetLimit, 1), 2_000)
    }

    public var snapshot: Snapshot {
        Snapshot(targets: groups.values.map(\.target).sorted(by: Self.precedes),
                 hasStaleCandidates: stale, isTruncated: truncated,
                 isCapabilityUnavailable: isCapabilityUnavailable)
    }

    public mutating func append(
        document: T5IndexedDocument, graph: T5BlockReachability.Result, nativeRelatedVersion: Int?
    ) async throws {
        try Task.checkCancellation()
        guard !isCapabilityUnavailable else { return }
        guard !requestSpaceID.isEmpty, !source.providerID.isEmpty, !source.canonicalReference.isEmpty,
              !source.canonicalReference.hasPrefix("anytype-note:") else {
            throw T5SpaceRelatedDocumentsError.invalidIdentity
        }
        guard nativeRelatedVersion == 1, document.spaceID == requestSpaceID,
              !document.objectID.isEmpty, !document.typeID.isEmpty,
              document.isEligible, document.isProjectionReady else {
            stale = true
            return
        }
        var candidateStale = false
        var incoming: [String: Group] = [:]
        let identity = source.indexValue
        let metadata = Self.metadataOnly(document)
        var hasMatchingRecord = false
        for (offset, record) in document.records.enumerated() {
            if offset.isMultiple(of: 128) {
                await Task.yield()
                try Task.checkCancellation()
            }
            let item = record.item
            let resolvedReference = item.canonicalKey.isEmpty ? item.externalID : item.canonicalKey
            guard item.kind == .ref, item.role == .context || item.role == .sourceQuote,
                  !resolvedReference.hasPrefix("anytype-note:"),
                  TorahDerivedQueryProjection.identity(item) == identity else { continue }
            hasMatchingRecord = true
            guard record.spaceId == requestSpaceID, record.objectId == document.objectID,
                  !item.id.isEmpty else { candidateStale = true; continue }
            if let blockID = record.blockId {
                guard !blockID.isEmpty, graph.spaceID == requestSpaceID,
                      graph.rootID == document.objectID, graph.isVerified,
                      graph.reachableBlockIDs.contains(blockID) else {
                    candidateStale = true
                    continue
                }
            }
            let id = Self.targetID(spaceID: requestSpaceID, objectID: document.objectID, blockID: record.blockId)
            var group = incoming[id] ?? Group(id: id, document: metadata, blockID: record.blockId)
            switch item.role {
            case .context: group.contextIDs.insert(item.id)
            case .sourceQuote: group.quoteIDs.insert(item.id)
            }
            incoming[id] = group
        }
        if !hasMatchingRecord { candidateStale = true }
        try Task.checkCancellation()
        var pending = groups
        let pendingStale = stale || candidateStale
        var pendingTruncated = truncated
        for (id, group) in incoming {
            if var existing = pending[id] {
                existing.contextIDs.formUnion(group.contextIDs)
                existing.quoteIDs.formUnion(group.quoteIDs)
                pending[id] = existing
            } else {
                pending[id] = group
            }
        }
        if pending.count > targetLimit {
            pendingTruncated = true
            let retainedIDs = Set(pending.values.map(\.target).sorted(by: Self.precedes).prefix(targetLimit).map(\.id))
            pending = pending.filter { retainedIDs.contains($0.key) }
        }
        try Task.checkCancellation()
        groups = pending
        stale = pendingStale
        truncated = pendingTruncated
    }

    private var isCapabilityUnavailable: Bool {
        if case .unavailable = capability { return true }
        return false
    }

    private static func targetID(spaceID: String, objectID: String, blockID: String?) -> String {
        [spaceID, objectID, blockID ?? ""].map { "\($0.utf8.count):\($0)" }.joined(separator: "|")
    }

    private static func precedes(_ lhs: Target, _ rhs: Target) -> Bool {
        let leftDate = lhs.document.updatedAt ?? .distantPast
        let rightDate = rhs.document.updatedAt ?? .distantPast
        if leftDate != rightDate { return leftDate > rightDate }
        return lhs.id < rhs.id
    }

    private static func metadataOnly(_ document: T5IndexedDocument) -> T5IndexedDocument {
        T5IndexedDocument(objectID: document.objectID, spaceID: document.spaceID, title: document.title,
            typeID: document.typeID, iconEmoji: document.iconEmoji, iconName: document.iconName,
            iconImageID: document.iconImageID, updatedAt: document.updatedAt, isNote: document.isNote,
            isEligible: document.isEligible, isProjectionReady: document.isProjectionReady,
            canUnlink: document.canUnlink, records: [])
    }
}
