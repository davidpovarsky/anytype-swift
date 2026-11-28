import Foundation
import PinkhaAnyIntegration

public enum AnyHeartNativeSourceAccountError: Error, Equatable, Sendable {
    case invalidLifecycle, invalidAuthority, inactiveCapture, sessionCloseFailed
}

/// An in-memory response from the app's real WalletCreateSession call.
/// The controller takes ownership before validating the response, so an
/// unexpected account/scope can never leak a newly allocated native session.
public struct AnyHeartNativeSourceSessionGrant: Sendable, CustomStringConvertible,
                                               CustomDebugStringConvertible {
    fileprivate let token: String
    fileprivate let accountID: String
    fileprivate let isFull: Bool
    fileprivate let isAppAssociated: Bool

    public init(sessionToken: String, accountID: String,
                isFull: Bool, isAppAssociated: Bool) {
        token = sessionToken; self.accountID = accountID
        self.isFull = isFull; self.isAppAssociated = isAppAssociated
    }

    public var description: String { "AnyHeartNativeSourceSessionGrant(redacted)" }
    public var debugDescription: String { description }

    fileprivate func session(expectedAccountID: String, spaceID: String) throws -> AnyHeartNativeSourceSession {
        guard isFull, !isAppAssociated, Data(accountID.utf8) == Data(expectedAccountID.utf8) else {
            throw AnyHeartNativeSourceAccountError.invalidAuthority
        }
        return try .init(sessionToken: token, accountID: accountID, spaceID: spaceID)
    }
}

/// Inject the original app's masked WalletCreateSession/WalletCloseSession
/// calls. The create callback returns the actual response, including a token
/// whose account/scope is unexpected; the controller must close that token.
public struct AnyHeartNativeSourceSessionAuthority: Sendable {
    public typealias Create = @Sendable (_ expectedAccountID: String) async throws -> AnyHeartNativeSourceSessionGrant
    public typealias Close = @Sendable (_ ownedSessionToken: String) async throws -> Void
    fileprivate let create: Create
    fileprivate let close: Close

    public init(create: @escaping Create, close: @escaping Close) {
        self.create = create; self.close = close
    }
}

/// Owns the additional native account session used for one source review.
/// Invalidation drains real native work before closing only this owned token.
/// A close failure remains explicit and retryable; account/engine ownership
/// must not transfer until invalidate has returned successfully.
public actor AnyHeartNativeSourceAccountController {
    public enum State: Equatable, Sendable {
        case idle, acquiringSession, capturing, ready, validating
        case invalidating(AnyHeartNativeSourceCaptureCoordinator.InvalidationReason)
        case sessionCloseFailed
    }

    public private(set) var state: State = .idle
    private let authority: AnyHeartNativeSourceSessionAuthority
    private let bridge: AnyHeartNativeSourceBridge
    private let privateDirectory: URL
    private var lifecycleID: UUID?
    private var invalidation: AnyHeartNativeSourceCaptureCoordinator.InvalidationReason?
    private var grant: AnyHeartNativeSourceSessionGrant?
    private var coordinator: AnyHeartNativeSourceCaptureCoordinator?
    private var captureTask: Task<AnyHeartNativeSourceCaptureReview, Error>?
    private var validationTask: Task<Void, Error>?
    private var cleanupTask: Task<Void, Error>?

    public init(authority: AnyHeartNativeSourceSessionAuthority,
                bridge: AnyHeartNativeSourceBridge, privateDirectory: URL) throws {
        // Apply the same source-root contract before acquiring any authority.
        _ = try AnyHeartNativeSourceCaptureCoordinator(bridge: bridge, privateDirectory: privateDirectory)
        self.authority = authority; self.bridge = bridge; self.privateDirectory = privateDirectory
    }

    public func capture(accountID: String, spaceID: String) async throws -> AnyHeartNativeSourceCaptureReview {
        guard lifecycleID == nil, cleanupTask == nil, state == .idle else {
            throw AnyHeartNativeSourceAccountError.invalidLifecycle
        }
        guard [accountID, spaceID].allSatisfy({
            !$0.isEmpty && $0.utf8.count <= 4096 && !$0.contains("\0")
        }) else { throw AnyHeartNativeSourceAccountError.invalidAuthority }
        try Task.checkCancellation()
        let id = UUID()
        lifecycleID = id; invalidation = nil; state = .acquiringSession
        let task = Task { try await self.performCapture(id: id, accountID: accountID, spaceID: spaceID) }
        captureTask = task
        return try await withTaskCancellationHandler {
            do {
                let review = try await task.value
                try Task.checkCancellation()
                try requireActive(id)
                return review
            } catch {
                let original = error
                try await invalidate(id: id, reason: error is CancellationError ? .userCancelled : .released)
                throw original
            }
        } onCancel: {
            // The caller's catch also awaits this same cleanup, including a
            // late mint. This task only signals cancellation promptly.
            Task { try? await self.invalidate(id: id, reason: .userCancelled) }
        }
    }

    public func revalidate(source: AnyDestinationSourceBinding) async throws {
        guard state == .ready, let id = lifecycleID, let coordinator, invalidation == nil else {
            throw AnyHeartNativeSourceAccountError.inactiveCapture
        }
        try Task.checkCancellation()
        state = .validating
        let task = Task { try await self.performValidation(id: id, source: source, coordinator: coordinator) }
        validationTask = task
        try await withTaskCancellationHandler {
            do {
                try await task.value
                try Task.checkCancellation()
                try requireActive(id)
            } catch {
                let original = error
                try await invalidate(id: id, reason: error is CancellationError ? .userCancelled : .nativeValidationFailed)
                throw original
            }
        } onCancel: {
            Task { try? await self.invalidate(id: id, reason: .userCancelled) }
        }
    }

    public func invalidate(reason: AnyHeartNativeSourceCaptureCoordinator.InvalidationReason) async throws {
        guard let id = lifecycleID else { return }
        try await invalidate(id: id, reason: reason)
    }

    public func cancel() async throws { try await invalidate(reason: .userCancelled) }
    public func release() async throws { try await invalidate(reason: .released) }

    private func performCapture(id: UUID, accountID: String, spaceID: String) async throws -> AnyHeartNativeSourceCaptureReview {
        try Task.checkCancellation()
        try requireActive(id)
        let authority = self.authority
        // Do not cancel this task. Invocation checks cancellation after its
        // native call; cancelling it could hide a successfully minted token.
        let minted = try await Task.detached(priority: .userInitiated) {
            try await authority.create(accountID)
        }.value
        grant = minted
        try Task.checkCancellation()
        try requireActive(id)
        let session = try minted.session(expectedAccountID: accountID, spaceID: spaceID)
        let coordinator = try AnyHeartNativeSourceCaptureCoordinator(bridge: bridge, privateDirectory: privateDirectory)
        self.coordinator = coordinator; state = .capturing
        let review = try await coordinator.capture(session: session, requestID: "app-source-" + id.uuidString)
        try Task.checkCancellation()
        try requireActive(id)
        state = .ready
        return review
    }

    private func performValidation(id: UUID, source: AnyDestinationSourceBinding,
                                   coordinator: AnyHeartNativeSourceCaptureCoordinator) async throws {
        try await coordinator.revalidate(source: source)
        try Task.checkCancellation()
        try requireActive(id)
        state = .ready
    }

    private func requireActive(_ id: UUID) throws {
        guard lifecycleID == id, invalidation == nil else {
            throw AnyHeartNativeSourceAccountError.inactiveCapture
        }
    }

    private func invalidate(id: UUID, reason: AnyHeartNativeSourceCaptureCoordinator.InvalidationReason) async throws {
        guard lifecycleID == id else { return }
        if let cleanupTask { try await cleanupTask.value; return }
        invalidation = invalidation ?? reason
        state = .invalidating(invalidation ?? reason)
        let task = Task { try await self.drainAndClose(id: id) }
        cleanupTask = task
        try await task.value
    }

    private func drainAndClose(id: UUID) async throws {
        captureTask?.cancel(); validationTask?.cancel()
        if let coordinator { await coordinator.invalidate(invalidation ?? .released) }
        // Await completion even after cancellation. The native mint/capture/
        // validate callbacks can finish late and still own native resources.
        if let captureTask { _ = await captureTask.result }
        if let validationTask { _ = await validationTask.result }
        if let coordinator { await coordinator.invalidate(invalidation ?? .released) }
        if let grant, !grant.token.isEmpty {
            let authority = self.authority, token = grant.token
            do {
                // A caller cancelling its engine switch must not hide the
                // result of closing the token either.
                try await Task.detached { try await authority.close(token) }.value
            } catch {
                state = .sessionCloseFailed; cleanupTask = nil
                throw AnyHeartNativeSourceAccountError.sessionCloseFailed
            }
        }
        guard lifecycleID == id else { throw AnyHeartNativeSourceAccountError.invalidLifecycle }
        grant = nil; coordinator = nil; captureTask = nil; validationTask = nil
        lifecycleID = nil; invalidation = nil; cleanupTask = nil; state = .idle
    }
}
