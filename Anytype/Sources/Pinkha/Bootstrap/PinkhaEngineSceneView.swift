#if PINKHA_DUAL_ENGINE_RUNTIME
import Foundation
import SwiftUI
import UIKit
import Observation
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

    func restore(for scene: String) async {
        visibleScenes.insert(scene)
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
                // Construct the private account store before changing the active UI.
                if anyPresentation == nil {
                    let application = try PinkhaEmbeddedAnyApplication(
                        dataDirectory: PinkhaEmbeddedAnyApplication.defaultDataDirectory(),
                        credentialService: "io.pinkha.anynative.accounts.v1")
                    anyPresentation = PinkhaEmbeddedAnyPresentation(application: application)
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
            }
        }
    }

    private func resumeHeartServices() async throws {
        let account = Container.shared.accountManager().account.id
        if !account.isEmpty {
            try await PinkhaSharingAccountOwner.shared.didOpen(engine: .heart, accountID: account)
        }
        try PinkhaHanlinAccountOwner.shared.activateEngine(PinkhaHanlinEngineNamespace.heart)
    }

    func releaseWindow(_ scene: String) async {
        visibleScenes.remove(scene)
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
        .disabled(owner.switching)
        .safeAreaInset(edge: .top, spacing: 0) {
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
        .alert("החלפת מנוע", isPresented: Binding(
            get: { owner.problem != nil }, set: { if !$0 { owner.problem = nil } }
        )) {
            Button("סגור", role: .cancel) { owner.problem = nil }
        } message: { Text(owner.problem ?? "") }
        .task { await owner.restore(for: scene) }
        .onDisappear { Task { await owner.releaseWindow(scene) } }
        .onOpenURL { _ in
            // Existing app links belong to the existing Heart router. Make its
            // retained coordinator visible before a user follows the routed result.
            Task { await owner.select(.heart, for: scene) }
        }
    }
}
#endif
