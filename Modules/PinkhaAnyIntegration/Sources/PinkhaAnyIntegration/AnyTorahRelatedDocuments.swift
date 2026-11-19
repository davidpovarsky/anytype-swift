import Foundation
import PinkhaKit
import PinkhaAnyEngine

public struct AnyTorahRelatedDocumentMetadata: Sendable {
    public let objectID: String
    public let spaceID: String
    public let title: String
    public let typeID: String
    public let iconEmoji: String?
    public let iconName: String?
    public let iconImageID: String?
    public let updatedAt: Date?
    public let isNote: Bool
    public let canUnlink: Bool

    public init(objectID: String, spaceID: String, title: String, typeID: String,
                iconEmoji: String? = nil, iconName: String? = nil, iconImageID: String? = nil,
                updatedAt: Date? = nil, isNote: Bool = false, canUnlink: Bool = false) {
        self.objectID = objectID; self.spaceID = spaceID; self.title = title; self.typeID = typeID
        self.iconEmoji = iconEmoji; self.iconName = iconName; self.iconImageID = iconImageID
        self.updatedAt = updatedAt; self.isNote = isNote; self.canUnlink = canUnlink
    }

    func indexed(records: [TorahStoredAssociationRecord], ready: Bool) -> T5IndexedDocument {
        .init(objectID: objectID, spaceID: spaceID, title: title, typeID: typeID,
              iconEmoji: iconEmoji, iconName: iconName, iconImageID: iconImageID, updatedAt: updatedAt,
              isNote: isNote, isEligible: true, isProjectionReady: ready, canUnlink: canUnlink, records: records)
    }
}

public protocol AnyTorahRelatedDocumentReading: Sendable {
    var workspace: AnyTorahWorkspace { get }
    /// Return only after checking current scope, document eligibility and read
    /// permission. Permissions here are metadata; writes must authorize again.
    func metadata(objectID: String) async throws -> AnyTorahRelatedDocumentMetadata
}

/// Object index metadata plus the same current target/ACL gate as canonical
/// associations. Native any.icon is a client-defined string; the host supplies
/// its own proven codec instead of guessing whether a string is an emoji/file.
public struct AnyHTTPTorahRelatedDocumentReader: AnyTorahRelatedDocumentReading, Sendable {
    public typealias IconDecoder = @Sendable (String) throws -> (emoji: String?, name: String?, imageID: String?)
    public let workspace: AnyTorahWorkspace
    private let client: AnyHTTPClient
    private let access: AnyHTTPTorahTargetAccess
    private let allowedTypeIDs: Set<String>
    private let noteTypeIDs: Set<String>
    private let noteCollectionIDs: Set<String>
    private let decodeIcon: IconDecoder

    public init(client: AnyHTTPClient, workspace: AnyTorahWorkspace, allowedTypeIDs: Set<String>,
                noteTypeIDs: Set<String> = [], noteCollectionIDs: Set<String> = [],
                decodeIcon: @escaping IconDecoder = { _ in (nil, nil, nil) }) throws {
        guard noteTypeIDs.isSubset(of: allowedTypeIDs) else { throw AnyEngineError.invalidIdentity("note type scope") }
        self.workspace = workspace; self.client = client; self.allowedTypeIDs = allowedTypeIDs
        self.noteTypeIDs = noteTypeIDs; self.noteCollectionIDs = noteCollectionIDs
        self.decodeIcon = decodeIcon
        self.access = try .init(client: client, workspace: workspace, allowedTypeIDs: allowedTypeIDs)
    }

    public func metadata(objectID: String) async throws -> AnyTorahRelatedDocumentMetadata {
        let target = TorahAssociationTarget.object(objectId: objectID)
        try await access.validate(target, intent: .read)
        let base = ["v1", "spaces", workspace.spaceID]
        let response = try await client.requestJSON(method: "POST", path: base + ["objects", "query"],
            body: .object(["filter": .object(["id": .string(objectID)]),
                           "limit": .integer(2), "includeTotal": .bool(true)]))
        guard let records = response["records"]?.array, records.count == 1,
              response["total"]?.integer == 1, response["hasNext"]?.bool == false,
              let row = records.first else { throw TorahAssociationRepositoryError.targetNotFound }
        try AnyHTTPTorahTargetAccess.validateObject(.object(["objectId": .string(objectID), "record": row]),
            target: target, workspace: workspace, allowedTypeIDs: allowedTypeIDs,
            excludedCollectionIDs: ["bin", "template"])
        let member = try await client.requestJSON(method: "GET", path: base + ["members", "me"])
        try AnyHTTPTorahTargetAccess.validateMember(member, workspace: workspace, intent: .read)
        try await access.validate(target, intent: .read)
        let typeID = try row["any"]!.requireString("type")
        let collections = Set(row["any"]?["collections"]?.array?.compactMap(\.string) ?? [])
        let canWrite = ["owner", "admin", "writer"].contains(member["permission"]?.string ?? "")
        var icon: (emoji: String?, name: String?, imageID: String?) = (nil, nil, nil)
        if let raw = row["any"]?["icon"]?.string { icon = try decodeIcon(raw) }
        let updatedAt: Date?
        if let instant = row["modifiedAt"]?["$date"]?.string {
            let formatter = ISO8601DateFormatter()
            formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            if let date = formatter.date(from: instant) { updatedAt = date }
            else {
                formatter.formatOptions = [.withInternetDateTime]
                updatedAt = formatter.date(from: instant)
            }
            guard updatedAt != nil else { throw AnyEngineError.malformedResponse("native modifiedAt") }
        } else { updatedAt = nil }
        return .init(objectID: objectID, spaceID: workspace.spaceID,
            title: row["any"]?["name"]?.string ?? "", typeID: typeID,
            iconEmoji: icon.0, iconName: icon.1, iconImageID: icon.2, updatedAt: updatedAt,
            isNote: noteTypeIDs.contains(typeID) || !collections.isDisjoint(with: noteCollectionIDs),
            canUnlink: canWrite)
    }
}

public struct AnyTorahRelatedDocumentsResult: Sendable {
    public enum Coverage: String, Sendable { case boundedCanonicalSnapshot }
    public let documents: T5SpaceRelatedDocumentsResult
    public let coverage: Coverage
    public let scannedClaimCount: Int
    public let candidateObjectCount: Int
    public let canonicalSnapshotHash: String
    /// The canonical claims snapshot is atomic. Live document metadata/ACL reads
    /// happen afterwards, so this is not an atomic cross-document transaction.
    public let atomicAcrossDocuments = false
}

/// Uses the original paged T5 query over a complete bounded native canonical
/// snapshot. This is an explicit fallback, not native derived-index activation.
/// Expanded block/source-quote results stay behind the verified native contract.
public actor AnyTorahRelatedDocumentsService {
    public nonisolated let workspace: AnyTorahWorkspace
    private let operations: any AnyTorahOperationStore
    private let associations: AnyTorahAssociationRepository
    private let reader: any AnyTorahRelatedDocumentReading
    private let query: T5SpaceRelatedDocumentsQuery

    public init(workspace: AnyTorahWorkspace, operations: any AnyTorahOperationStore,
                associations: AnyTorahAssociationRepository, reader: any AnyTorahRelatedDocumentReading,
                pageSize: Int = 50, candidateLimit: Int = 500) throws {
        guard operations.workspace == workspace, associations.workspace == workspace,
              reader.workspace == workspace else { throw AnyEngineError.invalidIdentity("related-document workspace") }
        self.workspace = workspace; self.operations = operations; self.associations = associations
        self.reader = reader; self.query = .init(pageSize: pageSize, candidateLimit: candidateLimit)
    }

    public func documents(source: T5SourceIdentity) async throws -> AnyTorahRelatedDocumentsResult {
        guard !source.providerID.isEmpty, !source.canonicalReference.isEmpty,
              !source.canonicalReference.hasPrefix("anytype-note:") else {
            throw T5SpaceRelatedDocumentsError.invalidIdentity
        }
        let projection = try await operations.snapshot()
        guard projection.all.allSatisfy({ $0.operation.spaceID == self.workspace.spaceID }) else {
            throw TorahAssociationRepositoryError.targetOutsideSpace
        }
        let matching: (AnyTorahClaim) throws -> Bool = { claim in
            let operation = claim.operation
            guard operation.kind != .remove, operation.targetBlockID.isEmpty,
                  operation.providerID.precomposedStringWithCanonicalMapping == source.providerID,
                  operation.canonicalRef.precomposedStringWithCanonicalMapping == source.canonicalReference else { return false }
            let location = TorahAssociationLocation(spaceId: operation.spaceID,
                target: .object(objectId: operation.targetObjectID))
            let envelope = try TorahAssociationPayloadCodec().decodeCanonicalDocument(
                operation.payload, legacyLocation: location)
            guard envelope.records.count == 1, let record = envelope.records.first,
                  record.location == location, record.item.providerID == operation.providerID,
                  (record.item.canonicalKey.isEmpty ? record.item.externalID : record.item.canonicalKey) == operation.canonicalRef else {
                throw TorahAssociationRepositoryError.malformedCanonicalData
            }
            return source.matches(record.item)
        }
        var candidates = Set(try projection.live.filter(matching).map { $0.operation.targetObjectID })
        for group in projection.conflicts.values {
            let relevant = try group.filter(matching)
            candidates.formUnion(relevant.map { $0.operation.targetObjectID })
        }
        let candidateIDs = candidates.sorted()
        let associations = self.associations, reader = self.reader, workspace = self.workspace
        let result = try await query.execute(spaceID: workspace.spaceID, source: source) { excludedIDs, limit in
            let excluded = Set(excludedIDs)
            let pageIDs = candidateIDs.filter { !excluded.contains($0) }.prefix(limit)
            var page: [T5IndexedDocument] = []
            for id in pageIDs {
                try Task.checkCancellation()
                do {
                    let metadata = try await reader.metadata(objectID: id)
                    guard metadata.objectID == id, metadata.spaceID == workspace.spaceID else {
                        throw TorahAssociationRepositoryError.targetOutsideSpace
                    }
                    let canonical = try await associations.snapshot(
                        projection: projection, target: .object(objectId: id), spaceID: workspace.spaceID)
                    page.append(metadata.indexed(records: canonical.records, ready: canonical.conflicts.isEmpty))
                } catch {
                    if Self.isUnavailableCandidate(error) {
                        page.append(.init(objectID: id, spaceID: workspace.spaceID, title: "", typeID: "",
                                          isEligible: false, isProjectionReady: false, records: []))
                    } else { throw error }
                }
            }
            return page
        }
        let ids = projection.all.map(\.id).sorted()
        let hash = AnyContentDigest.sha256(Data(ids.map { "\($0.utf8.count):\($0)" }.joined(separator: "|").utf8))
        return .init(documents: result, coverage: .boundedCanonicalSnapshot,
                     scannedClaimCount: projection.all.count, candidateObjectCount: candidateIDs.count,
                     canonicalSnapshotHash: hash)
    }

    /// Revalidate exact current document-context source associations before
    /// unlinking. Block links and quote content never enter this mutation.
    public func unlinkDocument(objectID: String, source: T5SourceIdentity,
                               authorize: @escaping @Sendable () async throws -> Void = {}) async throws {
        try await authorize()
        let metadata = try await reader.metadata(objectID: objectID)
        guard metadata.objectID == objectID, metadata.spaceID == workspace.spaceID, metadata.canUnlink else {
            throw TorahAssociationRepositoryError.permissionDenied
        }
        let current = try await associations.listDocumentAssociations(objectId: objectID, spaceId: workspace.spaceID)
        for item in current where source.matches(item) {
            try await associations.removeAssociation(associationId: item.id, target: .object(objectId: objectID),
                                                       spaceId: workspace.spaceID, authorize: authorize)
        }
        try await authorize()
        let after = try await associations.listDocumentAssociations(objectId: objectID, spaceId: workspace.spaceID)
        guard !after.contains(where: source.matches) else { throw AnyEngineError.unverifiedWrite }
    }

    private static func isUnavailableCandidate(_ error: Error) -> Bool {
        if let error = error as? TorahAssociationRepositoryError {
            switch error {
            case .permissionDenied, .targetNotFound: return true
            default: return false
            }
        }
        if case AnyEngineError.http(let status, _) = error {
            return [403, 404, 410].contains(status)
        }
        return false
    }
}
