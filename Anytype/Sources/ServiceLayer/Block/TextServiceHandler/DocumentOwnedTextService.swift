import Foundation
import Services

final class DocumentOwnedTextService: TextServiceProtocol {
    private let owner: EditorDocumentWriteOwner
    private let service: any TextServiceProtocol

    init(owner: EditorDocumentWriteOwner, service: any TextServiceProtocol) {
        self.owner = owner
        self.service = service
    }

    func setText(contextId: String, blockId: String, middlewareString: MiddlewareString) async throws {
        try await owner.performMutation(contextId: contextId) { [service] in
            try await service.setText(contextId: contextId, blockId: blockId, middlewareString: middlewareString)
        }
    }

    func setTextForced(contextId: String, blockId: String, middlewareString: MiddlewareString) async throws {
        try await owner.performMutation(contextId: contextId) { [service] in
            try await service.setTextForced(contextId: contextId, blockId: blockId, middlewareString: middlewareString)
        }
    }

    func setStyle(contextId: String, blockId: String, style: Style) async throws {
        try await owner.performMutation(contextId: contextId) { [service] in
            try await service.setStyle(contextId: contextId, blockId: blockId, style: style)
        }
    }

    func split(contextId: String, blockId: String, range: NSRange, style: Style, mode: SplitMode) async throws -> String {
        try await owner.performMutation(contextId: contextId) { [service] in
            try await service.split(contextId: contextId, blockId: blockId, range: range, style: style, mode: mode)
        }
    }

    func merge(contextId: String, firstBlockId: String, secondBlockId: String) async throws {
        try await owner.performMutation(contextId: contextId) { [service] in
            try await service.merge(contextId: contextId, firstBlockId: firstBlockId, secondBlockId: secondBlockId)
        }
    }

    func checked(contextId: String, blockId: String, newValue: Bool) async throws {
        try await owner.performMutation(contextId: contextId) { [service] in
            try await service.checked(contextId: contextId, blockId: blockId, newValue: newValue)
        }
    }

    func setTextIcon(contextId: String, blockId: String, imageObjectId: String, emojiUnicode: String) async throws {
        try await owner.performMutation(contextId: contextId) { [service] in
            try await service.setTextIcon(contextId: contextId, blockId: blockId, imageObjectId: imageObjectId, emojiUnicode: emojiUnicode)
        }
    }
}
