import Foundation

/// One-way presentation invalidation from actual host publishers; no permission is granted here.
final class PinkhaHanlinRevocationFence: @unchecked Sendable {
    private let lock = NSLock()
    private var revoked = false
    private var handler: (@Sendable () -> Void)?

    /// One owner. Registration after revocation also fires, outside the lock.
    func onRevoke(_ handler: @escaping @Sendable () -> Void) {
        lock.lock()
        let notify = revoked
        if !notify { precondition(self.handler == nil); self.handler = handler }
        lock.unlock()
        if notify { handler() }
    }

    func revoke() {
        lock.lock()
        guard !revoked else { lock.unlock(); return }
        revoked = true
        let handler = handler
        self.handler = nil
        lock.unlock()
        handler?()
    }
    var isRevoked: Bool { lock.lock(); defer { lock.unlock() }; return revoked }
}
