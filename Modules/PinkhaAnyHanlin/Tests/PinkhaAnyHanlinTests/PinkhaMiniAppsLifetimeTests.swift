import Foundation
import Testing
import PinkhaHanlinCore

@MainActor
private final class MiniAppsTestGate {
    private var open = false
    private var waiters: [CheckedContinuation<Void, Never>] = []
    func wait() async {
        if open { return }
        await withCheckedContinuation { waiters.append($0) }
    }
    func release() {
        open = true
        let pending = waiters
        waiters.removeAll()
        for waiter in pending { waiter.resume() }
    }
}

@Suite("MiniApps native operation ownership")
@MainActor
struct PinkhaMiniAppsLifetimeTests {
    @Test
    func revocationWaitsForNativeCompletionWithoutCancellingIssuedWork() async throws {
        let owner = PinkhaMiniAppsLifetime()
        let started = MiniAppsTestGate()
        let nativeCompletion = MiniAppsTestGate()
        var nativeFinished = false
        var nativeCancelled = false
        var lateAcknowledged = false
        try owner.submit { lease in
            started.release()
            await nativeCompletion.wait()
            nativeCancelled = Task.isCancelled
            nativeFinished = true
            if owner.isCurrent(lease) { lateAcknowledged = true }
        }
        await started.wait()
        let releaseNative = Task { @MainActor in
            while owner.acceptsOperations { await Task.yield() }
            #expect(!nativeFinished)
            #expect(throws: CancellationError.self) { try owner.lease() }
            nativeCompletion.release()
        }
        let token = await owner.revokeAndDrain()
        #expect(nativeFinished)
        #expect(!nativeCancelled)
        #expect(!lateAcknowledged)
        await releaseNative.value
        owner.resume(token)
        #expect(owner.acceptsOperations)
    }

    @Test
    func authenticationCannotReleaseAnIndependentEngineSwitchHold() async throws {
        let owner = PinkhaMiniAppsLifetime()
        let before = try owner.lease()
        let engine = await owner.revokeAndDrain()
        let authentication = await owner.revokeAndDrain()
        owner.resume(authentication)
        #expect(!owner.acceptsOperations)
        owner.resume(authentication)
        owner.resume(UUID())
        #expect(!owner.acceptsOperations)
        #expect(throws: CancellationError.self) { try owner.validate(before) }
        owner.resume(engine)
        #expect(owner.acceptsOperations)
        #expect(throws: CancellationError.self) { try owner.validate(before) }
        try owner.validate(owner.lease())
    }

    @Test
    func queuedWorkIsRejectedIfItsOwnerChangesBeforeItStarts() async throws {
        let owner = PinkhaMiniAppsLifetime()
        var issuedNativeWrite = false
        try owner.submit { _ in issuedNativeWrite = true }
        let token = await owner.revokeAndDrain()
        #expect(!issuedNativeWrite)
        owner.resume(token)
    }

    @Test
    func resumedAccountCannotAuthorizeAnOldPresentationCallback() async throws {
        let owner = PinkhaMiniAppsLifetime()
        let presentationLease = try owner.lease()
        let token = await owner.revokeAndDrain()
        owner.resume(token)
        var acknowledgements = 0
        if owner.isCurrent(presentationLease) { acknowledgements += 1 }
        #expect(acknowledgements == 0)
        let current = try owner.lease()
        try owner.validate(current)
        #expect(current != presentationLease)
    }
}
