import SwiftUI
import Services
import AnytypeCore

@MainActor
@Observable
final class PrimaryAuthViewModel {

    var createAccountTaskId: String?
    var inProgress = false
    var errorText: String? {
        didSet { showError = errorText.isNotNil }
    }
    var showError: Bool = false

    // MARK: - State
    @ObservationIgnored
    private let state: JoinFlowState
    @ObservationIgnored
    private let originalEditorCaller: OriginalEditorAuthCaller?

    private var originalAuthService: any AuthServiceProtocol { originalEditorCaller ?? authService }
    private var acceptsOriginalUI: Bool { originalEditorCaller?.isCurrent ?? true }

    // MARK: - Private
    @ObservationIgnored
    private weak var output: (any PrimaryAuthOutput)?

    @ObservationIgnored @Injected(\.serverConfigurationStorage)
    private var serverConfigurationStorage: any ServerConfigurationStorageProtocol
    @ObservationIgnored @Injected(\.appActionStorage)
    private var appActionStorage: AppActionStorage
    @ObservationIgnored @Injected(\.authService)
    private var authService: any AuthServiceProtocol
    @ObservationIgnored @Injected(\.seedService)
    private var seedService: any SeedServiceProtocol
    @ObservationIgnored @Injected(\.usecaseService)
    private var usecaseService: any UsecaseServiceProtocol
    @ObservationIgnored @Injected(\.workspaceService)
    private var workspaceService: any WorkspaceServiceProtocol
    @ObservationIgnored @Injected(\.pushNotificationsPermissionService)
    private var pushNotificationsPermissionService: any PushNotificationsPermissionServiceProtocol

    init(output: (any PrimaryAuthOutput)?, originalEditorCaller: OriginalEditorAuthCaller? = nil) {
        self.output = output
        self.originalEditorCaller = originalEditorCaller
        state = JoinFlowState(originalEditorCaller: originalEditorCaller)
    }

    // MARK: - Public

    func onAppear() {
        try? OriginalEditorAuthCaller.withUIAction(originalEditorCaller) {
            AnytypeAnalytics.instance().logMainAuthScreenShow()
            }
    }

    func startAppActionSubscription() async {
        for await action in appActionStorage.$action.values {
            guard acceptsOriginalUI else { return }
            guard let action else { continue }

            do {
                try OriginalEditorAuthCaller.withUIAction(originalEditorCaller) {
                    try handleAppAction(action: action)
                    appActionStorage.action = nil
                }
            } catch { /* The original unsupported/retired action remains unconsumed. */ }
        }
    }
    
    func onJoinButtonTap() {
        try? OriginalEditorAuthCaller.withUIAction(originalEditorCaller) {
            if state.mnemonic.isEmpty {
                createAccountTaskId = UUID().uuidString
            } else {
                onSuccess()
            }
            }
    }
    
    func onLoginButtonTap() {
        try? OriginalEditorAuthCaller.withUIAction(originalEditorCaller) {
            output?.onLoginSelected()
            }
    }
    
    func onSettingsButtonTap() {
        try? OriginalEditorAuthCaller.withUIAction(originalEditorCaller) {
            output?.onSettingsSelected()
            }
    }
    
    func onDebugMenuTap() {
        try? OriginalEditorAuthCaller.withUIAction(originalEditorCaller) {
            output?.onDebugMenuSelected()
            }
    }

    // MARK: - Create account step
    
    func createAccount() async {
        do {
            try await OriginalEditorAuthCaller.withUIOperation(originalEditorCaller) {
                await createAccountInOriginalFlow()
            }
        } catch {
            if acceptsOriginalUI { createAccountError(error) }
        }
    }

    private func createAccountInOriginalFlow() async {
        defer { if acceptsOriginalUI { createAccountTaskId = nil } }
        AnytypeAnalytics.instance().logStartCreateAccount()
        inProgress = true
        
        do {
            let mnemonic = try await originalAuthService.createWallet()
            try originalEditorCaller?.validateCurrent()
            state.mnemonic = mnemonic
            let iconOption = IconColorStorage.randomOption()
            let account = try await originalAuthService.createAccount(
                name: "",
                iconOption: iconOption,
                imagePath: ""
            )
            try originalEditorCaller?.validateCurrent()
            await pushNotificationsPermissionService.registerForRemoteNotificationsIfNeeded()
            try originalEditorCaller?.validateCurrent()
            try await setDefaultSpaceInfo(account.info.accountSpaceId, iconOption: iconOption)
            try originalEditorCaller?.validateCurrent()
            try? seedService.saveSeed(state.mnemonic)
            try originalEditorCaller?.validateCurrent()
            
            onSuccess()
        } catch {
            if acceptsOriginalUI { createAccountError(error) }
        }
    }
    
    private func setDefaultSpaceInfo(_ spaceId: String, iconOption: Int) async throws {
        guard spaceId.isNotEmpty else { return }
        if let caller = originalEditorCaller {
            _ = try? await caller.withNamedNativeRPC("ObjectImportUseCase") {
                try await usecaseService.setObjectImportDefaultUseCase(spaceId: spaceId)
            }
            try caller.validateCurrent()
            try? await caller.withNamedNativeRPC("WorkspaceSetInfo") {
                try await workspaceService.workspaceSetDetails(
                    spaceId: spaceId,
                    details: [.name(Loc.myFirstSpace), .iconOption(iconOption)]
                )
            }
            try caller.validateCurrent()
        } else {
            _ = try? await usecaseService.setObjectImportDefaultUseCase(spaceId: spaceId)
            try? await workspaceService.workspaceSetDetails(
                spaceId: spaceId,
                details: [.name(Loc.myFirstSpace), .iconOption(iconOption)]
            )
        }
    }
    
    private func onSuccess() {
        inProgress = false
        output?.onJoinSelected(state: state)
    }
    
    private func createAccountError(_ error: some Error) {
        inProgress = false
        errorText = error.localizedDescription
    }
    
    private func handleAppAction(action: AppAction) throws {
        switch action {
        case .createObjectFromQuickAction:
            throw AuthViewModelError.unsupportedAppAction
        case .deepLink(let deeplink, _):
            switch deeplink {
            case .networkConfig(let config):
                try updateNetworkConfig(config)
            case .quickCapture, .showSharingExtension, .galleryImport, .invite, .object, .membership, .hi, .chatMessage:
                throw AuthViewModelError.unsupportedAppAction
            }
        }
    }
    
    private func updateNetworkConfig(_ config: String) throws {
        try serverConfigurationStorage.addConfiguration(fileBase64Content: config, setupAsCurrent: true)
        AnytypeAnalytics.instance().logUploadNetworkConfiguration()
        AnytypeAnalytics.instance().logSelectNetwork(type: .selfHost, route: .deeplink)
    }
}
