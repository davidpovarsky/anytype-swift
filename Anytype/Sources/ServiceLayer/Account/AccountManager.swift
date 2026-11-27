import Foundation
import ProtobufMessages
import Combine
import Services
import AnytypeCore

protocol AccountManagerProtocol: AnyObject, Sendable {
    var account: AccountData { get set }
    var accountPublisher: AnyPublisher<AccountData, Never> { get }
    var editorWriteLifetime: EditorDocumentWriteLifetime? { get }
}

extension AccountManagerProtocol {
    // Other conformers keep their original behavior and cannot qualify an
    // account-bound original editor Host without an actual lifetime provider.
    var editorWriteLifetime: EditorDocumentWriteLifetime? { nil }
}

final class AccountManager: AccountManagerProtocol, Sendable {
    
    private let storage = AtomicPublishedStorage(AccountData.empty)
    private let writeLifetime = EditorDocumentWriteLifetime(isAvailable: false)

    var editorWriteLifetime: EditorDocumentWriteLifetime? { writeLifetime }
    
    var account: AccountData {
        get { storage.value }
        set {
            writeLifetime.markUnavailable()
            storage.value = newValue
            if !newValue.id.isEmpty { writeLifetime.confirmOpened() }
        }
    }
    
    var accountPublisher: AnyPublisher<AccountData, Never> {
        return storage.publisher.removeDuplicates().eraseToAnyPublisher()
    }
    
    init() { }
}
