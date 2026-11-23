import SwiftUI

@MainActor
@Observable
final class JoinViewModel: JoinBaseOutput, JoinFlowStepOutput {

    var step: JoinStep = JoinStep.firstStep
    var forward = true
    var errorText: String? {
        didSet {
            showError = errorText.isNotNil
        }
    }
    var showError: Bool = false
    var backButtonDisabled: Bool = false
    var dismiss = false

    @ObservationIgnored
    let state: JoinFlowState

    @ObservationIgnored @Injected(\.applicationStateService)
    private var applicationStateService: any ApplicationStateServiceProtocol
    @ObservationIgnored @Injected(\.accountManager)
    private var accountManager: any AccountManagerProtocol
    @ObservationIgnored @Injected(\.serverConfigurationStorage)
    private var serverConfigurationStorage: any ServerConfigurationStorageProtocol
    
    init(state: JoinFlowState) {
        self.state = state
        
        if step == .email, shouldSkipEmailStep() {
            onNext(with: step)
        }
    }
    
    func onBackButtonTap() {
        try? OriginalEditorAuthCaller.withUIAction(state.originalEditorCaller) {
            onBack()
        }
    }
    
    func setOwnedKeyboardDismiss(_ dismiss: KeyboardDismiss) {
        guard let caller = state.originalEditorCaller else { return }
        try? caller.withUIAction { state.originalKeyboardDismiss = dismiss }
    }

    // MARK: - JoinBaseOutput
    
    func onNext() {
        try? OriginalEditorAuthCaller.withUIAction(state.originalEditorCaller) {
            onNext(with: step)
        }
    }
    
    func onBack() {
        try? OriginalEditorAuthCaller.withUIAction(state.originalEditorCaller) {
            onBack(with: step)
        }
    }
    
    func onError(_ error: some Error) {
        try? OriginalEditorAuthCaller.withUIAction(state.originalEditorCaller) {
            errorText = error.localizedDescription
        }
    }
    
    func disableBackAction(_ disable: Bool) {
        try? OriginalEditorAuthCaller.withUIAction(state.originalEditorCaller) {
            backButtonDisabled = disable
        }
    }
    
    func keyPhraseMoreInfo() -> AnyView? {
        KeyPhraseMoreInfoView().eraseToAnyView()
    }
    
    private func onNext(with currentStep: JoinStep) {
        guard let nextStep = currentStep.next else {
            finishFlow()
            return
        }
        
        if nextStep == .email, shouldSkipEmailStep() {
            onNext(with: nextStep)
            return
        }
        
        forward = true
        
        withAnimation {
            step = nextStep
        }
    }
    
    private func onBack(with currentStep: JoinStep) {
        guard let previousStep = currentStep.previous else {
            dismiss.toggle()
            return
        }
        
        if previousStep == .email && shouldSkipEmailStep() {
            onBack(with: previousStep)
            return
        }
        
        if state.originalEditorCaller != nil { state.originalKeyboardDismiss?() }
        else { UIApplication.shared.hideKeyboard() }
        forward = false
        
        withAnimation {
            step = previousStep
        }
    }
    
    private func finishFlow() {
        guard state.originalEditorCaller?.isCurrent ?? true else { return }
        applicationStateService.state = .home
        sendSelectedOptions()
        AnytypeAnalytics.instance().logAccountOpen(
            analyticsId: accountManager.account.info.analyticsId
        )
    }
    
    private func sendSelectedOptions() {
        for option in state.selectedPersonaOptions {
            AnytypeAnalytics.instance().logClickOnboarding(step: .persona, type: option.analyticsValue)
        }
        
        for option in state.selectedUseCaseOptions {
            AnytypeAnalytics.instance().logClickOnboarding(step: .useCase, type: option.analyticsValue)
        }
    }
    
    private func shouldSkipEmailStep() -> Bool {
        serverConfigurationStorage.currentConfiguration() == .localOnly
    }
}
