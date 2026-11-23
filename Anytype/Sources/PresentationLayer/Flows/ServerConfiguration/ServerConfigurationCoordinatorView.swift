import Foundation
import SwiftUI

struct ServerConfigurationCoordinatorView: View {

    @State private var model: ServerConfigurationCoordinatorViewModel
    private let originalEditorCaller: OriginalEditorAuthCaller?

    init(originalEditorCaller: OriginalEditorAuthCaller? = nil) {
        self.originalEditorCaller = originalEditorCaller
        _model = State(initialValue: ServerConfigurationCoordinatorViewModel(originalEditorCaller: originalEditorCaller))
    }
    
    var body: some View {
        ServerConfigurationView(output: model, originalEditorCaller: originalEditorCaller)
            .sheet(isPresented: $model.showDocumentPicker) {
                ServerDocumentPickerView(originalEditorCaller: originalEditorCaller)
            }
    }
}
