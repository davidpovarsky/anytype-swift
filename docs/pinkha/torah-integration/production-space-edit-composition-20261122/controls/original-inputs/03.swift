import Foundation

/// Carries an existing owner's admission through asynchronous original services.
/// The binding is optional; ordinary invocations keep their original behavior.
public struct InvocationDispatchBinding: Sendable {
    /// Identity for passive caller bookkeeping; it grants no dispatch authority.
    public let contextIdentity = UUID()
    private let prepareBody: @Sendable (String) async throws -> InvocationDispatchPermit
    private let committedEvents: (@Sendable () -> InvocationDispatchBinding?)?

    public init(
        committedEvents: (@Sendable () -> InvocationDispatchBinding?)? = nil,
        prepare: @escaping @Sendable (String) async throws -> InvocationDispatchPermit
    ) {
        self.committedEvents = committedEvents
        prepareBody = prepare
    }

    func prepare(messageName: String) async throws -> InvocationDispatchPermit {
        try await prepareBody(messageName)
    }

    public func bindingForCommittedEvents() -> InvocationDispatchBinding? {
        if let committedEvents { return committedEvents() }
        return self
    }

    /// Checks a retained original context without dispatching native work. Used
    /// when an opened document is reused and must prove its original account.
    public func validateForOperation(named messageName: String) async throws {
        _ = try await prepareBody(messageName)
    }
}

/// Preparation may suspend. Admission itself runs synchronously on the original
/// RPC queue, immediately before invoking the unchanged native middleware body.
public struct InvocationDispatchPermit: Sendable {
    private let beginBody: @Sendable () throws -> InvocationDispatchCompletion

    public init(begin: @escaping @Sendable () throws -> InvocationDispatchCompletion) {
        beginBody = begin
    }

    func begin() throws -> InvocationDispatchCompletion { try beginBody() }
}

/// Finishes only after the actual native RPC returns, even if its awaiting caller
/// already received cancellation. Calling finish twice has no additional effect.
public final class InvocationDispatchCompletion: @unchecked Sendable {
    private let lock = NSLock()
    private var finishBody: (@Sendable () -> Void)?
    private var failureBody: (@Sendable () -> Void)?

    public init(finish: @escaping @Sendable () -> Void) {
        finishBody = finish
        failureBody = nil
    }

    public init(finish: @escaping @Sendable () -> Void, failed: @escaping @Sendable () -> Void) {
        finishBody = finish
        failureBody = failed
    }

    public func markFailed() {
        lock.lock()
        let body = finishBody != nil ? failureBody : nil
        failureBody = nil
        lock.unlock()
        body?()
    }

    public func finish() {
        lock.lock()
        let body = finishBody
        finishBody = nil
        failureBody = nil
        lock.unlock()
        body?()
    }

    deinit { finish() }
}

public enum InvocationDispatchContext {
    @TaskLocal public static var binding: InvocationDispatchBinding?
}
