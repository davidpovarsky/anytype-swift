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
        @ViewBuilder label: @escaping () -> Label,
        @ViewBuilder additionalMenuItems: @escaping () -> AdditionalMenuItems
    ) {
        self._model = State(initialValue: ObjectSettingsCoordinatorViewModel(objectId: objectId, spaceId: spaceId, output: output))
        self.quickCapture = quickCapture
        self.torahSession = torahSession
        self.label = label
        self.additionalMenuItems = additionalMenuItems
    }

    var body: some View {
        ObjectSettingsMenuView(objectId: model.objectId, spaceId: model.spaceId, output: model, quickCapture: quickCapture, labelView: label, additionalMenuItems: additionalMenuItems)
            .sheet(item: $model.coverPickerData) {
                ObjectCoverPicker(data: $0)
            }
            .sheet(item: $model.objectIconPickerData) {
                ObjectIconPicker(data: $0)
            }
            .sheet(item: $model.blockObjectSearchData) {
                BlockObjectSearchView(data: $0)
            }
            .sheet(item: $model.relationsListData, onDismiss: {
                torahSession?.dismissPropertiesPresentation()
            }) {
                PropertiesListCoordinatorView(document: $0.document, output: model, torahSession: torahSession)
            }
            .sheet(item: $model.versionHistoryData) {
                VersionHistoryCoordinatorView(data: $0, output: model)
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
        @ViewBuilder label: @escaping () -> Label
    ) {
        self.init(objectId: objectId, spaceId: spaceId, output: output, quickCapture: quickCapture, label: label, additionalMenuItems: { EmptyView() })
    }
}

extension ObjectSettingsMenuContainer where Label == AnyView, AdditionalMenuItems == EmptyView {
    init(objectId: String, spaceId: String, output: (any ObjectSettingsCoordinatorOutput)?) {
        self.init(objectId: objectId, spaceId: spaceId, output: output) {
            AnyView(
                Image(asset: .X24.more)
                    .foregroundStyle(Color.Text.primary)
            )
        }
    }
}
