#if DEBUG && targetEnvironment(simulator)
import Foundation
import ProtobufMessages

private enum OriginalEditorQualificationAuthError: Error {
    case unqualifiedService
}

extension AuthMiddleServiceProtocol {
    @_spi(OriginalEditorQualification)
    public func originalEditorQualificationCreateWallet(rootPath: String) async throws -> String {
        guard let original = self as? AuthMiddleService else {
            throw OriginalEditorQualificationAuthError.unqualifiedService
        }
        return try await original.createWallet(rootPath: rootPath)
    }

    @_spi(OriginalEditorQualification)
    public func originalEditorQualificationCreateAccount(
        name: String, imagePath: String, iconOption: Int,
        networkMode: Anytype_Rpc.Account.NetworkMode,
        joinStreamUrl: String, configPath: String?
    ) async throws -> AccountData {
        guard let original = self as? AuthMiddleService else {
            throw OriginalEditorQualificationAuthError.unqualifiedService
        }
        return try await original.createAccount(
            name: name, imagePath: imagePath, iconOption: iconOption,
            networkMode: networkMode, joinStreamUrl: joinStreamUrl, configPath: configPath
        )
    }

    @_spi(OriginalEditorQualification)
    public func originalEditorQualificationWalletRecovery(rootPath: String, mnemonic: String) async throws {
        guard let original = self as? AuthMiddleService else {
            throw OriginalEditorQualificationAuthError.unqualifiedService
        }
        try await original.walletRecovery(rootPath: rootPath, mnemonic: mnemonic)
    }

    @_spi(OriginalEditorQualification)
    public func originalEditorQualificationSelectAccount(
        id: String, rootPath: String, networkMode: Anytype_Rpc.Account.NetworkMode,
        joinStreamUrl: String, configPath: String?, preferredSpaceId: String
    ) async throws -> AccountData {
        guard let original = self as? AuthMiddleService else {
            throw OriginalEditorQualificationAuthError.unqualifiedService
        }
        return try await original.selectAccount(
            id: id, rootPath: rootPath, networkMode: networkMode,
            joinStreamUrl: joinStreamUrl, configPath: configPath, preferredSpaceId: preferredSpaceId
        )
    }
}
#endif
