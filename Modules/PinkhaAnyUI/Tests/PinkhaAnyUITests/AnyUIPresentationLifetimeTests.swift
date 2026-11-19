import Foundation
import Testing
import PinkhaAnyHost
@testable import PinkhaAnyUI

private actor LifetimeDrainGate {
    private var continuation: CheckedContinuation<Void, Never>?
    private var enteredWaiters: [CheckedContinuation<Void, Never>] = []
    func wait() async {
        await withCheckedContinuation { continuation in
            self.continuation = continuation
            for waiter in enteredWaiters { waiter.resume() }
            enteredWaiters = []
        }
    }
    func entered() async {
        if continuation != nil { return }
        await withCheckedContinuation { enteredWaiters.append($0) }
    }
    func release() { continuation?.resume(); continuation = nil }
}

@MainActor @Suite("Mounted native UI lifetime")
struct AnyUIPresentationLifetimeTests {
    @Test func revocationIsSynchronousAndOneWayBeforeAnyDrainSuspension() throws {
        let lifetime = AnyUIPresentationLifetime()
        var observed = false
        try lifetime.register(revoke: { observed = !lifetime.isActive }, drain: {})
        lifetime.revoke()
        #expect(observed)
        #expect(throws: AnyHostError.sessionClosed) { try lifetime.requireActive() }
        #expect(throws: AnyHostError.sessionClosed) { try lifetime.register(revoke: {}, drain: {}) }
    }

    @Test func concurrentDrainersWaitForTheSameOriginalCloseTask() async throws {
        let lifetime = AnyUIPresentationLifetime(), gate = LifetimeDrainGate()
        var starts = 0, completions = 0
        try lifetime.register(revoke: {}, drain: { starts += 1; await gate.wait(); completions += 1 })
        let first = Task { await lifetime.drain() }
        await gate.entered()
        let second = Task { await lifetime.drain() }
        #expect(starts == 1 && completions == 0)
        await gate.release()
        await first.value; await second.value
        #expect(starts == 1 && completions == 1)
    }

    @Test func unregisteredPresentationIsNotRevokedAgainByWorkspace() async throws {
        let lifetime = AnyUIPresentationLifetime()
        var calls = 0
        let token = try lifetime.register(revoke: { calls += 1 }, drain: { calls += 10 })
        lifetime.unregister(token)
        await lifetime.drain()
        #expect(calls == 0)
    }

    @Test func reentrantAndRepeatedRevokeCannotRepeatCallbacks() async throws {
        let lifetime = AnyUIPresentationLifetime()
        var calls = 0
        try lifetime.register(revoke: { calls += 1; lifetime.revoke() }, drain: {})
        lifetime.revoke(); lifetime.revoke()
        await lifetime.drain(); await lifetime.drain()
        #expect(calls == 1)
    }
}
