import Foundation
import SwiftUI
import Combine

@MainActor
final class ServerConfigurationViewModel: ObservableObject {
    
    // MARK: - DI
    
    @Injected(\.serverConfigurationStorage)
    private var storage: any ServerConfigurationStorageProtocol
    private weak var output: (any ServerConfigurationModuleOutput)?
    private let originalEditorCaller: OriginalEditorAuthCaller?
    
    // MARK: - State
    
    @Published var mainRows: [ServerConfigurationRow] = []
    @Published var rows: [ServerConfigurationRow] = []
    @Published var showLocalConfigurationAlert = false
    
    private var subscriptions = [AnyCancellable]()
    
    init(output: (any ServerConfigurationModuleOutput)?, originalEditorCaller: OriginalEditorAuthCaller? = nil) {
        self.output = output
        self.originalEditorCaller = originalEditorCaller
        storage.installedConfigurationsPublisher.receiveOnMain().sink { [weak self, originalEditorCaller] _ in
            if let originalEditorCaller {
                try? originalEditorCaller.withUIAction {
                    withAnimation { self?.updateRows() }
                }
            } else {
                withAnimation {
                    self?.updateRows()
                }
            }
        }.store(in: &subscriptions)
    }
    
    func onTapAddServer() {
        try? OriginalEditorAuthCaller.withUIAction(originalEditorCaller) {
            output?.onAddServerSelected()
        
        }
    }
    
    func setup(config: NetworkServerConfig) {
        try? OriginalEditorAuthCaller.withUIAction(originalEditorCaller) {
            storage.setupCurrentConfiguration(config: config)
            updateRows()
            AnytypeAnalytics.instance().logSelectNetwork(type: config.analyticsType, route: .onboarding)
        
        }
    }
    
    // MARK: - Private
    
    private func updateRows() {
        mainRows = [makeRow(config: .anytype), makeRow(config: .localOnly)]
        rows = storage.installedConfigurations().map { config in
            makeRow(config: config)
        }
    }
    
    private func makeRow(config: NetworkServerConfig) -> ServerConfigurationRow {
        ServerConfigurationRow(
            title: config.title,
            isSelected: config == storage.currentConfiguration(),
            onTap: { [weak self] in
                self?.handleOnTap(config: config)
            }
        )
    }
    
    private func handleOnTap(config: NetworkServerConfig) {
        try? OriginalEditorAuthCaller.withUIAction(originalEditorCaller) {
            guard config != storage.currentConfiguration() else { return }
            if config.isLocalOnly {
                showLocalConfigurationAlert.toggle()
            } else {
                setup(config: config)
            }
        
        }
    }
}
