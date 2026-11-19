import Foundation
import Testing
import PinkhaKit
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration

private actor RelatedStore: AnyTorahOperationStore {
    nonisolated let workspace: AnyTorahWorkspace
    private var claims: [AnyTorahClaim] = []
    init(_ workspace: AnyTorahWorkspace) { self.workspace = workspace }
    func snapshot() throws -> AnyTorahProjection { try .init(claims: claims) }
    func append(_ operation: AnyTorahOperation,
                authorize: @escaping @Sendable () async throws -> Void) async throws {
        try await authorize()
        if !claims.contains(where: { $0.id == operation.claimID }) {
            claims.append(try .init(operation: operation, creator: workspace.accountID))
        }
    }
    func inject(_ operation: AnyTorahOperation) throws {
        claims.append(try .init(operation: operation, creator: operation.authorID))
    }
}

private actor RelatedReader: AnyTorahRelatedDocumentReading, AnyTorahTargetAccess {
    nonisolated let workspace: AnyTorahWorkspace
    private var hidden = Set<String>()
    private var readOnly = Set<String>()
    init(_ workspace: AnyTorahWorkspace) { self.workspace = workspace }
    func hide(_ id: String) { hidden.insert(id) }
    func forbidWrite(_ id: String) { readOnly.insert(id) }
    func metadata(objectID: String) throws -> AnyTorahRelatedDocumentMetadata {
        try validate(.object(objectId: objectID), intent: .read)
        return .init(objectID: objectID, spaceID: workspace.spaceID, title: "Title " + objectID,
                     typeID: "page", updatedAt: Date(timeIntervalSince1970: 1_700_000_000),
                     canUnlink: !readOnly.contains(objectID))
    }
    func validate(_ target: TorahAssociationTarget, intent: AnyTorahTargetIntent) throws {
        if hidden.contains(target.objectId) { throw TorahAssociationRepositoryError.permissionDenied }
        if case .write = intent, readOnly.contains(target.objectId) {
            throw TorahAssociationRepositoryError.permissionDenied
        }
    }
}

@Suite("Original T5 related-document query over native canonical snapshots")
struct AnyTorahRelatedDocumentsTests {
    private func fixture(candidateLimit: Int = 500) throws -> (
        AnyTorahWorkspace, RelatedStore, RelatedReader, AnyTorahAssociationRepository, AnyTorahRelatedDocumentsService) {
        let workspace = try AnyTorahWorkspace(accountID: "account", spaceID: "space")
        let operations = RelatedStore(workspace)
        let reader = RelatedReader(workspace)
        let associations = try AnyTorahAssociationRepository(workspace: workspace, store: operations, access: reader)
        let service = try AnyTorahRelatedDocumentsService(
            workspace: workspace, operations: operations, associations: associations,
            reader: reader, pageSize: 2, candidateLimit: candidateLimit)
        return (workspace, operations, reader, associations, service)
    }
    private let source = T5SourceIdentity(providerID: "sefaria", canonicalReference: "Genesis 1:1")

    @Test func documentContextsExcludeBlockQuotesAndOtherKinds() async throws {
        let (_, _, _, associations, service) = try fixture()
        _ = try await associations.addAssociation(source.item, target: .object(objectId: "doc"), spaceId: "space")
        var quote = source.item; quote.id = "quote"; quote.role = .sourceQuote
        _ = try await associations.addAssociation(quote, target: .object(objectId: "quotes"), spaceId: "space")
        _ = try await associations.addAssociation(source.item,
            target: .block(objectId: "block", blockId: "b"), spaceId: "space")
        var topic = source.item; topic.id = "topic"; topic.kind = .topic
        _ = try await associations.addAssociation(topic, target: .object(objectId: "topic"), spaceId: "space")
        let result = try await service.documents(source: source)
        #expect(result.documents.matches.map(\.document.objectID) == ["doc"])
        #expect(result.candidateObjectCount == 1)
        #expect(result.scannedClaimCount == 4)
        #expect(result.coverage == .boundedCanonicalSnapshot && !result.atomicAcrossDocuments)
    }

    @Test func removedContextDoesNotBecomeAStaleLiveMatch() async throws {
        let (_, _, _, associations, service) = try fixture()
        let item = source.item
        _ = try await associations.addAssociation(item, target: .object(objectId: "doc"), spaceId: "space")
        try await associations.removeAssociation(associationId: item.id, target: .object(objectId: "doc"), spaceId: "space")
        let result = try await service.documents(source: source)
        #expect(result.documents.matches.isEmpty)
        #expect(result.candidateObjectCount == 0)
        #expect(result.scannedClaimCount == 2)
    }

    @Test func logicalConflictAcrossObjectsIsQuarantinedBeforeRelatedResults() async throws {
        let (workspace, store, _, _, service) = try fixture()
        let operationID = String(repeating: "a", count: 32)
        for objectID in ["one", "two"] {
            let item = source.item
            let record = TorahStoredAssociationRecord(
                location: .init(spaceId: workspace.spaceID, target: .object(objectId: objectID)), item: item)
            let envelope = TorahCanonicalAssociationsPayload(records: [record])
            let payload = try TorahAssociationPayloadCodec().encodeCanonicalDocument(envelope)
            let operation = try AnyTorahOperation(
                operationID: operationID, spaceID: workspace.spaceID, authorID: workspace.accountID,
                kind: .add, targetObjectID: objectID, providerID: item.providerID,
                canonicalRef: item.canonicalKey, payload: payload)
            try await store.inject(operation)
        }
        let result = try await service.documents(source: source)
        #expect(result.documents.matches.isEmpty)
        #expect(result.documents.hasStaleCandidates)
        #expect(result.candidateObjectCount == 2)
    }

    @Test func currentReadRevocationOmitsCandidateAndReportsCoverage() async throws {
        let (_, _, reader, associations, service) = try fixture()
        for id in ["visible", "revoked"] {
            _ = try await associations.addAssociation(source.item, target: .object(objectId: id), spaceId: "space")
        }
        await reader.hide("revoked")
        let result = try await service.documents(source: source)
        #expect(result.documents.matches.map(\.document.objectID) == ["visible"])
        #expect(result.documents.hasStaleCandidates)
    }

    @Test func originalCandidateBoundRemainsExplicit() async throws {
        let (_, _, _, associations, service) = try fixture(candidateLimit: 1)
        for id in ["one", "two"] {
            _ = try await associations.addAssociation(source.item, target: .object(objectId: id), spaceId: "space")
        }
        let result = try await service.documents(source: source)
        #expect(result.documents.matches.count == 1)
        #expect(result.documents.isTruncated)
        #expect(result.candidateObjectCount == 2)
    }

    @Test func unlinkRemovesOnlyCurrentDocumentContextAndKeepsQuoteBlockAndOtherSource() async throws {
        let (_, _, _, associations, service) = try fixture()
        let context = source.item
        _ = try await associations.addAssociation(context, target: .object(objectId: "doc"), spaceId: "space")
        var quote = source.item; quote.id = "quote"; quote.role = .sourceQuote
        _ = try await associations.addAssociation(quote, target: .object(objectId: "doc"), spaceId: "space")
        let other = T5SourceIdentity(providerID: "sefaria", canonicalReference: "Exodus 2:2").item
        _ = try await associations.addAssociation(other, target: .object(objectId: "doc"), spaceId: "space")
        _ = try await associations.addAssociation(source.item,
            target: .block(objectId: "doc", blockId: "b"), spaceId: "space")
        try await service.unlinkDocument(objectID: "doc", source: source)
        let remaining = try await associations.listDocumentAssociations(objectId: "doc", spaceId: "space")
        #expect(Set(remaining.map(\.id)) == Set([quote.id, other.id]))
        #expect(try await associations.listBlockAssociations(objectId: "doc", blockId: "b", spaceId: "space").count == 1)
    }

    @Test func readonlyMetadataNeverAuthorizesUnlink() async throws {
        let (_, _, reader, associations, service) = try fixture()
        _ = try await associations.addAssociation(source.item, target: .object(objectId: "doc"), spaceId: "space")
        await reader.forbidWrite("doc")
        await #expect(throws: TorahAssociationRepositoryError.permissionDenied) {
            try await service.unlinkDocument(objectID: "doc", source: source)
        }
        #expect(try await associations.listDocumentAssociations(objectId: "doc", spaceId: "space").count == 1)
    }

    @Test func internalNoteReferenceIsNotAnExternalRelatedSource() async throws {
        let (_, _, _, _, service) = try fixture()
        await #expect(throws: T5SpaceRelatedDocumentsError.invalidIdentity) {
            try await service.documents(source: .init(providerID: "sefaria", canonicalReference: "anytype-note:note"))
        }
    }
}
