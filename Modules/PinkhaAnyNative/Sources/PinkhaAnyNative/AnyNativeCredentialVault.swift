import Foundation
import Security

public struct AnyNativeAccount: Codable, Sendable, Equatable, Identifiable {
    public let id: String
    public let derivationIndex: UInt32
    public let needsRecoveryBackup: Bool
}

/// Never interpolate a credential into diagnostics, receipts, or UI errors.
struct AnyNativeCredential: Codable, Sendable, CustomStringConvertible, CustomDebugStringConvertible {
    let version: Int
    let accountID: String
    let derivationIndex: UInt32
    let mnemonic: String
    let needsRecoveryBackup: Bool
    var description: String { "AnyNativeCredential(redacted)" }
    var debugDescription: String { description }
    var metadata: AnyNativeAccount {
        .init(id: accountID, derivationIndex: derivationIndex, needsRecoveryBackup: needsRecoveryBackup)
    }
}

enum AnyNativeVaultError: Error, Equatable, Sendable {
    case unavailable(Int32)
    case malformedCredential
    case missingCredential
}

/// Managed Any keeps no recovery keys on disk. The native host owns this
/// separate Keychain namespace; the retained Heart account store is untouched.
protocol AnyNativeCredentialStoring: Sendable {
    func allMetadata() throws -> [AnyNativeAccount]
    func read(accountID: String) throws -> AnyNativeCredential
    func save(_ credential: AnyNativeCredential) throws
    func remove(accountID: String) throws
}

struct AnyNativeCredentialVault: AnyNativeCredentialStoring {
    let service: String

    init(service: String) throws {
        guard !service.isEmpty, service.utf8.count <= 200,
              service.allSatisfy({ $0.isASCII && !$0.isWhitespace && !$0.isNewline }) else {
            throw AnyNativeVaultError.malformedCredential
        }
        self.service = service
    }

    func allMetadata() throws -> [AnyNativeAccount] {
        var query = base
        query[kSecReturnData] = true
        query[kSecMatchLimit] = kSecMatchLimitAll
        var result: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        if status == errSecItemNotFound { return [] }
        guard status == errSecSuccess else { throw AnyNativeVaultError.unavailable(status) }
        guard let values = result as? [Data], values.count <= 128 else {
            throw AnyNativeVaultError.malformedCredential
        }
        return try values.map { try decode($0).metadata }.sorted { $0.id < $1.id }
    }

    func read(accountID: String) throws -> AnyNativeCredential {
        var query = base
        query[kSecAttrAccount] = accountID
        query[kSecReturnData] = true
        query[kSecMatchLimit] = kSecMatchLimitOne
        var result: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        if status == errSecItemNotFound { throw AnyNativeVaultError.missingCredential }
        guard status == errSecSuccess else { throw AnyNativeVaultError.unavailable(status) }
        guard let bytes = result as? Data else { throw AnyNativeVaultError.malformedCredential }
        let value = try decode(bytes)
        guard value.accountID == accountID else { throw AnyNativeVaultError.malformedCredential }
        return value
    }

    func save(_ credential: AnyNativeCredential) throws {
        try validate(credential)
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        let bytes = try encoder.encode(credential)
        var query = base
        query[kSecAttrAccount] = credential.accountID
        let updates: [CFString: Any] = [
            kSecValueData: bytes,
            kSecAttrAccessible: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        ]
        let status = SecItemUpdate(query as CFDictionary, updates as CFDictionary)
        if status == errSecItemNotFound {
            var item = query
            item.merge(updates) { _, new in new }
            let created = SecItemAdd(item as CFDictionary, nil)
            guard created == errSecSuccess else { throw AnyNativeVaultError.unavailable(created) }
        } else if status != errSecSuccess {
            throw AnyNativeVaultError.unavailable(status)
        }
    }

    /// Explicit removal deletes only the named credential in this app namespace.
    /// The caller must first drain that account and confirm recovery backup.
    func remove(accountID: String) throws {
        var query = base
        query[kSecAttrAccount] = accountID
        let status = SecItemDelete(query as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw AnyNativeVaultError.unavailable(status)
        }
    }

    private var base: [CFString: Any] {
        [kSecClass: kSecClassGenericPassword, kSecAttrService: service,
         kSecAttrSynchronizable: false]
    }

    private func decode(_ data: Data) throws -> AnyNativeCredential {
        guard data.count <= 16_384 else { throw AnyNativeVaultError.malformedCredential }
        let value = try JSONDecoder().decode(AnyNativeCredential.self, from: data)
        try validate(value)
        return value
    }

    private func validate(_ value: AnyNativeCredential) throws {
        guard value.version == 1, value.accountID.hasPrefix("A"),
              value.accountID.utf8.count <= 128, !value.mnemonic.isEmpty,
              value.mnemonic.utf8.count <= 4096 else {
            throw AnyNativeVaultError.malformedCredential
        }
    }
}
