import Foundation
import ProtobufMessages

/// A passive fence around the original account transition, not another account
/// selector. A cancelled caller cannot release it while its native RPC runs.
final class EditorAccountWriteTransition: Sendable {
    let binding: InvocationDispatchBinding
    private let operation: EditorDocumentWriteOperation
    private let state: State

    init(lifetime: EditorDocumentWriteLifetime, rpcNames: Set<String>) {
        let state = State(lifetime: lifetime)
        let operation = EditorDocumentWriteOperation { _ in state.release() }
        self.state = state
        self.operation = operation
        // This tracker is entered only from the original unbound AuthService.
        // Its ordinary committed global events keep that original context.
        binding = InvocationDispatchBinding(committedEvents: { nil }) { messageName in
            guard rpcNames.contains(messageName) else {
                throw EditorDocumentWriteError.rejected(.unqualifiedDispatch)
            }
            await lifetime.waitForOperationsToDrain()
            try Task.checkCancellation()
            return operation.permit { [] }
        }
    }

    func finish(verifiedAccountIsCurrent: @escaping @Sendable () -> Bool = { false }) {
        guard state.finishOuter(verifiedAccountIsCurrent: verifiedAccountIsCurrent) else { return }
        if operation.finishOuter() { state.release() }
    }

    /// Waits for the original transition's actual native drain and release
    /// effects. This does not certify a current account token or subscription.
    func finishAndWaitForRelease(
        verifiedAccountIsCurrent: @escaping @Sendable () -> Bool = { false }
    ) async {
        finish(verifiedAccountIsCurrent: verifiedAccountIsCurrent)
        await state.waitForRelease()
    }

    deinit { finish() }

    private final class State: @unchecked Sendable {
        private let lock = NSLock()
        private let lifetime: EditorDocumentWriteLifetime
        private let closing: EditorDocumentWriteLifetime.Observation
        private var outerFinished = false
        private var released = false
        private var releaseCompleted = false
        private var releaseWaiters: [CheckedContinuation<Void, Never>] = []
        private var verifiedAccountIsCurrent: (@Sendable () -> Bool)?

        init(lifetime: EditorDocumentWriteLifetime) {
            self.lifetime = lifetime
            closing = lifetime.beginClosing()
        }

        func finishOuter(verifiedAccountIsCurrent: @escaping @Sendable () -> Bool) -> Bool {
            lock.lock()
            defer { lock.unlock() }
            guard !outerFinished else { return false }
            outerFinished = true
            self.verifiedAccountIsCurrent = verifiedAccountIsCurrent
            return true
        }

        func waitForRelease() async {
            await withCheckedContinuation { continuation in
                lock.lock()
                if releaseCompleted {
                    lock.unlock()
                    continuation.resume()
                } else {
                    releaseWaiters.append(continuation)
                    lock.unlock()
                }
            }
        }

        func release() {
            lock.lock()
            guard outerFinished, !released else { lock.unlock(); return }
            released = true
            let verify = verifiedAccountIsCurrent
            verifiedAccountIsCurrent = nil
            lock.unlock()
            closing.cancel()
            // Setter confirmation while the close lease existed could not make
            // tokens available. Only a completed verified transition may do so.
            if verify?() == true { lifetime.confirmOpened() }
            // A release claim made before these effects is not completion.
            // Registration and completion share the same lock; resume outside it.
            lock.lock()
            releaseCompleted = true
            let waiters = releaseWaiters
            releaseWaiters.removeAll()
            lock.unlock()
            for waiter in waiters { waiter.resume() }
        }
    }
}
