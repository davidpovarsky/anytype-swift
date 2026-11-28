#if PINKHA_DUAL_ENGINE_RUNTIME
import Foundation
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration
import PinkhaEngineHost

/// One explicitly confirmed App migration owns its durable destination intent
/// from preparation through the complete C/E invocation and source-session
/// cleanup. The selected identifiers are routing metadata, never native authority.
actor PinkhaMigrationRunOwner {
    enum CloseReason: Sendable {
        case accountChanged, engineChanged, cancel, release
    }

    private let source: PinkhaHeartSourceCaptureController
    private let review: PinkhaEmbeddedHeartSourceReview
    private let destination: PinkhaEmbeddedAnyDestinationSelection
    private let presentation: PinkhaEmbeddedAnyPresentation
    private let selections: PinkhaMigrationSelectionStore

    private var started = false
    private var closing = false
    private var closed = false
    private var sourceClosed = false
    private var operation: PinkhaMigrationSelectionStore.Operation?
    private var running: Task<PinkhaMigrationSelectionStore.CompletedSelection, Error>?
    private var cleanup: Task<Void, Error>?
    private var cleanupID: UUID?

    init(source: PinkhaHeartSourceCaptureController,
         review: PinkhaEmbeddedHeartSourceReview,
         destination: PinkhaEmbeddedAnyDestinationSelection,
         presentation: PinkhaEmbeddedAnyPresentation,
         selections: PinkhaMigrationSelectionStore) {
        self.source = source
        self.review = review
        self.destination = destination
        self.presentation = presentation
        self.selections = selections
    }

    /// The Scene calls this only after showing the exact source and destination
    /// and receiving explicit confirmation. A retry never silently starts a
    /// second import: the same private intent and original journals are retained.
    func execute() async throws -> PinkhaMigrationSelectionStore.CompletedSelection {
        guard !started, !closing, !closed, cleanup == nil else {
            throw PinkhaMigrationSelectionError.busy
        }
        try Task.checkCancellation()
        started = true
        let task = Task { try await self.perform() }
        // Registration precedes the first suspension, including preparation of
        // the private intent. Cleanup joins a late prepare result too.
        running = task
        let result = try await withTaskCancellationHandler {
            try await task.value
        } onCancel: { task.cancel() }
        try Task.checkCancellation()
        guard !closing, !closed else { throw PinkhaMigrationSelectionError.changedSelection }
        return result
    }

    private func perform() async throws -> PinkhaMigrationSelectionStore.CompletedSelection {
        try Task.checkCancellation()
        guard !closing, !closed else { throw PinkhaMigrationSelectionError.changedSelection }
        let workspace = try AnyTorahWorkspace(accountID: destination.accountID,
                                               spaceID: destination.spaceID)
        let prepared = try await selections.prepare(review: review,
            networkID: destination.networkID, workspace: workspace)
        // Always retain a successfully prepared operation before checking
        // cancellation. A close that raced the actor hop must release this
        // exact operation only after this actual task has reached its terminal.
        operation = prepared
        try Task.checkCancellation()
        guard !closing, !closed else { throw PinkhaMigrationSelectionError.changedSelection }

        let presentation = self.presentation
        let destination = self.destination
        let selections = self.selections
        _ = try await source.executeMigrationWithOrdinaryProperties(
            prepared.request, inDestination: { body in
                try await presentation.performDestinationOperation(
                    expectedAccountID: destination.accountID,
                    expectedSpaceID: destination.spaceID
                ) { client, session, lease in
                    let completion = try await body(client, session, lease)
                    // This is inside E's actual body, before its final delivery
                    // fence. Retain a known original outcome even when the
                    // caller was cancelled; the Store owns and joins that work.
                    try await selections.retainOrdinary(completion, for: prepared)
                    return completion
                }
            })
        try Task.checkCancellation()
        guard !closing, !closed else { throw PinkhaMigrationSelectionError.changedSelection }
        let saved = try await selections.savedSelections(
            networkID: destination.networkID, workspace: workspace)
        let matching = saved.filter {
            Data($0.sourceAccountID.utf8) == Data(review.descriptor.sourceAccountID.utf8)
                && Data($0.sourceSpaceID.utf8) == Data(review.descriptor.sourceSpaceID.utf8)
                && $0.captureManifestSHA256 == review.descriptor.manifestSHA256
        }
        guard matching.count == 1, let completed = matching[0].completed else {
            throw PinkhaMigrationSelectionError.invalidCompletion
        }
        try Task.checkCancellation()
        guard !closing, !closed else { throw PinkhaMigrationSelectionError.changedSelection }
        // The cold decoder's locators still confer no native lease. Opening an
        // editor must go through the original imported-context owner.
        return completed
    }

    /// Revoke admission synchronously, then join the entire original C/E call,
    /// even when source-native cleanup fails. A failed close retains the same
    /// source and Store operation for a visible retry. No files are removed.
    func closeAndDrain(_ reason: CloseReason) async throws {
        if closed { return }
        if let cleanup {
            try await cleanup.value
            return
        }
        closing = true
        let pending = running
        pending?.cancel()
        let ticket = UUID()
        let task = Task {
            var sourceFailure: (any Error)?
            if !self.sourceClosed {
                do {
                    switch reason {
                    case .accountChanged: try await self.source.invalidate(reason: .accountChanged)
                    case .engineChanged: try await self.source.invalidate(reason: .engineChanged)
                    case .cancel: try await self.source.cancel()
                    case .release: try await self.source.release()
                    }
                    self.sourceClosed = true
                } catch { sourceFailure = error }
            }
            // Always join the real task, including late intent preparation and
            // immutable outcome retention. No cleanup callback awaits itself.
            _ = try? await pending?.value
            if let sourceFailure { throw sourceFailure }
            if let operation = self.operation {
                try await self.selections.release(operation)
                self.operation = nil
            }
            self.running = nil
            self.closed = true
        }
        cleanupID = ticket
        cleanup = task
        defer {
            if cleanupID == ticket {
                cleanupID = nil
                cleanup = nil
            }
        }
        // An outer cancelled Scene task must still await this uncancelled
        // cleanup owner; it cannot transfer source/namespace ownership early.
        try await task.value
    }
}
#endif
