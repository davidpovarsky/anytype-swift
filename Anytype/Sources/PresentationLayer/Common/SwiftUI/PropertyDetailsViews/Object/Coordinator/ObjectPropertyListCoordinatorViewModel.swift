import Foundation
import SwiftUI
import Services

@MainActor
protocol ObjectPropertyListCoordinatorModuleOutput: AnyObject {
    func onObjectOpen(screenData: ScreenData)
}

@MainActor
@Observable
final class ObjectPropertyListCoordinatorViewModel: ObjectPropertyListModuleOutput {

    let data: ObjectPropertyListData

    private weak var output: (any ObjectPropertyListCoordinatorModuleOutput)?

    @ObservationIgnored
    @Injected(\.objectTypeProvider)
    private var objectTypeProvider: any ObjectTypeProviderProtocol

    var deletionAlertData: DeletionAlertData?
    var dismiss = false
    
    init(
        data: ObjectPropertyListData,
        output: (any ObjectPropertyListCoordinatorModuleOutput)?
    ) {
        self.data = data
        self.output = output
    }
    
    func obtainLimitedObjectTypes(with typesIds: [String]) -> [ObjectType] {
        typesIds.compactMap { try? objectTypeProvider.objectType(id: $0) }
    }

    // MARK: - ObjectPropertyListModuleOutput
    
    func onClose() {
        try? data.configuration.withCurrentOriginalProperty { dismiss.toggle() }
    }
    
    func onObjectOpen(screenData: ScreenData?) {
        guard (try? data.configuration.withCurrentOriginalProperty {}) != nil else { return }
        guard let screenData else { return }
        output?.onObjectOpen(screenData: screenData)
        onClose()
    }
    
    func onDeleteTap(completion: @escaping (_ isSuccess: Bool) -> Void) {
        guard (try? data.configuration.withCurrentOriginalProperty {}) != nil else { return }
        deletionAlertData = DeletionAlertData(
            title: Loc.Relation.Delete.Alert.title,
            description: Loc.Relation.Object.Delete.Alert.description,
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

extension ObjectPropertyListCoordinatorViewModel {
    struct DeletionAlertData: Identifiable {
        let id = UUID()
        let title: String
        let description: String
        let completion: (_ isSuccess: Bool) -> Void
    }
}
