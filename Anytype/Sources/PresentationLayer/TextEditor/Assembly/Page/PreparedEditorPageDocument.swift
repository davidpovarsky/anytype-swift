import Foundation

enum PreparedEditorPageDocumentError: Error, Equatable {
    case emptyIdentity
    case objectMismatch
    case spaceMismatch
    case modeMismatch
    case documentNotOpened
}

@MainActor
enum PreparedEditorPageDocument {
    static func validate(data: EditorPageObject, document: any BaseDocumentProtocol) throws {
        guard !data.objectId.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              !data.spaceId.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            throw PreparedEditorPageDocumentError.emptyIdentity
        }
        guard data.objectId == document.objectId else {
            throw PreparedEditorPageDocumentError.objectMismatch
        }
        guard data.spaceId == document.spaceId else {
            throw PreparedEditorPageDocumentError.spaceMismatch
        }
        guard data.mode == document.mode else {
            throw PreparedEditorPageDocumentError.modeMismatch
        }
        guard document.isOpened else {
            throw PreparedEditorPageDocumentError.documentNotOpened
        }
    }
}
