import Foundation
import ProtobufMessages

private enum OriginalLocalAnnotationAuthenticationError: Error {
    case unqualifiedOriginalService
}

/// Additive access to the original implementation. Every account operation is
/// unconditionally localOnly; no network selection or credential is exposed to
/// the public editor facade. The caller retains the original account transition.
extension AuthMiddleServiceProtocol {
    @_spi(OriginalEditorLocalAnnotation)
    public func originalLocalAnnotationCreateWallet(rootPath: String) async throws -> String {
        guard let original = self as? AuthMiddleService else {
            throw OriginalLocalAnnotationAuthenticationError.unqualifiedOriginalService
        }
        return try await original.createWallet(rootPath: rootPath)
    }

    @_spi(OriginalEditorLocalAnnotation)
    public func originalLocalAnnotationCreateAccount() async throws -> AccountData {
        guard let original = self as? AuthMiddleService else {
            throw OriginalLocalAnnotationAuthenticationError.unqualifiedOriginalService
        }
        return try await original.createAccount(name: "Local Torah annotations", imagePath: "", iconOption: 0,
            networkMode: .localOnly, joinStreamUrl: "", configPath: nil)
    }

    @_spi(OriginalEditorLocalAnnotation)
    public func originalLocalAnnotationRecoverWallet(rootPath: String, mnemonic: String) async throws {
        guard let original = self as? AuthMiddleService else {
            throw OriginalLocalAnnotationAuthenticationError.unqualifiedOriginalService
        }
        try await original.walletRecovery(rootPath: rootPath, mnemonic: mnemonic)
    }

    @_spi(OriginalEditorLocalAnnotation)
    public func originalLocalAnnotationSelectAccount(id: String, rootPath: String,
                                                     preferredSpaceID: String) async throws -> AccountData {
        guard let original = self as? AuthMiddleService else {
            throw OriginalLocalAnnotationAuthenticationError.unqualifiedOriginalService
        }
        return try await original.selectAccount(id: id, rootPath: rootPath,
            networkMode: .localOnly, joinStreamUrl: "", configPath: nil, preferredSpaceId: preferredSpaceID)
    }
}
