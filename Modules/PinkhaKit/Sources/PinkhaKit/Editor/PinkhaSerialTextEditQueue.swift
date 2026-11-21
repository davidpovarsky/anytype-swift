/// Serializes whole-text native writes and coalesces edits that have not begun.
/// It never retries a dispatched mutation or calls a failed write successful.
/// Engine-specific code remains responsible for persistence and conflicts.
@MainActor
public final class PinkhaSerialTextEditQueue {
    private var generation: UInt64 = 0
    private var revision: UInt64 = 0
    private var tail: Task<Void, any Error>?
    public private(set) var hasPendingChanges = false

    public init() {}

    /// Return false only when the native adapter intentionally defers an edit,
    /// for example while a composition or a slash search owns the live buffer.
    /// Dirty ownership then remains until a later successful edit or explicit reset.
    @discardableResult
    public func enqueue(
        _ write: @escaping @MainActor () async throws -> Bool
    ) -> Task<Void, any Error> {
        revision &+= 1
        let submittedRevision = revision
        let submittedGeneration = generation
        let predecessor = tail
        hasPendingChanges = true
        let task = Task { @MainActor in
            // A failed predecessor must not prevent a later user correction.
            // Its error is still available to its own waiter; no write is retried.
            _ = try? await predecessor?.value
            guard generation == submittedGeneration, revision == submittedRevision else { return }
            let saved = try await write()
            guard generation == submittedGeneration, revision == submittedRevision else { return }
            if saved { hasPendingChanges = false }
        }
        tail = task
        return task
    }

    /// Keyboard structural actions wait for the current text before splitting or
    /// merging a block. New edits queued during suspension are included.
    public func drain() async throws {
        while let task = tail {
            let observedRevision = revision
            let observedGeneration = generation
            try await task.value
            if observedRevision == revision, observedGeneration == generation { return }
        }
    }

    /// Only an explicit owner/identity reset may discard dirty ownership.
    /// Keep the old task as a predecessor: resetting must never overlap native writes.
    public func resetOwnership() {
        generation &+= 1
        revision &+= 1
        hasPendingChanges = false
    }
}
