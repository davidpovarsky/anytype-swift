import Foundation

/// One-way presentation invalidation from actual host publishers; no permission is granted here.
public final class PinkhaHanlinRevocationFence: @unchecked Sendable {
    public init() {}
    private let lock = NSLock()
    private var revoked = false
    private var handler: (@Sendable () -> Void)?

    /// One owner. Registration after revocation also fires, outside the lock.
    public func onRevoke(_ handler: @escaping @Sendable () -> Void) {
        lock.lock()
        let notify = revoked
        if !notify { precondition(self.handler == nil); self.handler = handler }
        lock.unlock()
        if notify { handler() }
    }

    public func revoke() {
        lock.lock()
        guard !revoked else { lock.unlock(); return }
        revoked = true
        let handler = handler
        self.handler = nil
        lock.unlock()
        handler?()
    }
    public var isRevoked: Bool { lock.lock(); defer { lock.unlock() }; return revoked }
}
