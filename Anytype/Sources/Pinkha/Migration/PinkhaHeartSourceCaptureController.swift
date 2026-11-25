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
        let controller = self.controller
        return try await Self.observed(.sourceReview, by: observation) {
            try await controller.capture(accountID: accountID, spaceID: spaceID)
        }
    }

    func revalidate(source: AnyDestinationSourceBinding) async throws {
        try await controller.revalidate(source: source)
    }

    /// Await this before replacing the active account or engine. A native
    /// close failure keeps the owned token for retry and prevents transfer.
    func invalidate(reason: AnyHeartNativeSourceCaptureCoordinator.InvalidationReason) async throws {
        try await controller.invalidate(reason: reason)
    }

    func cancel() async throws { try await controller.cancel() }
    func release() async throws { try await controller.release() }
}
#endif
