import SwiftUI
import UIKit
import Observation
import PinkhaAnyRuntime
import PinkhaAnyUI
import PinkhaAnyHost
import PinkhaAnyEngine
import PinkhaSharing

/// A scene keeps this owner while switching engines. Suspension waits for real
/// document/AI work and native shutdown before another scene can use the engine.
@MainActor
public final class AnyNativePresentationSession {
    fileprivate let model: AnyNativeRootModel

    public init(application: AnyNativeApplication, network: AnyEmbeddedNetwork = .official) {
        model = AnyNativeRootModel(application: application, network: network)
    }

    public func resume() { model.resume() }

    public func suspendAndWait() async {
        model.suspend()
        await model.waitForSuspension()
    }
}

@MainActor
public struct AnyNativeRootView: View {
    @State private var model: AnyNativeRootModel
    @Environment(\.scenePhase) private var scenePhase
    private let isActive: Bool

    public init(application: AnyNativeApplication, network: AnyEmbeddedNetwork = .official) {
        _model = State(initialValue: AnyNativeRootModel(application: application, network: network))
        isActive = true
    }

    public init(session: AnyNativePresentationSession, isActive: Bool = true) {
        _model = State(initialValue: session.model)
        self.isActive = isActive
    }

    public var body: some View {
        Group {
            switch model.page {
            case .starting:
                ProgressView("פותחים את המרחב שלך")
            case .accounts:
                accountView
            case .backup:
                backupView
            case .spaces:
                spacesView
            case .workspace:
                if let owner = model.workspace, let lifetime = model.presentationLifetime,
                   let recovery = model.libraryRecovery {
                    AnyNativeLibraryView(client: owner.client, session: owner.session,
                        objects: owner.objects, blocks: owner.blocks, capabilities: owner.capabilities,
                        onRequestClose: { await model.closeWorkspace(expectedSession: owner.session) },
                        lifetime: lifetime, recovery: recovery,
                        onManageMembers: { model.showMembers() })
                } else {
                    ProgressView()
                }
            }
        }
        .disabled(model.busy && model.page != .workspace)
        .alert("לא ניתן להשלים את הפעולה", isPresented: Binding(
            get: { model.errorMessage != nil },
            set: { if !$0 { model.errorMessage = nil } }
        )) {
            Button("סגור", role: .cancel) { model.errorMessage = nil }
        } message: { Text(model.errorMessage ?? "") }
        .sheet(isPresented: Binding(get: { model.showingMembers },
                                   set: { model.showingMembers = $0 })) {
            if let service = model.sharingService {
                PinkhaSpaceMembersView(service: service)
            }
        }
        .sheet(isPresented: Binding(get: { model.showingJoin },
                                   set: { model.showingJoin = $0 })) {
            PinkhaJoinSpaceView(join: { invitation in
                try await model.joinSpace(invitation: invitation)
            })
        }
        .task(id: isActive) {
            if isActive { model.resume() }
            else { model.suspend(); await model.waitForSuspension() }
        }
        .onOpenURL { url in _ = AnyMiniAppsReturnRouter.shared.receive(url) }
        .onChange(of: scenePhase) { _, phase in
            guard isActive else { return }
            if phase == .active { model.resume() }
            if phase == .background { model.suspend() }
        }
    }

    private var accountView: some View {
        NavigationStack {
            Form {
                if !model.runtimeReady {
                    Section {
                        Button("הפעל מחדש את המנוע", systemImage: "arrow.clockwise") { model.resume() }
                    }
                }
                if !model.savedAccounts.isEmpty {
                    Section("החשבונות במכשיר") {
                        ForEach(model.savedAccounts) { account in
                            Button {
                                model.open(account)
                            } label: {
                                Label(String(account.id.suffix(8)), systemImage: "person.crop.circle")
                            }
                            .accessibilityIdentifier("any-native-saved-account")
                            .disabled(!model.runtimeReady)
                        }
                    }
                }
                Section {
                    Button("יצירת חשבון חדש", systemImage: "person.badge.plus") { model.createAccount() }
                        .accessibilityIdentifier("any-native-account-create")
                        .disabled(!model.runtimeReady)
                }
                Section {
                    SecureField("ביטוי שחזור", text: $model.restorePhrase)
                        .accessibilityIdentifier("any-native-account-restore-phrase")
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .privacySensitive()
                    Picker("מקור החשבון", selection: $model.restoreIndex) {
                        Text("Any").tag(UInt32(1))
                        Text("חשבון Anytype קודם").tag(UInt32(0))
                    }
                    Button("שחזור") { model.restoreAccount() }
                        .accessibilityIdentifier("any-native-account-restore")
                        .disabled(!model.runtimeReady || model.restorePhrase.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                } header: {
                    Text("שחזור חשבון")
                } footer: {
                    Text("שחזור החשבון פותח את הזהות שלך. העברת מסמכים מהגרסה הקודמת נעשית בתהליך ייבוא נפרד.")
                }
            }
            .navigationTitle("Pinkha")
        }
    }

    private var backupView: some View {
        NavigationStack {
            Form {
                Section {
                    Text("שמור את ביטוי השחזור במקום פרטי. הוא מאפשר לשחזר את החשבון אם המכשיר אבד.")
                    if !model.recoveryText.isEmpty {
                        Text(model.recoveryText)
                            .font(.body.monospaced())
                            .textSelection(.enabled)
                            .environment(\.layoutDirection, .leftToRight)
                            .privacySensitive()
                    } else {
                        Button("הצגת ביטוי השחזור") { model.showRecovery() }
                            .accessibilityIdentifier("any-native-backup-show-phrase")
                    }
                }
                Section {
                    Toggle("שמרתי את ביטוי השחזור במקום בטוח", isOn: $model.backupAcknowledged)
                        .accessibilityIdentifier("any-native-backup-acknowledged")
                    Button("המשך") { model.acknowledgeBackup() }
                        .accessibilityIdentifier("any-native-backup-continue")
                        .disabled(!model.backupAcknowledged || model.recoveryText.isEmpty)
                }
            }
            .navigationTitle("גיבוי החשבון")
        }
    }

    private var spacesView: some View {
        NavigationStack {
            List {
                Section("המרחבים שלי") {
                    ForEach(model.spaces.filter { $0.status == "active" }) { space in
                        Button {
                            model.openSpace(space)
                        } label: {
                            Label(space.name.isEmpty ? "ללא שם" : space.name, systemImage: "books.vertical")
                        }
                    }
                    if model.spaces.isEmpty {
                        ContentUnavailableView("אין עדיין מרחבים", systemImage: "books.vertical",
                            description: Text("צור מרחב חדש כדי להתחיל."))
                    }
                }
                Section("מרחב חדש") {
                    TextField("שם המרחב", text: $model.newSpaceName)
                        .accessibilityIdentifier("any-native-space-name")
                    Button("יצירת מרחב") { model.createSpace() }
                        .accessibilityIdentifier("any-native-space-create")
                        .disabled(model.newSpaceName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
                Section {
                    Button("הצטרפות למרחב", systemImage: "person.crop.circle.badge.plus") { model.showingJoin = true }
                        .accessibilityIdentifier("any-native-space-join")
                    Button("רענון מרחבים", systemImage: "arrow.clockwise") { model.refreshSpaces() }
                    Button("יציאה מהחשבון", role: .destructive) { model.signOut() }
                        .accessibilityIdentifier("any-native-account-sign-out")
                }
            }
            .navigationTitle("המרחבים שלי")
        }
    }
}

@Observable
@MainActor
fileprivate final class AnyNativeRootModel {
    enum Page: Equatable { case starting, accounts, backup, spaces, workspace }
    let application: AnyNativeApplication
    let network: AnyEmbeddedNetwork
    var page = Page.starting
    var busy = false
    var errorMessage: String?
    var savedAccounts: [AnyNativeAccount] = []
    var account: AnyNativeAccount?
    var spaces: [AnyNativeSpace] = []
    var workspace: AnyNativeWorkspaceOwner?
    var sharingService: AnyNativeSharingService?
    var showingMembers = false
    var showingJoin = false
    var presentationLifetime: AnyUIPresentationLifetime?
    var libraryRecovery: AnyNativeLibraryRecovery?
    private struct RecoveryKey: Hashable {
        let accountID: String
        let spaceID: String
    }
    private var recoveries: [RecoveryKey: AnyNativeLibraryRecovery] = [:]
    var restorePhrase = ""
    var restoreIndex: UInt32 = 1
    var recoveryText = ""
    var backupAcknowledged = false
    var newSpaceName = ""
    private var operation: Task<Void, Never>?
    private var suspension: Task<Void, Never>?
    private var joining: Task<PinkhaSharingJoinResult, Error>?
    private var wantsForeground = true
    private var started = false
    var runtimeReady: Bool { started }
    private var lastAccountID: String?
    private var lastSpaceID: String?
    private var emergency: AnyEmbeddedEmergencyStop?
    private var backgroundTask = UIBackgroundTaskIdentifier.invalid
    private var epoch = UUID()

    init(application: AnyNativeApplication, network: AnyEmbeddedNetwork) {
        self.application = application; self.network = network
    }

    func resume() {
        wantsForeground = true
        guard suspension == nil, !started, operation == nil else { return }
        execute {
            if !(await self.application.isRunning()) {
                try await self.application.start(network: self.network)
            }
            try Task.checkCancellation()
            self.started = true
            self.emergency = await self.application.emergencyStop()
            if let pending = await self.application.pendingRecoveryAccount() {
                try Task.checkCancellation()
                self.account = pending
                self.lastAccountID = pending.id
                self.backupAcknowledged = false
                self.page = .backup
                return
            }
            self.savedAccounts = try await self.application.savedAccounts()
            try Task.checkCancellation()
            if let id = self.lastAccountID, self.savedAccounts.contains(where: { $0.id == id }) {
                let account = try await self.application.openSavedAccount(id: id)
                try Task.checkCancellation()
                try await self.didAuthenticate(account)
                if let spaceID = self.lastSpaceID, self.page == .spaces {
                    try await self.openSpaceOwned(id: spaceID)
                }
            } else {
                self.page = .accounts
            }
        }
    }

    func createAccount() {
        execute {
            let account = try await self.application.createAccount()
            try Task.checkCancellation()
            try await self.didAuthenticate(account)
        }
    }

    func restoreAccount() {
        let phrase = restorePhrase, index = restoreIndex
        restorePhrase = ""
        execute {
            let account = try await self.application.restoreAccount(mnemonic: phrase, derivationIndex: index)
            try Task.checkCancellation()
            try await self.didAuthenticate(account)
        }
    }

    func open(_ metadata: AnyNativeAccount) {
        execute {
            let account = try await self.application.openSavedAccount(id: metadata.id)
            try Task.checkCancellation()
            try await self.didAuthenticate(account)
        }
    }

    private func didAuthenticate(_ account: AnyNativeAccount) async throws {
        self.account = account
        lastAccountID = account.id
        backupAcknowledged = false
        if account.needsRecoveryBackup {
            let phrase = try await application.recoveryPhrase(accountID: account.id)
            try Task.checkCancellation()
            recoveryText = phrase
            page = .backup
        } else {
            try await loadSpaces()
        }
    }

    func showRecovery() {
        guard let id = account?.id else { return }
        execute {
            let phrase = try await self.application.recoveryPhrase(accountID: id)
            try Task.checkCancellation()
            self.recoveryText = phrase
        }
    }

    func acknowledgeBackup() {
        guard let id = account?.id, backupAcknowledged else { return }
        execute {
            try await self.application.acknowledgeRecoveryBackup(accountID: id)
            try Task.checkCancellation()
            self.recoveryText = ""
            self.account = await self.application.currentAccount()
            self.started = await self.application.isRunning()
            self.emergency = await self.application.emergencyStop()
            try await self.loadSpaces()
        }
    }

    private func loadSpaces() async throws {
        let values = try await application.listSpaces()
        try Task.checkCancellation()
        spaces = values
        page = .spaces
    }

    func refreshSpaces() { execute { try await self.loadSpaces() } }

    func showMembers() {
        guard page == .workspace, let workspace, presentationLifetime?.isActive == true else { return }
        do {
            sharingService = try AnyNativeSharingService(owner: workspace)
            showingMembers = true
        } catch { report(error) }
    }

    func joinSpace(invitation: String) async throws -> PinkhaSharingJoinResult {
        guard page == .spaces, started, account != nil,
              operation == nil, suspension == nil, joining == nil else {
            throw AnyNativeApplicationError.busy
        }
        let ticket = epoch
        let work = Task { @MainActor in
            let result = try await application.joinSpace(invitation: invitation)
            try Task.checkCancellation()
            guard ticket == epoch, wantsForeground else { throw CancellationError() }
            try await loadSpaces()
            return result
        }
        joining = work
        defer { joining = nil }
        return try await withTaskCancellationHandler {
            try await work.value
        } onCancel: { work.cancel() }
    }

    func createSpace() {
        let name = newSpaceName
        execute {
            let id = try await self.application.createSpace(name: name)
            try Task.checkCancellation()
            self.newSpaceName = ""
            try await self.openSpaceOwned(id: id)
        }
    }

    func openSpace(_ space: AnyNativeSpace) {
        execute { try await self.openSpaceOwned(id: space.id) }
    }

    private func openSpaceOwned(id: String) async throws {
        let owner = try await application.connectSpace(id: id)
        try Task.checkCancellation()
        let key = RecoveryKey(accountID: owner.workspace.accountID, spaceID: owner.workspace.spaceID)
        let recovery = recoveries[key] ?? AnyNativeLibraryRecovery(workspace: owner.workspace)
        recoveries[key] = recovery
        libraryRecovery = recovery
        workspace = owner
        presentationLifetime = AnyUIPresentationLifetime()
        lastSpaceID = id
        page = .workspace
    }

    func closeWorkspace(expectedSession: AnyApplicationSession) async {
        guard workspace?.session === expectedSession else { return }
        let task = execute {
            guard self.workspace?.session === expectedSession else { return }
            self.showingMembers = false
            self.sharingService = nil
            let lifetime = self.presentationLifetime
            lifetime?.revoke()
            await lifetime?.drain()
            try await self.application.closeSpace()
            try Task.checkCancellation()
            self.workspace = nil
            self.presentationLifetime = nil
            self.lastSpaceID = nil
            try await self.loadSpaces()
        }
        await task?.value
    }

    func signOut() {
        execute {
            self.showingMembers = false
            self.showingJoin = false
            self.sharingService = nil
            self.presentationLifetime?.revoke()
            await self.presentationLifetime?.drain()
            try await self.application.signOut()
            self.workspace = nil
            self.presentationLifetime = nil
            self.account = nil
            self.lastAccountID = nil
            self.lastSpaceID = nil
            self.recoveryText = ""
            self.savedAccounts = try await self.application.savedAccounts()
            self.page = .accounts
        }
    }

    func suspend() {
        wantsForeground = false
        recoveryText = ""
        restorePhrase = ""
        showingMembers = false
        showingJoin = false
        sharingService = nil
        presentationLifetime?.revoke()
        guard suspension == nil else { return }
        guard started || operation != nil || joining != nil || workspace != nil || emergency != nil else { return }
        epoch = UUID()
        let pending = operation
        pending?.cancel()
        let pendingJoin = joining
        pendingJoin?.cancel()
        let lifetime = presentationLifetime
        let stopSignal = emergency
        page = .starting
        backgroundTask = UIApplication.shared.beginBackgroundTask(withName: "Close native workspace") { [weak self] in
            stopSignal?.requestStop()
            Task { @MainActor in self?.endBackgroundTask() }
        }
        suspension = Task {
            await pending?.value
            _ = try? await pendingJoin?.value
            await lifetime?.drain()
            await application.stop()
            workspace = nil
            presentationLifetime = nil
            emergency = nil
            account = nil
            started = false
            busy = false
            endBackgroundTask()
            suspension = nil
            if wantsForeground { resume() }
        }
    }

    func waitForSuspension() async { await suspension?.value }

    private func endBackgroundTask() {
        guard backgroundTask != .invalid else { return }
        UIApplication.shared.endBackgroundTask(backgroundTask)
        backgroundTask = .invalid
    }

    @discardableResult
    private func execute(_ action: @escaping @MainActor () async throws -> Void) -> Task<Void, Never>? {
        guard operation == nil, suspension == nil, joining == nil else { return nil }
        busy = true
        let ticket = epoch
        let task = Task {
            defer {
                operation = nil
                if ticket == epoch { busy = false }
            }
            do { try await action() }
            catch is CancellationError { }
            catch {
                let running = await application.isRunning()
                let pending = await application.pendingRecoveryAccount()
                let stopSignal = await application.emergencyStop()
                guard ticket == epoch, !Task.isCancelled else { return }
                started = running
                emergency = stopSignal
                if let pending {
                    account = pending
                    lastAccountID = pending.id
                    recoveryText = ""
                    backupAcknowledged = false
                    page = .backup
                } else if page == .starting || !running {
                    page = .accounts
                }
                report(error)
            }
        }
        operation = task
        return task
    }

    private func report(_ error: any Error) {
        // Recovery phrases, control tokens, raw responses and private push keys
        // never enter user diagnostics or logs.
        switch error {
        case AnyNativeApplicationError.recoveryBackupRequired:
            errorMessage = AnyUIErrorText.text("יש לשמור את ביטוי השחזור לפני פתיחת המרחב.",
                "Save your recovery phrase before opening the Space.")
        case AnyEngineError.writeUncertain, AnyHostError.writeUncertain:
            errorMessage = AnyUIErrorText.text("עדיין לא ניתן לאשר את תוצאת הפעולה. רענן את המרחב לפני ניסיון נוסף.",
                "The result of the operation cannot be confirmed yet. Refresh the Space before trying again.")
        case AnyEmbeddedRuntimeError.unexpectedVersion, AnyUIActivationError.unexpectedRuntimeContract:
            errorMessage = AnyUIErrorText.text("גרסת האפליקציה אינה תואמת למנוע. יש להתקין בנייה תואמת.",
                "This app version does not match the engine. Install a matching build.")
        case AnyNativeApplicationError.secureStorageUnavailable:
            errorMessage = AnyUIErrorText.text("לא ניתן לשמור כעת את החשבון במכשיר. שמור את ביטוי השחזור המוצג במסך הגיבוי ונסה שוב; פתיחת מסמכים תתאפשר לאחר שהשמירה תאושר.",
                "Your account cannot be saved on this device right now. Keep the recovery phrase shown on the backup screen and try again. Documents will become available after saving is confirmed.")
        case AnyNativeApplicationError.busy:
            errorMessage = AnyUIErrorText.text("פעולה אחרת עדיין מסתיימת. נסה שוב לאחר סיומה.",
                "Another operation is still finishing. Try again after it completes.")
        default:
            errorMessage = AnyUIErrorText.text("הפעולה לא הושלמה. אפשר לנסות שוב או לפתוח מחדש את האפליקציה.",
                "The operation did not complete. Try again or reopen the app.")
        }
    }
}
