import SwiftUI
@preconcurrency import Combine
import Services

@MainActor
@Observable
final class LoginViewModel {
    var phrase = ""
    var loadingInProgress = false
    var accountSelectInProgress = false
    var entropy: String = ""
    var errorText: String? {
        didSet {
            showError = errorText.isNotNil
        }
    }
    var showError: Bool = false
    var dismiss = false
    var accountId: String?
    var walletRecoveryTaskId: String?
    var logoutTaskId: String?
    var canRestoreFromKeychain: Bool = false

    var backButtonDisabled: Bool {
        loadingInProgress && !accountSelectInProgress
    }

    @ObservationIgnored @Injected(\.authService)
    private var authService: any AuthServiceProtocol
    @ObservationIgnored @Injected(\.seedService)
    private var seedService: any SeedServiceProtocol
    @ObservationIgnored @Injected(\.localAuthService)
    private var localAuthService: any LocalAuthServiceProtocol
    @ObservationIgnored @Injected(\.cameraPermissionVerifier)
    private var cameraPermissionVerifier: any CameraPermissionVerifierProtocol
    @ObservationIgnored @Injected(\.accountEventHandler)
    private var accountEventHandler: any AccountEventHandlerProtocol
    @ObservationIgnored @Injected(\.applicationStateService)
    private var applicationStateService: any ApplicationStateServiceProtocol
    @ObservationIgnored @Injected(\.pushNotificationsPermissionService)
    private var pushNotificationsPermissionService: any PushNotificationsPermissionServiceProtocol

    @ObservationIgnored
    private weak var output: (any LoginOutput)?
    
    @ObservationIgnored
    private let originalEditorCaller: OriginalEditorAuthCaller?
    @ObservationIgnored
    private let accountShowLifetime: EditorDocumentWriteLifetime?
    @ObservationIgnored
    private let accountShowCapture: EditorDocumentWriteCapture?
    @ObservationIgnored
    private let accountShowReadiness: OriginalApplicationConsumerDemand?
    @ObservationIgnored
    private var accountShowRetirement: EditorDocumentWriteLifetime.Observation?

    private var originalAuthService: any AuthServiceProtocol {
        if let originalEditorCaller { return originalEditorCaller }
        return authService
    }

    private var acceptsOriginalUI: Bool { originalEditorCaller?.isCurrent ?? true }

    init(output: (any LoginOutput)?, originalEditorCaller: OriginalEditorAuthCaller? = nil) {
        self.output = output
        self.originalEditorCaller = originalEditorCaller
        if let originalEditorCaller {
            let lifetime = EditorDocumentWriteLifetime()
            let readiness = OriginalApplicationConsumerDemand { lifetime.markUnavailable() }
            let capture = try? EditorDocumentWriteCapture(lifetime)
            accountShowLifetime = lifetime
            accountShowCapture = capture
            accountShowReadiness = readiness
            if capture == nil { readiness.end() }
            accountShowRetirement = originalEditorCaller.observeRetirement { readiness.end() }
        } else {
            accountShowLifetime = nil
            accountShowCapture = nil
            accountShowReadiness = nil
        }
    }

    deinit {
        accountShowRetirement?.cancel()
        accountShowReadiness?.end()
    }
    
    func onAppear() {
        try? OriginalEditorAuthCaller.withUIAction(originalEditorCaller) {
            AnytypeAnalytics.instance().logLoginScreenShow()
            canRestoreFromKeychain = (try? seedService.obtainSeed()).isNotNil
        
        }
    }
    
    func onEnterButtonAction() {
        try? OriginalEditorAuthCaller.withUIAction(originalEditorCaller) {
            AnytypeAnalytics.instance().logClickLogin(button: .phrase)
            walletRecoveryTaskId = UUID().uuidString
        
        }
    }
    
    func onScanQRButtonAction() async {
        do {
            try await OriginalEditorAuthCaller.withUIOperation(originalEditorCaller) {
                try await scanQRInOriginalFlow()
            }
        } catch {
            guard acceptsOriginalUI else { return }
            errorText = error.localizedDescription
        }
    }

    private func scanQRInOriginalFlow() async throws {
        AnytypeAnalytics.instance().logClickLogin(button: .qr)
        let isGranted = await cameraPermissionVerifier.cameraIsGranted()
        try originalEditorCaller?.validateCurrent()
        if isGranted {
            output?.onOpenQRCodeSelected(
                data: QrCodeScannerData(
                    entropy: Binding(
                        get: { self.acceptsOriginalUI ? self.entropy : "" },
                        set: { value in
                            try? OriginalEditorAuthCaller.withUIAction(self.originalEditorCaller) {
                                self.entropy = value
                            }
                        }
                    ),
                    error: Binding(
                        get: { self.acceptsOriginalUI ? self.errorText : nil },
                        set: { value in
                            try? OriginalEditorAuthCaller.withUIAction(self.originalEditorCaller) {
                                self.errorText = value
                            }
                        }
                    )
                )
            )
        } else {
            output?.onOpenSettingsSelected()
        }
    }
    
    func onKeychainButtonAction() async throws {
        try await OriginalEditorAuthCaller.withUIOperation(originalEditorCaller) {
            try await keychainInOriginalFlow()
        }
    }

    private func keychainInOriginalFlow() async throws {
        AnytypeAnalytics.instance().logClickLogin(button: .keychain)
        try await localAuthWithContinuation { [weak self] in
            guard let self else { return }
            try originalEditorCaller?.validateCurrent()
            phrase = try seedService.obtainSeed()
            await walletRecovery()
        }
    }
    
    func openPublicDebugMenuTap() {
        try? OriginalEditorAuthCaller.withUIAction(originalEditorCaller) {
            output?.onOpenPublicDebugMenuSelected()
        
        }
    }
    
    private func localAuthWithContinuation(_ continuation: @escaping () async throws -> Void) async throws {
        do {
            try await localAuthService.auth(reason: Loc.accessToKeyFromKeychain)
            try originalEditorCaller?.validateCurrent()
            try await continuation()
        } catch LocalAuthServiceError.passcodeNotSet {
            try originalEditorCaller?.validateCurrent()
            output?.onOpenSecureAlertSelected(
                data: SecureAlertData(completion: { [caller = originalEditorCaller] proceed in
                    guard proceed else { return }
                    try await OriginalEditorAuthCaller.withUIOperation(caller) {
                        try await continuation()
                    }
                })
            )
        }
    }
    
    func onbackButtonAction() {
        try? OriginalEditorAuthCaller.withUIAction(originalEditorCaller) {
            guard accountSelectInProgress else {
                dismiss.toggle()
                return
            }
            accountId = nil
            logoutAction()
        
        }
    }
    
    func logoutAction() {
        try? OriginalEditorAuthCaller.withUIAction(originalEditorCaller) {
            logoutTaskId = UUID().uuidString
        
        }
    }
    
    func logout() async {
        guard let caller = originalEditorCaller else {
            defer {
                logoutTaskId = nil
                dismiss.toggle()
            }
            try? await authService.logout(removeData: false)
            return
        }
        do {
            try await caller.withUIOperation {
                try await caller.logout(removeData: false)
                try caller.validateCurrent()
                logoutTaskId = nil
                dismiss.toggle()
            }
        } catch {
            guard caller.isCurrent else { return }
            // A failed original Stop keeps the same UI owner available to retry.
            logoutTaskId = nil
            errorText = error.localizedDescription
        }
    }
    
    func onEntropySet() async {
        do {
            try await OriginalEditorAuthCaller.withUIOperation(originalEditorCaller) {
                await entropyInOriginalFlow()
            }
        } catch {
            guard acceptsOriginalUI else { return }
            errorText = error.localizedDescription
        }
    }

    private func entropyInOriginalFlow() async {
        guard entropy.isNotEmpty else { return }
        do {
            let recoveredPhrase = try await originalAuthService.mnemonicByEntropy(entropy)
            try originalEditorCaller?.validateCurrent()
            phrase = recoveredPhrase
            await walletRecovery()
        } catch {
            guard acceptsOriginalUI else { return }
            errorText = error.localizedDescription
        }
    }

    func walletRecovery() async {
        do {
            try await OriginalEditorAuthCaller.withUIOperation(originalEditorCaller) {
                await walletRecoveryInOriginalFlow()
            }
        } catch {
            guard acceptsOriginalUI else { return }
            recoverWalletError(error)
        }
    }

    private func walletRecoveryInOriginalFlow() async {
        do {
            loadingInProgress = true
            
            if let readiness = accountShowReadiness {
                try await readiness.waitUntilRequested()
                try originalEditorCaller?.validateCurrent()
            }
            try await originalAuthService.walletRecovery(mnemonic: phrase.trimmingCharacters(in: .whitespacesAndNewlines))
            try originalEditorCaller?.validateCurrent()
            try accountShowReadiness?.validateRequested()
            try seedService.saveSeed(phrase)
            
            await recoverWalletSuccess()
        } catch {
            guard acceptsOriginalUI else { return }
            recoverWalletError(error)
        }
    }
    
    private func recoverWalletSuccess() async {
        await accountRecover()
    }
    
    private func recoverWalletError(_ error: some Error) {
        guard acceptsOriginalUI else { return }
        stopButtonsLoading()
        errorText = error.localizedDescription
        walletRecoveryTaskId = nil
    }
    
    func handleAccountShowEvent() async {
        guard let caller = originalEditorCaller else {
            for await accountId in await accountEventHandler.accountShowPublisher.values {
                self.accountId = accountId
            }
            return
        }
        guard let readiness = accountShowReadiness else { return }
        defer { readiness.end() }
        await withTaskCancellationHandler {
            guard caller.isCurrent else { return }
            let publisher = await accountEventHandler.accountShowPublisher
            guard caller.isCurrent, !Task.isCancelled else { return }
            for await accountId in OriginalDemandObservingPublisher(
                upstream: publisher, readiness: readiness
            ).values {
                try? caller.withUIAction { self.accountId = accountId }
            }
        } onCancel: {
            readiness.end()
        }
    }
    
    private func accountRecover() async {
        do {
            if let caller = originalEditorCaller {
                try await recoverWithOriginalConsumer(caller)
            } else {
                try await authService.accountRecover()
            }
        } catch {
            guard acceptsOriginalUI else { return }
            stopButtonsLoading()
            errorText = error.localizedDescription
        }
    }

    /// The original native AccountRecover can synchronously broadcast AccountShow.
    /// Admit it only with the real original consumer installed and requesting
    /// demand, retaining both that consumer and every preexisting Auth ancestor.
    private func recoverWithOriginalConsumer(_ caller: OriginalEditorAuthCaller) async throws {
        guard let readiness = accountShowReadiness, let capture = accountShowCapture else {
            throw OriginalApplicationConsumerDemand.ReadinessError.consumerEnded
        }
        try caller.validateCurrent()
        try readiness.validateRequested()
        let attempt = try OriginalAuthAttempt(kind: .ordinary, restricting: [capture])
        let admissions = try attempt.admitStage()
        try await withTaskCancellationHandler {
            do {
                try await OriginalAuthRequestContext.$parent.withValue(attempt) {
                    try await caller.accountRecover()
                }
                try attempt.validate()
                try readiness.validateRequested()
                for admission in admissions { admission.cancel() }
                attempt.finishOuter()
                await attempt.waitForDrain()
                try caller.validateCurrent()
            } catch {
                attempt.retire()
                for admission in admissions { admission.cancel() }
                attempt.finishOuter()
                await attempt.waitForDrain()
                throw error
            }
        } onCancel: {
            attempt.retire()
        }
    }
    
    func selectAccount() async {
        do {
            try await OriginalEditorAuthCaller.withUIOperation(originalEditorCaller) {
                await selectAccountInOriginalFlow()
            }
        } catch {
            // A late AccountShow or SwiftUI task cannot select for a new owner.
        }
    }

    private func selectAccountInOriginalFlow() async {
        guard let accountId else { return }
        defer {
            if acceptsOriginalUI {
                stopButtonsLoading()
                accountSelectInProgress = false
            }
        }
        do {
            accountSelectInProgress = true
            let account = try await originalAuthService.selectAccount(id: accountId, preferredSpaceId: "")
            try originalEditorCaller?.validateCurrent()
            
            switch account.status {
            case .active:
                applicationStateService.state = .home
            case .pendingDeletion:
                applicationStateService.state = .delete
            case .deleted:
                errorText = Loc.vaultDeleted
            }
            
            await pushNotificationsPermissionService.registerForRemoteNotificationsIfNeeded()
            try originalEditorCaller?.validateCurrent()
        } catch is CancellationError {
            // Ignore cancellations
        } catch SelectAccountError.accountLoadIsCanceled {
            // Ignore load cancellation
        } catch SelectAccountError.accountIsDeleted {
            guard acceptsOriginalUI else { return }
            errorText = Loc.vaultDeleted
        } catch SelectAccountError.failedToFetchRemoteNodeHasIncompatibleProtoVersion {
            guard acceptsOriginalUI else { return }
            errorText = Loc.Vault.Select.Incompatible.Version.Error.text
        } catch SelectAccountError.accountStoreNotMigrated {
            guard acceptsOriginalUI else { return }
            output?.onOpenMigrationSelected(
                data: MigrationModuleData(
                    id: accountId,
                    onFinish: { [weak self, caller = originalEditorCaller] in
                        guard caller?.isCurrent ?? true else { return }
                        await self?.selectAccount()
                    },
                    originalEditorCaller: originalEditorCaller
                )
            )
        } catch {
            guard acceptsOriginalUI else { return }
            errorText = Loc.selectVaultError
        }
    }
    
    private func stopButtonsLoading() {
        loadingInProgress = false
    }
}
