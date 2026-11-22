import Foundation
import SwiftUI
import AnytypeCore

struct EditorPageCoordinatorView: View {

    @State private var model: EditorPageCoordinatorViewModel
    @Environment(\.pageNavigation) private var pageNavigation
    @Environment(\.dismiss) private var dismiss

    init(data: EditorPageObject, showHeader: Bool, childPreparation: PreparedEditorChildPreparation? = nil) {
        self._model = State(initialValue: EditorPageCoordinatorViewModel(
            data: data, showHeader: showHeader, childPreparation: childPreparation
        ))
    }
    
    init(preparedModel: EditorPageCoordinatorViewModel) {
        self._model = State(initialValue: preparedModel)
    }

    var body: some View {
        editor
            .ignoresSafeArea()
            .torahEditorHost(session: model.torahSession)
            .task { await model.prepareQualifiedEditor() }
            .onAppear {
                model.pageNavigation = pageNavigation
            }
            .onChange(of: model.dismiss) {
                dismiss()
            }
            .sheet(item: $model.relationValueData) { data in
                PropertyValueCoordinatorView(data: data, output: model)
            }
            .sheet(item: $model.codeLanguageData) {
                CodeLanguageListView(data: $0, documentWriteOwner: model.documentWriteOwner)
            }
            .sheet(item: $model.covertPickerData) { data in
                if let session = model.preparedEditorSession {
                    ObjectCoverPicker(data: data, dependencies: session.services.header)
                } else if !model.hasQualifiedPreparation {
                    ObjectCoverPicker(data: data)
                }
            }
            .sheet(item: $model.linkToObjectData) {
                LinkToObjectSearchView(data: $0) { data in
                    model.showEditorScreen(data: data)
                }
            }
            .sheet(item: $model.objectIconPickerData) { data in
                if let session = model.preparedEditorSession {
                    ObjectIconPicker(data: data, dependencies: session.services.header)
                } else if !model.hasQualifiedPreparation {
                    ObjectIconPicker(data: data)
                }
            }
            .sheet(item: $model.textIconPickerData) { data in
                if let session = model.preparedEditorSession {
                    TextIconPickerView(data: data, dependencies: session.services.blockActionService)
                } else if !model.hasQualifiedPreparation {
                    TextIconPickerView(data: data)
                }
            }
            .sheet(item: $model.blockObjectSearchData) {
                BlockObjectSearchView(data: $0)
            }
            .sheet(item: $model.relationsSearchData) {
                PropertyCreationView(data: $0)
            }
            .anytypeSheet(item: $model.undoRedoObjectId) {
                UndoRedoView(objectId: $0.value, documentWriteOwner: model.documentWriteOwner)
            }
            .anytypeSheet(item: $model.syncStatusSpaceId) {
                SyncStatusInfoView(spaceId: $0.value)
            }
            .snackbar(toastBarData: $model.toastBarData)
            .openUrl(url: $model.openUrlData)
            .cameraAccessFullScreenCover(item: $model.cameraData) {
                SimpleCameraView(data: $0)
            }
    }

    @ViewBuilder
    private var editor: some View {
        if model.hasQualifiedPreparation {
            if let preparedState = model.preparedState {
                EditorPageView(preparedState: preparedState)
            } else if model.preparationFailed {
                DocumentCommonOpenErrorView { dismiss() }
            } else {
                ProgressView()
            }
        } else {
            EditorPageView(
                data: model.data,
                output: model,
                showHeader: model.showHeader,
                torahSession: model.torahSession
            )
        }
    }

}

