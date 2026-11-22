import Foundation
import Services

extension DocumentMode: Sendable {}
extension BlocksReadonlyReason: Sendable {}
extension EditBlocksPermission: Sendable {}
extension ObjectPermissions: Sendable {}

struct EditorPageObject: Sendable {
    let objectId: String
    let spaceId: String
    let mode: DocumentMode
}

protocol BaseDocumentProtocol: AnyObject, Sendable {
    var objectId: String { get }
    var spaceId: String { get }
    var mode: DocumentMode { get }
    var isOpened: Bool { get }
    var isLocked: Bool { get }
    var permissions: ObjectPermissions { get }
}

final class BaseDocument: BaseDocumentProtocol, EditorDocumentWriteLifetimeProviding, @unchecked Sendable {
    private let lock = NSLock()
    private var currentObjectID: String
    private var opened = true
    let spaceId: String
    let mode: DocumentMode = .handling
    let isLocked = false
    let permissions: ObjectPermissions
    let editorWriteLifetime = EditorDocumentWriteLifetime()

    init(objectID: String, spaceID: String) {
        currentObjectID = objectID
        spaceId = spaceID
        var permissions = ObjectPermissions()
        permissions.canEditBlocks = true
        permissions.editBlocks = .edit
        self.permissions = permissions
    }

    var objectId: String {
        lock.lock()
        defer { lock.unlock() }
        return currentObjectID
    }

    var isOpened: Bool {
        lock.lock()
        defer { lock.unlock() }
        return opened
    }

    func replaceObjectID(_ value: String) {
        lock.lock()
        currentObjectID = value
        lock.unlock()
    }

    func markClosed() {
        lock.lock()
        opened = false
        lock.unlock()
        editorWriteLifetime.markUnavailable()
    }
}

@MainActor
final class PreparedEditorPageSession {
    let data: EditorPageObject
    let document: any BaseDocumentProtocol
    let owner: EditorDocumentWriteOwner
    let hasExternalSourceBinding = true
    private let sessionLifetime = EditorDocumentWriteLifetime()

    init(data: EditorPageObject, document: BaseDocument,
         sourceBinding: EditorDocumentWriteSourceBinding,
         onDrained: @escaping @MainActor () -> Void) throws {
        self.data = data
        self.document = document
        owner = try EditorDocumentWriteOwner(
            data: data, lifetimeDocument: document,
            sessionLifetime: sessionLifetime, sourceBinding: sourceBinding,
            onDrained: onDrained
        )
    }
}

final class PortableBasicUserInfo: BasicUserInfoStorageProtocol, @unchecked Sendable {
    private let lock = NSLock()
    private var user = ""
    private var analytics: String?
    var usersId: String {
        get {
            lock.lock()
            defer { lock.unlock() }
            return user
        }
        set {
            lock.lock()
            user = newValue
            lock.unlock()
        }
    }
    var analyticsId: String? {
        get {
            lock.lock()
            defer { lock.unlock() }
            return analytics
        }
        set {
            lock.lock()
            analytics = newValue
            lock.unlock()
        }
    }
    func cleanUserIdAfterLogout() { usersId = "" }
}

@MainActor
final class Container {
    static let shared = Container()
    private var manager = AccountManager()
    private var basic = PortableBasicUserInfo()
    func install(manager: AccountManager, basic: PortableBasicUserInfo) {
        self.manager = manager
        self.basic = basic
    }
    func accountManager() -> any AccountManagerProtocol { manager }
    func basicUserInfoStorage() -> any BasicUserInfoStorageProtocol { basic }
}
