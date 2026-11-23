
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
