import SwiftUI
import AnytypeCore

struct ObjectSettingsMenuContainer<Label: View, AdditionalMenuItems: View>: View {

    @State private var model: ObjectSettingsCoordinatorViewModel
    private let quickCapture: Bool
    private let torahSession: TorahEditorSession?
    private let label: () -> Label
    private let additionalMenuItems: () -> AdditionalMenuItems

    init(
        objectId: String,
        spaceId: String,
        output: (any ObjectSettingsCoordinatorOutput)?,
        quickCapture: Bool = false,
        torahSession: TorahEditorSession? = nil,
        preparedSession: PreparedEditorPageSession? = nil,
        @ViewBuilder label: @escaping () -> Label,
        @ViewBuilder additionalMenuItems: @escaping () -> AdditionalMenuItems
    ) {
        self._model = State(initialValue: ObjectSettingsCoordinatorViewModel(
            objectId: objectId, spaceId: spaceId, output: output, preparedSession: preparedSession
        ))
        self.quickCapture = quickCapture
        self.torahSession = torahSession
        self.label = label
        self.additionalMenuItems = additionalMenuItems
    }

    var body: some View {
        ObjectSettingsMenuView(objectId: model.objectId, spaceId: model.spaceId, output: model,
                              quickCapture: quickCapture, preparedSession: model.preparedSession,
                              labelView: label, additionalMenuItems: additionalMenuItems)
            .sheet(item: $model.coverPickerData) {
                ObjectCoverPicker(data: $0, dependencies: model.preparedSession?.services.header ?? .original())
            }
            .sheet(item: $model.objectIconPickerData) {
                ObjectIconPicker(data: $0, dependencies: model.preparedSession?.services.header ?? .original())
            }
            .sheet(item: $model.blockObjectSearchData) {
                BlockObjectSearchView(data: $0)
            }
            .sheet(item: $model.relationsListData, onDismiss: {
                torahSession?.dismissPropertiesPresentation()
            }) {
                PropertiesListCoordinatorView(document: $0.document, output: model, torahSession: torahSession,
                                              preparedSession: model.preparedSession)
            }
            .sheet(item: $model.versionHistoryData) {
                VersionHistoryCoordinatorView(data: $0, output: model, preparedSession: model.preparedSession)
            }
            .sheet(item: $model.publishingData) {
                PublishToWebCoordinator(data: $0)
            }
            .sheet(item: $model.chatEditData) { data in
                ChatCreateView(data: data)
            }
    }
}

extension ObjectSettingsMenuContainer where AdditionalMenuItems == EmptyView {
    init(
        objectId: String,
        spaceId: String,
        output: (any ObjectSettingsCoordinatorOutput)?,
        quickCapture: Bool = false,
        preparedSession: PreparedEditorPageSession? = nil,
        @ViewBuilder label: @escaping () -> Label
    ) {
        self.init(objectId: objectId, spaceId: spaceId, output: output, quickCapture: quickCapture,
                  preparedSession: preparedSession, label: label, additionalMenuItems: { EmptyView() })
    }
}

extension ObjectSettingsMenuContainer where Label == AnyView, AdditionalMenuItems == EmptyView {
    init(objectId: String, spaceId: String, output: (any ObjectSettingsCoordinatorOutput)?,
         preparedSession: PreparedEditorPageSession? = nil) {
        self.init(objectId: objectId, spaceId: spaceId, output: output, preparedSession: preparedSession) {
            AnyView(
                Image(asset: .X24.more)
                    .foregroundStyle(Color.Text.primary)
            )
        }
    }
}
