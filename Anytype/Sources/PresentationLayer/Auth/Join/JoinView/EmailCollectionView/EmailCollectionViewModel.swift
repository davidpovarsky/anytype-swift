import SwiftUI
import Services

@MainActor
@Observable
final class EmailCollectionViewModel {

    var inputText: String {
        didSet {
            if state.originalEditorCaller?.isCurrent ?? true { state.email = inputText }
        }
    }
    var inProgress = false
    var saveEmailTaskId: String? = nil
    var showIncorrectEmailError = false

    // MARK: - DI

    @ObservationIgnored
    private let state: JoinFlowState
    @ObservationIgnored
    private weak var output: (any JoinBaseOutput)?

    @ObservationIgnored @Injected(\.membershipService)
    private var membershipService: any MembershipServiceProtocol
    
    init(state: JoinFlowState, output: (any JoinBaseOutput)?) {
        self.state = state
        self.inputText = state.email
        self.output = output
    }
    
    func onAppear() {
        try? OriginalEditorAuthCaller.withUIAction(state.originalEditorCaller) {
            AnytypeAnalytics.instance().logScreenOnboarding(step: .email)
        }
    }
    
    func onNextAction() {
        try? OriginalEditorAuthCaller.withUIAction(state.originalEditorCaller) {
            if state.email.isValidEmail() {
                showIncorrectEmailError = false
                saveEmailTaskId = UUID().uuidString
            } else {
                showIncorrectEmailError = true
            }
        }
    }
    
    func onSkipAction() {
        try? OriginalEditorAuthCaller.withUIAction(state.originalEditorCaller) {
            AnytypeAnalytics.instance().logScreenOnboardingSkipEmail()
            onSuccess()
        }
    }
    
    func saveEmail() async {
        guard let caller = state.originalEditorCaller else {
            startLoading()
            try? await membershipService.getVerificationEmailOnOnboarding(email: state.email)
            AnytypeAnalytics.instance().logScreenOnboardingEnterEmail()
            onSuccess()
            return
        }
        do {
            try await caller.withUIOperation {
                startLoading()
                try? await caller.withNamedNativeRPC("MembershipV2SubscribeToUpdates") {
                    try await membershipService.getVerificationEmailOnOnboarding(email: state.email)
                }
                try caller.validateCurrent()
                AnytypeAnalytics.instance().logScreenOnboardingEnterEmail()
                onSuccess()
            }
        } catch {
            if caller.isCurrent { saveEmailError(error) }
        }
    }
    
    private func onSuccess() {
        stopLoading()
        if state.originalEditorCaller != nil { state.originalKeyboardDismiss?() }
        else { UIApplication.shared.hideKeyboard() }
        output?.onNext()
    }
    
    private func saveEmailError(_ error: some Error) {
        stopLoading()
        output?.onError(error)
    }
    
    private func startLoading() {
        output?.disableBackAction(true)
        inProgress = true
    }
    
    private func stopLoading() {
        output?.disableBackAction(false)
        inProgress = false
    }
}
