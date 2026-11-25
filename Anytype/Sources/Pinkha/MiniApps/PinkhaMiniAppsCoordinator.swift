import Foundation
import Combine
import SwiftUI
import UIKit
import DeepLinks
import HanlinMiniAppsBridge
import PinkhaHanlinCore
import PinkhaHanlinUI

@MainActor
final class PinkhaMiniAppsCoordinator {
    static let shared = PinkhaMiniAppsCoordinator()

    private final class Registration {
        weak var editor: EditorPageController?
        let accountID: String
        var subscriptions: Set<AnyCancellable> = []
        init(editor: EditorPageController, accountID: String) {
            self.editor = editor
            self.accountID = accountID
        }
    }
    private final class Presentation {
        weak var controller: UIViewController?
        let confirmation: Bool
        init(_ controller: UIViewController, confirmation: Bool) {
            self.controller = controller
            self.confirmation = confirmation
        }
    }
    private let lifetime = PinkhaMiniAppsLifetime()
    private var presentations: [Presentation] = []
    private var confirmations: [UUID: PinkhaMiniAppsConfirmation] = [:]
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

    /// Returns only after all issued native work has returned. The caller keeps its
    /// hold while Heart is unavailable and releases it after its own transition ends.
    @discardableResult
    func prepareEngineAccountChange() async throws -> UUID {
        let token = lifetime.revoke()
        for confirmation in Array(confirmations.values) { confirmation.cancel() }
        let mounted = presentations.filter { !$0.confirmation }.compactMap(\.controller)
        presentations.removeAll()
        for controller in mounted where controller.presentingViewController != nil {
            await withCheckedContinuation { continuation in
                controller.dismiss(animated: false) { continuation.resume() }
            }
        }
        await lifetime.drain()
        // A task revoked before it started never entered the adapter's defer block.
        preparing.removeAll()
        applying.removeAll()
        applyingDocuments.removeAll()
        return token
    }

    func resumeAfterAccountChange(_ token: UUID) {
        lifetime.resume(token)
        guard lifetime.acceptsOperations else { return }
        let accountID = Container.shared.accountManager().account.id
        registrations = registrations.filter { $0.value.editor != nil && $0.value.accountID == accountID }
        for editor in registrations.values.compactMap(\.editor) { consume(editor: editor) }
    }

    func attach(editor: EditorPageController) {
        let id = ObjectIdentifier(editor)
        let accountID = Container.shared.accountManager().account.id
        guard registrations[id]?.accountID != accountID else { consume(editor: editor); return }
        let registration = Registration(editor: editor, accountID: accountID)
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

    func present(editor: EditorPageController, selection: PinkhaMiniAppsTextSelection? = nil) {
        let id = ObjectIdentifier(editor)
        guard lifetime.acceptsOperations, isCurrent(editor), isVisible(editor),
              editor.presentedViewController == nil, preparing.insert(id).inserted else { return }
        do {
            try lifetime.submit { [weak self, weak editor] lease in
                guard let self else { return }
                defer { preparing.remove(id) }
                guard let editor else { return }
                do {
                    try validate(lease, editor: editor)
                    let store = try MiniAppBridgeStore(appGroupIdentifier: "group.com.itorah.shared")
                    let context = try await PinkhaMiniAppsContext.capture(
                        editor: editor, store: store, selection: selection,
                        authorize: { try self.validate(lease, editor: editor) })
                    try validate(lease, editor: editor)
                    guard isVisible(editor),
                          context.source.documentID == editor.viewModel.document.objectId,
                          context.source.metadata["anytype.accountID"] == Container.shared.accountManager().account.id
                    else { throw PinkhaMiniAppsError.documentUnavailable }
                    let controller = PinkhaMiniAppsPresentation.makePicker(store: store, source: context.source,
                        inputs: context.inputs,
                        operation: context.source.selection?.text.isEmpty == false ? .replaceSelection : .insert,
                        callbacks: PinkhaMiniAppsContext.callbacks,
                        onOpen: { [weak self, weak editor] url in
                            guard let self, let editor, (try? self.validate(lease, editor: editor)) != nil else { return }
                            // The shared picker already initiates its own dismissal.
                            UIApplication.shared.open(url, options: [:]) { opened in
                                guard !opened else { return }
                                Task { @MainActor in
                                    guard (try? self.validate(lease, editor: editor)) != nil else { return }
                                    if let presentation = editor.presentedViewController {
                                        presentation.dismiss(animated: true) {
                                            guard (try? self.validate(lease, editor: editor)) != nil else { return }
                                            self.show(error: PinkhaMiniAppsError.companionMissing, on: editor)
                                        }
                                    } else {
                                        self.show(error: PinkhaMiniAppsError.companionMissing, on: editor)
                                    }
                                }
                            }
                        })
                    track(controller)
                    editor.present(controller, animated: true)
                } catch {
                    if lifetime.isCurrent(lease), isCurrent(editor) { show(error: error, on: editor) }
                }
            }
        } catch { preparing.remove(id) }
    }

    /// Uses the existing queued object route for cold starts and an exact mounted
    /// editor for warm returns. The bridge file remains pending until that editor saves.
    func routeCallback(_ url: URL) -> (handled: Bool, link: DeepLink?) {
        guard url.scheme?.lowercased() == PinkhaMiniAppsContext.callbacks.success?.scheme?.lowercased(),
              url.host == "miniapps", url.path == "/return" else { return (false, nil) }
        guard let id = MiniAppBridgeStore.requestID(from: url),
              let store = try? MiniAppBridgeStore(appGroupIdentifier: "group.com.itorah.shared"),
              let request = try? store.request(id: id),
              request.source.appID == PinkhaMiniAppsContext.sourceAppID,
              let objectID = request.source.documentID,
              let spaceID = request.source.metadata["anytype.spaceID"]
        else { return (true, nil) }
        guard PinkhaMiniAppsEngineScope.heart.matches(request.source) else { return (false, nil) }
        guard lifetime.acceptsOperations,
              request.source.metadata["anytype.accountID"] == Container.shared.accountManager().account.id
        else { return (true, nil) }
        let editors = registrations.values.compactMap(\.editor).filter {
            isCurrent($0) && isVisible($0) && $0.viewModel.document.objectId == objectID &&
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
        guard lifetime.acceptsOperations, isCurrent(editor), isVisible(editor),
              editor.viewModel.document.isOpened, editor.presentedViewController == nil,
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
                  PinkhaMiniAppsEngineScope.heart.matches(request.source),
                  request.source.documentID == document.objectId,
                  request.source.metadata["anytype.spaceID"] == document.spaceId,
                  request.source.metadata["anytype.accountID"] == Container.shared.accountManager().account.id
            else { continue }
            applying.insert(result.requestID)
            applyingDocuments.insert(identity)
            do {
                try lifetime.submit { [weak self, weak editor] lease in
                    guard let self else { return }
                    defer {
                        applying.remove(result.requestID)
                        applyingDocuments.remove(identity)
                        if let editor { consume(editor: editor, skipping: skipping.union([result.requestID])) }
                    }
                    guard let editor, isVisible(editor) else { return }
                    do {
                        try validate(lease, editor: editor)
                        if result.status == .cancelled {
                            _ = try store.acknowledgeResult(id: result.requestID, sourceAppID: request.source.appID)
                        } else if result.status == .error || result.operation == .display || result.operation == .custom {
                            presentResult(result, request: request, store: store, editor: editor, lease: lease)
                        } else {
                            if result.operation != request.operation {
                                let confirmation = PinkhaMiniAppsConfirmation()
                                confirmations[result.requestID] = confirmation
                                defer { confirmations.removeValue(forKey: result.requestID) }
                                let accepted = await confirmation.request(from: editor,
                                    title: PinkhaMiniAppsStrings.operationChangeTitle,
                                    message: PinkhaMiniAppsStrings.operationChangeMessage(result.operation),
                                    applyTitle: PinkhaMiniAppsStrings.apply,
                                    cancelTitle: PinkhaMiniAppsStrings.cancel,
                                    register: { [weak self] in self?.track($0, confirmation: true) },
                                    unregister: { [weak self] controller in
                                        self?.presentations.removeAll { $0.controller === controller }
                                    })
                                try validate(lease, editor: editor)
                                guard accepted else { return }
                            }
                            // Preserve the native editor flush before applying the returned result.
                            editor.view.endEditing(true)
                            let preserved = try await PinkhaMiniAppsResultApplier.apply(
                                request: request, result: result, editor: editor, store: store,
                                authorize: { try self.validate(lease, editor: editor) })
                            try validate(lease, editor: editor)
                            if preserved { show(message: PinkhaMiniAppsStrings.sourceChanged, on: editor) }
                        }
                        reported.remove(result.requestID)
                    } catch {
                        if lifetime.isCurrent(lease), isCurrent(editor),
                           reported.insert(result.requestID).inserted { show(error: error, on: editor) }
                    }
                }
            } catch {
                applying.remove(result.requestID)
                applyingDocuments.remove(identity)
            }
            // Serialize mutations for one editor, including separate invocations.
            break
        }
    }

    private func presentResult(_ result: MiniAppResult, request: MiniAppInvocation,
                               store: MiniAppBridgeStore, editor: EditorPageController,
                               lease: PinkhaMiniAppsLifetime.Lease) {
        guard editor.presentedViewController == nil else { return }
        let controller = PinkhaMiniAppsPresentation.makeResult(result: result, store: store,
            title: PinkhaMiniAppsStrings.title, attachmentTitle: PinkhaMiniAppsStrings.attachment,
            closeTitle: PinkhaMiniAppsStrings.close) { [weak self, weak editor] in
            guard let self, let editor, (try? validate(lease, editor: editor)) != nil else { return }
            do {
                _ = try store.acknowledgeResult(id: result.requestID, sourceAppID: request.source.appID)
                consume(editor: editor)
            } catch { show(error: error, on: editor) }
        }
        track(controller)
        editor.present(controller, animated: true)
    }

    private func track(_ controller: UIViewController, confirmation: Bool = false) {
        presentations.removeAll { $0.controller == nil }
        presentations.append(Presentation(controller, confirmation: confirmation))
    }

    private func validate(_ lease: PinkhaMiniAppsLifetime.Lease, editor: EditorPageController) throws {
        try lifetime.validate(lease)
        guard isCurrent(editor) else { throw PinkhaMiniAppsError.documentUnavailable }
    }

    private func isCurrent(_ editor: EditorPageController) -> Bool {
        let registration = registrations[ObjectIdentifier(editor)]
        return registration?.editor === editor &&
            registration?.accountID == Container.shared.accountManager().account.id
    }

    private func isVisible(_ editor: EditorPageController) -> Bool {
        editor.viewIfLoaded?.window?.windowScene?.activationState == .foregroundActive
    }

    private func show(error: Error, on editor: EditorPageController) {
        show(message: error.localizedDescription, on: editor)
    }

    private func show(message: String, on editor: EditorPageController) {
        guard lifetime.acceptsOperations, isCurrent(editor), isVisible(editor),
              editor.presentedViewController == nil else { return }
        let alert = UIAlertController(title: PinkhaMiniAppsStrings.title, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: PinkhaMiniAppsStrings.close, style: .cancel) { [weak self, weak editor, weak alert] _ in
            alert?.dismiss(animated: true) {
                if let editor { self?.consume(editor: editor) }
            }
        })
        track(alert)
        editor.present(alert, animated: true)
    }
}
