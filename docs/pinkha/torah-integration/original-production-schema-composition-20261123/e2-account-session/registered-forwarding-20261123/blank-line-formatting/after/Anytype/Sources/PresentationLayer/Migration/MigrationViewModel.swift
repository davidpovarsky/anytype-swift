import Foundation
import Combine
import Services

struct MigrationModuleData: Identifiable {
    let id: String
    let onFinish: () async -> Void
    let originalEditorCaller: OriginalEditorAuthCaller?

    init(
        id: String, onFinish: @escaping () async -> Void,
        originalEditorCaller: OriginalEditorAuthCaller? = nil
    ) {
        self.id = id
        self.onFinish = onFinish
        self.originalEditorCaller = originalEditorCaller
    }
}

enum MigrationState: Equatable {
    case initial
    case progress
    case error(title: String, message: String)
}

@MainActor
@Observable
final class MigrationViewModel {

    @ObservationIgnored
    private let data: MigrationModuleData
    @ObservationIgnored
    private var activeProcess: Process?

    var progress: CGFloat = 0
    var startFlowId: String?
    var dismiss = false
    var state = MigrationState.initial

    @ObservationIgnored @Injected(\.accountMigrationService)
    private var accountMigrationService: any AccountMigrationServiceProtocol
    @ObservationIgnored @Injected(\.localRepoService)
    private var localRepoService: any LocalRepoServiceProtocol
    @ObservationIgnored @Injected(\.processSubscriptionService)
    private var processSubscriptionService: any ProcessSubscriptionServiceProtocol

    @ObservationIgnored
    private weak var output: (any MigrationModuleOutput)?
    @ObservationIgnored
    private var processSubscription: AnyCancellable?
    
    // MARK: - Initializer
    
    init(data: MigrationModuleData, output: (any MigrationModuleOutput)?) {
        self.data = data
        self.output = output
    }
    
    func startFlow() async {
        guard let caller = data.originalEditorCaller else {
            async let processSubscription: () = subscribeOnProcess()
            async let migration: () = startMigration()
            (_, _) = await (processSubscription, migration)
            return
        }
        do {
            try await caller.withUIOperation {
                try await subscribeOnOwnedProcess(caller)
                try caller.validateCurrent()
                await startMigration()
            }
        } catch {
            guard caller.isCurrent else { return }
            state = .error(title: Loc.error, message: Loc.unknownError)
        }
    }
    
    func startUpdate() {
        try? OriginalEditorAuthCaller.withUIAction(data.originalEditorCaller) {
            clearProcessData()
            state = .progress
            startFlowId = UUID().uuidString

        }
    }
    
    func readMore() {
        try? OriginalEditorAuthCaller.withUIAction(data.originalEditorCaller) {
            output?.onReadMoreTap()

        }
    }
    
    func onDebugTap() {
        try? OriginalEditorAuthCaller.withUIAction(data.originalEditorCaller) {
            output?.onDebugTap()

        }
    }
    
    private func subscribeOnProcess() async {
        processSubscription?.cancel()
        processSubscription = await processSubscriptionService.addHandler { [weak self] events in
            await self?.handleProcesses(events: events)
        }
    }
    
    /// Register the original process consumer before the real migration.
    /// Its callback retains this presentation's caller; progress is not a drain.
    private func subscribeOnOwnedProcess(_ caller: OriginalEditorAuthCaller) async throws {
        try caller.validateCurrent()
        processSubscription?.cancel()
        let subscription = await processSubscriptionService.addHandler { [weak self, caller] events in
            guard caller.isCurrent else { return }
            await self?.handleProcesses(events: events)
        }
        do {
            try caller.validateCurrent()
            processSubscription = subscription
        } catch {
            subscription.cancel()
            throw error
        }
    }

    private func startMigration() async {
        do {
            if let caller = data.originalEditorCaller {
                try await caller.withNamedNativeRPC("AccountMigrate") {
                    try await accountMigrationService.accountMigrate(id: data.id, rootPath: localRepoService.middlewareRepoPath)
                }
                try caller.validateCurrent()
            } else {
                try await accountMigrationService.accountMigrate(id: data.id, rootPath: localRepoService.middlewareRepoPath)
            }
            dismiss.toggle()
            await data.onFinish()
            try data.originalEditorCaller?.validateCurrent()
        } catch is CancellationError {
            // Ignore cancellations
        } catch let AccountMigrationError.notEnoughFreeSpace(requaredSpace) {
            guard data.originalEditorCaller?.isCurrent ?? true else { return }
            let size = ByteCountFormatter.fileFormatter.string(fromByteCount: requaredSpace)
            state = .error(
                title: Loc.Migration.Error.NotEnoughtSpace.title,
                message: Loc.Migration.Error.NotEnoughtSpace.message(size)
            )
        } catch {
            guard data.originalEditorCaller?.isCurrent ?? true else { return }
            state = .error(
                title: Loc.error,
                message: Loc.unknownError
            )
        }
    }
    
    func tryAgainTapped() {
        startUpdate()
    }
    
    private func clearProcessData() {
        activeProcess = nil
        progress = 0
    }
    
    private func handleProcesses(events: [ProcessEvent]) {
        try? OriginalEditorAuthCaller.withUIAction(data.originalEditorCaller) {
            for event in events {
                switch event {
                case .new(let process):
                    guard activeProcess.isNil else { return }
                    activeProcess = process
                    updateProgress(with: process)
                case .update(let process):
                    guard process.id == activeProcess?.id else { return }
                    activeProcess = process
                    updateProgress(with: process)
                case .done(let process):
                    guard process.id == activeProcess?.id else { return }
                    activeProcess = nil
                    updateProgress(with: process)
                }
            }

        }
    }
    
    private func updateProgress(with process: Process) {
        progress = CGFloat(process.progress.done) / CGFloat(process.progress.total)
    }
}
