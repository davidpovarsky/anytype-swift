import Foundation
import Testing
import PinkhaKit
import PinkhaAnyEngine
import TorahInspectorCore
@testable import PinkhaAnyIntegration
@testable import PinkhaAnyUI

@Suite("Native related presentation target identity")
struct AnyNativeTorahRelatedIdentityTests {
    private let source = T5SourceIdentity(providerID: "sefaria", canonicalReference: "Genesis 1:1")

    @Test func matchingMetadataPreservesExactDocumentAndSource() async throws {
        let fixture = try fixture(metadataObject: "document", metadataSpace: "space")
        let result = try await fixture.presentation.snapshot(source: source)
        #expect(result.documents.count == 1)
        #expect(result.documents[0].objectID == "document")
        #expect(result.documents[0].spaceID == "space")
        #expect(result.documents[0].sourceReference == source.canonicalReference)
        #expect(result.documents[0].canUnlink)
        #expect(await fixture.index.reads == 2)
    }

    @Test(arguments: [false, true])
    func mismatchedMetadataCannotBeDisplayed(foreignSpace: Bool) async throws {
        let fixture = try fixture(metadataObject: foreignSpace ? "document" : "other-document",
                                  metadataSpace: foreignSpace ? "other-space" : "space")
        await #expect(throws: TorahAssociationRepositoryError.targetOutsideSpace) {
            try await fixture.presentation.snapshot(source: source)
        }
    }

    @Test(arguments: [false, true])
    func mismatchedMetadataCannotAuthorizeUnlink(foreignSpace: Bool) async throws {
        let fixture = try fixture(metadataObject: foreignSpace ? "document" : "other-document",
                                  metadataSpace: foreignSpace ? "other-space" : "space")
        await #expect(throws: TorahAssociationRepositoryError.permissionDenied) {
            try await fixture.presentation.unlink(document: document(), source: source, authorize: {})
        }
        #expect(await fixture.store.reads == 0)
        #expect(await fixture.store.writes == 0)
    }

    @Test func staleSourceRowCannotUnlinkTheCurrentSelection() async throws {
        let fixture = try fixture(metadataObject: "document", metadataSpace: "space")
        await #expect(throws: TorahAssociationRepositoryError.targetNotFound) {
            try await fixture.presentation.unlink(
                document: document(reference: "Exodus 2:2"), source: source, authorize: {})
        }
        #expect(await fixture.index.reads == 0)
        #expect(await fixture.reader.reads == 0)
        #expect(await fixture.store.reads == 0)
        #expect(await fixture.store.writes == 0)
    }

    @Test func currentReadOnlyMetadataCannotAuthorizeUnlink() async throws {
        let fixture = try fixture(metadataObject: "document", metadataSpace: "space", canUnlink: false)
        await #expect(throws: TorahAssociationRepositoryError.permissionDenied) {
            try await fixture.presentation.unlink(document: document(), source: source, authorize: {})
        }
        #expect(await fixture.store.reads == 0)
        #expect(await fixture.store.writes == 0)
    }

    private func document(reference: String? = nil) -> TorahRelatedDocument {
        .init(id: "document", spaceID: "space", objectID: "document", title: "Document",
              sourceReference: reference ?? source.canonicalReference, kind: .document,
              typeID: "page", canUnlink: true)
    }

    private func fixture(metadataObject: String, metadataSpace: String, canUnlink: Bool = true) throws -> Fixture {
        let workspace = try AnyTorahWorkspace(accountID: "account", spaceID: "space")
        let index = RelatedIdentityIndex(workspace: workspace, source: source)
        let reader = RelatedIdentityReader(workspace: workspace, objectID: metadataObject,
                                            spaceID: metadataSpace, canUnlink: canUnlink)
        let store = RelatedIdentityStore(workspace: workspace)
        let associations = try AnyTorahAssociationRepository(workspace: workspace, store: store, access: reader)
        return try .init(index: index, reader: reader, store: store,
                         presentation: AnyNativeTorahRelatedPresentation(
                            index: index, reader: reader, associations: associations))
    }

    private struct Fixture {
        let index: RelatedIdentityIndex
        let reader: RelatedIdentityReader
        let store: RelatedIdentityStore
        let presentation: AnyNativeTorahRelatedPresentation
    }
}

private actor RelatedIdentityIndex: AnyNativeTorahRelatedQuerying {
    nonisolated let workspace: AnyTorahWorkspace
    private let source: T5SourceIdentity
    private(set) var reads = 0

    init(workspace: AnyTorahWorkspace, source: T5SourceIdentity) {
        self.workspace = workspace
        self.source = source
    }

    func related(to source: T5SourceIdentity, limit: Int) throws -> AnyNativeRelatedQueryResult {
        guard source.providerID == self.source.providerID,
              source.canonicalReference == self.source.canonicalReference, limit == 1000 else {
            throw AnyEngineError.invalidIdentity("unexpected related query")
        }
        reads += 1
        return .init(identity: source.indexValue, targets: [.init(
            target: .object(objectId: "document"), contextItemIDs: ["context"],
            sourceQuoteItemIDs: [], canSafelyUnlink: true,
            semanticInputSHA256: String(repeating: "a", count: 64))],
            conflictingTargets: [], unsupportedClaimsPresent: false,
            readiness: .init(coverage: .complete, generation: String(repeating: "b", count: 64)))
    }
}

private actor RelatedIdentityReader: AnyTorahRelatedDocumentReading, AnyTorahTargetAccess {
    nonisolated let workspace: AnyTorahWorkspace
    private let objectID: String
    private let spaceID: String
    private let canUnlink: Bool
    private(set) var reads = 0

    init(workspace: AnyTorahWorkspace, objectID: String, spaceID: String, canUnlink: Bool) {
        self.workspace = workspace
        self.objectID = objectID
        self.spaceID = spaceID
        self.canUnlink = canUnlink
    }

    func metadata(objectID: String) -> AnyTorahRelatedDocumentMetadata {
        reads += 1
        return .init(objectID: self.objectID, spaceID: spaceID, title: "Document", typeID: "page", canUnlink: canUnlink)
    }

    func validate(_ target: TorahAssociationTarget, intent: AnyTorahTargetIntent) {}
}

private actor RelatedIdentityStore: AnyTorahOperationStore {
    nonisolated let workspace: AnyTorahWorkspace
    private(set) var reads = 0
    private(set) var writes = 0
    init(workspace: AnyTorahWorkspace) { self.workspace = workspace }
    func snapshot() throws -> AnyTorahProjection {
        reads += 1
        return try .init(claims: [])
    }
    func append(_ operation: AnyTorahOperation,
                authorize: @escaping @Sendable () async throws -> Void) async throws {
        try await authorize()
        writes += 1
    }
}
