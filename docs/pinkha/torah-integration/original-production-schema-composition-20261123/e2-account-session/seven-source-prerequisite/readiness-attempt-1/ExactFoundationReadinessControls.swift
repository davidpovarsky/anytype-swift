import Foundation
import Dispatch

final class OriginalApplicationConsumerDemand: @unchecked Sendable {
    enum ReadinessError: Error {
        case consumerEnded
        case demandNotForwarded
        case alreadyWaiting
    }

    private enum State {
        case waiting
        case requested
        case ended
    }

    private let lock = NSLock()
    private var state: State = .waiting
    private var waiter: CheckedContinuation<Void, Error>?
    private let onEnd: @Sendable () -> Void

    init(onEnd: @escaping @Sendable () -> Void = {}) {
        self.onEnd = onEnd
    }

    /// Called only after a positive request returned from the original
    /// upstream subscription. Completion/cancellation during that call wins.
    func didForwardPositiveDemand() {
        lock.lock()
        guard case .waiting = state else {
            lock.unlock()
            return
        }
        state = .requested
        let continuation = waiter
        waiter = nil
        lock.unlock()
        continuation?.resume()
    }

    func end() {
        lock.lock()
        guard case .ended = state else {
            state = .ended
            let continuation = waiter
            waiter = nil
            lock.unlock()
            continuation?.resume(throwing: ReadinessError.consumerEnded)
            onEnd()
            return
        }
        lock.unlock()
    }

    /// A synchronous admission fact, checked again after every startup await.
    /// It does not claim continuous demand or change AsyncPublisher buffering.
    func validateRequested() throws {
        lock.lock()
        defer { lock.unlock() }
        switch state {
        case .requested: return
        case .waiting: throw ReadinessError.demandNotForwarded
        case .ended: throw ReadinessError.consumerEnded
        }
    }

    func waitUntilRequested() async throws {
        try await withTaskCancellationHandler {
            try Task.checkCancellation()
            try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
                lock.lock()
                switch state {
                case .waiting:
                    guard waiter == nil else {
                        lock.unlock()
                        continuation.resume(throwing: ReadinessError.alreadyWaiting)
                        return
                    }
                    waiter = continuation
                    lock.unlock()
                case .requested:
                    lock.unlock()
                    continuation.resume()
                case .ended:
                    lock.unlock()
                    continuation.resume(throwing: ReadinessError.consumerEnded)
                }
            }
            try Task.checkCancellation()
            try validateRequested()
        } onCancel: {
            self.end()
        }
    }
}



private final class E2Counter: @unchecked Sendable {
    private let lock = NSLock()
    private var storage = 0
    func increment() { lock.lock(); storage += 1; lock.unlock() }
    var value: Int { lock.lock(); defer { lock.unlock() }; return storage }
}

@main
struct E2ReadinessControls {
    @MainActor private static var assertions = 0

    @MainActor private static func check(_ value: @autoclosure () -> Bool) {
        assertions += 1
        precondition(value(), "E2 readiness assertion \(assertions) failed")
    }

    @MainActor private static func rejects(_ operation: () throws -> Void) {
        do { try operation(); check(false) } catch { check(true) }
    }

    @MainActor static func main() async throws {
        let name = CommandLine.arguments[1]
        switch name {
        case "no-demand-is-not-ready":
            let demand = OriginalApplicationConsumerDemand()
            rejects { try demand.validateRequested() }
        case "forwarded-demand-admits":
            let ended = E2Counter()
            let demand = OriginalApplicationConsumerDemand(onEnd: { ended.increment() })
            demand.didForwardPositiveDemand()
            try demand.validateRequested()
            try await demand.waitUntilRequested()
            demand.didForwardPositiveDemand()
            try demand.validateRequested()
            check(ended.value == 0)
        case "terminal-before-acknowledgment-wins":
            let ended = E2Counter()
            let demand = OriginalApplicationConsumerDemand(onEnd: { ended.increment() })
            demand.end()
            demand.didForwardPositiveDemand()
            rejects { try demand.validateRequested() }
            do { try await demand.waitUntilRequested(); check(false) } catch { check(true) }
            demand.end()
            check(ended.value == 1)
        case "terminal-after-demand-invalidates":
            let ended = E2Counter()
            let demand = OriginalApplicationConsumerDemand(onEnd: { ended.increment() })
            demand.didForwardPositiveDemand()
            try demand.validateRequested()
            demand.end()
            rejects { try demand.validateRequested() }
            demand.didForwardPositiveDemand()
            rejects { try demand.validateRequested() }
            check(ended.value == 1)
        case "cancelled-waiter-closes-readiness":
            let ended = E2Counter()
            let demand = OriginalApplicationConsumerDemand(onEnd: { ended.increment() })
            let waiter = Task { try await demand.waitUntilRequested() }
            waiter.cancel()
            switch await waiter.result {
            case .success: check(false)
            case .failure: check(true)
            }
            rejects { try demand.validateRequested() }
            demand.didForwardPositiveDemand()
            rejects { try demand.validateRequested() }
            check(ended.value == 1)
        case "pending-wait-receives-demand":
            let demand = OriginalApplicationConsumerDemand()
            let waiter = Task { try await demand.waitUntilRequested() }
            demand.didForwardPositiveDemand()
            try await waiter.value
            try demand.validateRequested()
            check(true)
        case "one-of-two-terminated-does-not-admit":
            let first = OriginalApplicationConsumerDemand()
            let second = OriginalApplicationConsumerDemand()
            first.didForwardPositiveDemand()
            second.end()
            second.didForwardPositiveDemand()
            rejects {
                try first.validateRequested()
                try second.validateRequested()
            }
            do { try await second.waitUntilRequested(); check(false) } catch { check(true) }
            try first.validateRequested()
        case "concurrent-end-remains-terminal":
            for _ in 0..<32 {
                let ended = E2Counter()
                let demand = OriginalApplicationConsumerDemand(onEnd: { ended.increment() })
                DispatchQueue.concurrentPerform(iterations: 2) { index in
                    if index == 0 { demand.end() } else { demand.didForwardPositiveDemand() }
                }
                rejects { try demand.validateRequested() }
                demand.end()
                check(ended.value == 1)
            }
        default:
            preconditionFailure("Unknown control")
        }
        print("PASS \(name) assertions=\(assertions)")
    }
}
