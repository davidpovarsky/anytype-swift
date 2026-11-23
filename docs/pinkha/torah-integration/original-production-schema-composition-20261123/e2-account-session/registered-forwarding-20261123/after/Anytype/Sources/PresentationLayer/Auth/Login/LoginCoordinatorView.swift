import SwiftUI

struct LoginCoordinatorView: View {

    @State private var model = LoginCoordinatorViewModel()
    @Environment(\.pageNavigation) private var pageNavigation
    private let originalEditorCaller: OriginalEditorAuthCaller?

    init(originalEditorCaller: OriginalEditorAuthCaller? = nil) {
        self.originalEditorCaller = originalEditorCaller
    }
    
    var body: some View {
        LoginView(output: model, originalEditorCaller: originalEditorCaller)
            .cameraPermissionAlert(isPresented: $model.showOpenSettingsURL)
            .sheet(isPresented: originalEditorCaller == nil ? $model.showPublicDebugMenu : .constant(false)) {
                // Whole-app debug administration is outside embedded account bootstrap.
                // Keep the complete original standalone destination.
                if originalEditorCaller == nil {
                    PublicDebugMenuView()
                }
            }
            .anytypeSheet(item: $model.secureAlertData) {
                SecureAlertView(data: $0)
            }
            .fullScreenCover(item: $model.migrationData) {
                MigrationCoordinatorView(data: $0)
            }
            .sheet(item: $model.qrCodeScannerData) { data in
                QrCodeScannerView(qrCode: data.entropy, error: data.error)
            }
    }
}
