#if PINKHA_DUAL_ENGINE_RUNTIME
import Foundation
import PinkhaAnyHost
import PinkhaAnyIntegration
import ProtobufMessages

/// Original-app adapter for reviewing the currently loaded Heart source.
/// The host supplies SeedService.obtainSeed on the main actor; neither the
/// mnemonic, session token nor returned app token is persisted or presented.
actor PinkhaHeartSourceCaptureController {
    private let controller: AnyHeartNativeSourceAccountController
    private let observation: AnyHeartNativeSourceCaptureDiagnostics?
    private let privateCaptureParent: URL
    private var capturedReview: AnyHeartNativeSourceCaptureReview?
    private var migrationProducer: AnyHeartNativeMigrationProducer?
    private var migrationTask: Task<AnyHeartNativeMigrationCompletion, Error>?
    private var migrationTicket: UUID?
    private var generation = UUID()
    private var captureTicket: UUID?
    private var captureTask: Task<AnyHeartNativeSourceCaptureReview, Error>?
    // This facade never reopens after invalidation. The Scene releases it only
    // after successful drain, then constructs a fresh owner for a new review.
    private var invalidating = false
    private var cleanup: Task<Void, Error>?
    private var cleanupID: UUID?

    init(privateDirectory: URL,
         obtainSeed: @escaping @MainActor @Sendable () throws -> String) throws {
#if DEBUG
        let env = ProcessInfo.processInfo.environment
        let observation = env["PINKHA_HEART_SOURCE_CAPTURE_OBSERVER"] == "1" &&
            env["PINKHA_SIMULATOR_UI_DISPOSABLE"] == "1"
            ? try? AnyHeartNativeSourceCaptureDiagnostics(privateDirectory: privateDirectory) : nil
#else
        let observation: AnyHeartNativeSourceCaptureDiagnostics? = nil
#endif
        self.observation = observation
        privateCaptureParent = privateDirectory
        let authority = AnyHeartNativeSourceSessionAuthority(create: { expectedAccountID in
            try await Self.observed(.runtimeCheck, by: observation) {
                try await Self.requireQualifiedRuntime()
            }
            var request = Anytype_Rpc.Wallet.CreateSession.Request()
            request.mnemonic = try await Self.observed(.seedRead, by: observation) {
                try await obtainSeed()
            }
            let sessionRequest = request
            let response = try await Self.observed(.sessionCreate, by: observation) {
                try await ClientCommands.walletCreateSession(sessionRequest).invoke(
                    requestMask: { $0 = .init() },
                    responseMask: { $0.token = ""; $0.appToken = "" }
                )
            }
            let appAssociated = !response.appHash.isEmpty || !response.appName.isEmpty ||
                response.hasGrant || response.appExpireAt != 0 || response.appCreatedAt != 0
            // Only observe the returned booleans. The existing account controller
            // independently validates the actual grant and owns/cleans the token.
            observation?.record(.sessionGrant, .observed, authority: .init(
                accountMatches: response.accountID.utf8.elementsEqual(expectedAccountID.utf8),
                full: response.accountScope == .full, appAssociated: appAssociated,
                tokenPresent: !response.token.isEmpty
            ))
            return AnyHeartNativeSourceSessionGrant(
                sessionToken: response.token, accountID: response.accountID,
                isFull: response.accountScope == .full, isAppAssociated: appAssociated
            )
        }, close: { token in
            var request = Anytype_Rpc.Wallet.CloseSession.Request()
            request.token = token
            let closeRequest = request
            _ = try await Self.observed(.sessionClose, by: observation) {
                try await ClientCommands.walletCloseSession(closeRequest).invoke(
                    requestMask: { $0 = .init() }
                )
            }
        })
        let bridge = AnyHeartNativeSourceBridge(capture: { token, account, space, directory, request in
            try await Self.observed(.nativeCapture, by: observation) {
                try await Task.detached(priority: .userInitiated) {
                    try PinkhaLoadedAccountSourceNative.capture(
                        sessionToken: token, accountID: account, spaceID: space,
                        privateDirectory: directory, requestID: request
                    )
                }.value
            }
        }, validate: { token, request, manifest in
            try await Self.observed(.runtimeCheck, by: observation) {
                try await Self.requireQualifiedRuntime()
            }
            try await Self.observed(.nativeValidate, by: observation) {
                try await Task.detached(priority: .userInitiated) {
                    try PinkhaLoadedAccountSourceNative.validate(
                        sessionToken: token, requestID: request, manifestSHA256: manifest
                    )
                }.value
            }
        }, cancel: { token, request in
            PinkhaLoadedAccountSourceNative.cancel(sessionToken: token, requestID: request)
        }, release: { token, request in
            PinkhaLoadedAccountSourceNative.release(sessionToken: token, requestID: request)
        })
        controller = try AnyHeartNativeSourceAccountController(
            authority: authority, bridge: bridge, privateDirectory: privateDirectory
        )
    }

    private enum RuntimeFailure: LocalizedError {
        case unqualifiedNativeRuntime

        var errorDescription: String? {
            NSLocalizedString("The loaded engine does not match this app's migration source profile.",
                              comment: "Source capture refuses a different native runtime")
        }
    }

    /// Check the actual linked native runtime before obtaining the seed or
    /// minting a session. The generated producer profile binds the complete
    /// Heart/Any/SDK source closure; symbol presence is insufficient.
    private static func requireQualifiedRuntime() async throws {
        let actual = try await ClientCommands.appGetVersion().invoke(qos: .userInitiated).version
        guard actual.utf8.elementsEqual(PinkhaUnifiedRuntimeProfile.heartVersion.utf8) else {
            throw RuntimeFailure.unqualifiedNativeRuntime
        }
    }

    /// Observation never catches-and-continues, changes a return value or retries
    /// native work. Re-throw the same original failure after closed diagnostics.
    private static func observed<Result: Sendable>(
        _ phase: AnyHeartNativeSourceCaptureDiagnostics.Phase,
        by observation: AnyHeartNativeSourceCaptureDiagnostics?,
        operation: @Sendable () async throws -> Result
    ) async throws -> Result {
        observation?.record(phase, .started)
        do {
            let result = try await operation()
            observation?.record(phase, .succeeded)
            return result
        } catch {
            observation?.record(phase, .failed, error: error)
            throw error
        }
    }

    func capture(accountID: String, spaceID: String) async throws -> AnyHeartNativeSourceCaptureReview {
        guard !invalidating, cleanup == nil, captureTicket == nil,
              capturedReview == nil, migrationProducer == nil else {
            throw AnyHeartNativeSourceAccountError.invalidLifecycle
        }
        try Task.checkCancellation()
        let ticket = UUID(), current = generation
        captureTicket = ticket
        let controller = self.controller, observation = self.observation
        let task = Task {
            try await Self.observed(.sourceReview, by: observation) {
                try await controller.capture(accountID: accountID, spaceID: spaceID)
            }
        }
        // The actual task is registered before suspension. A UUID alone cannot
        // drain a source capture that has not yet entered its account actor.
        captureTask = task
        defer {
            if captureTicket == ticket {
                captureTicket = nil
                captureTask = nil
            }
        }
        do {
            let review = try await withTaskCancellationHandler {
                try await task.value
            } onCancel: { task.cancel() }
            try Task.checkCancellation()
            // A completed review may still be awaiting delivery to this actor
            // after the original source owner was invalidated and drained.
            guard !invalidating, generation == current, captureTicket == ticket else {
                throw AnyHeartNativeSourceAccountError.inactiveCapture
            }
            capturedReview = review
            return review
        } catch {
            let original = error
            // The owned child is already terminal here. Joining it from this
            // outer caller cannot create a self-join, and closes a token even
            // when parent cancellation arrived just after child completion.
            if Task.isCancelled { try await invalidate(reason: .userCancelled) }
            throw original
        }
    }

    /// Compose C's producer with this exact live source owner and its actual
    /// review. The caller supplies E's same-presentation destination operation;
    /// no source token, second source account session or replacement executor
    /// crosses this facade. This result currently carries two real references;
    /// it does not claim that the ordinary-property migration is complete.
    func executeMigration(
        _ request: AnyHeartNativeMigrationRequest,
        inDestination: @escaping AnyHeartNativeMigrationProducer.DestinationOperation
    ) async throws -> AnyHeartNativeMigrationCompletion {
        guard !invalidating, cleanup == nil, captureTicket == nil,
              let review = capturedReview else {
            throw AnyHeartNativeSourceAccountError.inactiveCapture
        }
        guard migrationTask == nil, migrationTicket == nil else {
            throw AnyHeartNativeMigrationProducerError.busy
        }
        let current = generation, ticket = UUID()
        let producer: AnyHeartNativeMigrationProducer
        if let retained = migrationProducer {
            producer = retained
        } else {
            producer = try AnyHeartNativeMigrationProducer(source: controller,
                review: review, privateCaptureParent: privateCaptureParent)
            // Retain before the first suspension. Invalidation must join this
            // producer's entire destination invocation and its delivery fence.
            migrationProducer = producer
        }
        let task = Task {
            try await producer.execute(request, inDestination: inDestination)
        }
        migrationTicket = ticket
        migrationTask = task
        defer {
            if migrationTicket == ticket {
                migrationTicket = nil
                migrationTask = nil
            }
        }
        do {
            let result = try await withTaskCancellationHandler {
                try await task.value
            } onCancel: { task.cancel() }
            guard !invalidating, generation == current, capturedReview != nil else {
                throw AnyHeartNativeSourceAccountError.inactiveCapture
            }
            try Task.checkCancellation()
            return result
        } catch {
            let original = error
            if Task.isCancelled { try await invalidate(reason: .userCancelled) }
            throw original
        }
    }

    func revalidate(source: AnyDestinationSourceBinding) async throws {
        try await controller.revalidate(source: source)
    }

    /// Await this before replacing the active account or engine. Revoke App
    /// admission before suspending, then join the producer when one exists.
    /// A native close failure keeps that same producer and source owner for a
    /// retry; neither a failed close nor a cancelled caller permits transfer.
    func invalidate(reason: AnyHeartNativeSourceCaptureCoordinator.InvalidationReason) async throws {
        if let cleanup { try await cleanup.value; return }
        invalidating = true
        generation = UUID()
        captureTicket = nil
        migrationTicket = nil
        capturedReview = nil
        let controller = self.controller, producer = migrationProducer,
            pendingCapture = captureTask, pendingMigration = migrationTask, id = UUID()
        cleanupID = id
        pendingCapture?.cancel()
        pendingMigration?.cancel()
        let task = Task {
            let native = Task {
                if let producer {
                    try await producer.invalidate(reason: reason)
                } else {
                    try await controller.invalidate(reason: reason)
                }
            }
            let nativeResult = await native.result
            // Always settle the actual registered capture call, including
            // when it starts late or closing the original token failed.
            if let pendingCapture { _ = await pendingCapture.result }
            // Join the public producer invocation too. Its outer cancellation
            // cleanup can outlive its registered destination child.
            if let pendingMigration { _ = await pendingMigration.result }
            try nativeResult.get()
        }
        cleanup = task
        do {
            try await task.value
            if cleanupID == id {
                migrationProducer = nil
                captureTask = nil
                migrationTask = nil
                cleanup = nil
                cleanupID = nil
                // Admission stays closed permanently on this facade.
            }
        } catch {
            if cleanupID == id {
                cleanup = nil
                cleanupID = nil
            }
            throw error
        }
    }

    func cancel() async throws { try await invalidate(reason: .userCancelled) }
    func release() async throws { try await invalidate(reason: .released) }
}
#endif
