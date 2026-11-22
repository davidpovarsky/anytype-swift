import AnytypeCore
import Foundation

public protocol BasicUserInfoStorageProtocol: AnyObject, Sendable {
    var usersId: String { get set }
    var analyticsId: String? { get set }
    
    func cleanUserIdAfterLogout()
}

