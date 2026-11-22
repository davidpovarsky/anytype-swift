#if DEBUG && targetEnvironment(simulator)
import Foundation
import Security

extension KeychainStore {
    @_spi(OriginalEditorQualification)
    public func addOriginalEditorQualificationItem(
        item: String, queryable: GenericPasswordQueryable
    ) throws {
        guard let bytes = item.data(using: .utf8) else {
            throw KeychainError.stringItem2DataConversionError
        }
        var query = queryable.query
        query[String(kSecValueData)] = bytes
        let status = SecItemAdd(query as CFDictionary, nil)
        guard status == errSecSuccess else {
            throw KeychainError.keychainError(status: status)
        }
    }
}
#endif
