import Services

protocol EditorLocalEventPublishing: Sendable {
    func refresh(contextId: String) async
    func setStyle(contextId: String, blockId: String) async
    func setToggled(contextId: String, blockId: String) async
    func setText(contextId: String, blockId: String, text: MiddlewareString) async
    func setLoadingState(contextId: String, blockId: String) async
}

struct OriginalEditorLocalEventPublisher: EditorLocalEventPublishing {
    func refresh(contextId: String) async {
        await EventsBunch(contextId: contextId, localEvents: [.general]).send()
    }

    func setStyle(contextId: String, blockId: String) async {
        await EventsBunch(contextId: contextId, localEvents: [.setStyle(blockId: blockId)]).send()
    }

    func setToggled(contextId: String, blockId: String) async {
        await EventsBunch(contextId: contextId, localEvents: [.setToggled(blockId: blockId)]).send()
    }

    func setText(contextId: String, blockId: String, text: MiddlewareString) async {
        await EventsBunch(contextId: contextId, localEvents: [.setText(blockId: blockId, text: text)]).send()
    }

    func setLoadingState(contextId: String, blockId: String) async {
        await EventsBunch(contextId: contextId, localEvents: [.setLoadingState(blockId: blockId)]).send()
    }
}
