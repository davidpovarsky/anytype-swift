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

    var sourceSpaceName: String { sourceBinding?.spaceName ?? "" }

    func captureSource(for scene: String) async {
        guard engine == .heart, !switching, !sourceClosing, visibleScenes.contains(scene) else { return }
        if sourceBinding != nil {
            sourceWindow = scene
            sourceReviewPresented = true
            return
        }
        guard let selected = PinkhaHeartSourceSelection.current() else {
            problem = "יש לפתוח מרחב בחשבון Heart לפני בדיקת המקור להעברה."
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
                sourceProblem = "לא ניתן להשלים את בדיקת המקור. הנתונים המקוריים נשמרו. סגור את הבדיקה ונסה שוב."
            }
            if sourceTicket == ticket {
                sourceCaptureTask = nil
                sourceCapturing = false
            }
        } catch {
            sourceProblem = "לא ניתן לפתוח את בדיקת המקור כעת."
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
        sourceClosing = true
        let pending = sourceCaptureTask
        let task = Task {
            do {
                switch reason {
                case .accountChanged: try await controller.invalidate(reason: .accountChanged)
                case .engineChanged: try await controller.invalidate(reason: .engineChanged)
                case .cancel: try await controller.cancel()
                case .release: try await controller.release()
                }
            } catch {
                _ = try? await pending?.value
                throw error
            }
            _ = try? await pending?.value
        }
        sourceCleanup = task
        defer {
            sourceCleanup = nil
            sourceClosing = false
            sourceCapturing = false
            sourceCaptureTask = nil
        }
        do {
            try await task.value
            sourceReview = nil
            sourceBinding = nil
            sourceProblem = nil
            sourceReviewPresented = false
            sourceWindow = nil
        } catch {
            sourceReview = nil
            sourceProblem = "לא ניתן לסגור כעת את הרשאת המקור. הפעולה נשמרה לסגירה חוזרת; לא בוצעה העברה למנוע האחר."
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
        guard !switching, !scene.isEmpty,
              selected != engine || (selected == .any && anyWindow != scene) || problem != nil else { return }
        switching = true
        defer { switching = false }
        UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder),
                                        to: nil, from: nil, for: nil)
        do {
            switch selected {
            case .any:
                try await endSourceReview(.engineChanged)
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
            problem = "לא ניתן להשלים את המעבר כעת. המתן לסיום הפעולה ונסה שוב."
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
    @SceneStorage("pinkha.app.engine-window.v1") private var scene = UUID().uuidString
    private let heart: HeartContent

    init(@ViewBuilder heart: () -> HeartContent) { self.heart = heart() }

    var body: some View {
        // A physical row keeps the shared selector outside each engine's real
        // UIKit navigation bar. A safe-area overlay at the common ZStack root
        // lets embedded navigation bars keep their window-top coordinates.
        VStack(spacing: 0) {
            engineBar
            engineContent
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .clipped()
        }
        .disabled(owner.switching)
        .sheet(isPresented: Binding(
            get: { owner.sourceReviewPresented && owner.sourceWindow == scene },
            set: { showing in if !showing { Task { await owner.dismissSourceReview() } } }
        )) {
            NavigationStack {
                Group {
                    if let review = owner.sourceReview {
                        PinkhaEmbeddedHeartSourceReviewView(review: review, spaceName: owner.sourceSpaceName)
                    } else {
                        VStack(spacing: 16) {
                            if owner.sourceCapturing || owner.sourceClosing { ProgressView() }
                            Text(owner.sourceSpaceName).font(.headline)
                            Text(owner.sourceProblem ?? "נקראים נתוני המקור וההרשאות המקוריות. לא מתבצעת כתיבה ליעד.")
                                .multilineTextAlignment(.center)
                        }
                        .padding()
                    }
                }
                .navigationTitle("בדיקת מקור Heart")
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) {
                        Button(owner.sourceCapturing ? "ביטול" : "סגירה") {
                            Task { await owner.dismissSourceReview() }
                        }
                        .disabled(owner.sourceClosing)
                        .accessibilityIdentifier("pinkha.engine.migration.close-review")
                    }
                }
            }
            .interactiveDismissDisabled(true)
        }
        .alert("Pinkha", isPresented: Binding(
            get: { owner.problem != nil }, set: { if !$0 { owner.problem = nil } }
        )) {
            Button("סגור", role: .cancel) { owner.problem = nil }
        } message: { Text(owner.problem ?? "") }
        .task { await owner.restore(for: scene) }
        .task { await owner.observeHeartAccount() }
        .task { await owner.observeHeartSpace() }
        .onDisappear { Task { await owner.releaseWindow(scene) } }
        .onOpenURL { url in
            // An Any return is admitted only from its immutable local SDK request.
            // Other existing links keep the original Heart routing.
            let target: PinkhaAppEngine = PinkhaEmbeddedAnyMiniAppsReturnRouter.shared.receive(url) ? .any : .heart
            Task { await owner.select(target, for: scene) }
        }
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
                        Label("המרחב פתוח בחלון אחר", systemImage: "rectangle.on.rectangle")
                    } actions: {
                        Button("פתיחה בחלון הזה") { Task { await owner.select(.any, for: scene) } }
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
                if owner.engine == .heart {
                    Divider()
                    Button("סקירת מקור להעברה", systemImage: "doc.text.magnifyingglass") {
                        Task { await owner.captureSource(for: scene) }
                    }
                    .accessibilityIdentifier("pinkha.engine.migration.review-source")
                    .disabled(owner.currentSource == nil || owner.sourceClosing)
                }
            } label: {
                Label(owner.engine.name, systemImage: "arrow.triangle.2.circlepath")
            }
            .accessibilityLabel("מנוע")
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
