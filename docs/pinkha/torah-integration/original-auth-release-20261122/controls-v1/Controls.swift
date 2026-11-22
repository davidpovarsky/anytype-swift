import Foundation
#if os(Windows)
import ucrt
#elseif canImport(Glibc)
import Glibc
#else
import Darwin
#endif

private struct ControlFailure: Error, CustomStringConvertible {
    let description: String
}
private func require(_ condition: @autoclosure () -> Bool, _ message: String) throws {
    if !condition() { throw ControlFailure(description: message) }
}
private final class EventLog: @unchecked Sendable {
    private let lock = NSLock()
    private var events: [String] = []
    func append(_ value: String) { lock.lock(); events.append(value); lock.unlock() }
    func snapshot() -> [String] { lock.lock(); defer { lock.unlock() }; return events }
}
private final class Gate: @unchecked Sendable {
    private let lock = NSLock()
    private var opened = false
    private var waiters: [CheckedContinuation<Void, Never>] = []
    func open() {
        lock.lock()
        opened = true
        let pending = waiters
        waiters.removeAll()
        lock.unlock()
        for waiter in pending { waiter.resume() }
    }
    func wait() async {
        await withCheckedContinuation { continuation in
            lock.lock()
            if opened { lock.unlock(); continuation.resume() }
            else { waiters.append(continuation); lock.unlock() }
        }
    }
}
private final class Probe: @unchecked Sendable {
    let started = Gate()
    private let lock = NSLock()
    private var returned = false
    private var cancelled = false
    private var returnedCancelled = false
    private var verifiedCalls = 0
    private var timedOut = false
    func markReturned(cancelled: Bool = false) {
        lock.lock(); returned = true; returnedCancelled = cancelled; lock.unlock()
    }
    func markCancelled() { lock.lock(); cancelled = true; lock.unlock() }
    func markVerified() { lock.lock(); verifiedCalls += 1; lock.unlock() }
    func markTimedOut() { lock.lock(); timedOut = true; lock.unlock() }
    var didReturn: Bool { lock.lock(); defer { lock.unlock() }; return returned }
    var wasCancelled: Bool { lock.lock(); defer { lock.unlock() }; return cancelled }
    var didReturnCancelled: Bool { lock.lock(); defer { lock.unlock() }; return returnedCancelled }
    var verificationCount: Int { lock.lock(); defer { lock.unlock() }; return verifiedCalls }
    var didTimeOut: Bool { lock.lock(); defer { lock.unlock() }; return timedOut }
}

// A bounded observation after the waiter task announces invocation. It does not
// expose or claim proof of the private continuation-array registration instant.
private func observePending(
    _ probe: Probe, lifetime: EditorDocumentWriteLifetime, log: EventLog
) async throws {
    await probe.started.wait()
    try await Task.sleep(nanoseconds: 75_000_000)
    try require(!probe.didReturn, "waiter returned before the original release boundary")
    try require(lifetime.token() == nil, "account lifetime became available before release")
    log.append("observed-pending-75ms")
}

private enum Case: String, CaseIterable {
    case immediateVerifiedRelease
    case admittedOriginalOperationMustDrain
    case concurrentWaiterCannotSkipReleaseEffects
    case otherClosingLeaseStillDeniesCapture
    case cancelledWaiterDoesNotReleaseNativeOperation
    case duplicateFinishCannotUpgradeVerification
}
private struct CaseObservation: Codable {
    let name: String
    let status: String
    let events: [String]
    let details: [String: String]
    let error: String?
}
private struct SuiteObservation: Codable {
    let status: String
    let scope: String
    let processID: Int32
    let cases: [CaseObservation]
}

private func immediateVerifiedRelease(_ log: EventLog) async throws -> [String: String] {
    let lifetime = EditorDocumentWriteLifetime()
    let transition = EditorAccountWriteTransition(lifetime: lifetime, rpcNames: ["AccountSelect"])
    try require(lifetime.token() == nil, "transition did not close the real lifetime")
    log.append("before-finish-no-token")
    await transition.finishAndWaitForRelease {
        log.append("original-verification")
        return true
    }
    log.append("wait-returned")
    let firstCapture = try EditorDocumentWriteCapture(lifetime)
    try firstCapture.validate()
    log.append("first-real-capture-current")
    try require(log.snapshot() == [
        "before-finish-no-token", "original-verification",
        "wait-returned", "first-real-capture-current"
    ], "immediate release event order differs")
    return ["firstCapture": "current", "admittedNativeBodies": "0"]
}

private func admittedOriginalOperationMustDrain(_ log: EventLog) async throws -> [String: String] {
    let lifetime = EditorDocumentWriteLifetime()
    let transition = EditorAccountWriteTransition(lifetime: lifetime, rpcNames: ["AccountSelect"])
    let permit = try await transition.binding.prepare(messageName: "AccountSelect")
    let completion = try permit.begin()
    let probe = Probe()
    log.append("original-permit-began")
    transition.finish {
        probe.markVerified()
        log.append("original-verification")
        return true
    }
    log.append("outer-finished-native-still-admitted")
    let waiter = Task.detached {
        log.append("waiter-invoked")
        probe.started.open()
        await transition.finishAndWaitForRelease()
        probe.markReturned()
        log.append("wait-returned")
    }
    var pendingFailure: Error?
    do { try await observePending(probe, lifetime: lifetime, log: log) }
    catch { pendingFailure = error }
    log.append("fixture-ends-original-native-body")
    completion.finish()
    await waiter.value
    if let pendingFailure { throw pendingFailure }
    try require(probe.verificationCount == 1, "original verification did not run exactly once")
    let firstCapture = try EditorDocumentWriteCapture(lifetime)
    try firstCapture.validate()
    log.append("first-real-capture-current")
    let events = log.snapshot()
    try require(events.firstIndex(of: "fixture-ends-original-native-body")!
        < events.firstIndex(of: "original-verification")!, "verification preceded actual tracked completion")
    try require(events.firstIndex(of: "original-verification")!
        < events.firstIndex(of: "wait-returned")!, "waiter bypassed verification")
    return ["verificationCalls": "1", "firstCapture": "current",
            "nativeScope": "actual original permit/completion; disposable native-body boundary"]
}

private func concurrentWaiterCannotSkipReleaseEffects(_ log: EventLog) async throws -> [String: String] {
    let lifetime = EditorDocumentWriteLifetime()
    let transition = EditorAccountWriteTransition(lifetime: lifetime, rpcNames: ["AccountSelect"])
    let verifyEntered = Gate()
    let finishReturned = Gate()
    let releaseVerification = DispatchSemaphore(value: 0)
    let probe = Probe()
    DispatchQueue.global().async {
        transition.finish {
            probe.markVerified()
            log.append("verification-entered-after-lease-cancel")
            verifyEntered.open()
            if releaseVerification.wait(timeout: .now() + 10) == .timedOut { probe.markTimedOut() }
            log.append("verification-returning-before-confirm-open")
            return true
        }
        log.append("original-finish-returned")
        finishReturned.open()
    }
    await verifyEntered.wait()
    let waiter = Task.detached {
        log.append("second-waiter-invoked")
        probe.started.open()
        await transition.finishAndWaitForRelease {
            log.append("ILLEGAL-second-verification")
            return true
        }
        probe.markReturned()
        log.append("second-waiter-returned")
    }
    var pendingFailure: Error?
    do { try await observePending(probe, lifetime: lifetime, log: log) }
    catch { pendingFailure = error }
    log.append("fixture-unblocks-verification")
    releaseVerification.signal()
    await finishReturned.wait()
    await waiter.value
    if let pendingFailure { throw pendingFailure }
    try require(!probe.didTimeOut, "verification fixture exceeded its finite deadline")
    try require(probe.verificationCount == 1, "first verification changed")
    let events = log.snapshot()
    try require(!events.contains("ILLEGAL-second-verification"), "duplicate waiter replaced verification")
    try require(events.firstIndex(of: "verification-returning-before-confirm-open")!
        < events.firstIndex(of: "second-waiter-returned")!, "released claim was mistaken for completed effects")
    try EditorDocumentWriteCapture(lifetime).validate()
    log.append("first-real-capture-current")
    return ["verificationCalls": "1", "secondWaiter": "after-release-effects",
            "negativeObservation": "75ms after invocation announced; no private-state instrumentation"]
}

private func otherClosingLeaseStillDeniesCapture(_ log: EventLog) async throws -> [String: String] {
    let lifetime = EditorDocumentWriteLifetime()
    let other = lifetime.beginClosing()
    let transition = EditorAccountWriteTransition(lifetime: lifetime, rpcNames: ["AccountSelect"])
    await transition.finishAndWaitForRelease {
        log.append("original-verification")
        return true
    }
    log.append("this-transition-returned")
    do {
        _ = try EditorDocumentWriteCapture(lifetime)
        throw ControlFailure(description: "other closing lease was ignored")
    } catch let error as EditorDocumentWriteError {
        try require(error == .rejected(.retired), "wrong original capture denial")
        log.append("first-capture-denied-retired")
    }
    other.cancel()
    try require(lifetime.token() == nil, "closing cancellation itself incorrectly reopened account")
    log.append("other-cancel-does-not-confirm-open")
    return ["waitReturn": "Void only", "firstCapture": "rejected(retired)",
            "otherClosingCancellationReopens": "false"]
}

private func cancelledWaiterDoesNotReleaseNativeOperation(_ log: EventLog) async throws -> [String: String] {
    let lifetime = EditorDocumentWriteLifetime()
    let transition = EditorAccountWriteTransition(lifetime: lifetime, rpcNames: ["AccountSelect"])
    let completion = try await transition.binding.prepare(messageName: "AccountSelect").begin()
    let probe = Probe()
    log.append("original-permit-began")
    let waiter = Task.detached {
        await withTaskCancellationHandler {
            log.append("waiter-invoked")
            probe.started.open()
            await transition.finishAndWaitForRelease {
                probe.markVerified()
                log.append("original-verification-after-native-drain")
                return !probe.wasCancelled
            }
            probe.markReturned(cancelled: Task.isCancelled)
            log.append("cancelled-waiter-returned-after-drain")
        } onCancel: {
            probe.markCancelled()
            log.append("actual-task-cancellation-observed")
        }
    }
    await probe.started.wait()
    waiter.cancel()
    var pendingFailure: Error?
    do {
        try await observePending(probe, lifetime: lifetime, log: log)
        try require(probe.wasCancelled, "actual cancellation handler did not run")
    } catch { pendingFailure = error }
    log.append("fixture-ends-original-native-body")
    completion.finish()
    await waiter.value
    if let pendingFailure { throw pendingFailure }
    try require(probe.didReturnCancelled, "cancelled task identity was lost")
    try require(probe.verificationCount == 1, "verification did not run once at actual drain")
    try require(lifetime.token() == nil, "cancelled caller's verification reopened the account")
    let events = log.snapshot()
    try require(events.firstIndex(of: "fixture-ends-original-native-body")!
        < events.firstIndex(of: "original-verification-after-native-drain")!, "cancellation released early")
    return ["actualTaskCancelled": "true", "waitReturnBeforeDrain": "false",
            "postDrainAccountToken": "unavailable", "authAttemptIntegration": "not tested"]
}

private func duplicateFinishCannotUpgradeVerification(_ log: EventLog) async throws -> [String: String] {
    let lifetime = EditorDocumentWriteLifetime()
    let transition = EditorAccountWriteTransition(lifetime: lifetime, rpcNames: ["AccountSelect"])
    let probe = Probe()
    transition.finish()
    log.append("first-finish-unverified")
    await transition.finishAndWaitForRelease {
        probe.markVerified()
        return true
    }
    log.append("duplicate-wait-returned")
    try require(probe.verificationCount == 0, "second finish upgraded immutable first verification")
    try require(lifetime.token() == nil, "unverified transition became available")
    do {
        _ = try EditorDocumentWriteCapture(lifetime)
        throw ControlFailure(description: "unverified transition yielded an account capture")
    } catch let error as EditorDocumentWriteError {
        try require(error == .rejected(.retired), "wrong original denied capture")
        log.append("first-capture-denied-retired")
    }
    return ["lateVerificationCalls": "0", "firstCapture": "rejected(retired)"]
}

@main
private struct AccountTransitionReleaseControls {
    static func main() async {
        var observations: [CaseObservation] = []
        for item in Case.allCases {
            let log = EventLog()
            do {
                let details: [String: String]
                switch item {
                case .immediateVerifiedRelease: details = try await immediateVerifiedRelease(log)
                case .admittedOriginalOperationMustDrain: details = try await admittedOriginalOperationMustDrain(log)
                case .concurrentWaiterCannotSkipReleaseEffects: details = try await concurrentWaiterCannotSkipReleaseEffects(log)
                case .otherClosingLeaseStillDeniesCapture: details = try await otherClosingLeaseStillDeniesCapture(log)
                case .cancelledWaiterDoesNotReleaseNativeOperation: details = try await cancelledWaiterDoesNotReleaseNativeOperation(log)
                case .duplicateFinishCannotUpgradeVerification: details = try await duplicateFinishCannotUpgradeVerification(log)
                }
                observations.append(.init(name: item.rawValue, status: "PASS", events: log.snapshot(), details: details, error: nil))
                print("PASS \(item.rawValue)")
            } catch {
                observations.append(.init(name: item.rawValue, status: "FAIL", events: log.snapshot(), details: [:], error: String(describing: error)))
                print("FAIL \(item.rawValue): \(error)")
            }
        }
        let passed = observations.count == 6 && observations.allSatisfy { $0.status == "PASS" }
        let result = SuiteObservation(
            status: passed ? "PASS" : "FAIL",
            scope: "Windows portable original transition/lifetime/operation/dispatch; no native Auth, Combine, subscriptions or StageB",
            processID: ProcessInfo.processInfo.processIdentifier,
            cases: observations
        )
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        do {
            let data = try encoder.encode(result)
            print("CONTROL_RESULT=" + String(decoding: data, as: UTF8.self))
        } catch { print("RESULT_ENCODING_FAILURE"); exit(2) }
        exit(passed ? 0 : 1)
    }
}
