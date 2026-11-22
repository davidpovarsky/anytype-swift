import Foundation
import Services
import SwiftUI

struct ObjectPropertyTypeItem {
    let name: String
    let isSelected: Bool
}

@MainActor
@Observable
final class ObjectPropertyListViewModel {

    var selectedOptionsIds: [String] = []
    var options: [ObjectPropertyOption] = []
    var isEmpty = false
    var searchText = ""

    let configuration: PropertyModuleConfiguration

    @ObservationIgnored
    private let interactor: any ObjectPropertyListInteractorProtocol
    @ObservationIgnored
    private let relationSelectedOptionsModel: any PropertySelectedOptionsModelProtocol
    @ObservationIgnored
    private let preloadedReadOnlyOptions: [ObjectPropertyOption]?

    @ObservationIgnored
    @Injected(\.objectActionsService)
    private var objectActionsService: any ObjectActionsServiceProtocol

    @ObservationIgnored
    private weak var output: (any ObjectPropertyListModuleOutput)?

    init(data: ObjectPropertyListData, output: (any ObjectPropertyListModuleOutput)?) {
        self.configuration = data.configuration
        self.output = output
        self.interactor = data.interactor
        self.relationSelectedOptionsModel = data.relationSelectedOptionsModel
        self.preloadedReadOnlyOptions = data.preloadedReadOnlyOptions
    }

    func startSelectedOptionsSubscription() async {
        guard (try? configuration.withCurrentOriginalProperty {}) != nil else { return }
        for await ids in relationSelectedOptionsModel.selectedOptionsIdsPublisher.values {
            guard (try? configuration.withCurrentOriginalProperty { selectedOptionsIds = ids }) != nil else { return }
        }
    }


    func onClear() {
        configuration.scheduleOriginalPropertyAction { [self] in
            try await configuration.originalSelectedOptionsModel(relationSelectedOptionsModel).onClear()
        }
    }
    
    func onOpenAsObject(_ option: ObjectPropertyOption) {
        try? configuration.withCurrentOriginalProperty { output?.onObjectOpen(screenData: option.objectScreenData) }
    }
    
    func onOpen(_ option: ObjectPropertyOption) {
        try? configuration.withCurrentOriginalProperty { output?.onObjectOpen(screenData: option.screenData) }
    }
    
    func onObjectDuplicate(_ option: ObjectPropertyOption) {
        configuration.scheduleOriginalPropertyAction { [self] in
            let newOptionId: String
            if let scope = configuration.originalEditorScope {
                let service = try OriginalObjectActionsServiceBinding.requireOriginal(objectActionsService)
                newOptionId = try await scope.withSelectedObjects(ids: [option.id], requiredPermissions: [.duplicate]) { [self] in
                    try await service.duplicate(objectId: option.id)
                }
            } else {
                newOptionId = try await objectActionsService.duplicate(objectId: option.id)
            }
            try configuration.withCurrentOriginalProperty {}
            try await configuration.originalSelectedOptionsModel(relationSelectedOptionsModel).optionSelected(newOptionId)
            try configuration.withCurrentOriginalProperty {}
            await searchTextChanged()
        }
    }
    
    func onOptionDelete(with indexSet: IndexSet) {
        indexSet.forEach { deleteIndex in
            guard deleteIndex < options.count else { return }
            let optionToDelete = options[deleteIndex]
            onOptionDelete(optionToDelete)
        }
    }
    
    func onOptionDelete(_ option: ObjectPropertyOption) {
        guard (try? configuration.withCurrentOriginalProperty {}) != nil else { return }
        output?.onDeleteTap { [weak self] isSuccess in
            guard let self else { return }
            guard (try? configuration.withCurrentOriginalProperty {}) != nil else { return }
            if isSuccess {
                removeRelationOption(option)
            } else {
                options = options
            }
        }
    }
    
    func optionSelected(_ option: ObjectPropertyOption) {
        if configuration.isEditable {
            configuration.scheduleOriginalPropertyAction { [self] in
                try await configuration.originalSelectedOptionsModel(relationSelectedOptionsModel).optionSelected(option.id)
                try configuration.withCurrentOriginalProperty { closeIfNeeded() }
            }
        } else {
            onOpen(option)
        }
    }
    
    func objectRelationTypeItems() -> [ObjectPropertyTypeItem]? {
        let typesNames = interactor.limitedObjectTypes.map { $0.displayName }
        
        guard typesNames.isNotEmpty else { return nil }
        
        var items = typesNames.enumerated().map { index, name in
            var separator = ","
            if typesNames.count - 1 == index {
                separator = ""
            }
            return ObjectPropertyTypeItem(name: name + separator, isSelected: true)
            
        }
        let title = typesNames.count == 1 ? Loc.Relation.ObjectType.Header.title : Loc.Relation.ObjectTypes.Header.title
        items.insert(
            ObjectPropertyTypeItem(
                name: title,
                isSelected: false
            ),
            at: 0
        )
        return items
    }
    
    func searchTextChanged() async {
        guard (try? configuration.withCurrentOriginalProperty {}) != nil else { return }
        // Read-only object relations (links/backlinks) render already-resolved objects
        // instead of re-querying via filtered search, which drops hidden/legacy objects.
        if let preloadedReadOnlyOptions {
            options = preloadedReadOnlyOptions
            setEmptyIfNeeded()
            return
        }
        do {
            let selectedOptions = try await interactor.searchOptions(text: searchText, limitObjectIds: selectedOptionsIds)
            try configuration.withCurrentOriginalProperty {}
            let rawOptions = try await interactor.searchOptions(text: searchText, excludeObjectIds: selectedOptionsIds)
            try configuration.withCurrentOriginalProperty {}
            
            let selectedReorder = selectedOptions
                .reordered(
                    by: selectedOptionsIds
                ) { $0.id }
            
            options = selectedReorder + rawOptions
            
            if !configuration.isEditable {
                options = options.filter { selectedOptionsIds.contains($0.id) }
            }
            
            setEmptyIfNeeded()
        } catch {}
    }
    
    private func removeRelationOption(_ option: ObjectPropertyOption) {
        configuration.scheduleOriginalPropertyAction { [self] in
            try configuration.withCurrentOriginalProperty {
                if let index = options.firstIndex(of: option) {
                    options.remove(at: index)
                }
            }
            if let scope = configuration.originalEditorScope {
                let service = try OriginalObjectActionsServiceBinding.requireOriginal(objectActionsService)
                try await scope.withSelectedObjects(ids: [option.id], requiredPermissions: [.archive]) { [self] in
                    try await service.setArchive(objectIds: [option.id], true)
                }
            } else {
                try await objectActionsService.setArchive(objectIds: [option.id], true)
            }
            try configuration.withCurrentOriginalProperty {}
            try await configuration.originalSelectedOptionsModel(relationSelectedOptionsModel).removeRelationOptionFromSelectedIfNeeded(option.id)
            try configuration.withCurrentOriginalProperty { setEmptyIfNeeded() }
        }
    }
    
    private func setEmptyIfNeeded() {
        isEmpty = options.isEmpty && searchText.isEmpty
    }
    
    private func closeIfNeeded() {
        if configuration.selectionMode == .single {
            output?.onClose()
        }
    }
}
