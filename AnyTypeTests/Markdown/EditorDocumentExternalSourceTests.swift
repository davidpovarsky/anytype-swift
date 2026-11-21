import Foundation
import Testing
@testable import Anytype

@MainActor
struct EditorDocumentExternalSourceTests {
    @Test
    func sourceMismatchRefusesDispatchAndCannotBeRevived() async throws {
        var current = true
        let probe = ExternalSourceWriteProbe()
        let owner = try makeOwner(source: .init(lifetime: .init(), isCurrent: { current }))
        current = false
        let first = await failure {
            try await owner.performMutation(contextId: "owned") { await probe.write() }
        }
        current = true
        let second = await failure {
            try await owner.performMutation(contextId: "owned") { await probe.write() }
        }
        #expect(first == .rejected(.documentChanged))
        #expect(second == .rejected(.retired))
        #expect(await probe.count == 0)
    }

    @Test
    func sourceRetirementKeepsTheActualAdmittedWriteAndDrainsOnce() async throws {
        let lifetime = EditorDocumentWriteLifetime()
        let probe = ExternalSourceWriteProbe(hold: true)
        var drained = 0
        let owner = try makeOwner(
            source: .init(lifetime: lifetime, isCurrent: { true }), onDrained: { drained += 1 }
        )
        let operation = Task {
            await failure {
                try await owner.performMutation(contextId: "owned") { await probe.write() }
            }
        }
        await probe.waitForEntry()
        lifetime.markUnavailable()
        #expect(owner.isRetired)
        #expect(owner.pendingOperationCount == 1)
        #expect(drained == 0)
        await probe.release()
        #expect(await operation.value == .completedWithoutOwnership(.retired))
        #expect(await probe.count == 1)
        #expect(owner.isDrained)
        #expect(drained == 1)
    }

    @Test
    func sourceRevisionIsRecheckedAfterOriginalReadCompletes() async throws {
        var current = true
        let probe = ExternalSourceWriteProbe(hold: true)
        let owner = try makeOwner(source: .init(lifetime: .init(), isCurrent: { current }))
        let operation = Task {
            await failure {
                _ = try await owner.performRead(contextId: "owned", spaceId: "owned-space") {
                    await probe.write()
                    return Data([1, 2, 3])
                }
            }
        }
        await probe.waitForEntry()
        current = false
        await probe.release()
        #expect(await operation.value == .completedWithoutOwnership(.documentChanged))
        #expect(await probe.count == 1)
        #expect(owner.isRetired && owner.isDrained)
    }

    @Test
    func retiringOneSourceDoesNotRetireAnotherOwner() async throws {
        let firstLifetime = EditorDocumentWriteLifetime()
        let first = try makeOwner(source: .init(lifetime: firstLifetime, isCurrent: { true }))
        let second = try makeOwner(source: .init(lifetime: .init(), isCurrent: { true }))
        let probe = ExternalSourceWriteProbe()
        firstLifetime.markUnavailable()
        let firstFailure = await failure {
            try await first.performMutation(contextId: "owned") { await probe.write() }
        }
        try await second.performMutation(contextId: "owned") { await probe.write() }
        #expect(firstFailure == .rejected(.retired))
        #expect(await probe.count == 1)
        #expect(!second.isRetired && second.isDrained)
    }

    private func makeOwner(
        source: EditorDocumentWriteSourceBinding,
        onDrained: (@MainActor () -> Void)? = nil
    ) throws -> EditorDocumentWriteOwner {
        let document = MockBaseDocument(objectId: "owned", details: nil)
        document.mockSpaceId = "owned-space"
        document.mockMode = .handling
        document.mockPermissions.canEditBlocks = true
        return try EditorDocumentWriteOwner(
            data: .init(objectId: document.objectId, spaceId: document.spaceId, mode: document.mode),
            document: document, sourceBinding: source, onDrained: onDrained
        )
    }

    private func failure(_ body: () async throws -> Void) async -> EditorDocumentWriteError? {
        do { try await body(); return nil }
        catch { return error as? EditorDocumentWriteError }
    }
}

private actor ExternalSourceWriteProbe {
    private(set) var count = 0
    private var entered = false
    private var released: Bool
    private var entryWaiters: [CheckedContinuation<Void, Never>] = []
    private var releaseWaiters: [CheckedContinuation<Void, Never>] = []

    init(hold: Bool = false) { released = !hold }

    func write() async {
        entered = true
        let waiters = entryWaiters
        entryWaiters.removeAll()
        for waiter in waiters { waiter.resume() }
        if !released { await withCheckedContinuation { releaseWaiters.append($0) } }
        count += 1
    }

    func waitForEntry() async {
        if !entered { await withCheckedContinuation { entryWaiters.append($0) } }
    }

    func release() {
        released = true
        let waiters = releaseWaiters
        releaseWaiters.removeAll()
        for waiter in waiters { waiter.resume() }
    }
}
