import Foundation
import Testing
@testable import Anytype

@MainActor
@Suite("Property picker selection ownership")
struct PropertyCreationSelectionTests {
    @Test("Native failure remains visible and an explicit successful retry clears it")
    func failureAndRetry() async {
        let selection = PinkhaPropertyPickerSelection()
        var calls = 0
        var publications = 0
        let failed = await selection.perform(spaceID: "space", objectID: "object", propertyID: "property") {
            calls += 1
            throw SelectionProbeFailure.native
        }
        #expect(!failed)
        #expect(selection.failed)
        #expect(!selection.isRunning)

        let retried = await selection.perform(
            spaceID: "space", objectID: "object", propertyID: "property",
            publishSuccess: { publications += 1 }
        ) {
            calls += 1
        }
        #expect(retried)
        #expect(calls == 2)
        #expect(publications == 1)
        #expect(!selection.failed)
        #expect(!selection.isRunning)
    }

    @Test("Repeated taps cannot start a second write while the original is pending")
    func pendingSelectionOwnsTheWrite() async {
        let selection = PinkhaPropertyPickerSelection()
        let probe = SuspendedPropertySelection()
        let first = Task {
            await selection.perform(spaceID: "space", objectID: "object", propertyID: "first") {
                try await probe.run()
            }
        }
        await probe.waitUntilStarted()
        #expect(selection.isRunning)
        var secondRan = false
        let second = await selection.perform(spaceID: "space", objectID: "object", propertyID: "second") {
            secondRan = true
        }
        #expect(!second)
        #expect(!secondRan)
        #expect(selection.isRunning)
        probe.finish()
        #expect(await first.value)
        #expect(!selection.isRunning)
    }

    @Test("Cancellation does not display a failed native mutation")
    func cancellationDoesNotPublishFailure() async {
        let selection = PinkhaPropertyPickerSelection()
        let completed = await selection.perform(spaceID: "space", objectID: "object", propertyID: "property") {
            throw CancellationError()
        }
        #expect(!completed)
        #expect(!selection.failed)
        #expect(!selection.isRunning)
    }

    @Test("A cancelled caller ignores a late provider error")
    func cancelledLateErrorDoesNotPublishFailure() async {
        let selection = PinkhaPropertyPickerSelection()
        let probe = SuspendedPropertySelection()
        let task = Task {
            await selection.perform(spaceID: "space", objectID: "object", propertyID: "property") {
                try await probe.run()
            }
        }
        await probe.waitUntilStarted()
        task.cancel()
        probe.finish(error: SelectionProbeFailure.native)
        #expect(!(await task.value))
        #expect(!selection.failed)
        #expect(!selection.isRunning)
    }

    @Test("A cancelled consumer cannot publish a late successful mutation")
    func cancelledLateSuccessRetainsOutcomeWithoutPublishing() async {
        let selection = PinkhaPropertyPickerSelection()
        let probe = SuspendedPropertySelection()
        var completedMutations = 0
        var publications = 0
        let task = Task {
            await selection.perform(
                spaceID: "space", objectID: "object", propertyID: "property",
                publishSuccess: { publications += 1 }
            ) {
                try await probe.run()
                completedMutations += 1
            }
        }
        await probe.waitUntilStarted()
        task.cancel()
        #expect(selection.isRunning)
        #expect(completedMutations == 0)
        #expect(publications == 0)
        probe.finish()
        #expect(await task.value) // The operation completed; no rollback is claimed.
        #expect(completedMutations == 1)
        #expect(publications == 0)
        #expect(!selection.failed)
        #expect(!selection.isRunning)
    }

    @Test("A pre-cancelled caller cannot issue a native mutation")
    func preCancelledSelectionDoesNotWrite() async {
        let selection = PinkhaPropertyPickerSelection()
        var ran = false
        let task = Task {
            await selection.perform(spaceID: "space", objectID: "object", propertyID: "property") {
                ran = true
            }
        }
        task.cancel()
        #expect(!(await task.value))
        #expect(!ran)
        #expect(!selection.failed)
        #expect(!selection.isRunning)
    }
}

private enum SelectionProbeFailure: Error { case native }

@MainActor
private final class SuspendedPropertySelection {
    private var operation: CheckedContinuation<Void, any Error>?
    private var started: CheckedContinuation<Void, Never>?

    func run() async throws {
        try await withCheckedThrowingContinuation { continuation in
            operation = continuation
            started?.resume()
            started = nil
        }
    }

    func waitUntilStarted() async {
        guard operation == nil else { return }
        await withCheckedContinuation { started = $0 }
    }

    func finish(error: (any Error)? = nil) {
        if let error { operation?.resume(throwing: error) }
        else { operation?.resume() }
        operation = nil
    }
}
