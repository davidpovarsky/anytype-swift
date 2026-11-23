import Foundation
import SwiftUI

struct ServerDocumentPickerView: View {

    @State private var model: ServerDocumentPickerViewModel

    init(originalEditorCaller: OriginalEditorAuthCaller? = nil) {
        _model = State(initialValue: ServerDocumentPickerViewModel(originalEditorCaller: originalEditorCaller))
    }
    
    var body: some View {
        DocumentPicker(contentTypes: [.yaml]) { url in
            model.onSelectFile(url: url)
        }
    }
}
