import Foundation
import Testing
@testable import PinkhaKit

@Suite("Bootstrap account operation lifetime", .timeLimit(.minutes(1)))
struct PinkhaBootstrapOperationsTests {
    @Test func logoutDrainsAcceptedWriterAndRejectsNewWork() async throws {
        let operations = PinkhaBootstrapOperations<Int>()
        let entered = BootstrapSignal()
        let release = BootstrapSignal()
        let retired = BootstrapSignal()
        let events = BootstrapEvents()
        let accepted = Task {
            try await operations.run {
                await events.append("writer entered")
                await entered.open()
                await release.wait()
                await events.append("writer committed")
                return 17
            }
        }
        await entered.wait()
        let close = Task {
            await operations.closeAndDrain()
            await events.append("logout")
            await retired.open()
        }
        await waitForClosedAdmission(operations)
        #expect(await retired.isOpen == false)
        do {
            _ = try await operations.run {
                await events.append("late writer")
                return 99
            }
            Issue.record("A new writer entered a retiring account")
        } catch PinkhaBootstrapAdmissionError.accountClosed {}
        do {
            try await operations.reopen()
            Issue.record("A replacement account opened before the old writer drained")
        } catch PinkhaBootstrapAdmissionError.operationsInFlight {}
        #expect(await events.values == ["writer entered"])
        await release.open()
        #expect(try await accepted.value == 17)
        await close.value
        #expect(await events.values == ["writer entered", "writer committed", "logout"])
        try await operations.reopen()
        #expect(try await operations.run { 23 } == 23)
    }

    @Test func failedWriterStillDrainsAndPreservesItsFailure() async throws {
        let operations = PinkhaBootstrapOperations<Int>()
        let entered = BootstrapSignal()
        let release = BootstrapSignal()
        let accepted = Task {
            try await operations.run {
                await entered.open()
                await release.wait()
                throw BootstrapTestFailure.original
            }
        }
        await entered.wait()
        let close = Task { await operations.closeAndDrain() }
        await waitForClosedAdmission(operations)
        await release.open()
        do {
            _ = try await accepted.value
            Issue.record("The original failure was lost")
        } catch BootstrapTestFailure.original {}
        await close.value
        try await operations.reopen()
        #expect(try await operations.run { 31 } == 31)
    }

    @Test func cancelledCallerDoesNotReleaseItsRetainedWriter() async throws {
        let operations = PinkhaBootstrapOperations<Int>()
        let entered = BootstrapSignal()
        let release = BootstrapSignal()
        let retired = BootstrapSignal()
        let events = BootstrapEvents()
        let caller = Task {
            try await operations.run {
                await entered.open()
                await release.wait()
                await events.append("retained writer completed")
                return 41
            }
        }
        await entered.wait()
        caller.cancel()
        let close = Task {
            await operations.closeAndDrain()
            await events.append("logout")
            await retired.open()
        }
        await waitForClosedAdmission(operations)
        #expect(await retired.isOpen == false)
        await release.open()
        #expect(try await caller.value == 41)
        await close.value
        #expect(await events.values == ["retained writer completed", "logout"])
    }

    private func waitForClosedAdmission(_ operations: PinkhaBootstrapOperations<Int>) async {
        while await operations.accepting { await Task.yield() }
    }
}

private enum BootstrapTestFailure: Error { case original }

private actor BootstrapSignal {
    private(set) var isOpen = false
    private var waiters: [CheckedContinuation<Void, Never>] = []

    func wait() async {
        guard !isOpen else { return }
        await withCheckedContinuation { waiters.append($0) }
    }

    func open() {
        guard !isOpen else { return }
        isOpen = true
        let pending = waiters
        waiters.removeAll()
        for waiter in pending { waiter.resume() }
    }
}

private actor BootstrapEvents {
    private(set) var values: [String] = []
    func append(_ value: String) { values.append(value) }
}
