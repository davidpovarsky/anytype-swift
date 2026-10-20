import Foundation
import PinkhaKit
import SwiftProtobuf
import Testing
import TorahInspectorCore
@testable import Anytype

@Suite("T2-L native single-writer repository")
struct TorahAssociationNativeRepositoryTests {
    private let spaceId = "space"
    private let objectId = "document"

    @Test("Concurrent mutations in one process are serialized without lost updates")
    func concurrentMutationsRetainEveryAssociation() async throws {
        let store = NativeStoreProbe(spaceId: spaceId, objectId: objectId, blockIds: ["block"])
        let repository = makeRepository(store: store)

        try await withThrowingTaskGroup(of: Void.self) { group in
            for index in 0..<24 {
                group.addTask {
                    _ = try await repository.addAssociation(
                        association(index),
                        target: index.isMultiple(of: 2)
                            ? .object(objectId: objectId)
                            : .block(objectId: objectId, blockId: "block"),
                        spaceId: spaceId
                    )
                }
            }
            try await group.waitForAll()
        }

        let document = try await repository.listDocumentAssociations(objectId: objectId, spaceId: spaceId)
        let block = try await repository.listBlockAssociations(
            objectId: objectId,
            blockId: "block",
            spaceId: spaceId
        )
        #expect(document.count == 12)
        #expect(block.count == 12)
        #expect(Set(document.map(\.id) + block.map(\.id)).count == 24)
        #expect(await store.maximumConcurrentWrites() == 1)
        #expect(await store.unrelatedDetails() == ["name": "untouched", "custom": "preserved"])
        #expect(await store.blockFingerprints() == ["block": "unchanged"])
    }

    @Test("A lost acknowledgement succeeds only after exact native readback")
    func acknowledgementLossReconcilesByReadback() async throws {
        let store = NativeStoreProbe(
            spaceId: spaceId,
            objectId: objectId,
            blockIds: [],
            writeBehavior: .persistThenThrow
        )
        let repository = makeRepository(store: store)

        let stored = try await repository.addAssociation(
            association(1),
            target: .object(objectId: objectId),
            spaceId: spaceId
        )

        #expect(stored.id == "association-1")
        #expect(try await repository.listDocumentAssociations(objectId: objectId, spaceId: spaceId).map(\.id) == ["association-1"])
    }

    @Test("An unacknowledged and unpersisted write is visibly uncertain")
    func uncertainWriteIsNotReportedAsSaved() async {
        let store = NativeStoreProbe(
            spaceId: spaceId,
            objectId: objectId,
            blockIds: [],
            writeBehavior: .throwWithoutPersisting
        )
        let repository = makeRepository(store: store)

        do {
            _ = try await repository.addAssociation(
                association(2),
                target: .object(objectId: objectId),
                spaceId: spaceId
            )
            Issue.record("An uncertain write was reported as successful")
        } catch let error as TorahAssociationRepositoryError {
            guard case .writeUncertain = error else {
                Issue.record("Expected writeUncertain, got \(error)")
                return
            }
        } catch {
            Issue.record("Unexpected error: \(error)")
        }
    }

    @Test("Future and malformed native values fail closed before any write")
    func invalidNativePayloadsFailClosed() async {
        for (value, expected) in [
            (#"{"version":99,"records":[]}"#, TorahAssociationRepositoryError.unsupportedPayloadVersion(99)),
            ("{", TorahAssociationRepositoryError.malformedCanonicalData)
        ] {
            let store = NativeStoreProbe(spaceId: spaceId, objectId: objectId, blockIds: [], value: value)
            let repository = makeRepository(store: store)
            do {
                _ = try await repository.addAssociation(
                    association(3),
                    target: .object(objectId: objectId),
                    spaceId: spaceId
                )
                Issue.record("Invalid canonical data was overwritten")
            } catch let error as TorahAssociationRepositoryError {
                #expect(error == expected)
            } catch {
                Issue.record("Unexpected error: \(error)")
            }
            #expect(await store.writeCount() == 0)
        }
    }

    @Test("A present non-string native property fails closed")
    func wrongTypedNativePropertyFailsClosed() {
        let value = Google_Protobuf_Value.with { $0.numberValue = 42 }

        do {
            _ = try TorahAssociationNativePropertyValue.decode(value)
            Issue.record("A wrong-typed native value was treated as an absent property")
        } catch let error as TorahAssociationRepositoryError {
            #expect(error == .malformedCanonicalData)
        } catch {
            Issue.record("Unexpected error: \(error)")
        }
    }

    @Test("Trial mutations require every disposable-document confirmation")
    func mutationOptInFailsClosed() {
        #expect(!TorahEditorSafetyPolicy.mutationIsAuthorized(
            disposableSpaceConfirmed: false,
            freshDocumentConfirmed: true,
            confirmation: "DISPOSABLE"
        ))
        #expect(!TorahEditorSafetyPolicy.mutationIsAuthorized(
            disposableSpaceConfirmed: true,
            freshDocumentConfirmed: false,
            confirmation: "DISPOSABLE"
        ))
        #expect(!TorahEditorSafetyPolicy.mutationIsAuthorized(
            disposableSpaceConfirmed: true,
            freshDocumentConfirmed: true,
            confirmation: "production"
        ))
        #expect(TorahEditorSafetyPolicy.mutationIsAuthorized(
            disposableSpaceConfirmed: true,
            freshDocumentConfirmed: true,
            confirmation: " disposable "
        ))
    }

    @Test("External Torah drops copy while internal editor drags remain moves")
    func dragOperationsStaySeparated() {
        #expect(TorahEditorSafetyPolicy.dropOperation(
            containsTorahSource: true,
            mutationIsAuthorized: true,
            canPlace: true
        ) == .copy)
        #expect(TorahEditorSafetyPolicy.dropOperation(
            containsTorahSource: false,
            mutationIsAuthorized: true,
            canPlace: true
        ) == .move)
        #expect(TorahEditorSafetyPolicy.dropOperation(
            containsTorahSource: true,
            mutationIsAuthorized: false,
            canPlace: true
        ) == .forbidden)
    }

    @MainActor
    @Test("Resolved verses preserve section and exact-segment identity")
    func resolvedVerseSelection() throws {
        let resolved = ResolvedReference(
            canonical: "Genesis 1:1",
            labelHe: "בראשית א׳:א׳",
            nodeType: "JaggedArrayNode",
            depth: 2,
            startIndexes: [1, 1],
            firstAvailableSectionRef: "Genesis 1"
        )

        let selection = try TorahEditorSession.inspectorSelection(for: resolved)

        #expect(selection.canonicalRef == "Genesis 1")
        #expect(selection.preferredSegmentRef == "Genesis 1:1")
        #expect(selection.scope == .segment)
    }

    @Test("Space, block, deletion, archive, and detail permissions are enforced")
    func targetAndPermissionGuards() async {
        let cases: [(NativeStoreProbe, TorahAssociationTarget, TorahAssociationRepositoryError)] = [
            (NativeStoreProbe(spaceId: "other", objectId: objectId, blockIds: []), .object(objectId: objectId), .targetOutsideSpace),
            (NativeStoreProbe(spaceId: spaceId, objectId: objectId, blockIds: []), .block(objectId: objectId, blockId: "missing"), .targetNotFound),
            (NativeStoreProbe(spaceId: spaceId, objectId: objectId, blockIds: [], isDeleted: true), .object(objectId: objectId), .targetNotFound),
            (NativeStoreProbe(spaceId: spaceId, objectId: objectId, blockIds: [], isArchived: true), .object(objectId: objectId), .targetNotFound),
            (NativeStoreProbe(spaceId: spaceId, objectId: objectId, blockIds: [], canWrite: false), .object(objectId: objectId), .permissionDenied)
        ]

        for (store, target, expected) in cases {
            let repository = makeRepository(store: store)
            do {
                _ = try await repository.addAssociation(association(4), target: target, spaceId: spaceId)
                Issue.record("Guarded mutation unexpectedly succeeded")
            } catch let error as TorahAssociationRepositoryError {
                #expect(error == expected)
            } catch {
                Issue.record("Unexpected error: \(error)")
            }
            #expect(await store.writeCount() == 0)
        }
    }

    private func makeRepository(store: NativeStoreProbe) -> AnytypeTorahAssociationRepository {
        AnytypeTorahAssociationRepository(
            nativeStore: store,
            manifestProvider: ManifestProbe(spaceId: spaceId),
            coordinator: TorahAssociationMutationCoordinator(),
            statusCenter: TorahAssociationPersistenceStatusCenter()
        )
    }

    private func association(_ index: Int) -> TorahAssociationItem {
        TorahAssociationItem(
            id: "association-\(index)",
            kind: .ref,
            role: .context,
            providerID: "sefaria",
            externalID: "Genesis.1.\(index + 1)",
            canonicalKey: "Genesis 1:\(index + 1)",
            labelHe: "בראשית א",
            labelEn: "Genesis 1:\(index + 1)"
        )
    }
}

private struct ManifestProbe: TorahAssociationManifestProvider {
    let spaceId: String

    func manifest(spaceId requestedSpaceId: String) async throws -> PinkhaSpaceManifest {
        PinkhaSpaceManifest(
            spaceId: requestedSpaceId,
            parentPropertyId: "parent-id",
            parentPropertyKey: "parent-key",
            orderPropertyId: "order-id",
            orderPropertyKey: "order-key",
            documentAssociationsPropertyId: "associations-id",
            documentAssociationsPropertyKey: "pinkha-associations",
            folderTypeId: "folder-id",
            bookFolderTypeId: "book-folder-id",
            registeredDocumentTypes: [
                PinkhaSchemaRoles.chiddushKey: "chiddush-id",
                PinkhaSchemaRoles.articleKey: "article-id",
                PinkhaSchemaRoles.researchKey: "research-id"
            ],
            defaultTemplateIds: [
                PinkhaSchemaRoles.chiddushKey: "chiddush-template",
                PinkhaSchemaRoles.articleKey: "article-template",
                PinkhaSchemaRoles.researchKey: "research-template"
            ]
        )
    }
}

private actor NativeStoreProbe: TorahAssociationNativeStore {
    enum WriteBehavior: Sendable {
        case succeed
        case persistThenThrow
        case throwWithoutPersisting
    }

    private let spaceId: String
    private let objectId: String
    private let blockIds: Set<String>
    private let isDeleted: Bool
    private let isArchived: Bool
    private let canWrite: Bool
    private let writeBehavior: WriteBehavior
    private var value: String?
    private var writes = 0
    private var concurrentWrites = 0
    private var maxConcurrentWrites = 0
    private let otherDetails = ["name": "untouched", "custom": "preserved"]
    private let blocks = ["block": "unchanged"]

    init(
        spaceId: String,
        objectId: String,
        blockIds: Set<String>,
        value: String? = nil,
        isDeleted: Bool = false,
        isArchived: Bool = false,
        canWrite: Bool = true,
        writeBehavior: WriteBehavior = .succeed
    ) {
        self.spaceId = spaceId
        self.objectId = objectId
        self.blockIds = blockIds
        self.value = value
        self.isDeleted = isDeleted
        self.isArchived = isArchived
        self.canWrite = canWrite
        self.writeBehavior = writeBehavior
    }

    func readDocument(
        spaceId: String,
        objectId: String,
        propertyKey: String
    ) async throws -> TorahAssociationNativeDocumentSnapshot {
        TorahAssociationNativeDocumentSnapshot(
            spaceId: self.spaceId,
            objectId: self.objectId,
            isDeleted: isDeleted,
            isArchived: isArchived,
            canWriteDetails: canWrite,
            blockIds: blockIds,
            propertyValue: value
        )
    }

    func writeDocumentProperty(objectId: String, propertyKey: String, value: String) async throws {
        writes += 1
        concurrentWrites += 1
        maxConcurrentWrites = max(maxConcurrentWrites, concurrentWrites)
        defer { concurrentWrites -= 1 }
        try await Task.sleep(for: .milliseconds(2))
        switch writeBehavior {
        case .succeed:
            self.value = value
        case .persistThenThrow:
            self.value = value
            throw ProbeError.lostAcknowledgement
        case .throwWithoutPersisting:
            throw ProbeError.lostAcknowledgement
        }
    }

    func writeCount() -> Int { writes }
    func maximumConcurrentWrites() -> Int { maxConcurrentWrites }
    func unrelatedDetails() -> [String: String] { otherDetails }
    func blockFingerprints() -> [String: String] { blocks }
}

private enum ProbeError: Error {
    case lostAcknowledgement
}
