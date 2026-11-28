#if PINKHA_DUAL_ENGINE_RUNTIME
import Foundation
import SwiftUI
import UIKit
import Observation
import Combine
import Factory
import PinkhaEngineHost
import PinkhaHanlinCore
import PinkhaSharing
import PinkhaAnyEngine

enum PinkhaAppEngine: String, CaseIterable, Identifiable {
    case heart, any
    var id: String { rawValue }
    var name: String { self == .heart ? "Heart" : "Any" }
}

/// There is one native Any controller per process and one presentation lease.
/// Existing Heart scenes retain their coordinator, editor state and native account.
@MainActor @Observable
final class PinkhaEngineSceneOwner {
    static let shared = PinkhaEngineSceneOwner()
    private static let preferenceKey = "pinkha.app.selected-engine.v1"

    private(set) var engine = PinkhaAppEngine.heart
    private(set) var anyWindow: String?
    private(set) var anyPresentation: PinkhaEmbeddedAnyPresentation?
    private(set) var switching = false
    var problem: String?
    private var restored = false
    private var visibleScenes = Set<String>()
    private var heartMiniAppsHold: UUID?

    // One source review owns one actual Full wallet session until native close
    // succeeds. A failed close retains that ownership for a visible retry.
    private(set) var currentSource: PinkhaHeartSourceSelection?
    private(set) var sourceReview: PinkhaEmbeddedHeartSourceReview?
    private(set) var sourceReviewPresented = false
    private(set) var sourceWindow: String?
    private(set) var sourceCapturing = false
    private(set) var sourceClosing = false
    private(set) var sourceProblem: String?
    private var sourceBinding: PinkhaHeartSourceSelection?
    @ObservationIgnored private var sourceController: PinkhaHeartSourceCaptureController?
    @ObservationIgnored private var sourceCaptureTask: Task<PinkhaEmbeddedHeartSourceReview, Error>?
    @ObservationIgnored private var sourceCleanup: Task<Void, Error>?
    @ObservationIgnored private var sourceTicket: UUID?

    private(set) var selectingMigrationDestination = false
    private(set) var migrationConfirmationPresented = false
    private(set) var migrationDestination: PinkhaEmbeddedAnyDestinationSelection?
    private(set) var migrationRunning = false
    private(set) var migrationNotice: String?
    private(set) var importedDocuments: PinkhaImportedDocumentsPresentation?
    private(set) var importedWindow: String?
    @ObservationIgnored private var migrationSelections: PinkhaMigrationSelectionStore?
    @ObservationIgnored private var migrationRun: PinkhaMigrationRunOwner?
    @ObservationIgnored private var migrationTask: Task<PinkhaMigrationSelectionStore.CompletedSelection, Error>?
    @ObservationIgnored private var importedOpenTicket: UUID?

    var sourceSpaceName: String { sourceBinding?.spaceName ?? "" }
    var sourceAccountID: String { sourceBinding?.accountID ?? "" }
    var sourceSpaceID: String { sourceBinding?.spaceID ?? "" }

    private func selectionStore() throws -> PinkhaMigrationSelectionStore {
        if let migrationSelections { return migrationSelections }
        let store = try PinkhaMigrationSelectionStore(
            privateDirectory: PinkhaMigrationSelectionStore.privateDirectory())
        migrationSelections = store
        return store
    }

    /// This is the only engine transition that retains an explicitly reviewed
    /// source. Ordinary switches still close it before changing engines.
    func chooseMigrationDestination(for scene: String) async {
        guard engine == .heart, !switching, !sourceCapturing, !sourceClosing,
              migrationRun == nil, sourceReview != nil,
              let ticket = sourceTicket, let bound = sourceBinding,
              Self.sameSource(bound, PinkhaHeartSourceSelection.current()),
              sourceWindow == scene, visibleScenes.contains(scene) else { return }
        sourceReviewPresented = false
        migrationNotice = nil
        await select(.any, for: scene, retainingSource: ticket)
        guard sourceTicket == ticket, sourceBinding != nil else { return }
        if engine == .any, anyWindow == scene, visibleScenes.contains(scene),
           Self.sameSource(bound, PinkhaHeartSourceSelection.current()) {
            selectingMigrationDestination = true
        } else {
            sourceReviewPresented = true
        }
    }

    func reviewMigrationDestination(for scene: String) async {
        guard selectingMigrationDestination, !migrationRunning, !sourceClosing,
              !switching, engine == .any, anyWindow == scene,
              visibleScenes.contains(scene), let ticket = sourceTicket,
              let bound = sourceBinding, sourceReview != nil,
              let presentation = anyPresentation else { return }
        do {
            let destination = try await presentation.selectedDestination()
            try Task.checkCancellation()
            guard sourceTicket == ticket, selectingMigrationDestination,
                  engine == .any, anyWindow == scene, anyPresentation === presentation,
                  visibleScenes.contains(scene),
                  Self.sameSource(bound, PinkhaHeartSourceSelection.current()) else {
                throw PinkhaMigrationSelectionError.changedSelection
            }
            migrationDestination = destination
            migrationConfirmationPresented = true
        } catch {
            guard !(error is CancellationError), sourceTicket == ticket,
                  selectingMigrationDestination, engine == .any,
                  anyWindow == scene, anyPresentation === presentation,
                  visibleScenes.contains(scene) else { return }
            problem = PinkhaMigrationText.text("Open the destination Space in Any, then choose it again.")
        }
    }

    func chooseAnotherMigrationDestination() {
        guard !migrationRunning, !sourceClosing else { return }
        migrationConfirmationPresented = false
        migrationDestination = nil
    }

    private static func sameDestination(_ first: PinkhaEmbeddedAnyDestinationSelection,
                                        _ second: PinkhaEmbeddedAnyDestinationSelection) -> Bool {
        Data(first.accountID.utf8) == Data(second.accountID.utf8)
            && Data(first.spaceID.utf8) == Data(second.spaceID.utf8)
            && Data(first.networkID.utf8) == Data(second.networkID.utf8)
    }

    /// The button confirming the displayed source and destination is the only
    /// caller. Re-read the selected scope before preparing any durable intent.
    func confirmMigration(for scene: String) async {
        guard migrationConfirmationPresented, selectingMigrationDestination,
              !migrationRunning, !sourceClosing, !switching,
              engine == .any, anyWindow == scene, visibleScenes.contains(scene),
              let ticket = sourceTicket, let bound = sourceBinding,
              let review = sourceReview, let controller = sourceController,
              let selected = migrationDestination, let presentation = anyPresentation else { return }
        migrationRunning = true
        defer {
            if sourceController === controller { migrationRunning = false }
        }
        do {
            let current = try await presentation.selectedDestination()
            try Task.checkCancellation()
            guard sourceTicket == ticket, migrationConfirmationPresented,
                  engine == .any, anyWindow == scene, anyPresentation === presentation,
                  visibleScenes.contains(scene),
                  Self.sameSource(bound, PinkhaHeartSourceSelection.current()),
                  Self.sameDestination(selected, current) else {
                throw PinkhaMigrationSelectionError.changedSelection
            }
            let run = PinkhaMigrationRunOwner(source: controller, review: review,
                destination: current, presentation: presentation, selections: try selectionStore())
            migrationRun = run
            migrationConfirmationPresented = false
            let task = Task { try await run.execute() }
            // Register the real invocation before suspension so account/engine
            // changes and cancellation join its late outcome retention too.
            migrationTask = task
            _ = try await task.value
            // An external drain may already have retired this source and
            // admitted a fresh review. This caller owns only its captured source.
            guard sourceController === controller else { return }
            let mayNotify = sourceTicket == ticket && !sourceClosing
                && engine == .any && anyWindow == scene && visibleScenes.contains(scene)
            try await endSourceReview(.release)
            if mayNotify, sourceController == nil,
               engine == .any, anyWindow == scene,
               anyPresentation === presentation, visibleScenes.contains(scene) {
                migrationNotice = PinkhaMigrationText.text("The import is saved. Open Imported documents to review the result.")
            }
        } catch {
            guard sourceController === controller else { return }
            // A failed native close retains this exact owner for a visible
            // retry. Do not turn it into an automatic second cleanup attempt.
            if sourceTicket != ticket, sourceBinding != nil, sourceProblem != nil {
                problem = sourceProblem
                return
            }
            let wasCancelled = error is CancellationError || sourceTicket != ticket || sourceClosing
            do { try await endSourceReview(.cancel) }
            catch {
                guard sourceController === controller else { return }
                problem = sourceProblem
                return
            }
            if !wasCancelled, sourceController == nil,
               engine == .any, anyWindow == scene,
               anyPresentation === presentation, visibleScenes.contains(scene) {
                problem = PinkhaMigrationText.text("The import did not finish. Saved progress and the original source are retained. Review Imported documents before trying again.")
            }
        }
    }

    func cancelMigration() async {
        migrationNotice = nil
        do { try await endSourceReview(.cancel) }
        catch { problem = sourceProblem }
    }

    func dismissMigrationNotice() { migrationNotice = nil }

    func showSavedImports(for scene: String) async {
        guard engine == .any, anyWindow == scene, !switching,
              visibleScenes.contains(scene), !migrationRunning, !sourceClosing,
              importedDocuments == nil, importedOpenTicket == nil,
              let presentation = anyPresentation else { return }
        let ticket = UUID()
        importedOpenTicket = ticket
        defer {
            if importedOpenTicket == ticket { importedOpenTicket = nil }
        }
        do {
            let destination = try await presentation.selectedDestination()
            try Task.checkCancellation()
            guard importedOpenTicket == ticket, engine == .any, anyWindow == scene,
                  anyPresentation === presentation, !switching,
                  visibleScenes.contains(scene) else { return }
            let model = PinkhaImportedDocumentsPresentation(presentation: presentation,
                destination: destination, selections: try selectionStore())
            importedDocuments = model
            importedWindow = scene
            migrationNotice = nil
            await model.loadSaved()
        } catch {
            guard importedOpenTicket == ticket else { return }
            problem = PinkhaMigrationText.text("Open the destination Space in Any to review its imported documents.")
        }
    }

    func dismissImportedDocuments() async {
        importedOpenTicket = nil
        guard let model = importedDocuments else {
            importedWindow = nil
            return
        }
        model.requestClose()
        await model.closeAndDrain()
        if importedDocuments === model {
            importedDocuments = nil
            importedWindow = nil
        }
    }

    func suspendMigration(for scene: String) async {
        if importedWindow == scene { await dismissImportedDocuments() }
        if sourceWindow == scene, selectingMigrationDestination || migrationRunning {
            do { try await endSourceReview(.cancel) }
            catch { problem = sourceProblem }
        }
    }

    func captureSource(for scene: String) async {
        guard engine == .heart, !switching, !sourceClosing, visibleScenes.contains(scene) else { return }
        if sourceBinding != nil {
            sourceWindow = scene
            sourceReviewPresented = true
            return
        }
        guard let selected = PinkhaHeartSourceSelection.current() else {
            problem = PinkhaMigrationText.text("Open a Space in your Heart account before reviewing a migration source.")
            return
        }
        do {
            if sourceController == nil {
                sourceController = try PinkhaHeartSourceCaptureController(
                    privateDirectory: PinkhaHeartSourceSelection.privateDirectory(),
                    obtainSeed: { try Container.shared.seedService().obtainSeed() })
            }
            guard let controller = sourceController else { return }
            let ticket = UUID()
            sourceTicket = ticket
            sourceBinding = selected
            sourceWindow = scene
            sourceProblem = nil
            sourceReview = nil
            sourceReviewPresented = true
            sourceCapturing = true
            let task = Task { try await controller.capture(accountID: selected.accountID, spaceID: selected.spaceID) }
            sourceCaptureTask = task
            do {
                let review = try await task.value
                guard sourceTicket == ticket, engine == .heart,
                      Self.sameSource(selected, PinkhaHeartSourceSelection.current()) else {
                    if sourceTicket == ticket { try await endSourceReview(.accountChanged) }
                    return
                }
                sourceReview = review
            } catch {
                guard sourceTicket == ticket else { return }
                sourceProblem = PinkhaMigrationText.text("The source review could not be completed. Your original data is retained. Close the review and try again.")
            }
            if sourceTicket == ticket {
                sourceCaptureTask = nil
                sourceCapturing = false
            }
        } catch {
            sourceProblem = PinkhaMigrationText.text("The source review cannot be opened right now.")
            problem = sourceProblem
        }
    }

    private enum SourceEnd { case accountChanged, engineChanged, cancel, release }

    private func endSourceReview(_ reason: SourceEnd) async throws {
        if let cleanup = sourceCleanup {
            try await cleanup.value
            return
        }
        guard let controller = sourceController, sourceBinding != nil else {
            sourceReviewPresented = false
            sourceWindow = nil
            return
        }
        sourceTicket = nil
        migrationConfirmationPresented = false
        sourceClosing = true
        let pending = sourceCaptureTask
        let pendingMigration = migrationTask
        let run = migrationRun
        let task = Task {
            do {
                if let run {
                    let closeReason: PinkhaMigrationRunOwner.CloseReason
                    switch reason {
                    case .accountChanged: closeReason = .accountChanged
                    case .engineChanged: closeReason = .engineChanged
                    case .cancel: closeReason = .cancel
                    case .release: closeReason = .release
                    }
                    try await run.closeAndDrain(closeReason)
                } else {
                switch reason {
                case .accountChanged: try await controller.invalidate(reason: .accountChanged)
                case .engineChanged: try await controller.invalidate(reason: .engineChanged)
                case .cancel: try await controller.cancel()
                case .release: try await controller.release()
                }
                }
            } catch {
                _ = try? await pending?.value
                _ = try? await pendingMigration?.value
                throw error
            }
            _ = try? await pending?.value
            _ = try? await pendingMigration?.value
        }
        sourceCleanup = task
        defer {
            sourceCleanup = nil
            sourceClosing = false
            sourceCapturing = false
            sourceCaptureTask = nil
            migrationTask = nil
            migrationRunning = false
        }
        do {
            try await task.value
            // A later review gets a fresh owner after this complete drain.
            sourceController = nil
            migrationRun = nil
            selectingMigrationDestination = false
            migrationDestination = nil
            sourceReview = nil
            sourceBinding = nil
            sourceProblem = nil
            sourceReviewPresented = false
            sourceWindow = nil
        } catch {
            sourceReview = nil
            sourceProblem = PinkhaMigrationText.text("The source session could not be closed. It is retained for another close attempt; the engine switch did not complete.")
            throw error
        }
    }

    func dismissSourceReview() async {
        do { try await endSourceReview(sourceCapturing ? .cancel : .release) }
        catch { problem = sourceProblem }
    }

    // Called by the original authentication decorator before its native account
    // mutation. Stream observation below also invalidates externally changed UI.
    func prepareHeartAccountChange() async throws {
        try await endSourceReview(.accountChanged)
    }

    private static func sameSource(_ first: PinkhaHeartSourceSelection,
                                   _ second: PinkhaHeartSourceSelection?) -> Bool {
        guard let second else { return false }
        return Data(first.accountID.utf8) == Data(second.accountID.utf8)
            && Data(first.spaceID.utf8) == Data(second.spaceID.utf8)
    }

    func refreshSourceSelection() async {
        let current = PinkhaHeartSourceSelection.current()
        currentSource = current
        guard let bound = sourceBinding, !Self.sameSource(bound, current) else { return }
        do { try await endSourceReview(.accountChanged) }
        catch { problem = sourceProblem }
    }

    func observeHeartAccount() async {
        await refreshSourceSelection()
        for await _ in Container.shared.accountManager().accountPublisher.values {
            if Task.isCancelled { return }
            await refreshSourceSelection()
        }
    }

    func observeHeartSpace() async {
        await refreshSourceSelection()
        for await _ in Container.shared.activeSpaceManager().workspaceInfoStream {
            if Task.isCancelled { return }
            await refreshSourceSelection()
        }
    }

    func restore(for scene: String) async {
        visibleScenes.insert(scene)
        await refreshSourceSelection()
        guard !restored else { return }
        restored = true
        if UserDefaults.standard.string(forKey: Self.preferenceKey) == PinkhaAppEngine.any.rawValue {
            await select(.any, for: scene)
        }
    }

    func select(_ selected: PinkhaAppEngine, for scene: String) async {
        await select(selected, for: scene, retainingSource: nil)
    }

    private func select(_ selected: PinkhaAppEngine, for scene: String,
                        retainingSource: UUID?) async {
        guard !switching, !scene.isEmpty,
              selected != engine || (selected == .any && anyWindow != scene) || problem != nil else { return }
        switching = true
        defer { switching = false }
        UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder),
                                        to: nil, from: nil, for: nil)
        do {
            await dismissImportedDocuments()
            migrationNotice = nil
            if let retainingSource {
                guard selected == .any, engine == .heart,
                      sourceTicket == retainingSource, sourceReview != nil,
                      let bound = sourceBinding,
                      Self.sameSource(bound, PinkhaHeartSourceSelection.current()) else {
                    throw PinkhaMigrationSelectionError.changedSelection
                }
            } else {
                try await endSourceReview(.engineChanged)
            }
            switch selected {
            case .any:
                // Construct the private account store before changing the active UI.
                if anyPresentation == nil {
                    let configuration = try PinkhaEmbeddedAnyLaunchConfiguration.current()
                    let application = try PinkhaEmbeddedAnyApplication(
                        dataDirectory: configuration.dataDirectory,
                        credentialService: configuration.credentialService)
                    anyPresentation = PinkhaEmbeddedAnyPresentation(application: application)
                }
                if heartMiniAppsHold == nil {
                    heartMiniAppsHold = try await PinkhaMiniAppsCoordinator.shared.prepareEngineAccountChange()
                }
                try await PinkhaHanlinAccountOwner.shared.deactivateEngine(PinkhaHanlinEngineNamespace.heart)
                await PinkhaSharingAccountOwner.shared.closeAndDrain(engine: .heart)
                if engine == .any && anyWindow != scene {
                    await anyPresentation?.suspendAndWait()
                }
                if let retainingSource {
                    guard sourceTicket == retainingSource, sourceReview != nil,
                          let bound = sourceBinding,
                          Self.sameSource(bound, PinkhaHeartSourceSelection.current()) else {
                        throw PinkhaMigrationSelectionError.changedSelection
                    }
                }
                try PinkhaHanlinAccountOwner.shared.activateEngine(PinkhaHanlinEngineNamespace.any)
                anyWindow = scene
                engine = .any
                anyPresentation?.resume()
            case .heart:
                try await PinkhaHanlinAccountOwner.shared.deactivateEngine(PinkhaHanlinEngineNamespace.any)
                await anyPresentation?.suspendAndWait()
                anyWindow = nil
                try await resumeHeartServices()
                engine = .heart
            }
            if engine == .any, !visibleScenes.contains(scene) {
                await anyPresentation?.suspendAndWait()
                if anyWindow == scene { anyWindow = nil }
            }
            UserDefaults.standard.set(selected.rawValue, forKey: Self.preferenceKey)
            problem = nil
        } catch {
            // Never reinterpret an incomplete transition as a successful engine switch.
            // Data and native account credentials stay in their existing private stores.
            problem = PinkhaMigrationText.text("The engine switch could not be completed. Wait for the operation to finish and try again.")
            if engine == .heart {
                try? await resumeHeartServices()
            } else {
                try? PinkhaHanlinAccountOwner.shared.activateEngine(PinkhaHanlinEngineNamespace.any)
                anyPresentation?.resume()
            }
        }
    }

    private func resumeHeartServices() async throws {
        let account = Container.shared.accountManager().account.id
        if !account.isEmpty {
            try await PinkhaSharingAccountOwner.shared.didOpen(engine: .heart, accountID: account)
        }
        try PinkhaHanlinAccountOwner.shared.activateEngine(PinkhaHanlinEngineNamespace.heart)
        if let token = heartMiniAppsHold {
            PinkhaMiniAppsCoordinator.shared.resumeAfterAccountChange(token)
            heartMiniAppsHold = nil
        }
    }

    func releaseWindow(_ scene: String) async {
        visibleScenes.remove(scene)
        if importedWindow == scene || anyWindow == scene {
            await dismissImportedDocuments()
        }
        if sourceWindow == scene {
            do { try await endSourceReview(.cancel) }
            catch { sourceWindow = nil; problem = sourceProblem }
        }
        guard anyWindow == scene, !switching else { return }
        switching = true
        defer { switching = false }
        await anyPresentation?.suspendAndWait()
        if anyWindow == scene { anyWindow = nil }
    }
}

@MainActor
struct PinkhaEngineSceneView<HeartContent: View>: View {
    @State private var owner = PinkhaEngineSceneOwner.shared
    @Environment(\.scenePhase) private var scenePhase
    @SceneStorage("pinkha.app.engine-window.v1") private var scene = UUID().uuidString
    private let heart: HeartContent

    init(@ViewBuilder heart: () -> HeartContent) { self.heart = heart() }

    var body: some View {
        // A physical row keeps the shared selector outside each engine's real
        // UIKit navigation bar. A safe-area overlay at the common ZStack root
        // lets embedded navigation bars keep their window-top coordinates.
        VStack(spacing: 0) {
            engineBar
            migrationBar
            engineContent
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .clipped()
        }
        .disabled(owner.switching)
        .sheet(isPresented: Binding(
            get: { owner.sourceReviewPresented && owner.sourceWindow == scene },
            set: { showing in
                if !showing && owner.sourceReviewPresented {
                    Task { await owner.dismissSourceReview() }
                }
            }
        )) {
            NavigationStack {
                Group {
                    if let review = owner.sourceReview {
                        PinkhaEmbeddedHeartSourceReviewView(review: review, spaceName: owner.sourceSpaceName)
                    } else {
                        VStack(spacing: 16) {
                            if owner.sourceCapturing || owner.sourceClosing { ProgressView() }
                            Text(owner.sourceSpaceName).font(.headline)
                            Text(owner.sourceProblem ?? PinkhaMigrationText.text("Reading the source data and its original permissions. No destination data is being written."))
                                .multilineTextAlignment(.center)
                        }
                        .padding()
                    }
                }
                .navigationTitle(PinkhaMigrationText.text("Review Heart source"))
                .toolbar {
                    ToolbarItem(placement: .confirmationAction) {
                        Button(PinkhaMigrationText.text("Choose destination")) {
                            Task { await owner.chooseMigrationDestination(for: scene) }
                        }
                        .disabled(owner.sourceReview == nil || owner.sourceCapturing || owner.sourceClosing)
                        .accessibilityIdentifier("pinkha.engine.migration.choose-destination")
                    }
                    ToolbarItem(placement: .cancellationAction) {
                        Button(owner.sourceCapturing ? PinkhaMigrationText.text("Cancel") : PinkhaMigrationText.text("Close review")) {
                            Task { await owner.dismissSourceReview() }
                        }
                        .disabled(owner.sourceClosing)
                        .accessibilityIdentifier("pinkha.engine.migration.close-review")
                    }
                }
            }
            .interactiveDismissDisabled(true)
        }
        .sheet(isPresented: Binding(
            get: { owner.migrationConfirmationPresented && owner.sourceWindow == scene },
            set: { showing in if !showing { owner.chooseAnotherMigrationDestination() } }
        )) {
            migrationConfirmation
        }
        .sheet(isPresented: Binding(
            get: { owner.importedDocuments != nil && owner.importedWindow == scene },
            set: { showing in if !showing { Task { await owner.dismissImportedDocuments() } } }
        )) {
            if let model = owner.importedDocuments {
                PinkhaImportedDocumentsView(model: model,
                    onClose: { await owner.dismissImportedDocuments() })
            }
        }
        .alert("Pinkha", isPresented: Binding(
            get: { owner.problem != nil }, set: { if !$0 { owner.problem = nil } }
        )) {
            Button(PinkhaMigrationText.text("Close"), role: .cancel) { owner.problem = nil }
        } message: { Text(owner.problem ?? "") }
        .task { await owner.restore(for: scene) }
        .task { await owner.observeHeartAccount() }
        .task { await owner.observeHeartSpace() }
        .onDisappear { Task { await owner.releaseWindow(scene) } }
        .onChange(of: scenePhase) { _, phase in
            if phase == .background { Task { await owner.suspendMigration(for: scene) } }
        }
        .onOpenURL { url in
            // An Any return is admitted only from its immutable local SDK request.
            // Other existing links keep the original Heart routing.
            let target: PinkhaAppEngine = PinkhaEmbeddedAnyMiniAppsReturnRouter.shared.receive(url) ? .any : .heart
            Task { await owner.select(target, for: scene) }
        }
    }

    @ViewBuilder
    private var migrationBar: some View {
        if owner.sourceWindow == scene,
           owner.selectingMigrationDestination || owner.migrationRunning || owner.sourceClosing {
            HStack(spacing: 12) {
                if owner.migrationRunning || owner.sourceClosing { ProgressView() }
                Text(owner.sourceClosing
                     ? PinkhaMigrationText.text("Closing the source and waiting for active work.")
                     : owner.migrationRunning
                     ? PinkhaMigrationText.text("Importing into the confirmed Space. You can cancel and keep saved progress.")
                     : PinkhaMigrationText.text("Open a destination Space in Any, then choose Use this Space."))
                    .font(.footnote)
                Spacer()
                if !owner.migrationRunning && !owner.sourceClosing {
                    Button(PinkhaMigrationText.text("Use this Space")) {
                        Task { await owner.reviewMigrationDestination(for: scene) }
                    }
                    .accessibilityIdentifier("pinkha.engine.migration.use-destination")
                }
                Button(PinkhaMigrationText.text("Cancel"), role: .cancel) {
                    Task { await owner.cancelMigration() }
                }
                .disabled(owner.sourceClosing)
                .accessibilityIdentifier("pinkha.engine.migration.cancel")
            }
            .padding()
            .background(.thinMaterial)
        } else if owner.anyWindow == scene, let notice = owner.migrationNotice {
            HStack(spacing: 12) {
                Text(notice).font(.footnote)
                Spacer()
                Button(PinkhaMigrationText.text("Imported documents")) {
                    Task { await owner.showSavedImports(for: scene) }
                }
                Button(PinkhaMigrationText.text("Close")) { owner.dismissMigrationNotice() }
            }
            .padding()
            .background(.thinMaterial)
        }
    }

    private var migrationConfirmation: some View {
        NavigationStack {
            Form {
                Section(PinkhaMigrationText.text("Source")) {
                    LabeledContent(PinkhaMigrationText.text("Engine"), value: "Heart")
                    if !owner.sourceSpaceName.isEmpty {
                        LabeledContent(PinkhaMigrationText.text("Space"), value: owner.sourceSpaceName)
                    }
                    LabeledContent(PinkhaMigrationText.text("Account ID"), value: owner.sourceAccountID)
                    LabeledContent(PinkhaMigrationText.text("Space ID"), value: owner.sourceSpaceID)
                }
                if let destination = owner.migrationDestination {
                    Section(PinkhaMigrationText.text("Destination")) {
                        LabeledContent(PinkhaMigrationText.text("Engine"), value: "Any")
                        if !destination.displayName.isEmpty {
                            LabeledContent(PinkhaMigrationText.text("Space"), value: destination.displayName)
                        }
                        LabeledContent(PinkhaMigrationText.text("Account ID"), value: destination.accountID)
                        LabeledContent(PinkhaMigrationText.text("Space ID"), value: destination.spaceID)
                    }
                }
                Section {
                    Text(PinkhaMigrationText.text("The original Heart source is retained. Import creates data in the displayed destination. Cancellation keeps saved progress for review."))
                    Button(PinkhaMigrationText.text("Import into this Space")) {
                        Task { await owner.confirmMigration(for: scene) }
                    }
                    .disabled(owner.migrationRunning || owner.sourceClosing)
                    .accessibilityIdentifier("pinkha.engine.migration.confirm")
                    Button(PinkhaMigrationText.text("Choose another Space")) {
                        owner.chooseAnotherMigrationDestination()
                    }
                    .disabled(owner.migrationRunning || owner.sourceClosing)
                }
            }
            .navigationTitle(PinkhaMigrationText.text("Confirm import"))
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(PinkhaMigrationText.text("Cancel"), role: .cancel) {
                        Task { await owner.cancelMigration() }
                    }
                    .disabled(owner.sourceClosing)
                }
            }
        }
        .interactiveDismissDisabled(true)
    }

    private var engineContent: some View {
        ZStack {
            // Keeping this subtree mounted preserves the original app's coordinator,
            // navigation, editor drafts and live native account while it is hidden.
            heart
                .opacity(owner.engine == .heart ? 1 : 0)
                .allowsHitTesting(owner.engine == .heart && !owner.switching)
                .accessibilityHidden(owner.engine != .heart)
            if owner.engine == .any {
                if owner.anyWindow == scene, let presentation = owner.anyPresentation {
                    PinkhaEmbeddedAnyRootView(session: presentation)
                } else {
                    ContentUnavailableView {
                        Label(PinkhaMigrationText.text("This Space is open in another window"), systemImage: "rectangle.on.rectangle")
                    } actions: {
                        Button(PinkhaMigrationText.text("Open in this window")) { Task { await owner.select(.any, for: scene) } }
                            .accessibilityIdentifier("pinkha.engine.claim-window")
                    }
                }
            }
        }
    }

    private var engineBar: some View {
        HStack {
            Text("Pinkha").font(.headline)
            Spacer()
            if owner.switching { ProgressView() }
            Menu {
                ForEach(PinkhaAppEngine.allCases) { engine in
                    Button {
                        Task { await owner.select(engine, for: scene) }
                    } label: {
                        Label(engine.name, systemImage: owner.engine == engine ? "checkmark.circle.fill" : "circle")
                    }
                    .accessibilityIdentifier("pinkha.engine.select." + engine.rawValue)
                }
                if owner.engine == .any {
                    Divider()
                    Button(PinkhaMigrationText.text("Imported documents"), systemImage: "tray.full") {
                        Task { await owner.showSavedImports(for: scene) }
                    }
                    .disabled(owner.anyWindow != scene || owner.migrationRunning || owner.sourceClosing)
                    .accessibilityIdentifier("pinkha.engine.migration.imported-documents")
                }
                if owner.engine == .heart {
                    Divider()
                    Button(PinkhaMigrationText.text("Review migration source"), systemImage: "doc.text.magnifyingglass") {
                        Task { await owner.captureSource(for: scene) }
                    }
                    .accessibilityIdentifier("pinkha.engine.migration.review-source")
                    .disabled(owner.currentSource == nil || owner.sourceClosing)
                }
            } label: {
                Label(owner.engine.name, systemImage: "arrow.triangle.2.circlepath")
            }
            .accessibilityLabel(PinkhaMigrationText.text("Engine"))
            .accessibilityValue(owner.engine.name)
            .accessibilityIdentifier("pinkha.engine.selector")
            .disabled(owner.switching)
        }
        .padding(.horizontal)
        .frame(minHeight: 44)
        .background(.ultraThinMaterial)
    }
}
#endif
