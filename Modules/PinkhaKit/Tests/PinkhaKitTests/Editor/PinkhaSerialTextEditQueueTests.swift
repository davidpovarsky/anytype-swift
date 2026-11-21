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

    @Test("Mandatory commands preserve the latest full text on both sides of the barrier")
    func mandatoryWritePreservesBothCoalescingSegments() async throws {
        let queue = PinkhaSerialTextEditQueue()
        let gate = TextEditTestGate()
        var writes = [String]()
        queue.enqueue { writes.append("in flight"); await gate.pause(); return true }
        await gate.waitUntilPaused()
        queue.enqueue { writes.append("obsolete before"); return true }
        queue.enqueue { writes.append("latest before"); return true }
        queue.enqueue(mode: .mandatory) { writes.append("command"); return true }
        queue.enqueue { writes.append("obsolete after"); return true }
        queue.enqueue { writes.append("latest after"); return true }
        gate.resume()
        try await queue.drain()
        #expect(writes == ["in flight", "latest before", "command", "latest after"])
        #expect(!queue.hasPendingChanges)
    }

    @Test("Consecutive mandatory commands cannot be cancelled by a later full-text draft")
    func consecutiveMandatoryWritesCannotBeCoalesced() async throws {
        let queue = PinkhaSerialTextEditQueue()
        let gate = TextEditTestGate()
        var writes = [String]()
        queue.enqueue { writes.append("in flight"); await gate.pause(); return true }
        await gate.waitUntilPaused()
        queue.enqueue(mode: .mandatory) { writes.append("first command"); return true }
        queue.enqueue(mode: .mandatory) { writes.append("second command"); return true }
        queue.enqueue { writes.append("later text"); return true }
        gate.resume()
        try await queue.drain()
        #expect(writes == ["in flight", "first command", "second command", "later text"])
        #expect(!queue.hasPendingChanges)
    }

    @Test("A rejected mandatory command is reported and cannot acknowledge a later draft")
    func failedMandatoryWriteDoesNotAcknowledgeLaterDraft() async throws {
        let queue = PinkhaSerialTextEditQueue()
        let commandGate = TextEditTestGate()
        let laterGate = TextEditTestGate()
        var attempts = [String]()
        let command = queue.enqueue(mode: .mandatory) {
            attempts.append("command")
            await commandGate.pause()
            throw TextEditTestError.denied
        }
        await commandGate.waitUntilPaused()
        queue.enqueue {
            attempts.append("later text")
            await laterGate.pause()
            return true
        }
        commandGate.resume()
        do { try await command.value; Issue.record("Expected the command failure") }
        catch TextEditTestError.denied {}
        catch { Issue.record("Unexpected error: \(error)") }
        await laterGate.waitUntilPaused()
        #expect(queue.hasPendingChanges)
        #expect(attempts == ["command", "later text"])
        laterGate.resume()
        try await queue.drain()
        #expect(!queue.hasPendingChanges)
        #expect(attempts == ["command", "later text"], "A structural mutation is never retried implicitly")
    }

    @Test("An identity reset retires a mandatory command that has not reached native code")
    func identityResetRetiresUndispatchedMandatoryWrite() async throws {
        let queue = PinkhaSerialTextEditQueue()
        let gate = TextEditTestGate()
        var writes = [String]()
        queue.enqueue { writes.append("old in flight"); await gate.pause(); return true }
        await gate.waitUntilPaused()
        queue.enqueue(mode: .mandatory) { writes.append("retired command"); return true }
        queue.resetOwnership()
        queue.enqueue { writes.append("new owner"); return true }
        gate.resume()
        try await queue.drain()
        #expect(writes == ["old in flight", "new owner"])
        #expect(!queue.hasPendingChanges)
    }

    @Test("Resetting an in-flight mandatory command neither overlaps nor acknowledges the new owner")
    func identityResetWaitsForDispatchedMandatoryWrite() async throws {
        let queue = PinkhaSerialTextEditQueue()
        let oldGate = TextEditTestGate()
        let newGate = TextEditTestGate()
        var writes = [String]()
        var concurrent = 0
        var maximumConcurrent = 0
        queue.enqueue(mode: .mandatory) {
            concurrent += 1
            maximumConcurrent = max(maximumConcurrent, concurrent)
            writes.append("old command")
            await oldGate.pause()
            concurrent -= 1
            return true
        }
        await oldGate.waitUntilPaused()
        queue.resetOwnership()
        queue.enqueue {
            concurrent += 1
            maximumConcurrent = max(maximumConcurrent, concurrent)
            writes.append("new owner")
            await newGate.pause()
            concurrent -= 1
            return true
        }
        oldGate.resume()
        await newGate.waitUntilPaused()
        #expect(queue.hasPendingChanges)
        #expect(writes == ["old command", "new owner"])
        #expect(maximumConcurrent == 1)
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
