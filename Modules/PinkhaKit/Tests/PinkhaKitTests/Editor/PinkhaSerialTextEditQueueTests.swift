import Testing
@testable import PinkhaKit

@Suite("Serial native text writes", .serialized)
@MainActor
struct PinkhaSerialTextEditQueueTests {
    @Test("A delayed native fork serializes writes and carries only the latest queued text")
    func delayedFirstWriteCoalescesNewerInput() async throws {
        let queue = PinkhaSerialTextEditQueue()
        let gate = TextEditTestGate()
        var writes = [String]()
        var concurrent = 0
        var maximumConcurrent = 0
        let first = queue.enqueue {
            concurrent += 1; maximumConcurrent = max(maximumConcurrent, concurrent)
            writes.append("W")
            await gate.pause()
            concurrent -= 1
            return true
        }
        await gate.waitUntilPaused()
        queue.enqueue { writes.append("Wave15"); return true }
        queue.enqueue {
            concurrent += 1; maximumConcurrent = max(maximumConcurrent, concurrent)
            writes.append("Wave15 drop anchor")
            concurrent -= 1
            return true
        }
        #expect(queue.hasPendingChanges)
        #expect(writes == ["W"])
        gate.resume()
        try await first.value
        try await queue.drain()
        #expect(writes == ["W", "Wave15 drop anchor"])
        #expect(maximumConcurrent == 1)
        #expect(!queue.hasPendingChanges)
    }

    @Test("Failure preserves dirty ownership and a later user correction can save")
    func failedWriteDoesNotAcknowledgeText() async throws {
        let queue = PinkhaSerialTextEditQueue()
        let failed = queue.enqueue { throw TextEditTestError.denied }
        do { try await failed.value; Issue.record("Expected native failure") }
        catch TextEditTestError.denied {}
        catch { Issue.record("Unexpected error: \(error)") }
        #expect(queue.hasPendingChanges)
        var attempts = 0
        queue.enqueue { attempts += 1; return true }
        try await queue.drain()
        #expect(attempts == 1, "No implicit retry of the failed native request")
        #expect(!queue.hasPendingChanges)
    }

    @Test("A deferred composition remains dirty until its explicit commit")
    func deferredEditWaitsForCommit() async throws {
        let queue = PinkhaSerialTextEditQueue()
        try await queue.enqueue { false }.value
        #expect(queue.hasPendingChanges)
        try await queue.enqueue { true }.value
        #expect(!queue.hasPendingChanges)
    }

    @Test("Identity reset drops queued old edits and waits for the dispatched request")
    func identityResetDoesNotOverlapOrAcknowledgeNewOwner() async throws {
        let queue = PinkhaSerialTextEditQueue()
        let oldGate = TextEditTestGate()
        let newGate = TextEditTestGate()
        var writes = [String]()
        queue.enqueue { writes.append("old in flight"); await oldGate.pause(); return true }
        await oldGate.waitUntilPaused()
        queue.enqueue { writes.append("obsolete queued"); return true }
        queue.resetOwnership()
        #expect(!queue.hasPendingChanges)
        queue.enqueue { writes.append("new owner"); await newGate.pause(); return true }
        #expect(queue.hasPendingChanges)
        #expect(writes == ["old in flight"])
        oldGate.resume()
        await newGate.waitUntilPaused()
        #expect(queue.hasPendingChanges, "The old receipt must not acknowledge the new draft")
        #expect(writes == ["old in flight", "new owner"])
        newGate.resume()
        try await queue.drain()
        #expect(!queue.hasPendingChanges)
    }
}

private enum TextEditTestError: Error { case denied }

@MainActor
private final class TextEditTestGate {
    private var paused: CheckedContinuation<Void, Never>?
    private var arrival: CheckedContinuation<Void, Never>?

    func pause() async {
        await withCheckedContinuation { continuation in
            paused = continuation
            arrival?.resume()
            arrival = nil
        }
    }

    func waitUntilPaused() async {
        if paused != nil { return }
        await withCheckedContinuation { arrival = $0 }
    }

    func resume() {
        paused?.resume()
        paused = nil
    }
}
