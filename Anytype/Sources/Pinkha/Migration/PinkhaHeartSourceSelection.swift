#if PINKHA_DUAL_ENGINE_RUNTIME
import Foundation

/// Identity from the original app's loaded account and explicitly active
/// workspace. There is no default, most-recent or technical-space fallback.
struct PinkhaHeartSourceSelection: Equatable, Sendable {
    let accountID: String
    let spaceID: String
    let spaceName: String

    @MainActor
    static func current() -> Self? {
        let accounts = Container.shared.accountManager()
        let activeSpaces = Container.shared.activeSpaceManager()
        let views = Container.shared.spaceViewsStorage()
        let before = accounts.account
        guard case .active = before.status, !before.id.isEmpty,
              let opened = activeSpaces.workspaceInfo, !opened.accountSpaceId.isEmpty,
              let view = views.spaceView(spaceId: opened.accountSpaceId), view.isActive,
              Data(view.targetSpaceId.utf8) == Data(opened.accountSpaceId.utf8) else { return nil }
        let after = accounts.account
        guard case .active = after.status,
              Data(before.id.utf8) == Data(after.id.utf8),
              let current = activeSpaces.workspaceInfo,
              Data(current.accountSpaceId.utf8) == Data(opened.accountSpaceId.utf8) else { return nil }
        return .init(accountID: after.id, spaceID: opened.accountSpaceId, spaceName: view.name)
    }

    /// The native reader requires an actual private directory, not a
    /// user-visible Documents export. Resolve Apple's /var aliases once.
    static func privateDirectory() throws -> URL {
        let support = try FileManager.default.url(for: .applicationSupportDirectory,
            in: .userDomainMask, appropriateFor: nil, create: true).resolvingSymlinksInPath()
        let directory = support.appendingPathComponent("Pinkha", isDirectory: true)
            .appendingPathComponent("NativeSourceCaptures", isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true,
                                                attributes: [.posixPermissions: 0o700])
        let values = try directory.resourceValues(forKeys: [.isDirectoryKey, .isSymbolicLinkKey])
        let attributes = try FileManager.default.attributesOfItem(atPath: directory.path)
        guard values.isDirectory == true, values.isSymbolicLink != true,
              directory.standardizedFileURL == directory.resolvingSymlinksInPath().standardizedFileURL,
              (attributes[.posixPermissions] as? NSNumber)?.intValue == 0o700 else {
            throw CocoaError(.fileReadNoPermission)
        }
        return directory
    }
}
#endif
