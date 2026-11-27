
// These controlled-store regressions exercise the unchanged repository rename
// operation and its original conditional-store dependency. They are not Native,
// mounted UI, HTTP, account, or whole-application acceptance.
private enum HierarchyRawTitleExample: String, CaseIterable, Sendable {
    case latin, hebrew

    var original: String {
        switch self {
        case .latin: "Title caf\u{00E9}"
        case .hebrew: "Title \u{05E9}\u{05B8}\u{05C1}"
        }
    }

    var requested: String {
        switch self {
        case .latin: "Title cafe\u{0301}"
        case .hebrew: "Title \u{05E9}\u{05C1}\u{05B8}"
        }
    }
}

/// A controlled server-side normalization outcome. The original conditional
/// fixture still validates the captured native fence and current membership,
/// performs the actual modeled patch, and supplies the subsequent readback.
private actor HierarchyRawTitleReadbackStore: AnyHierarchyConditionalRecordStore {
    nonisolated let workspace = hierarchyWorkspace
    nonisolated let schema = hierarchySchema
    nonisolated let engineStartedAt = "run"
    private let base: ConditionalHierarchyFixtureStore
    private let storedTitle: String
    private let losesReply: Bool
    private var requestedTitles: [String] = []

    init(storedTitle: String, losesReply: Bool) {
        self.base = ConditionalHierarchyFixtureStore([hierarchyRow("document", title: "Old")])
        self.storedTitle = storedTitle
        self.losesReply = losesReply
    }

    func validateMembership(intent: AnyTorahTargetIntent) async throws {
        try await base.validateMembership(intent: intent)
    }

    func readRows() async throws -> [AnyJSON] { try await base.readRows() }

    func readObject(objectID: String) async throws -> AnyJSON {
        try await base.readObject(objectID: objectID)
    }

    func patch(objectID: String, ownerID: String, values: [String: AnyJSON],
               authorize: @escaping @Sendable () async throws -> Void) async throws {
        throw AnyHierarchyError.incompatibleSchema
    }

    func patch(objectID: String, ownerID: String, values: [String: AnyJSON],
               fence: AnyConditionalPropertyFence,
               authorize: @escaping @Sendable () async throws -> Void) async throws {
        guard objectID == "document", ownerID == "any", values.count == 1,
              let requested = values["name"]?.string else {
            throw AnyHierarchyError.incompatibleSchema
        }
        requestedTitles.append(requested)
        var committed = values
        committed["name"] = .string(storedTitle)
        try await base.patch(objectID: objectID, ownerID: ownerID, values: committed,
                             fence: fence, authorize: authorize)
        if losesReply { throw AnyEngineError.writeUncertain }
    }

    func setArchived(objectID: String, archived: Bool,
                     authorize: @escaping @Sendable () async throws -> Void) async throws {
        try await base.setArchived(objectID: objectID, archived: archived, authorize: authorize)
    }

    func recordedRequests() -> [String] { requestedTitles }
    func countPatches() async -> Int { await base.base.countPatches() }
}

@Suite("Hierarchy rename preserves exact requested title bytes")
private struct AnyHierarchyRawTitleTests {
    @Test(arguments: HierarchyRawTitleExample.allCases)
    func canonicallyEquivalentRequestedRenameReachesTheOriginalStore(
        _ example: HierarchyRawTitleExample
    ) async throws {
        #expect(example.original == example.requested)
        #expect(Array(example.original.utf8) != Array(example.requested.utf8))
        let store = ConditionalHierarchyFixtureStore([
            hierarchyRow("document", title: example.original)
        ])
        let repository = try AnyHierarchyRepository(
            workspace: hierarchyWorkspace, store: store, allowedTypeIDs: ["page"])
        let result = try await repository.rename(
            objectID: "document", expectedTitle: example.original, newTitle: example.requested)
        #expect(result.objectID == "document")
        #expect(Array(result.title.utf8) == Array(example.requested.utf8))
        let row = try await store.readObject(objectID: "document")
        let stored = try #require(row["any"]?["name"]?.string)
        #expect(Array(stored.utf8) == Array(example.requested.utf8))
        let patchCount = await store.base.countPatches()
        let fences = await store.fences
        let unguarded = await store.unguardedCalls
        #expect(patchCount == 1)
        #expect(fences.count == 1)
        #expect(fences.first?.applySequence == 1)
        #expect(fences.first?.engineStartedAt == "run")
        #expect(unguarded == 0)

        // A byte-identical already-completed retry still succeeds without a
        // second dispatch, even though the original expected title is now old.
        let retry = try await repository.rename(
            objectID: "document", expectedTitle: example.original, newTitle: example.requested)
        let afterRetry = await store.base.countPatches()
        #expect(Array(retry.title.utf8) == Array(example.requested.utf8))
        #expect(afterRetry == 1)
    }

    @Test(arguments: HierarchyRawTitleExample.allCases)
    func canonicallyEquivalentStaleExpectedTitleRefusesBeforeDispatch(
        _ example: HierarchyRawTitleExample
    ) async throws {
        #expect(example.original == example.requested)
        #expect(Array(example.original.utf8) != Array(example.requested.utf8))
        let store = ConditionalHierarchyFixtureStore([
            hierarchyRow("document", title: example.original)
        ])
        let repository = try AnyHierarchyRepository(
            workspace: hierarchyWorkspace, store: store, allowedTypeIDs: ["page"])
        await #expect(throws: AnyHierarchyError.stalePlan("document")) {
            try await repository.rename(
                objectID: "document", expectedTitle: example.requested, newTitle: "Replacement")
        }
        let patchCount = await store.base.countPatches()
        let fences = await store.fences
        let row = try await store.readObject(objectID: "document")
        let stored = try #require(row["any"]?["name"]?.string)
        #expect(patchCount == 0)
        #expect(fences.isEmpty)
        #expect(Array(stored.utf8) == Array(example.original.utf8))
    }

    @Test(arguments: HierarchyRawTitleExample.allCases)
    func canonicallyEquivalentSuccessfulReadbackCannotCertifyRename(
        _ example: HierarchyRawTitleExample
    ) async throws {
        #expect(example.original == example.requested)
        #expect(Array(example.original.utf8) != Array(example.requested.utf8))
        let store = HierarchyRawTitleReadbackStore(storedTitle: example.original, losesReply: false)
        let repository = try AnyHierarchyRepository(
            workspace: hierarchyWorkspace, store: store, allowedTypeIDs: ["page"])
        await #expect(throws: AnyHierarchyError.incompleteWrite("document")) {
            try await repository.rename(
                objectID: "document", expectedTitle: "Old", newTitle: example.requested)
        }
        let requests = await store.recordedRequests()
        let patchCount = await store.countPatches()
        let row = try await store.readObject(objectID: "document")
        let stored = try #require(row["any"]?["name"]?.string)
        #expect(requests.map { Array($0.utf8) } == [Array(example.requested.utf8)])
        #expect(patchCount == 1)
        #expect(Array(stored.utf8) == Array(example.original.utf8))
    }

    @Test(arguments: HierarchyRawTitleExample.allCases)
    func canonicallyEquivalentReadbackPreservesTheOriginalWriteError(
        _ example: HierarchyRawTitleExample
    ) async throws {
        #expect(example.original == example.requested)
        #expect(Array(example.original.utf8) != Array(example.requested.utf8))
        let store = HierarchyRawTitleReadbackStore(storedTitle: example.original, losesReply: true)
        let repository = try AnyHierarchyRepository(
            workspace: hierarchyWorkspace, store: store, allowedTypeIDs: ["page"])
        await #expect(throws: AnyEngineError.writeUncertain) {
            try await repository.rename(
                objectID: "document", expectedTitle: "Old", newTitle: example.requested)
        }
        let requests = await store.recordedRequests()
        let patchCount = await store.countPatches()
        let row = try await store.readObject(objectID: "document")
        let stored = try #require(row["any"]?["name"]?.string)
        #expect(requests.map { Array($0.utf8) } == [Array(example.requested.utf8)])
        #expect(patchCount == 1)
        #expect(Array(stored.utf8) == Array(example.original.utf8))
    }
}
