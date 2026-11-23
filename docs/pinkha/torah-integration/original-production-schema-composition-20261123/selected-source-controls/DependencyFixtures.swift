
// Dependency fixtures for this source-bound portable probe only.
// No account bootstrap, subscription transport, UIKit, native RPC or database is implemented.
struct AccountData: Sendable { let id: String }
struct AccountInfo: Sendable { let accountSpaceId: String; let spaceViewId: String }
struct SpaceView: Sendable {
    let id: String; let targetSpaceId: String
    let accountStatus = 1; let localStatus = 1; let spaceAccessType = 1
    let spaceType = 1; let isLegacyStream = false
}
protocol AccountManagerProtocol: AnyObject, Sendable {
    var account: AccountData { get }
    var editorWriteLifetime: EditorDocumentWriteLifetime? { get }
}
final class AccountManager: AccountManagerProtocol, Sendable {
    let account = AccountData(id: "same-account-data")
    let editorWriteLifetime: EditorDocumentWriteLifetime?
    init(_ lifetime: EditorDocumentWriteLifetime) { editorWriteLifetime = lifetime }
}
protocol SpaceViewsStorageProtocol: AnyObject, Sendable {}
final class SpaceViewsStorage: SpaceViewsStorageProtocol, Sendable {
    let permission: OriginalSpaceViewPermission
    init(_ permission: OriginalSpaceViewPermission) { self.permission = permission }
    func currentOriginalSpaceViewPermission(spaceId: String) throws -> OriginalSpaceViewPermission {
        precondition(spaceId == permission.originalSpaceView.targetSpaceId)
        return permission
    }
}
struct OriginalChannelPinPermission {
    func capture(matching account: EditorDocumentWriteCapture, spaceId: String) throws -> EditorDocumentWriteCapture {
        fatalError("Unused dependency fixture: channel permission was invoked")
    }
}
struct OriginalParticipantEditPermission {
    var originalParticipant: Int { fatalError("Unused participant dependency") }
    func capture(matching account: EditorDocumentWriteCapture, spaceId: String) throws -> EditorDocumentWriteCapture {
        fatalError("Unused dependency fixture: participant permission was invoked")
    }
}
struct SpacePermissions {
    let canEdit: Bool
    init(spaceView: SpaceView, participant: Int, isLocalMode: Bool) {
        fatalError("Unused dependency fixture: SpacePermissions was invoked")
    }
}
enum FixtureNetworkMode { case localOnly }
struct FixtureConfiguration { let middlewareNetworkMode = FixtureNetworkMode.localOnly }
struct FixtureConfigurationStorage { func currentConfiguration() -> FixtureConfiguration { .init() } }
struct Container: Sendable {
    static let shared = Container()
    func serverConfigurationStorage() -> FixtureConfigurationStorage { .init() }
}
@MainActor final class EditorDocumentWriteOwner {
    fileprivate func beginTrackedWork(access: EditorDocumentOperationAccess) throws -> EditorDocumentParentWork {
        .init(owner: self, lease: UUID(), lineage: .current)
    }
    fileprivate func finishTrackedWork(_ lease: UUID, failed: Bool) {}
}
@MainActor final class FixtureCurrentness { var value = true }
