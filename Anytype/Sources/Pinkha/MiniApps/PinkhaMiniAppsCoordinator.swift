import Foundation
import Combine
import SwiftUI
import UIKit
import DeepLinks
import HanlinMiniAppsBridge
import HanlinMiniAppsPicker

@MainActor
final class PinkhaMiniAppsCoordinator {
    static let shared = PinkhaMiniAppsCoordinator()

    private final class Registration {
        weak var editor: EditorPageController?
        var subscriptions: Set<AnyCancellable> = []
        init(editor: EditorPageController) { self.editor = editor }
    }
    private var registrations: [ObjectIdentifier: Registration] = [:]
    private var preparing = Set<ObjectIdentifier>()
    private var applying = Set<UUID>()
    private struct DocumentIdentity: Hashable {
        let account: String
        let space: String
        let object: String
    }
    private var applyingDocuments = Set<DocumentIdentity>()
    private var reported = Set<UUID>()

    func attach(editor: EditorPageController) {
        let id = ObjectIdentifier(editor)
        guard registrations[id] == nil else { consume(editor: editor); return }
        let registration = Registration(editor: editor)
        registrations[id] = registration
        editor.viewModel.document.syncPublisher.receive(on: DispatchQueue.main).sink { [weak self, weak editor] _ in
            guard let editor else { return }
            self?.consume(editor: editor)
        }.store(in: &registration.subscriptions)
        NotificationCenter.default.publisher(for: UIScene.didActivateNotification)
            .receive(on: DispatchQueue.main).sink { [weak self, weak editor] _ in
                guard let editor else { return }
                self?.consume(editor: editor)
            }.store(in: &registration.subscriptions)
        consume(editor: editor)
    }

    func detach(editor: EditorPageController) {
        registrations.removeValue(forKey: ObjectIdentifier(editor))
    }

    func present(editor: EditorPageController, range: NSRange? = nil) {
        let id = ObjectIdentifier(editor)
        guard isVisible(editor), editor.presentedViewController == nil,
              preparing.insert(id).inserted else { return }
        Task { [weak self, weak editor] in
            guard let self, let editor else { return }
            defer { preparing.remove(id) }
            do {
                let store = try MiniAppBridgeStore(appGroupIdentifier: "group.com.itorah.shared")
                let context = try await PinkhaMiniAppsContext.capture(editor: editor, store: store, range: range)
                guard isVisible(editor),
                      context.source.documentID == editor.viewModel.document.objectId,
                      context.source.metadata["anytype.accountID"] == Container.shared.accountManager().account.id
                else { throw PinkhaMiniAppsError.documentUnavailable }
                let picker = MiniAppPicker(store: store, source: context.source,
                    inputs: context.inputs,
                    operation: context.source.selection?.text.isEmpty == false ? .replaceSelection : .insert,
                    callbacks: PinkhaMiniAppsContext.callbacks,
                    onOpen: { [weak self, weak editor] url in
                        guard let self, let editor else { return }
                        // The shared picker already initiates its own dismissal.
                        UIApplication.shared.open(url, options: [:]) { opened in
                            guard !opened else { return }
                            Task { @MainActor in
                                if let presentation = editor.presentedViewController {
                                    presentation.dismiss(animated: true) {
                                        self.show(error: PinkhaMiniAppsError.companionMissing, on: editor)
                                    }
                                } else {
                                    self.show(error: PinkhaMiniAppsError.companionMissing, on: editor)
                                }
                            }
                        }
                    })
                let controller = UIHostingController(rootView: picker)
                controller.modalPresentationStyle = .pageSheet
                controller.sheetPresentationController?.detents = [.medium(), .large()]
                controller.sheetPresentationController?.prefersGrabberVisible = true
                editor.present(controller, animated: true)
            } catch { show(error: error, on: editor) }
        }
    }

    /// Uses the existing queued object route for cold starts and an exact mounted
    /// editor for warm returns. The bridge file remains pending until that editor saves.
    func routeCallback(_ url: URL) -> (handled: Bool, link: DeepLink?) {
        guard url.scheme == PinkhaMiniAppsContext.callbacks.success?.scheme,
              url.host == "miniapps", url.path == "/return" else { return (false, nil) }
        guard let id = MiniAppBridgeStore.requestID(from: url),
              let store = try? MiniAppBridgeStore(appGroupIdentifier: "group.com.itorah.shared"),
              let request = try? store.request(id: id),
              request.source.appID == PinkhaMiniAppsContext.sourceAppID,
              let objectID = request.source.documentID,
              let spaceID = request.source.metadata["anytype.spaceID"]
        else { return (true, nil) }
        let editors = registrations.values.compactMap(\.editor).filter {
            isVisible($0) && $0.viewModel.document.objectId == objectID &&
                $0.viewModel.document.spaceId == spaceID
        }
        let original = editors.first {
            $0.viewIfLoaded?.window?.windowScene?.session.persistentIdentifier == request.source.sceneID
        } ?? editors.first
        if let original {
            consume(editor: original)
            return (true, nil)
        }
        return (true, .object(objectId: objectID, spaceId: spaceID))
    }

    func consume(editor: EditorPageController, skipping: Set<UUID> = []) {
        guard isVisible(editor), editor.viewModel.document.isOpened,
              editor.presentedViewController == nil,
              let store = try? MiniAppBridgeStore(appGroupIdentifier: "group.com.itorah.shared"),
              let results = try? store.pendingResults(sourceAppID: PinkhaMiniAppsContext.sourceAppID)
        else { return }
        let document = editor.viewModel.document
        let identity = DocumentIdentity(account: Container.shared.accountManager().account.id,
            space: document.spaceId, object: document.objectId)
        guard !applyingDocuments.contains(identity) else { return }
        for result in results {
            guard !skipping.contains(result.requestID), !applying.contains(result.requestID),
                  let request = try? store.request(id: result.requestID),
                  request.source.documentID == document.objectId,
                  request.source.metadata["anytype.spaceID"] == document.spaceId,
                  request.source.metadata["anytype.accountID"] == Container.shared.accountManager().account.id
            else { continue }
            applying.insert(result.requestID)
            applyingDocuments.insert(identity)
            Task { [weak self, weak editor] in
                guard let self else { return }
                defer {
                    applying.remove(result.requestID)
                    applyingDocuments.remove(identity)
                    if let editor { consume(editor: editor, skipping: skipping.union([result.requestID])) }
                }
                guard let editor, isVisible(editor) else { return }
                do {
                    if result.status == .cancelled {
                        _ = try store.acknowledgeResult(id: result.requestID, sourceAppID: request.source.appID)
                    } else if result.status == .error || result.operation == .display || result.operation == .custom {
                        presentResult(result, request: request, store: store, editor: editor)
                    } else {
                        // End native editing before applying the return to avoid an old
                        // first-responder buffer subsequently writing over its saved result.
                        editor.view.endEditing(true)
                        let preserved = try await PinkhaMiniAppsResultApplier.apply(
                            request: request, result: result, editor: editor, store: store)
                        if preserved { show(message: PinkhaMiniAppsStrings.sourceChanged, on: editor) }
                    }
                    reported.remove(result.requestID)
                } catch {
                    if reported.insert(result.requestID).inserted { show(error: error, on: editor) }
                }
            }
            // Serialize mutations for one editor, including separate invocations.
            break
        }
    }

    private func presentResult(_ result: MiniAppResult, request: MiniAppInvocation,
                               store: MiniAppBridgeStore, editor: EditorPageController) {
        guard editor.presentedViewController == nil else { return }
        let controller = PinkhaMiniAppsResultController(result: result, store: store) { [weak self, weak editor] in
            do {
                _ = try store.acknowledgeResult(id: result.requestID, sourceAppID: request.source.appID)
                if let editor { self?.consume(editor: editor) }
            } catch {
                if let editor { self?.show(error: error, on: editor) }
            }
        }
        controller.modalPresentationStyle = .pageSheet
        controller.sheetPresentationController?.detents = [.medium(), .large()]
        controller.sheetPresentationController?.prefersGrabberVisible = true
        controller.presentationController?.delegate = controller
        editor.present(controller, animated: true)
    }

    private func isVisible(_ editor: EditorPageController) -> Bool {
        editor.viewIfLoaded?.window?.windowScene?.activationState == .foregroundActive
    }

    private func show(error: Error, on editor: EditorPageController) {
        show(message: error.localizedDescription, on: editor)
    }

    private func show(message: String, on editor: EditorPageController) {
        guard isVisible(editor), editor.presentedViewController == nil else { return }
        let alert = UIAlertController(title: PinkhaMiniAppsStrings.title, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: PinkhaMiniAppsStrings.close, style: .cancel) { [weak self, weak editor, weak alert] _ in
            alert?.dismiss(animated: true) {
                if let editor { self?.consume(editor: editor) }
            }
        })
        editor.present(alert, animated: true)
    }
}

@MainActor
private final class PinkhaMiniAppsResultController: UIHostingController<PinkhaMiniAppsResultView>, UIAdaptivePresentationControllerDelegate {
    private let onClosed: () -> Void
    private var finished = false

    init(result: MiniAppResult, store: MiniAppBridgeStore, onClosed: @escaping () -> Void) {
        self.onClosed = onClosed
        super.init(rootView: PinkhaMiniAppsResultView(result: result, store: store, onDone: {}))
        rootView = PinkhaMiniAppsResultView(result: result, store: store) { [weak self] in
            guard let self else { return }
            dismiss(animated: true) { self.finish() }
        }
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) { fatalError("unavailable initializer") }

    func presentationControllerDidDismiss(_ presentationController: UIPresentationController) {
        finish()
    }

    private func finish() {
        guard !finished else { return }
        finished = true
        onClosed()
    }
}

private struct PinkhaMiniAppsResultView: View {
    let result: MiniAppResult
    let store: MiniAppBridgeStore
    let onDone: () -> Void

    var body: some View {
        NavigationStack {
            List {
                if let message = result.message, !message.isEmpty {
                    Text(message).textSelection(.enabled)
                }
                ForEach(Array(result.items.enumerated()), id: \.offset) { _, item in
                    switch item.kind {
                    case .text, .json:
                        Text(item.text ?? "").textSelection(.enabled)
                    case .url:
                        if let url = item.url { Link(item.name ?? url.absoluteString, destination: url) }
                    case .file:
                        if let id = item.attachmentID, let url = try? store.attachmentURL(id: id) {
                            ShareLink(item: url) {
                                Label(item.name ?? PinkhaMiniAppsStrings.attachment, systemImage: "doc")
                            }
                        }
                    }
                }
            }
            .navigationTitle(PinkhaMiniAppsStrings.title)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button(PinkhaMiniAppsStrings.close, action: onDone)
                }
            }
        }
    }
}
