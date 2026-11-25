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

    init(privateDirectory: URL,
         obtainSeed: @escaping @MainActor @Sendable () throws -> String) throws {
        let authority = AnyHeartNativeSourceSessionAuthority(create: { _ in
            try await Self.requireQualifiedRuntime()
            var request = Anytype_Rpc.Wallet.CreateSession.Request()
            request.mnemonic = try await obtainSeed()
            let response = try await ClientCommands.walletCreateSession(request).invoke(
                requestMask: { $0 = .init() },
                responseMask: { $0.token = ""; $0.appToken = "" }
            )
            return AnyHeartNativeSourceSessionGrant(
                sessionToken: response.token, accountID: response.accountID,
                isFull: response.accountScope == .full,
                isAppAssociated: !response.appHash.isEmpty || !response.appName.isEmpty ||
                    response.hasGrant || response.appExpireAt != 0 || response.appCreatedAt != 0
            )
        }, close: { token in
            var request = Anytype_Rpc.Wallet.CloseSession.Request()
            request.token = token
            _ = try await ClientCommands.walletCloseSession(request).invoke(
                requestMask: { $0 = .init() }
            )
        })
        let bridge = AnyHeartNativeSourceBridge(capture: { token, account, space, directory, request in
            try await Task.detached(priority: .userInitiated) {
                try PinkhaLoadedAccountSourceNative.capture(
                    sessionToken: token, accountID: account, spaceID: space,
                    privateDirectory: directory, requestID: request
                )
            }.value
        }, validate: { token, request, manifest in
            try await Self.requireQualifiedRuntime()
            try await Task.detached(priority: .userInitiated) {
                try PinkhaLoadedAccountSourceNative.validate(
                    sessionToken: token, requestID: request, manifestSHA256: manifest
                )
            }.value
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

    func capture(accountID: String, spaceID: String) async throws -> AnyHeartNativeSourceCaptureReview {
        try await controller.capture(accountID: accountID, spaceID: spaceID)
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
