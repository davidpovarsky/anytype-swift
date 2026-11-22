import Foundation
import Services
import SwiftUI
import AnytypeCore


struct PropertiesListCoordinatorView: View {

    @State private var model: PropertiesListCoordinatorViewModel
    private let torahSession: TorahEditorSession?
    private let preparedSession: PreparedEditorPageSession?

    init(document: some BaseDocumentProtocol, output: (any PropertyValueCoordinatorOutput)?, torahSession: TorahEditorSession? = nil,
         preparedSession: PreparedEditorPageSession? = nil) {
        self.torahSession = torahSession
        self.preparedSession = preparedSession
        _model = State(initialValue: PropertiesListCoordinatorViewModel(document: document, output: output, preparedSession: preparedSession))
    }
    
    var body: some View {
        ObjectPropertiesView(
            document: model.document,
            output: model,
            torahSession: torahSession,
            preparedSession: preparedSession
        )
        .onDisappear { model.cancelTypePreparation() }
        .sheet(item: $model.relationValueData) { data in
            PropertyValueCoordinatorView(data: data, output: model)
        }
        .sheet(item: $model.relationsSearchData) {
            PropertyCreationView(data: $0)
        }
        .sheet(item: $model.objectTypeData, onDismiss: model.didDismissTypeProperties) { data in
            if let child = model.preparedTypePropertiesSession,
               child.document.objectId.utf8.elementsEqual(data.objectId.utf8),
               child.document.spaceId.utf8.elementsEqual(data.spaceId.utf8) {
                TypePropertiesView(preparedSession: child)
            } else if preparedSession == nil {
                TypePropertiesView(data: data)
            }
        }
        .sheet(isPresented: $model.showTypePicker) {
            ObjectTypeSearchView(
                title: Loc.changeType,
                spaceId: model.document.spaceId,
                settings: .editorChangeType
            ) { type in
                model.onTypeSelected(type)
            }
        }
        .snackbar(toastBarData: $model.typePropertiesToast)
    }
}
