import Foundation

protocol EditorDocumentWriteLifetimeProviding: AnyObject, Sendable {
    var editorWriteLifetime: EditorDocumentWriteLifetime { get }
}

/// A passive generation belonging to one actual document. Invalidation does not
/// close the document, cancel an admitted service operation, or undo its effects.
final class EditorDocumentWriteLifetime: @unchecked Sendable {
    struct Token: Equatable, Sendable {
        fileprivate let source: UUID
        fileprivate let generation: UInt64
    }

    final class Observation: @unchecked Sendable {
        private let lock = NSLock()
        private var cancelBody: (@Sendable () -> Void)?

        init(cancel: @escaping @Sendable () -> Void) { cancelBody = cancel }
        func cancel() {
            lock.lock()
            let body = cancelBody
            cancelBody = nil
            lock.unlock()
            body?()
        }
        deinit { cancel() }
    }

    private let lock = NSLock()
    private let source = UUID()
    private var generation: UInt64 = 0
    private var exhausted = false
    private var available: Bool
    private var closingLeases: Set<UUID> = []
    private var admittedOperations: Set<UUID> = []
    private var drainWaiters: [CheckedContinuation<Void, Never>] = []
    private var observers: [UUID: @Sendable () -> Void] = [:]

    init(isAvailable: Bool = true) { available = isAvailable }

    func token() -> Token? {
        lock.lock()
        defer { lock.unlock() }
        return available && !exhausted ? Token(source: source, generation: generation) : nil
    }

    func isCurrent(_ token: Token) -> Bool {
        lock.lock()
        defer { lock.unlock() }
        return available && !exhausted && token.source == source && token.generation == generation
    }

    /// Admission and retirement use the same lock. A native call admitted before
    /// retirement keeps its lease until the actual synchronous RPC body returns.
    func admitOperation(_ token: Token) -> Observation? {
        let id = UUID()
        lock.lock()
        guard available, !exhausted, token.source == source, token.generation == generation else {
            lock.unlock()
            return nil
        }
        admittedOperations.insert(id)
        lock.unlock()
        return Observation { [self] in finishOperation(id) }
    }

    /// Used after beginClosing has synchronously stopped new admissions. Caller
    /// cancellation cannot make a still-running original native body disappear.
    func waitForOperationsToDrain() async {
        await withCheckedContinuation { continuation in
            lock.lock()
            if admittedOperations.isEmpty {
                lock.unlock()
                continuation.resume()
            } else {
                drainWaiters.append(continuation)
                lock.unlock()
            }
        }
    }

    private func finishOperation(_ id: UUID) {
        lock.lock()
        admittedOperations.remove(id)
        let waiters = admittedOperations.isEmpty ? drainWaiters : []
        if admittedOperations.isEmpty { drainWaiters.removeAll() }
        lock.unlock()
        for waiter in waiters { waiter.resume() }
    }

    func invalidate() {
        lock.lock()
        let callbacks = invalidateLocked()
        lock.unlock()
        for callback in callbacks { callback() }
    }

    /// The original close RPC may suspend while the document still reports open.
    /// Block new admissions as well as retiring captured tokens during that gap.
    func beginClosing() -> Observation {
        let id = UUID()
        lock.lock()
        closingLeases.insert(id)
        available = false
        let callbacks = invalidateLocked()
        lock.unlock()
        for callback in callbacks { callback() }
        return Observation { [weak self] in self?.finishClosing(id) }
    }

    func markUnavailable() {
        lock.lock()
        available = false
        let callbacks = invalidateLocked()
        lock.unlock()
        for callback in callbacks { callback() }
    }

    /// Called only after the original document has installed an opened view.
    /// A still-admitted close must finish before a later open can grant authority.
    func confirmOpened() {
        lock.lock()
        available = !exhausted && closingLeases.isEmpty
        lock.unlock()
    }

    private func finishClosing(_ id: UUID) {
        lock.lock()
        closingLeases.remove(id)
        // Completion, including failure, does not itself prove a fresh open.
        lock.unlock()
    }

    private func invalidateLocked() -> [@Sendable () -> Void] {
        if generation == UInt64.max {
            exhausted = true
        } else {
            generation += 1
        }
        let callbacks = Array(observers.values)
        observers.removeAll()
        return callbacks
    }

    /// Registration checks the expected token under the same lock as invalidation,
    /// so a change between capture and subscription cannot disappear.
    func observe(_ expected: Token, invalidated: @escaping @Sendable () -> Void) -> Observation {
        let id = UUID()
        lock.lock()
        let current = available && !exhausted && expected.source == source && expected.generation == generation
        if current { observers[id] = invalidated }
        lock.unlock()
        if !current { invalidated() }
        return Observation { [weak self] in self?.removeObserver(id) }
    }

    private func removeObserver(_ id: UUID) {
        lock.lock()
        observers.removeValue(forKey: id)
        lock.unlock()
    }
}

