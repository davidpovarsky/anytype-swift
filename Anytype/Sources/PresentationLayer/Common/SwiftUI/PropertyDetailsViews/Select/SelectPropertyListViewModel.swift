import Foundation
import Services
import SwiftUI

@MainActor
@Observable
final class SelectPropertyListViewModel {

    var selectedOptionsIds: [String] = []
    var options: [SelectPropertyOption] = []
    var isEmpty = false
    var searchText = ""

    let style: SelectPropertyListStyle
    let configuration: PropertyModuleConfiguration

    @ObservationIgnored
    private let relationSelectedOptionsModel: any PropertySelectedOptionsModelProtocol

    @ObservationIgnored
    @Injected(\.searchService)
    private var searchService: any SearchServiceProtocol

    @ObservationIgnored
    private weak var output: (any SelectPropertyListModuleOutput)?

    init(
        data: SelectPropertyListData,
        output: (any SelectPropertyListModuleOutput)?
    ) {
        self.style = data.style
        self.configuration = data.configuration
        self.output = output
        self.relationSelectedOptionsModel = data.relationSelectedOptionsModel
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
    
    func onCreate(with title: String?, color: Color? = nil) {
        guard (try? configuration.withCurrentOriginalProperty {}) != nil else { return }
        output?.onCreateTap(text: title, color: color, completion: { [weak self] option in
            self?.updateListOnCreate(with: option.id)
        })
    }
    
    func onOptionDuplicate(_ option: SelectPropertyOption) {
        onCreate(with: option.text, color: option.color)
    }
    
    func onOptionEdit(_ option: SelectPropertyOption) {
        guard (try? configuration.withCurrentOriginalProperty {}) != nil else { return }
        output?.onEditTap(option: option, completion: { [weak self] option in
            guard let self else { return }
            try? configuration.withCurrentOriginalProperty {
                if let index = options.firstIndex(where: { $0.id == option.id }) {
                    options[index] = option
                }
            }
        })
    }
    
    func onOptionDelete(with indexSet: IndexSet) {
        indexSet.forEach { deleteIndex in
            guard deleteIndex < options.count else { return }
            let optionToDelete = options[deleteIndex]
            onOptionDelete(optionToDelete)
        }
    }
    
    func onOptionDelete(_ option: SelectPropertyOption) {
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
    
    func optionSelected(_ optionId: String) {
        configuration.scheduleOriginalPropertyAction { [self] in
            try await configuration.originalSelectedOptionsModel(relationSelectedOptionsModel).optionSelected(optionId)
            try configuration.withCurrentOriginalProperty { closeIfNeeded() }
        }
    }
    
    func searchTextChanged() async {
        do {
            try configuration.withCurrentOriginalProperty {}
            let rawOptions = try await searchService.searchRelationOptions(
                text: searchText,
                relationKey: configuration.relationKey,
                excludedObjectIds: [],
                spaceId: configuration.spaceId
            ).map { SelectPropertyOption(relation: $0) }

            try configuration.withCurrentOriginalProperty {}
            
            switch configuration.selectionMode {
            case .single:
                options = rawOptions
            case .multi:
                options = rawOptions.reordered(
                    by: selectedOptionsIds
                ) { $0.id }
            }
            
            if !configuration.isEditable {
                options = options.filter { selectedOptionsIds.contains($0.id) }
            }
            
            setEmptyIfNeeded()
        } catch { }
    }
    
    private func updateListOnCreate(with optionId: String) {
        configuration.scheduleOriginalPropertyAction { [self] in
            try configuration.withCurrentOriginalProperty { searchText = "" }
            try await configuration.originalSelectedOptionsModel(relationSelectedOptionsModel).optionSelected(optionId)
            try configuration.withCurrentOriginalProperty {}
            await searchTextChanged()
        }
    }
    
    private func removeRelationOption(_ option: SelectPropertyOption) {
        configuration.scheduleOriginalPropertyAction { [self] in
            try configuration.withCurrentOriginalProperty {
                if let index = options.firstIndex(of: option) {
                    options.remove(at: index)
                }
            }
            try await configuration.originalSelectedOptionsModel(relationSelectedOptionsModel).removeRelationOption(option.id)
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
