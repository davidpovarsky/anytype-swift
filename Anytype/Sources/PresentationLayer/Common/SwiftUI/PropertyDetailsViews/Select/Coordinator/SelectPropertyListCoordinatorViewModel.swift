import Foundation
import SwiftUI

@MainActor
@Observable
final class SelectPropertyListCoordinatorViewModel: SelectPropertyListModuleOutput {

    let data: SelectPropertyListData

    var propertyData: PropertyData?
    var deletionAlertData: DeletionAlertData?
    var dismiss = false
    
    init(data: SelectPropertyListData) {
        self.data = data
    }

    // MARK: - SelectPropertyListModuleOutput
    
    func onClose() {
        try? data.configuration.withCurrentOriginalProperty { dismiss.toggle() }
    }
    
    func onCreateTap(text: String?, color: Color?, completion: @escaping (_ option: SelectPropertyOption) -> Void) {
        guard (try? data.configuration.withCurrentOriginalProperty {}) != nil else { return }
        propertyData = PropertyData(
            configuration: PropertyOptionSettingsConfiguration(
                option: PropertyOptionParameters(
                    text: text,
                    color: color
                ),
                mode: .create(
                    PropertyOptionSettingsMode.CreateData(
                        relationKey: data.configuration.relationKey,
                        spaceId: data.configuration.spaceId
                    )
                ),
                originalPropertyConfiguration: data.configuration
            ),
            completion: { [weak self] optionParams in
                guard let self, (try? self.data.configuration.withCurrentOriginalProperty {}) != nil else { return }
                completion(SelectPropertyOption(optionParams: optionParams))
                try? self.data.configuration.withCurrentOriginalProperty { self.propertyData = nil }
            }
        )
    }
    
    func onEditTap(option: SelectPropertyOption, completion: @escaping (_ option: SelectPropertyOption) -> Void) {
        guard (try? data.configuration.withCurrentOriginalProperty {}) != nil else { return }
        propertyData = PropertyData(
            configuration: PropertyOptionSettingsConfiguration(
                option: PropertyOptionParameters(
                    id: option.id,
                    text: option.text,
                    color: option.color
                ),
                mode: .edit,
                originalPropertyConfiguration: data.configuration
            ),
            completion: { [weak self] optionParams in
                guard let self, (try? self.data.configuration.withCurrentOriginalProperty {}) != nil else { return }
                completion(SelectPropertyOption(optionParams: optionParams))
                try? self.data.configuration.withCurrentOriginalProperty { self.propertyData = nil }
            }
        )
    }
    
    func onDeleteTap(completion: @escaping (_ isSuccess: Bool) -> Void) {
        guard (try? data.configuration.withCurrentOriginalProperty {}) != nil else { return }
        deletionAlertData = DeletionAlertData(
            title: Loc.Relation.Delete.Alert.title,
            description: Loc.Relation.Delete.Alert.description,
            completion: completion
        )
    }
    
    func deletionAlertView(data: DeletionAlertData) -> AnyView {
        let alertID = data.id
        return BottomAlertView(
            title: data.title,
            message: data.description,
            icon: .Dialog.question
        ) {
            BottomAlertButton(text: Loc.cancel, style: .secondary) { [weak self] in
                guard let self, (try? self.data.configuration.withCurrentOriginalProperty {}) != nil else { return }
                data.completion(false)
                self.deletionAlertData = nil
            }
            BottomAlertButton(text: Loc.delete, style: .warning,
                              prepareAction: self.data.configuration.originalPropertyButtonPreparation { [weak self] in
                guard let self, let alert = self.deletionAlertData, alert.id == alertID else {
                    throw EditorDocumentWriteError.rejected(.wrongContext)
                }
                try self.data.configuration.withOriginalPropertyActionCallback {
                    alert.completion(true)
                    try self.data.configuration.withCurrentOriginalProperty { self.deletionAlertData = nil }
                }
            }) { [weak self] in
                guard let self, (try? self.data.configuration.withCurrentOriginalProperty {}) != nil else { return }
                data.completion(true)
                self.deletionAlertData = nil
            }
        }.eraseToAnyView()
    }
}

extension SelectPropertyListCoordinatorViewModel {
    struct PropertyData: Identifiable {
        let id = UUID()
        let configuration: PropertyOptionSettingsConfiguration
        let completion: (_ optionParams: PropertyOptionParameters) -> Void
    }
    
    struct DeletionAlertData: Identifiable {
        let id = UUID()
        let title: String
        let description: String
        let completion: (_ isSuccess: Bool) -> Void
    }
}
