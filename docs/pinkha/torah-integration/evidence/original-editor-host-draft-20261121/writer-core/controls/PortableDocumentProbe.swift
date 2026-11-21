import Foundation

// Explicit disposable document model for exercising the actual production
// owner/lifetime code on a non-Apple host. This is not an editor or a backend.
enum DocumentMode: Equatable, Sendable {
    case handling
    case preview
    case version(String)
}

struct EditorPageObject: Sendable {
    let objectId: String
    let spaceId: String
    let mode: DocumentMode
}

struct PortablePermissions: Sendable {
    let canEditBlocks = true
}

protocol BaseDocumentProtocol: AnyObject, Sendable {
    var objectId: String { get }
    var spaceId: String { get }
    var mode: DocumentMode { get }
    var isOpened: Bool { get }
    var isLocked: Bool { get }
    var permissions: PortablePermissions { get }
}

final class PortableDocument: BaseDocumentProtocol, EditorDocumentWriteLifetimeProviding, Sendable {
    let objectId = "owned"
    let spaceId = "owned-space"
    let mode = DocumentMode.handling
    let isOpened = true
    let isLocked = false
    let permissions = PortablePermissions()
    let editorWriteLifetime = EditorDocumentWriteLifetime()
}
