import Services

struct DocumentOwnedLocalEventPublisher: EditorLocalEventPublishing {
    private let owner: EditorDocumentWriteOwner
    private let publisher: any EditorLocalEventPublishing

    init(owner: EditorDocumentWriteOwner, publisher: any EditorLocalEventPublishing) {
        self.owner = owner
        self.publisher = publisher
    }

    func refresh(contextId: String) async {
        await owner.performPublication(contextId: contextId) { [publisher] in
            await publisher.refresh(contextId: contextId)
        }
    }

    func setStyle(contextId: String, blockId: String) async {
        await owner.performPublication(contextId: contextId) { [publisher] in
            await publisher.setStyle(contextId: contextId, blockId: blockId)
        }
    }

    func setToggled(contextId: String, blockId: String) async {
        await owner.performPublication(contextId: contextId, requiresEditing: false) { [publisher] in
            await publisher.setToggled(contextId: contextId, blockId: blockId)
        }
    }

    func setText(contextId: String, blockId: String, text: MiddlewareString) async {
        await owner.performPublication(contextId: contextId) { [publisher] in
            await publisher.setText(contextId: contextId, blockId: blockId, text: text)
        }
    }

    func setLoadingState(contextId: String, blockId: String) async {
        await owner.performPublication(contextId: contextId) { [publisher] in
            await publisher.setLoadingState(contextId: contextId, blockId: blockId)
        }
    }
}
