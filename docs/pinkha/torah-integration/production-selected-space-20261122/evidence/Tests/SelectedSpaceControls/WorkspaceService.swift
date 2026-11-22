import Foundation

public protocol WorkspaceServiceProtocol: Sendable {
    func workspaceOpen(spaceId: String, withChat: Bool) async throws -> AccountInfo
}

public extension WorkspaceServiceProtocol {
    func workspaceOpenForOriginalSelection(spaceId: String) async throws -> AccountInfo {
        guard let original = self as? WorkspaceService else {
            throw OriginalWorkspaceSelectionError.unqualifiedService
        }
        return try await original.workspaceOpen(spaceId: spaceId, withChat: true)
    }
}

private enum OriginalWorkspaceSelectionError: Error {
    case unqualifiedService
}

final class WorkspaceService: WorkspaceServiceProtocol {
    public func workspaceOpen(spaceId: String, withChat: Bool) async throws -> AccountInfo {
        let result = try await ClientCommands.workspaceOpen(.with {
            $0.spaceID = spaceId
            $0.withChat = withChat
        }).invoke(qos: .userInitiated)

        return result.info.asModel
    }
}
