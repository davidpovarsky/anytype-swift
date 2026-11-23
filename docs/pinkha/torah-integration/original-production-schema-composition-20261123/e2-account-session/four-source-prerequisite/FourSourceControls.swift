
private enum ControlFailure: Error { case failed(String) }

private final class Checks {
    var count = 0
    func require(_ value: Bool, _ reason: String) throws {
        count += 1
        if !value { throw ControlFailure.failed(reason) }
    }
    func retired(_ operation: () throws -> Void) throws {
        count += 1
        do { try operation() }
        catch EditorDocumentWriteError.rejected(.retired) { return }
        throw ControlFailure.failed("Expected original retired rejection")
    }
}

private final class Flag: @unchecked Sendable {
    private let lock = NSLock()
    private var value = false
    func set() { lock.lock(); value = true; lock.unlock() }
    func read() -> Bool { lock.lock(); defer { lock.unlock() }; return value }
}

// Test-only read observations. Original implementation text is not rewritten.
private extension OriginalEventDeliveryFence {
    func controlSnapshot() -> (accepted: UInt64, delivered: UInt64, waiters: Int, failed: Bool) {
        lock.lock(); defer { lock.unlock() }
        return (accepted, delivered, waiters.count, failure != nil)
    }
}
private extension EditorDocumentWriteLifetime {
    func controlSnapshot() -> (admitted: Int, waiting: Int) {
        lock.lock(); defer { lock.unlock() }
        return (admittedOperations.count, drainWaiters.count)
    }
}

private func until(_ predicate: @Sendable () -> Bool) async throws {
    let limit = ContinuousClock.now.advanced(by: .seconds(5))
    while !predicate() {
        if ContinuousClock.now >= limit { throw ControlFailure.failed("Bounded state handshake did not arrive") }
        await Task.yield()
    }
}

private actor HeldSink {
    private var entered = 0
    private var released = 0
    private var held: [(Int, CheckedContinuation<Void, Never>)] = []
    private var enteredWaiters: [(Int, CheckedContinuation<Void, Never>)] = []
    private var completed: [Int] = []
    func receive(_ data: Data) async {
        entered += 1
        let ordinal = entered
        let ready = enteredWaiters.filter { $0.0 <= entered }
        enteredWaiters.removeAll { $0.0 <= entered }
        for row in ready { row.1.resume() }
        if ordinal > released {
            await withCheckedContinuation { held.append((ordinal, $0)) }
        }
        completed.append(Int(String(decoding: data, as: UTF8.self))!)
    }
    func waitForEntered(_ count: Int) async {
        if entered >= count { return }
        await withCheckedContinuation { enteredWaiters.append((count, $0)) }
    }
    func releaseThrough(_ count: Int) {
        released = max(released, count)
        let ready = held.filter { $0.0 <= released }
        held.removeAll { $0.0 <= released }
        for row in ready { row.1.resume() }
    }
    func values() -> [Int] { completed }
}

private struct FIFOFixture {
    let fence: OriginalEventDeliveryFence
    let continuation: AsyncStream<Data>.Continuation
    let sink: HeldSink
    let consumer: Task<Void, Never>
    init() {
        let fence = OriginalEventDeliveryFence()
        let (stream, continuation) = AsyncStream.makeStream(of: Data.self)
        let sink = HeldSink()
        self.fence = fence; self.continuation = continuation; self.sink = sink
        // Foundation transport harness only. The actual Lib decoder and event
        // handlers are not present or claimed to have executed here.
        consumer = Task {
            defer { fence.end() }
            for await data in stream {
                defer { fence.didDeliverOne() }
                await sink.receive(data)
            }
        }
    }
    func enqueue(_ value: Int) { fence.enqueue(Data(String(value).utf8), into: continuation) }
    func finish() async { continuation.finish(); await consumer.value }
}

@main private struct FourSourceControls {
    static func main() async throws {
        guard CommandLine.arguments.count == 2 else { throw ControlFailure.failed("One case required") }
        let name = CommandLine.arguments[1]
        let checks = Checks()
        switch name {
        case "fifo-empty-frontier":
            let fence = OriginalEventDeliveryFence()
            try await fence.waitForCurrentFrontier()
            let state = fence.controlSnapshot()
            try checks.require(state.accepted == 0 && state.delivered == 0 && state.waiters == 0 && !state.failed, "Empty frontier")
        case "fifo-held-and-frozen-frontiers":
            let fixture = FIFOFixture()
            fixture.enqueue(1)
            await fixture.sink.waitForEntered(1)
            let firstDone = Flag(), secondDone = Flag()
            let first = Task { try await fixture.fence.waitForCurrentFrontier(); firstDone.set() }
            try await until { fixture.fence.controlSnapshot().waiters == 1 }
            fixture.enqueue(2)
            let second = Task { try await fixture.fence.waitForCurrentFrontier(); secondDone.set() }
            try await until { fixture.fence.controlSnapshot().waiters == 2 }
            try checks.require(!firstDone.read() && !secondDone.read(), "Accepted is not delivered")
            try checks.require(fixture.fence.controlSnapshot().delivered == 0, "Handler has not returned")
            await fixture.sink.releaseThrough(1)
            try await first.value
            await fixture.sink.waitForEntered(2)
            try checks.require(firstDone.read() && !secondDone.read(), "Later event cannot extend first captured frontier")
            try checks.require(fixture.fence.controlSnapshot().delivered == 1, "Second handler is still held")
            await fixture.sink.releaseThrough(2)
            try await second.value
            try checks.require(await fixture.sink.values() == [1, 2], "Actual one-consumer delivery order")
            try checks.require(fixture.fence.controlSnapshot().delivered == 2, "Both handlers returned")
            await fixture.finish()
        case "fifo-canceled-waiter-retained":
            let fixture = FIFOFixture()
            fixture.enqueue(7); await fixture.sink.waitForEntered(1)
            let ended = Flag()
            let waiter = Task {
                do {
                    try await fixture.fence.waitForCurrentFrontier()
                    // Exact public adapter's post-wait cancellation check.
                    try Task.checkCancellation()
                    ended.set(); return false
                } catch is CancellationError { ended.set(); return true }
            }
            try await until { fixture.fence.controlSnapshot().waiters == 1 }
            waiter.cancel()
            try checks.require(!ended.read() && fixture.fence.controlSnapshot().waiters == 1, "Cancel cannot erase held delivery")
            try checks.require(fixture.fence.controlSnapshot().delivered == 0, "No native/handler completion inferred")
            await fixture.sink.releaseThrough(1)
            try checks.require(try await waiter.value, "Canceled caller rejects only after actual frontier")
            try checks.require(await fixture.sink.values() == [7], "Cancellation did not cancel underlying handler")
            await fixture.finish()
        case "fifo-end-rejects-unresolved":
            let fence = OriginalEventDeliveryFence()
            let (stream, continuation) = AsyncStream.makeStream(of: Data.self)
            fence.enqueue(Data("1".utf8), into: continuation)
            let waiter = Task {
                do { try await fence.waitForCurrentFrontier(); return false }
                catch OriginalEventDeliveryFence.Failure.ended { return true }
            }
            try await until { fence.controlSnapshot().waiters == 1 }
            fence.end()
            try checks.require(try await waiter.value, "Actual consumer-end hook rejects pending frontier")
            try checks.require(fence.controlSnapshot().delivered == 0 && fence.controlSnapshot().failed, "Termination is not delivery")
            do { try await fence.waitForCurrentFrontier(); throw ControlFailure.failed("Ended fence admitted") }
            catch OriginalEventDeliveryFence.Failure.ended { try checks.require(true, "Terminal remains terminal") }
            continuation.finish(); withExtendedLifetime(stream) {}
        case "fifo-terminated-yield-rejected":
            let fence = OriginalEventDeliveryFence()
            let (stream, continuation) = AsyncStream.makeStream(of: Data.self)
            continuation.finish()
            fence.enqueue(Data("1".utf8), into: continuation)
            do { try await fence.waitForCurrentFrontier(); throw ControlFailure.failed("Terminated yield admitted") }
            catch OriginalEventDeliveryFence.Failure.ended { try checks.require(true, "Actual terminated AsyncStream yield fails") }
            try checks.require(fence.controlSnapshot().delivered == 0 && fence.controlSnapshot().failed, "No completion from failed enqueue")
            withExtendedLifetime(stream) {}
        case "fifo-concurrent-enqueue":
            let fixture = FIFOFixture()
            await withTaskGroup(of: Void.self) { group in
                for value in 0..<128 { group.addTask { fixture.enqueue(value) } }
                await group.waitForAll()
            }
            await fixture.sink.waitForEntered(1)
            let waiter = Task { try await fixture.fence.waitForCurrentFrontier() }
            try await until { fixture.fence.controlSnapshot().waiters == 1 }
            try checks.require(fixture.fence.controlSnapshot().accepted == 128 && fixture.fence.controlSnapshot().delivered == 0, "Concurrent enqueues retained while handler held")
            await fixture.sink.releaseThrough(128)
            try await waiter.value
            let values = await fixture.sink.values()
            try checks.require(values.count == 128 && Set(values) == Set(0..<128), "Every actual concurrent input delivered once")
            try checks.require(fixture.fence.controlSnapshot().delivered == 128 && !fixture.fence.controlSnapshot().failed, "Counts follow actual handler returns")
            await fixture.finish()
        case "auth-frozen-parent-and-restriction":
            let parent = try OriginalAuthAttempt(kind: .ordinary, parent: nil)
            let lifetime = EditorDocumentWriteLifetime()
            let restriction = try EditorDocumentWriteCapture(lifetime)
            let plain = try OriginalAuthRequestContext.$parent.withValue(parent) { try OriginalAuthAttempt(kind: .ordinary) }
            let child = try OriginalAuthRequestContext.$parent.withValue(parent) { try OriginalAuthAttempt(kind: .startup, restricting: [restriction]) }
            defer { child.finishOuter(); plain.finishOuter(); parent.finishOuter() }
            try checks.require(plain.captures.count == 2 && child.captures.count == 3, "Default parent lineage plus exact extra restriction")
            try checks.require(child.captures[0].source === parent.captures[0].source && child.captures[0].token == parent.captures[0].token, "Frozen parent retained")
            try checks.require(child.captures[1].source === restriction.source && child.captures[1].token == restriction.token, "Frozen restriction retained")
            lifetime.markUnavailable()
            try checks.require(!child.isCurrent && parent.isCurrent && plain.isCurrent, "Only restricted descendant retires")
            try checks.retired { _ = try child.admitStage() }
            parent.retire()
            try checks.require(!plain.isCurrent, "Original default parent retirement preserved")
        case "auth-retired-restriction-rejected":
            let lifetime = EditorDocumentWriteLifetime()
            let restriction = try EditorDocumentWriteCapture(lifetime)
            lifetime.markUnavailable()
            try checks.retired { _ = try OriginalAuthAttempt(kind: .ordinary, parent: nil, restricting: [restriction]) }
            try checks.require(lifetime.controlSnapshot().admitted == 0, "Rejected constructor does not admit retired restriction")
        case "auth-permit-rechecks-restriction":
            let lifetime = EditorDocumentWriteLifetime()
            let restriction = try EditorDocumentWriteCapture(lifetime)
            let child = try OriginalAuthAttempt(kind: .startup, parent: nil, restricting: [restriction])
            defer { child.finishOuter() }
            let permit = try await child.startupBinding().prepare(messageName: "AccountSelect")
            lifetime.markUnavailable()
            try checks.retired { _ = try permit.begin() }
            try checks.require(lifetime.controlSnapshot().admitted == 0, "No admission after prepare-to-begin retirement")
        case "auth-admitted-restriction-real-completion-drain":
            let lifetime = EditorDocumentWriteLifetime()
            let restriction = try EditorDocumentWriteCapture(lifetime)
            let child = try OriginalAuthAttempt(kind: .startup, parent: nil, restricting: [restriction])
            let permit = try await child.startupBinding().prepare(messageName: "AccountSelect")
            let completion = try permit.begin()
            try checks.require(lifetime.controlSnapshot().admitted == 1, "Actual original permit admitted restriction")
            lifetime.markUnavailable()
            let drained = Flag()
            let waiter = Task { await lifetime.waitForOperationsToDrain(); drained.set() }
            try await until { lifetime.controlSnapshot().waiting == 1 }
            waiter.cancel()
            try checks.require(!drained.read() && lifetime.controlSnapshot().admitted == 1, "Caller cancellation cannot erase admitted work")
            completion.finish()
            await waiter.value
            try checks.require(drained.read() && lifetime.controlSnapshot().admitted == 0, "Original completion released actual admission")
            completion.finish()
            try checks.require(lifetime.controlSnapshot().admitted == 0 && !child.isCurrent, "Duplicate completion does not revive ownership")
            child.finishOuter(); await child.waitForDrain()
        default: throw ControlFailure.failed("Unknown case")
        }
        print("PASS \(name) assertions=\(checks.count)")
    }
}
