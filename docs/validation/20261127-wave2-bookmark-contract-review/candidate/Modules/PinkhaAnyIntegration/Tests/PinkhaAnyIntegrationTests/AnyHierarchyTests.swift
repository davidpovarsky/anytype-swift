import Foundation

import Testing

import PinkhaKit

import PinkhaAnyEngine

@testable import PinkhaAnyIntegration



private let hierarchyWorkspace = try! AnyTorahWorkspace(accountID: "account", spaceID: "space")

private let hierarchySchema = try! AnyHierarchySchema(

    collectionID: "wiki", parentPropertyID: "parent", positionPropertyID: "pos", folderPropertyID: "folder")



private func hierarchyRow(_ id: String, parent: String = "", position: String = "PPPP",

                          folder: Bool = false, type: String = "page", title: String? = nil,

                          space: String = "space") -> AnyJSON {

    .object(["id": .string(id), "spaceId": .string(space), "_applySeq": .integer(1),

             "_ver": .object(["id": .string("v0"), "any": .object(["name": .string("v0")]),

                              "wiki": .object(["parent": .string("v0"), "pos": .string("v0")])]),

             "any": .object(["type": .string(type), "name": .string(title ?? id), "collections": .array([.string("wiki")])]),

             "wiki": .object(["parent": .string(parent), "pos": .string(position), "folder": .bool(folder)]),

             "future": .object(["preserve": .string("unknown native content")])])

}



/// Explicit API dependency fixture; production creation is the host's one journal.

private actor HierarchyFixtureStore: AnyHierarchyRecordStore, AnyHierarchyObjectCreating {

    nonisolated let workspace = hierarchyWorkspace

    nonisolated let schema = hierarchySchema

    private var rows: [String: AnyJSON]

    private var intents: [String: (String, String)] = [:]

    private var patchCount = 0

    private var failPatch: Int?

    private var lostReplyPatch: Int?

    private var addChildOnArchive = false

    private var writeAllowed = true



    init(_ rows: [AnyJSON]) {

        self.rows = Dictionary(uniqueKeysWithValues: rows.map { ($0["id"]!.string!, $0) })

    }

    func validateMembership(intent: AnyTorahTargetIntent) throws {

        if case .write = intent, !writeAllowed { throw TorahAssociationRepositoryError.permissionDenied }

    }

    func readRows() -> [AnyJSON] {

        rows.values.filter {

            $0["any"]?["collections"]?.array?.contains(.string("bin")) != true &&

                $0["any"]?["collections"]?.array?.contains(.string("template")) != true

        }

    }

    func readObject(objectID: String) throws -> AnyJSON {

        guard let row = rows[objectID] else { throw PinkhaHierarchyError.nodeNotFound(objectId: objectID) }

        return row

    }

    func setFailure(patch: Int? = nil, lostReply: Int? = nil) {

        failPatch = patch; lostReplyPatch = lostReply

    }

    func injectConcurrentChildOnArchive() { addChildOnArchive = true }

    func countPatches() -> Int { patchCount }

    func countCreated() -> Int { intents.count }

    func revokeWrites() { writeAllowed = false }

    // A dependency-fixture event, not a substitute for the native CRDT witness.

    func receiveMembershipWithoutChangingVersion(objectID: String) throws {

        guard var row = rows[objectID]?.object, var any = row["any"]?.object else {

            throw AnyHierarchyError.malformedRow(objectID)

        }

        var collections = any["collections"]?.array ?? []

        collections.append(.string("late-collection"))

        any["collections"] = .array(collections); row["any"] = .object(any)

        row["_applySeq"] = .integer((row["_applySeq"]?.integer ?? 0) + 1)

        rows[objectID] = .object(row)

    }

    func patch(objectID: String, ownerID: String, values: [String: AnyJSON],

               authorize: @escaping @Sendable () async throws -> Void) async throws {

        try await authorize()

        try validateMembership(intent: .write)

        patchCount += 1

        if failPatch == patchCount { throw AnyEngineError.unverifiedWrite }

        guard var row = rows[objectID]?.object else { throw PinkhaHierarchyError.nodeNotFound(objectId: objectID) }

        var owner = row[ownerID]?.object ?? [:]

        for (key, value) in values { owner[key] = value }

        row[ownerID] = .object(owner)

        var version = row["_ver"]?.object ?? [:]

        var ownerVersion = version[ownerID]?.object ?? [:]

        for key in values.keys { ownerVersion[key] = .string("v" + String(patchCount)) }

        version[ownerID] = .object(ownerVersion); row["_ver"] = .object(version)

        row["_applySeq"] = .integer((row["_applySeq"]?.integer ?? 0) + 1)

        rows[objectID] = .object(row)

        if lostReplyPatch == patchCount { throw AnyEngineError.writeUncertain }

    }

    func setArchived(objectID: String, archived: Bool,

                     authorize: @escaping @Sendable () async throws -> Void) async throws {

        try await authorize()

        try validateMembership(intent: .write)

        guard var row = rows[objectID]?.object, var any = row["any"]?.object else {

            throw PinkhaHierarchyError.nodeNotFound(objectId: objectID)

        }

        var collections = any["collections"]?.array ?? []

        collections.removeAll { $0 == .string("bin") }

        if archived { collections.append(.string("bin")) }

        any["collections"] = .array(collections); row["any"] = .object(any); rows[objectID] = .object(row)

        if archived && addChildOnArchive {

            addChildOnArchive = false

            rows["concurrent"] = hierarchyRow("concurrent", parent: objectID)

        }

    }

    func ensureHierarchyObject(plan: AnyHierarchyCreationPlan,

                               authorize: @escaping @Sendable () async throws -> Void) async throws -> String {

        try await authorize()

        try validateMembership(intent: .write)

        if let existing = intents[plan.mutationID] {

            guard existing.0 == plan.fingerprint else { throw AnyEngineError.collision(plan.mutationID) }

            return existing.1

        }

        let id = "created-" + String(intents.count + 1)

        rows[id] = hierarchyRow(id, parent: plan.parentID ?? "", position: plan.position,

                                folder: plan.kind == .folder, type: plan.typeID, title: plan.title)

        intents[plan.mutationID] = (plan.fingerprint, id)

        return id

    }

}



@Suite("Native wiki hierarchy preserves the original tree domain")

struct AnyHierarchyTests {

    private func repository(_ rows: [AnyJSON]) throws -> (HierarchyFixtureStore, AnyHierarchyRepository) {

        let store = HierarchyFixtureStore(rows)

        return (store, try AnyHierarchyRepository(

            workspace: hierarchyWorkspace, store: store, creator: store, allowedTypeIDs: ["page"]))

    }



    @Test func nativeGoAllocatorGoldenVectorsMatchByteForByte() throws {

        struct Vector: Decodable { let after: String?; let before: String?; let result: String }

        let bytes = Data(Self.goldenJSON.utf8)

        let vectors = try JSONDecoder().decode([Vector].self, from: bytes)

        #expect(vectors.count == 41)

        for vector in vectors {

            #expect(try AnyLexicographicPosition.between(after: vector.after, before: vector.before) == vector.result)

        }

    }



    @Test func invalidOrEqualNativePositionsFailClosed() throws {

        for invalid in ["", "שלום", "\"", "\\", String(repeating: "P", count: 1025)] {

            #expect(!AnyLexicographicPosition.isValid(invalid))

        }

        #expect(throws: AnyEngineError.self) {

            try AnyLexicographicPosition.between(after: "PPPP", before: "PPPP")

        }

    }



    @Test func nativePositionsDriveOriginalTreeWithoutRewritingUnknownProperties() throws {

        let rows = [hierarchyRow("folder", folder: true),

                    hierarchyRow("last", parent: "folder", position: "PPQY"),

                    hierarchyRow("first", parent: "folder", position: "PPPP", title: "ראשון")]

        let state = try AnyHierarchySnapshot(workspace: hierarchyWorkspace, schema: hierarchySchema,

                                             rows: rows, allowedTypeIDs: ["page"])

        #expect(state.tree.children(of: "folder").map(\.objectId) == ["first", "last"])

        #expect(state.tree.pathString(for: "first") == "folder / ראשון")

        #expect(state.itemsByID["first"]?.position == "PPPP")

        #expect(state.nativeRows["first"]?["future"] == .object(["preserve": .string("unknown native content")]))

    }



    @Test func wrongSpaceMalformedAndUnsupportedMalformedRowsAreNotSilentlyDropped() throws {

        #expect(throws: AnyHierarchyError.self) {

            try AnyHierarchySnapshot(workspace: hierarchyWorkspace, schema: hierarchySchema,

                rows: [hierarchyRow("foreign", space: "other")], allowedTypeIDs: ["page"])

        }

        var unknown = hierarchyRow("unknown", type: "unregistered").object!

        unknown["wiki"] = .object(["parent": .string("folder")])

        #expect(throws: AnyHierarchyError.self) {

            try AnyHierarchySnapshot(workspace: hierarchyWorkspace, schema: hierarchySchema,

                rows: [.object(unknown)], allowedTypeIDs: ["page"])

        }

    }



    @Test func cycleRecoveryIsVisibleAndMoveValidatorStillRejectsDescendants() async throws {

        let bad = try AnyHierarchySnapshot(workspace: hierarchyWorkspace, schema: hierarchySchema,

            rows: [hierarchyRow("a", parent: "b", folder: true),

                   hierarchyRow("b", parent: "a", folder: true)], allowedTypeIDs: ["page"])

        #expect(!bad.issues.isEmpty)

        #expect(bad.tree.allNodes.count == 2)

        let (_, repository) = try repository([

            hierarchyRow("a", folder: true), hierarchyRow("b", parent: "a", folder: true)])

        await #expect(throws: PinkhaHierarchyError.self) {

            try await repository.prepareMove(objectID: "a", parentID: "b")

        }

    }



    @Test func moveAndReorderUseOneNativeParentPositionPatch() async throws {

        let (store, repository) = try repository([

            hierarchyRow("folder", folder: true), hierarchyRow("a", parent: "folder"),

            hierarchyRow("b", parent: "folder", position: "PPQY"), hierarchyRow("root", position: "PPZP")])

        let plan = try await repository.prepareMove(objectID: "root", parentID: "folder", beforeSiblingID: "b")

        #expect(plan.position > "PPPP" && plan.position < "PPQY")

        let moved = try await repository.commitPlacement(plan)

        #expect(moved.parentID == "folder")

        #expect(await store.countPatches() == 1)

        let snapshot = try await repository.snapshot()

        #expect(snapshot.tree.children(of: "folder").map(\.objectId) == ["a", "root", "b"])

        #expect(snapshot.nativeRows["root"]?["future"] == .object(["preserve": .string("unknown native content")]))

    }



    @Test func exactPlacementRetryUsesReadbackAndDoesNotOverwriteLaterMove() async throws {

        let (store, repository) = try repository([

            hierarchyRow("folder", folder: true), hierarchyRow("document", position: "PPQY")])

        let plan = try await repository.prepareMove(objectID: "document", parentID: "folder")

        await store.setFailure(lostReply: 1)

        _ = try await repository.commitPlacement(plan)

        _ = try await repository.commitPlacement(plan)

        #expect(await store.countPatches() == 1)

        let later = try await repository.prepareMove(objectID: "document", parentID: nil)

        _ = try await repository.commitPlacement(later)

        let reopened = try AnyHierarchyRepository(

            workspace: hierarchyWorkspace, store: store, allowedTypeIDs: ["page"])

        let frozen = try JSONDecoder().decode(AnyHierarchyPlacementPlan.self, from: JSONEncoder().encode(plan))

        await #expect(throws: AnyHierarchyError.stalePlan("document")) {

            try await reopened.commitPlacement(frozen)

        }

        #expect(await store.countPatches() == 2)

    }



    @Test func renameProtectsPriorTitleAndPreservesOtherNativeFields() async throws {

        let (store, repository) = try repository([hierarchyRow("document", title: "Old")])

        let result = try await repository.rename(objectID: "document", expectedTitle: "Old", newTitle: "חדש")

        #expect(result.title == "חדש")

        await #expect(throws: AnyHierarchyError.stalePlan("document")) {

            try await repository.rename(objectID: "document", expectedTitle: "Old", newTitle: "Stale")

        }

        #expect(await store.countPatches() == 1)

    }



    @Test func safeRemovalReparentsChildrenBeforeBinningOnlyTheFolder() async throws {

        let (store, repository) = try repository([

            hierarchyRow("folder", folder: true),

            hierarchyRow("a", parent: "folder"), hierarchyRow("b", parent: "folder", position: "PPQY"),

            hierarchyRow("existing", position: "PPZP")])

        let result = try await repository.removeFolderSafely(objectID: "folder")

        #expect(result.complete && result.folderArchived == true)

        #expect(result.reparentedIDs == ["a", "b"])

        #expect(!result.atomicAcrossObjects)

        let after = try await repository.snapshot()

        #expect(after.tree.rootNodes.map(\.objectId) == ["existing", "a", "b"])

        #expect(try await store.readObject(objectID: "a")["future"] != nil)

        #expect(try await store.readObject(objectID: "folder")["any"]?["collections"]?.array?.contains(.string("bin")) == true)

    }



    @Test func partialRemovalFailureLeavesFolderAndRemainingChildrenRecoverable() async throws {

        let (store, repository) = try repository([

            hierarchyRow("folder", folder: true), hierarchyRow("a", parent: "folder"),

            hierarchyRow("b", parent: "folder", position: "PPQY")])

        await store.setFailure(patch: 2)

        let partial = try await repository.removeFolderSafely(objectID: "folder")

        #expect(!partial.complete && partial.folderArchived == false)

        #expect(partial.reparentedIDs == ["a"])

        let state = try await repository.snapshot()

        #expect(state.itemsByID["b"]?.parentID == "folder")

        #expect(state.itemsByID["a"]?.parentID == nil)

        let completed = try await repository.removeFolderSafely(objectID: "folder")

        #expect(completed.complete)

        #expect(try await repository.snapshot().itemsByID["b"]?.parentID == nil)

    }



    @Test func unsupportedChildPreventsFolderRemoval() async throws {

        let (_, repository) = try repository([

            hierarchyRow("folder", folder: true), hierarchyRow("foreign", parent: "folder", type: "other")])

        await #expect(throws: AnyHierarchyError.unsupportedChild("foreign")) {

            try await repository.removeFolderSafely(objectID: "folder")

        }

        #expect(try await repository.snapshot().itemsByID["folder"] != nil)

    }



    @Test func concurrentChildRestoresFolderVisibilityAndReturnsIncompleteReceipt() async throws {

        let (store, repository) = try repository([hierarchyRow("folder", folder: true)])

        await store.injectConcurrentChildOnArchive()

        let result = try await repository.removeFolderSafely(objectID: "folder")

        #expect(!result.complete && result.folderArchived == false && result.recoveryError != nil)

        let state = try await repository.snapshot()

        #expect(state.itemsByID["folder"] != nil)

        #expect(state.itemsByID["concurrent"]?.parentID == "folder")

    }



    @Test func creationPlanIsImmutableAndDelegatesRetryToOneHostJournal() async throws {

        let (store, repository) = try repository([hierarchyRow("folder", folder: true)])

        let plan = try await repository.prepareCreation(

            typeID: "page", title: "מסמך", kind: .writingDocument, parentID: "folder")

        let reopened = try JSONDecoder().decode(AnyHierarchyCreationPlan.self, from: JSONEncoder().encode(plan))

        #expect(reopened == plan && reopened.fingerprint == plan.fingerprint)

        let first = try await repository.create(plan)

        let retry = try await repository.create(reopened)

        #expect(first == retry && first.parentID == "folder")

        #expect(await store.countCreated() == 1)

        let fresh = try AnyHierarchyRepository(workspace: hierarchyWorkspace, store: store, allowedTypeIDs: ["page"])

        #expect(try await fresh.snapshot().tree.pathString(for: first.objectID) == "folder / מסמך")

    }



    @Test func revokedWritesPreventNativeMutation() async throws {

        let (store, repository) = try repository([hierarchyRow("document")])

        let plan = try await repository.prepareMove(objectID: "document", parentID: nil)

        await store.revokeWrites()

        await #expect(throws: TorahAssociationRepositoryError.permissionDenied) {

            try await repository.commitPlacement(plan)

        }

        #expect(await store.countPatches() == 0)

    }



    private static let goldenJSON = #"""

[{"after":null,"before":null,"result":"PPPP"},{"after":"PPPP","before":null,"result":"PPQY"},{"after":null,"before":"PPPP","result":"PPOH"},{"after":"!!!#","before":null,"result":"!!#,"},{"after":null,"before":"!!!#","result":"!!!!~~}w"},{"after":"~~~~","before":null,"result":"~~~~!!#,"},{"after":null,"before":"~~~~","result":"~~}v"},{"after":"a0","before":null,"result":"a0!#"},{"after":null,"before":"a0","result":"`("},{"after":"PPPP!!!#","before":null,"result":"PPPP!!#,"},{"after":null,"before":"PPPP!!!#","result":"PPPO~~}x"},{"after":"!!!!~~~~","before":null,"result":"!!!#!!#+"},{"after":null,"before":"!!!!~~~~","result":"!!!!~~}v"},{"after":"PPPPPPPPPPPP","before":null,"result":"PPPPPPPPPPQY"},{"after":null,"before":"PPPPPPPPPPPP","result":"PPPPPPPPPPOH"},{"after":"PPPP","before":"PPPQ","result":"PPPPP!!#"},{"after":"!!!#","before":"!!!$","result":"!!!#P!!#"},{"after":"~~~~","before":"~~~~!!!#","result":"~~~~!!!!!!#,"},{"after":"PPPP","before":"PPPP!!!#","result":"PPPP!!!!!!#,"},{"after":"a0","before":"b0","result":"a0#,"},{"after":"PPPP!!!!!!!#","before":"PPPP!!!!!!!$","result":"PPPP!!!!!!!#P!!#"},{"after":"PPPP","before":"PPPQ","result":"PPPPP!!#"},{"after":"PPPPP!!#","before":"PPPQ","result":"PPPPP!#,"},{"after":"PPPPP!#,","before":"PPPQ","result":"PPPPP!$5"},{"after":"PPPPP!$5","before":"PPPQ","result":"PPPPP!%>"},{"after":"PPPPP!%>","before":"PPPQ","result":"PPPPP!&G"},{"after":"PPPPP!&G","before":"PPPQ","result":"PPPPP!'P"},{"after":"PPPPP!'P","before":"PPPQ","result":"PPPPP!(Y"},{"after":"PPPPP!(Y","before":"PPPQ","result":"PPPPP!)c"},{"after":"PPPPP!)c","before":"PPPQ","result":"PPPPP!*l"},{"after":"PPPPP!*l","before":"PPPQ","result":"PPPPP!+u"},{"after":"PPPPP!+u","before":"PPPQ","result":"PPPPP!,~"},{"after":"PPPPP!,~","before":"PPPQ","result":"PPPPP!.+"},{"after":"PPPPP!.+","before":"PPPQ","result":"PPPPP!/4"},{"after":"PPPPP!/4","before":"PPPQ","result":"PPPPP!0="},{"after":"PPPPP!0=","before":"PPPQ","result":"PPPPP!1F"},{"after":"PPPPP!1F","before":"PPPQ","result":"PPPPP!2O"},{"after":"PPPPP!2O","before":"PPPQ","result":"PPPPP!3X"},{"after":"PPPPP!3X","before":"PPPQ","result":"PPPPP!4b"},{"after":"PPPPP!4b","before":"PPPQ","result":"PPPPP!5k"},{"after":"PPPPP!5k","before":"PPPQ","result":"PPPPP!6t"}]

"""#

}





private actor ConditionalHierarchyFixtureStore: AnyHierarchyConditionalRecordStore {

    nonisolated let workspace = hierarchyWorkspace

    nonisolated let schema = hierarchySchema

    nonisolated let engineStartedAt: String

    let base: HierarchyFixtureStore

    var expected: [AnyJSON] = []

    var fences: [AnyConditionalPropertyFence] = []

    var unguardedCalls = 0

    var injectABA = false

    var injectSequenceChange = false

    init(_ rows: [AnyJSON], injectABA: Bool = false,

         injectSequenceChange: Bool = false, engineStartedAt: String = "run") {

        self.base = HierarchyFixtureStore(rows); self.injectABA = injectABA

        self.injectSequenceChange = injectSequenceChange

        self.engineStartedAt = engineStartedAt

    }

    func validateMembership(intent: AnyTorahTargetIntent) async throws { try await base.validateMembership(intent: intent) }

    func readRows() async throws -> [AnyJSON] { await base.readRows() }

    func readObject(objectID: String) async throws -> AnyJSON { try await base.readObject(objectID: objectID) }

    func patch(objectID: String, ownerID: String, values: [String: AnyJSON],

               authorize: @escaping @Sendable () async throws -> Void) async throws {

        unguardedCalls += 1

        throw AnyHierarchyError.incompatibleSchema

    }

    func patch(objectID: String, ownerID: String, values: [String: AnyJSON], fence: AnyConditionalPropertyFence,

               authorize: @escaping @Sendable () async throws -> Void) async throws {

        expected.append(fence.nativeVersion); fences.append(fence)

        if injectABA {

            injectABA = false

            try await base.patch(objectID: objectID, ownerID: schema.collectionID,

                                 values: [schema.positionPropertyID: .string("PPZZ")], authorize: {})

            try await base.patch(objectID: objectID, ownerID: schema.collectionID,

                                 values: [schema.positionPropertyID: .string("PPPP")], authorize: {})

        }

        if injectSequenceChange {

            injectSequenceChange = false

            try await base.receiveMembershipWithoutChangingVersion(objectID: objectID)

        }

        let current = try await base.readObject(objectID: objectID)

        guard try AnyConditionalPropertyFence(record: current, engineStartedAt: engineStartedAt) == fence else {

            throw AnyHierarchyError.stalePlan(objectID)

        }

        try await base.patch(objectID: objectID, ownerID: ownerID, values: values, authorize: authorize)

    }

    func setArchived(objectID: String, archived: Bool,

                     authorize: @escaping @Sendable () async throws -> Void) async throws {

        try await base.setArchived(objectID: objectID, archived: archived, authorize: authorize)

    }

}



extension AnyHierarchyTests {

    @Test func nativeConditionalStoreReceivesThePreparedNestedVersionWithoutFallback() async throws {

        let store = ConditionalHierarchyFixtureStore([

            hierarchyRow("folder", folder: true), hierarchyRow("document")])

        let repository = try AnyHierarchyRepository(workspace: hierarchyWorkspace, store: store, allowedTypeIDs: ["page"])

        let plan = try await repository.prepareMove(objectID: "document", parentID: "folder")

        _ = try await repository.commitPlacement(plan)

        #expect(await store.expected == [plan.expectedVersion])

        #expect(await store.unguardedCalls == 0)

        #expect(try await repository.snapshot().itemsByID["document"]?.parentID == "folder")

    }



    @Test func nativeConditionalVersionStopsABAInsideTheReadToWriteGap() async throws {

        let store = ConditionalHierarchyFixtureStore([

            hierarchyRow("folder", folder: true), hierarchyRow("document")], injectABA: true)

        let repository = try AnyHierarchyRepository(workspace: hierarchyWorkspace, store: store, allowedTypeIDs: ["page"])

        let plan = try await repository.prepareMove(objectID: "document", parentID: "folder")

        await #expect(throws: AnyHierarchyError.stalePlan("document")) {

            try await repository.commitPlacement(plan)

        }

        #expect(await store.unguardedCalls == 0)

        #expect(try await repository.snapshot().itemsByID["document"]?.parentID == nil)

        #expect(await store.base.countPatches() == 2)

    }

}

extension AnyHierarchyTests {

    @Test func persistedNativePlacementRetainsOriginalSequenceAndRun() async throws {

        let store = ConditionalHierarchyFixtureStore([

            hierarchyRow("folder", folder: true), hierarchyRow("document")])

        let repository = try AnyHierarchyRepository(workspace: hierarchyWorkspace, store: store, allowedTypeIDs: ["page"])

        let plan = try await repository.prepareMove(objectID: "document", parentID: "folder")

        let restored = try JSONDecoder().decode(AnyHierarchyPlacementPlan.self, from: JSONEncoder().encode(plan))

        #expect(restored == plan)

        #expect(restored.propertyFence?.applySequence == 1)

        #expect(restored.propertyFence?.engineStartedAt == "run")

        _ = try await repository.commitPlacement(restored)

        #expect(await store.fences == [try #require(plan.propertyFence)])

        #expect(await store.unguardedCalls == 0)

    }



    @Test func legacyNativePlacementCannotAcquireFreshFenceEvenWhenAlreadyApplied() async throws {

        let store = ConditionalHierarchyFixtureStore([

            hierarchyRow("folder", folder: true), hierarchyRow("document")])

        let repository = try AnyHierarchyRepository(workspace: hierarchyWorkspace, store: store, allowedTypeIDs: ["page"])

        let plan = try await repository.prepareMove(objectID: "document", parentID: "folder")

        _ = try await repository.commitPlacement(plan)

        var json = try #require(JSONDecoder().decode(AnyJSON.self, from: JSONEncoder().encode(plan)).object)

        json.removeValue(forKey: "propertyFence")

        let legacy = try JSONDecoder().decode(AnyHierarchyPlacementPlan.self, from: JSONEncoder().encode(AnyJSON.object(json)))

        #expect(legacy.propertyFence == nil)

        await #expect(throws: AnyHierarchyError.stalePlan("document")) {

            try await repository.commitPlacement(legacy)

        }

        #expect(await store.fences.count == 1)

        #expect(await store.unguardedCalls == 0)

    }



    @Test func persistedNativePlacementCannotRebindToAnotherEngineRun() async throws {

        let rows = [hierarchyRow("folder", folder: true), hierarchyRow("document")]

        let oldStore = ConditionalHierarchyFixtureStore(rows, engineStartedAt: "old-run")

        let oldRepository = try AnyHierarchyRepository(workspace: hierarchyWorkspace, store: oldStore, allowedTypeIDs: ["page"])

        let plan = try await oldRepository.prepareMove(objectID: "document", parentID: "folder")

        let newStore = ConditionalHierarchyFixtureStore(rows, engineStartedAt: "new-run")

        let newRepository = try AnyHierarchyRepository(workspace: hierarchyWorkspace, store: newStore, allowedTypeIDs: ["page"])

        await #expect(throws: AnyHierarchyError.stalePlan("document")) {

            try await newRepository.commitPlacement(plan)

        }

        #expect(await newStore.fences.isEmpty)

        #expect(await newStore.unguardedCalls == 0)

    }



    @Test func equalVersionWithAdvancedSequenceRefusesBeforeDispatch() async throws {

        let store = ConditionalHierarchyFixtureStore([

            hierarchyRow("folder", folder: true), hierarchyRow("document")])

        let repository = try AnyHierarchyRepository(workspace: hierarchyWorkspace, store: store, allowedTypeIDs: ["page"])

        let plan = try await repository.prepareMove(objectID: "document", parentID: "folder")

        try await store.base.receiveMembershipWithoutChangingVersion(objectID: "document")

        #expect(try await store.readObject(objectID: "document")["_ver"] == plan.expectedVersion)

        await #expect(throws: AnyHierarchyError.stalePlan("document")) {

            try await repository.commitPlacement(plan)

        }

        #expect(await store.fences.isEmpty)

        #expect(await store.base.countPatches() == 0)

    }



    @Test func capturedSequenceIsNotRefreshedInsideTheDispatchGap() async throws {

        let store = ConditionalHierarchyFixtureStore([

            hierarchyRow("folder", folder: true), hierarchyRow("document")], injectSequenceChange: true)

        let repository = try AnyHierarchyRepository(workspace: hierarchyWorkspace, store: store, allowedTypeIDs: ["page"])

        let plan = try await repository.prepareMove(objectID: "document", parentID: "folder")

        await #expect(throws: AnyHierarchyError.stalePlan("document")) {

            try await repository.commitPlacement(plan)

        }

        #expect(await store.fences == [try #require(plan.propertyFence)])

        #expect(try await store.readObject(objectID: "document")["_ver"] == plan.expectedVersion)

        #expect(try await store.readObject(objectID: "document")["_applySeq"] == .integer(2))

        #expect(await store.base.countPatches() == 0)

    }



    @Test func nativePlanCannotDowngradeToGenericPropertyWrites() async throws {

        let rows = [hierarchyRow("folder", folder: true), hierarchyRow("document")]

        let native = ConditionalHierarchyFixtureStore(rows)

        let nativeRepository = try AnyHierarchyRepository(workspace: hierarchyWorkspace, store: native, allowedTypeIDs: ["page"])

        let plan = try await nativeRepository.prepareMove(objectID: "document", parentID: "folder")

        let generic = HierarchyFixtureStore(rows)

        let genericRepository = try AnyHierarchyRepository(workspace: hierarchyWorkspace, store: generic, allowedTypeIDs: ["page"])

        await #expect(throws: AnyHierarchyError.incompatibleSchema) {

            try await genericRepository.commitPlacement(plan)

        }

        #expect(await generic.countPatches() == 0)

        #expect(try await genericRepository.prepareMove(objectID: "document", parentID: "folder").propertyFence == nil)

    }



    @Test func nativeRenamePassesOriginalSequenceAndRun() async throws {

        let store = ConditionalHierarchyFixtureStore([hierarchyRow("document")])

        let repository = try AnyHierarchyRepository(workspace: hierarchyWorkspace, store: store, allowedTypeIDs: ["page"])

        _ = try await repository.rename(objectID: "document", expectedTitle: "document", newTitle: "renamed")

        #expect(await store.fences.count == 1)

        #expect(await store.fences.first?.applySequence == 1)

        #expect(await store.fences.first?.engineStartedAt == "run")

        #expect(await store.unguardedCalls == 0)

    }

}




private enum HierarchyCreationQueueTestError: Error { case boundaryNotReached }

private func hierarchyCreationSignal(_ stream: AsyncStream<Void>) async throws {
    try await withThrowingTaskGroup(of: Bool.self) { group in
        group.addTask {
            var iterator = stream.makeAsyncIterator()
            return await iterator.next() != nil
        }
        group.addTask {
            try await Task.sleep(for: .seconds(5))
            return false
        }
        defer { group.cancelAll() }
        let signalled = try await group.next()
        try Task.checkCancellation()
        guard signalled == true else { throw HierarchyCreationQueueTestError.boundaryNotReached }
    }
}

/// Uses the existing explicit native-API dependency fixture. No HTTP, Native
/// process, permission bypass or second production queue is involved.
private struct HierarchyObservedCreator: AnyHierarchyObjectCreating {
    let scope: AnyTorahWorkspace
    let store: HierarchyFixtureStore
    let workspaceRead: AsyncStream<Void>.Continuation
    var workspace: AnyTorahWorkspace { workspaceRead.yield(()); return scope }

    func ensureHierarchyObject(plan: AnyHierarchyCreationPlan,
                               authorize: @escaping @Sendable () async throws -> Void) async throws -> String {
        try await store.ensureHierarchyObject(plan: plan, authorize: authorize)
    }
}

private struct HierarchyHeldCreator: AnyHierarchyObjectCreating {
    let workspace: AnyTorahWorkspace
    let store: HierarchyFixtureStore
    let entered: AsyncStream<Void>.Continuation
    let release: AsyncStream<Void>

    func ensureHierarchyObject(plan: AnyHierarchyCreationPlan,
                               authorize: @escaping @Sendable () async throws -> Void) async throws -> String {
        entered.yield(())
        try await hierarchyCreationSignal(release)
        try Task.checkCancellation()
        return try await store.ensureHierarchyObject(plan: plan, authorize: authorize)
    }
}

extension AnyHierarchyTests {
    @Test func creationOverrideRejectsAnotherWorkspaceBeforeDispatch() async throws {
        let (store, repository) = try repository([])
        let plan = try await repository.prepareCreation(typeID: "page", title: "", kind: .writingDocument)
        let observed = AsyncStream<Void>.makeStream(bufferingPolicy: .bufferingNewest(2))
        defer { observed.continuation.finish() }
        let foreign = HierarchyObservedCreator(
            scope: try AnyTorahWorkspace(accountID: "account", spaceID: "foreign"),
            store: store, workspaceRead: observed.continuation)
        await #expect(throws: AnyHierarchyError.incompatibleSchema) {
            try await repository.create(plan, using: foreign)
        }
        #expect(await store.countCreated() == 0)
        let ordinary = try await repository.create(plan)
        #expect(ordinary.title.isEmpty)
        #expect(await store.countCreated() == 1)
    }

    @Test func creationOverrideAndDefaultCreatorShareTheExistingMutationQueue() async throws {
        let store = HierarchyFixtureStore([])
        let defaultRead = AsyncStream<Void>.makeStream(bufferingPolicy: .bufferingNewest(2))
        let entered = AsyncStream<Void>.makeStream(bufferingPolicy: .bufferingNewest(1))
        let release = AsyncStream<Void>.makeStream(bufferingPolicy: .bufferingNewest(1))
        defer {
            defaultRead.continuation.finish(); entered.continuation.finish(); release.continuation.finish()
        }
        let ordinary = HierarchyObservedCreator(scope: hierarchyWorkspace, store: store,
                                                workspaceRead: defaultRead.continuation)
        let repository = try AnyHierarchyRepository(workspace: hierarchyWorkspace, store: store,
                                                     creator: ordinary, allowedTypeIDs: ["page"])
        // Consume the original constructor's workspace check before observing
        // the second create call's new selected-creator check.
        try await hierarchyCreationSignal(defaultRead.stream)
        let first = try await repository.prepareCreation(typeID: "page", title: "first", kind: .writingDocument)
        let second = try await repository.prepareCreation(typeID: "page", title: "second", kind: .writingDocument)
        let held = HierarchyHeldCreator(workspace: hierarchyWorkspace, store: store,
                                       entered: entered.continuation, release: release.stream)
        let (completed, handoffError) = await withTaskGroup(of: Result<AnyHierarchyItem, Error>.self) { group in
            var handoffError: Error?
            group.addTask {
                do { return .success(try await repository.create(first, using: held)) }
                catch { return .failure(error) }
            }
            do {
                try await hierarchyCreationSignal(entered.stream)
                group.addTask {
                    do { return .success(try await repository.create(second)) }
                    catch { return .failure(error) }
                }
                // The getter proves entry, not serial admission. Cancellation
                // must prevent dispatch even if the second call is scheduled late.
                try await hierarchyCreationSignal(defaultRead.stream)
            } catch { handoffError = error }
            group.cancelAll()
            release.continuation.finish()
            var completed: [Result<AnyHierarchyItem, Error>] = []
            for await outcome in group { completed.append(outcome) }
            return (completed, handoffError)
        }
        if let handoffError { throw handoffError }
        #expect(completed.count == 2)
        for outcome in completed {
            switch outcome {
            case .success:
                Issue.record("A canceled creation dispatched past the existing mutation queue")
            case .failure(let error):
                #expect(error is CancellationError)
            }
        }
        #expect(await store.countCreated() == 0)
        let recovered = try await repository.create(second)
        #expect(recovered.objectID == "created-1" && recovered.title == "second")
        #expect(await store.countCreated() == 1)
    }
}
