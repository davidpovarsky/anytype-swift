import Foundation

@MainActor
@Observable
final class ServerDocumentPickerViewModel {

    // MARK: - DI

    @ObservationIgnored
    @Injected(\.serverConfigurationStorage)
    private var storage: any ServerConfigurationStorageProtocol

    @ObservationIgnored
    private let originalEditorCaller: OriginalEditorAuthCaller?

    init(originalEditorCaller: OriginalEditorAuthCaller? = nil) {
        self.originalEditorCaller = originalEditorCaller
    }

    // MARK: - State

    var toast: ToastBarData?
    
    func onSelectFile(url: URL) {
        do {
            // The original storage operation is synchronous. Keep its real
            // scoped file-copy/configuration/publisher effects within this lease.
            try OriginalEditorAuthCaller.withUIAction(originalEditorCaller) {
                try storage.addConfiguration(filePath: url, setupAsCurrent: true)
                AnytypeAnalytics.instance().logUploadNetworkConfiguration()
                AnytypeAnalytics.instance().logSelectNetwork(type: .selfHost, route: .onboarding)
            }
        } catch {
            guard originalEditorCaller?.isCurrent ?? true else { return }
            toast = ToastBarData(Loc.error, type: .failure)
        }
    }
}
