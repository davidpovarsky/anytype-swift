import Foundation

/// One existing owner's operation, including native RPCs that outlive caller
/// cancellation. This state grants no authority; each dispatch supplies the
/// captured owner's synchronous validation before the native body may begin.
final class EditorDocumentWriteOperation: @unchecked Sendable {
    private let lock = NSLock()
    private var outerFinished = false
    private var runningRPCs = 0
    private var failed = false
    private var onDrained: (@Sendable (Bool) -> Void)?

    init(onDrained: @escaping @Sendable (Bool) -> Void) { self.onDrained = onDrained }

    var isAccepting: Bool {
        lock.lock()
        defer { lock.unlock() }
        return !outerFinished
    }

    var hasFailed: Bool {
        lock.lock()
        defer { lock.unlock() }
        return failed
    }

    func markFailed() {
        lock.lock()
        failed = true
        lock.unlock()
    }

    func permit(
        acquire: @escaping @Sendable () throws -> [EditorDocumentWriteLifetime.Observation]
    ) -> InvocationDispatchPermit {
        InvocationDispatchPermit { [self] in
            lock.lock()
            let admissions: [EditorDocumentWriteLifetime.Observation]
            do {
                guard !outerFinished else { throw EditorDocumentWriteError.rejected(.invalidLease) }
                admissions = try acquire()
                runningRPCs += 1
                lock.unlock()
            } catch {
                failed = true
                lock.unlock()
                throw error
            }
            return InvocationDispatchCompletion(finish: { [self] in
                for admission in admissions { admission.cancel() }
                finishRPC()
            }, failed: { [self] in markFailed() })
        }
    }

    /// The actor owner removes an already-drained operation synchronously. An
    /// RPC still running keeps the callback until its actual native completion.
    func finishOuter() -> Bool {
        lock.lock()
        defer { lock.unlock() }
        outerFinished = true
        guard runningRPCs == 0 else { return false }
        onDrained = nil
        return true
    }

    private func finishRPC() {
        lock.lock()
        runningRPCs -= 1
        let callback = outerFinished && runningRPCs == 0 ? onDrained : nil
        if callback != nil { onDrained = nil }
        let failed = failed
        lock.unlock()
        callback?(failed)
    }
}
