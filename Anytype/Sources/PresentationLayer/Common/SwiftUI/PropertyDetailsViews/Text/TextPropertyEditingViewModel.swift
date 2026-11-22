import Services
import Foundation

struct TextPropertyEditingViewData {
    let text: String?
    let type: TextPropertyViewType
    let config: PropertyModuleConfiguration
    let objectDetails: ObjectDetails
    let output: (any TextPropertyActionButtonViewModelDelegate)?
}

@MainActor
@Observable
final class TextPropertyEditingViewModel {

    var text: String
    var dismiss = false
    var textFocused = true
    var actionsViewModels: [any TextPropertyActionViewModelProtocol] = []
    var showPaste = false

    let config: PropertyModuleConfiguration
    let type: TextPropertyViewType

    @ObservationIgnored
    @Injected(\.textRelationEditingService)
    private var service: any TextPropertyEditingServiceProtocol
    @ObservationIgnored
    @Injected(\.pasteboardHelper)
    private var pasteboardHelper: any PasteboardHelperProtocol
    @ObservationIgnored
    @Injected(\.textRelationActionViewModelBuilder)
    private var builder: TextPropertyActionViewModelBuilder
    @ObservationIgnored
    @Injected(\.propertyDetailsStorage)
    private var propertyDetailsStorage: any PropertyDetailsStorageProtocol
    
    private let initialText: String
    
    init(data: TextPropertyEditingViewData) {
        let initialText = data.text ?? ""
        self.text = initialText
        self.initialText = initialText
        self.config = data.config
        self.type = data.type
        self.textFocused = data.config.isEditable
        
        self.actionsViewModels = builder.buildActionsViewModels(
            text: data.text,
            for: data.type,
            relationKey: data.config.relationKey,
            objectDetails: data.objectDetails,
            output: data.output
        )
        self.handleTextUpdate(text: self.text)
    }
    
    func onDisappear() {
        guard config.isEditable else { return }
        logChangeOrDeleteRelationValue()
    }
    
    func onClear() {
        try? config.withOriginalPropertyActionCallback {
            text = ""
            updateText(with: "")
        }
    }
    
    func onPaste() {
        try? config.withOriginalPropertyActionCallback {
            text = pasteboardHelper.obtainTextSlot() ?? ""
            updateText(with: text)
        }
    }
    
    func updatePasteState() {
        try? config.withCurrentOriginalProperty {
            showPaste = pasteboardHelper.hasSlots && text.isEmpty
        }
    }
    
    func onTextChanged(_ text: String) {
        updateText(with: text)
    }

    func acceptOriginalTextInput(_ text: String) {
        try? config.withOriginalPropertyActionCallback {
            self.text = text
            onTextChanged(text)
        }
    }
    
    func handlePasteboard() async {
        for await _ in pasteboardHelper.pasteboardChangePublisher().values {
            guard (try? config.withCurrentOriginalProperty {}) != nil else { return }
            updatePasteState()
        }
    }
    
    private func updateText(with text: String) {
        guard (try? config.withCurrentOriginalProperty {}) != nil else { return }
        updateRelation(with: text)
        handleTextUpdate(text: text)
        updatePasteState()
    }
    
    private func updateRelation(with value: String) {
        service.saveRelation(
            objectId: config.objectId,
            value: value,
            key: config.relationKey,
            textType: type,
            originalEditorScope: config.originalEditorScope
        )
        logEvent()
    }
    
    func handleTextUpdate(text: String) {
        for actionViewModel in actionsViewModels {
            actionViewModel.inputText = text
        }
        self.actionsViewModels = actionsViewModels
    }
    
    private func logEvent() {
        if let scope = config.originalEditorScope {
            try? scope.withCurrent { logCurrentEvent() }
        } else {
            logCurrentEvent()
        }
    }

    private func logCurrentEvent() {
        switch type {
        case .url:
            AnytypeAnalytics.instance().logRelationUrlEditMobile()
        default:
            break
        }
    }
    
    private func logChangeOrDeleteRelationValue() {
        guard initialText != text else { return }
        Task {
            let publish = { [self] in
                let relationDetails = try propertyDetailsStorage.relationsDetails(key: config.relationKey, spaceId: config.spaceId)
                AnytypeAnalytics.instance().logChangeOrDeleteRelationValue(
                    isEmpty: text.isEmpty,
                    format: relationDetails.format,
                    type: config.analyticsType,
                    key: relationDetails.analyticsKey
                )
            }
            if let scope = config.originalEditorScope { try scope.withCurrent(publish) }
            else { try publish() }
        }
    }
}
