import SwiftUI

@MainActor
@Observable
final class KeyPhraseViewModel {

    var key: String
    var keyShown: Bool {
        didSet {
            if state.originalEditorCaller?.isCurrent ?? true { state.keyShown = keyShown }
        }
    }
    var showMoreInfo = false
    var snackBar: ToastBarData?

    @ObservationIgnored
    let state: JoinFlowState

    @ObservationIgnored
    private weak var output: (any JoinFlowStepOutput)?
    
    init(
        state: JoinFlowState,
        output: (any JoinFlowStepOutput)?
    ) {
        self.state = state
        self.key = state.mnemonic
        self.keyShown = state.keyShown
        self.output = output
    }
    
    func onAppear() {
        try? OriginalEditorAuthCaller.withUIAction(state.originalEditorCaller) {
            AnytypeAnalytics.instance().logScreenOnboarding(step: .phrase)
        }
    }
    
    func onPrimaryButtonTap() {
        try? OriginalEditorAuthCaller.withUIAction(state.originalEditorCaller) {
            if keyShown {
                output?.onNext()
            } else {
                AnytypeAnalytics.instance().logClickOnboarding(step: .phrase, button: .showAndCopy)
                keyShown = true
            }
        }
    }

    func onSecondaryButtonTap() {
        try? OriginalEditorAuthCaller.withUIAction(state.originalEditorCaller) {
            AnytypeAnalytics.instance().logClickOnboarding(step: .phrase, button: .checkLater)
            output?.onNext()
        }
    }

    func onPhraseTap() {
        try? OriginalEditorAuthCaller.withUIAction(state.originalEditorCaller) {
            if keyShown {
                copy()
            } else {
                keyShown = true
            }
        }
    }
    
    func keyPhraseMoreInfo() -> AnyView? {
        guard state.originalEditorCaller?.isCurrent ?? true else { return nil }
        AnytypeAnalytics.instance().logClickOnboarding(step: .phrase, button: .moreInfo)
        return output?.keyPhraseMoreInfo()
    }
    
    private func copy() {
        try? OriginalEditorAuthCaller.withUIAction(state.originalEditorCaller) {
            AnytypeAnalytics.instance().logClickOnboarding(step: .phrase, button: .showAndCopy)
            UISelectionFeedbackGenerator().selectionChanged()
            UIPasteboard.general.string = state.mnemonic
            snackBar = ToastBarData(Loc.copied)
        }
    }
}
