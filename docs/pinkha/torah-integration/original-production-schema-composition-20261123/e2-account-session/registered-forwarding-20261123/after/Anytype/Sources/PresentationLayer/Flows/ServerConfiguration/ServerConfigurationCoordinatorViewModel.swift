import Foundation
import SwiftUI

@MainActor
@Observable
final class ServerConfigurationCoordinatorViewModel: ServerConfigurationModuleOutput {

    var showDocumentPicker: Bool = false
    @ObservationIgnored
    private let originalEditorCaller: OriginalEditorAuthCaller?

    init(originalEditorCaller: OriginalEditorAuthCaller? = nil) {
        self.originalEditorCaller = originalEditorCaller
    }
    
    // MARK: - ServerConfigurationModuleOutput
    
    func onAddServerSelected() {
        try? OriginalEditorAuthCaller.withUIAction(originalEditorCaller) {
            showDocumentPicker.toggle()

        }
    }
}
