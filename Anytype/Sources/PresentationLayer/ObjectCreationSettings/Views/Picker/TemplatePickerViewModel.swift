import Services
@preconcurrency import Combine
import SwiftUI

@MainActor
protocol TemplatePickerViewModuleOutput: AnyObject, ObjectSettingsCoordinatorOutput {
    func onTemplatesChanged(_ templates: [ObjectDetails], completion: ([TemplatePickerData]) -> Void)
    func selectionOptionsView(_ provider: some OptionsItemProvider) -> AnyView
    func onClose()
}

struct TemplatePickerViewModelData {
    enum Mode {
        case objectTemplate(objectId: String)
        case typeTemplate
    }
    
    let mode: Mode
    let typeId: String?
    let spaceId: String
    let defaultTemplateId: String?
    
    var objectId: String? {
        switch mode {
        case .objectTemplate(let objectId):
            return objectId
        case .typeTemplate:
            return nil
        }
    }
}

@MainActor
final class TemplatePickerViewModel: ObservableObject, OptionsItemProvider {    
    @Published var items = [Item]()
    @Published var selectedTab = 0
    
    var showApplyButton: Bool {
        if case .objectTemplate = data.mode { return true }
        return false
    }

    var spaceId: String { data.spaceId }

    private let data: TemplatePickerViewModelData
    private let documentWriteOwner: EditorDocumentWriteOwner?
    private var didSetupDefaultItem = false
    private var dismiss: DismissAction?
    
    @Injected(\.objectActionsService)
    private var objectService: any ObjectActionsServiceProtocol
    @Injected(\.templatesSubscription)
    private var templatesSubscriptionService: any TemplatesSubscriptionServiceProtocol

    weak var output: (any TemplatePickerViewModuleOutput)?
    
    // MARK: - OptionsItemProvider
    
    var optionsPublisher: AnyPublisher<[SelectionOptionsItemViewModel], Never> { $options.eraseToAnyPublisher() }
    @Published var options = [SelectionOptionsItemViewModel]()

    init(
        data: TemplatePickerViewModelData,
        output: (any TemplatePickerViewModuleOutput)?,
        documentWriteOwner: EditorDocumentWriteOwner? = nil
    ) {
        self.data = data
        self.output = output
        self.documentWriteOwner = documentWriteOwner
    }
    
    func setDismissAction(_ dismiss: DismissAction) {
        self.dismiss = dismiss
    }

    func onApplyButton() {
        guard let objectId = data.objectId else { return }
        
        let templateId = selectedTemplateId()
        let action: @MainActor @Sendable () async throws -> Void = { [self] in
            let service: any ObjectActionsServiceProtocol
            if let documentWriteOwner {
                service = DocumentOwnedObjectActionsService(owner: documentWriteOwner, service: objectService)
            } else {
                service = objectService
            }
            try await service.applyTemplate(objectId: objectId, templateId: templateId)
            if let documentWriteOwner {
                try documentWriteOwner.performSynchronousOperation(requiresEditing: false) { output?.onClose() }
            } else {
                output?.onClose()
            }
        }
        if let documentWriteOwner {
            do {
                let scheduled = try documentWriteOwner.scheduleMutation(contextId: objectId, requiredPermissions: [.applyTemplates])
                Task { try await scheduled.run(operation: action) }
            } catch { anytypeAssertionFailure(error.localizedDescription) }
        } else {
            Task { try await action() }
        }
    }

    func onCloseButtonTap() {
        output?.onClose()
    }

    func selectedItem() -> Item {
        let index = selectedTab >= items.count ? items.count - 1 : selectedTab
        return items[index]
    }
    
    func startTemplateSubscription() async {
        guard let typeId = data.typeId else { return }
        let publisher = await templatesSubscriptionService.startSubscription(
            objectType: typeId,
            spaceId: data.spaceId,
            update: nil
        )
        for await templates in publisher.values {
            if let documentWriteOwner {
                guard (try? documentWriteOwner.performSynchronousOperation(spaceId: data.spaceId, requiresEditing: false) { () -> Void in
                    updateItems(with: templates)
                    setupDefaultItem()
                }) != nil else { return }
            } else {
                updateItems(with: templates)
                setupDefaultItem()
            }
        }
    }
    
    private func setupDefaultItem() {
        guard !didSetupDefaultItem else { return }
        
        if let defaultIndex = items.firstIndex(where: { $0.templateId == data.defaultTemplateId}) {
            selectedTab = defaultIndex
        }
        
        didSetupDefaultItem = true
    }
    
    private func updateItems(with templates: [ObjectDetails]) {
        output?.onTemplatesChanged(templates, completion: { [weak self] models in
            guard let self else { return }
            items = models.enumerated().map { info -> TemplatePickerViewModel.Item in
                let model = info.element
                return .init(
                    id: info.offset,
                    view: model.editorView,
                    object: model.template,
                    templateId: model.template.id
                )
            }
            
            if items.count == 0 { dismiss?() }
        })
    }
    
    private func selectedTemplateId() -> String {
        let model = templateModel()
        let templateId = model.object.id
        AnytypeAnalytics.instance().logTemplateSelection(
            objectType: model.object.templateIsBundled ? .object(typeId: model.object.id) : .custom,
            route: .navigation
        )

        return templateId
    }
    
    private func templateModel() -> TemplatePickerViewModel.Item {
        selectedItem()
    }
}

extension TemplatePickerViewModel {
    struct Item: Identifiable {
        let id: Int
        let view: AnyView
        let object: ObjectDetails
        let templateId: String
    }
}
