#if canImport(UIKit) && canImport(HanlinMiniAppsBridge)
import Foundation
import Observation
import UIKit
import PinkhaAnyHost
import PinkhaHanlinUI
import HanlinMiniAppsBridge

/// Only a locally retained, exact-source request can select an Any document.
/// A URL query never supplies an account, Space, object, content or permission.
@Observable @MainActor
public final class AnyMiniAppsReturnRouter {
    public static let shared = AnyMiniAppsReturnRouter()
    public private(set) var requestID: UUID?
    private var target: (account: String, space: String, object: String)?

    @discardableResult
    public func receive(_ url: URL) -> Bool {
        guard url.scheme?.lowercased() == AnyMiniAppsCodec.callbacks.success?.scheme?.lowercased(),
              url.host == "miniapps", url.path == "/return",
              let id = MiniAppBridgeStore.requestID(from: url),
              let store = try? MiniAppBridgeStore(appGroupIdentifier: "group.com.itorah.shared"),
              let request = try? store.request(id: id),
              request.source.appID == AnyMiniAppsCodec.sourceAppID,
              PinkhaMiniAppsEngineScope.any.matches(request.source),
              let account = request.source.metadata["anytype.accountID"],
              let space = request.source.metadata["anytype.spaceID"],
              let object = request.source.documentID,
              !account.isEmpty, !space.isEmpty, AnyEditorBlock.validID(object) else { return false }
        target = (account, space, object)
        requestID = id
        return true
    }

    public func pendingObject(accountID: String, spaceID: String) -> String? {
        guard let target, target.account.utf8.elementsEqual(accountID.utf8),
              target.space.utf8.elementsEqual(spaceID.utf8) else { return nil }
        return target.object
    }

    public func didRoute(accountID: String, spaceID: String, objectID: String) {
        guard pendingObject(accountID: accountID, spaceID: spaceID)?.utf8.elementsEqual(objectID.utf8) == true else { return }
        target = nil
        requestID = nil
    }
}

@MainActor
final class AnyNativeMiniAppsCoordinator {
    static let shared = AnyNativeMiniAppsCoordinator()

    @MainActor
    private final class Registration {
        weak var document: AnyDocumentPresentation?
        let owner: UUID
        var active = true
        var task: Task<Void, Never>?
        weak var modal: UIViewController?
        var confirmation: PinkhaMiniAppsConfirmation?
        var deferred = Set<UUID>()
        init(_ document: AnyDocumentPresentation) { self.document = document; owner = document.mountedOwnerID }
    }
    private var registrations: [ObjectIdentifier: Registration] = [:]

    func attach(_ document: AnyDocumentPresentation) {
        guard document.isMounted, document.surface != nil else { return }
        let key = ObjectIdentifier(document)
        if let existing = registrations[key], existing.owner == document.mountedOwnerID, existing.active { return }
        let entry = Registration(document)
        registrations[key] = entry
        document.installPresentationLifecycle(revoke: { [weak self, weak entry] in
            guard let entry else { return }
            entry.active = false
            entry.task?.cancel()
            entry.confirmation?.cancel()
            entry.modal?.dismiss(animated: false)
            if self?.registrations[key] === entry { self?.registrations.removeValue(forKey: key) }
        }, drain: { [weak entry] in
            guard let entry else { return }
            let task = entry.task
            entry.active = false; task?.cancel()
            await task?.value
            entry.task = nil
        })
    }

    func present(_ document: AnyDocumentPresentation, additionalInputs: [MiniAppContent] = []) {
        attach(document)
        guard let entry = registration(document), entry.task == nil,
              let editor = document.surface as? AnyNativeEditorController,
              editor.presentedViewController == nil else { return }
        entry.task = Task { [weak self, weak document, weak editor, weak entry] in
            guard let self, let document, let editor, let entry else { return }
            defer { entry.task = nil }
            do {
                let store = try MiniAppBridgeStore(appGroupIdentifier: "group.com.itorah.shared")
                let captured = try await AnyMiniAppsCapturedContext.capture(
                    document: document, editor: editor, additionalInputs: additionalInputs)
                try require(entry, document: document)
                let picker = PinkhaMiniAppsPresentation.makePicker(store: store, source: captured.source,
                    inputs: captured.inputs,
                    operation: captured.source.selection?.text.isEmpty == false ? .replaceSelection : .insert,
                    callbacks: AnyMiniAppsCodec.callbacks) { [weak self, weak document, weak entry] url in
                        guard let self, let document, let entry else { return }
                        do { try self.require(entry, document: document) }
                        catch { return }
                        UIApplication.shared.open(url, options: [:]) { opened in
                            guard !opened else { return }
                            Task { @MainActor [weak document, weak entry] in
                                guard let document, entry?.active == true else { return }
                                document.message = AnyUIErrorText.text("יישום MiniApps אינו זמין במכשיר.", "The MiniApps companion is unavailable on this device.")
                            }
                        }
                    }
                entry.modal = picker
                editor.present(picker, animated: true)
            } catch {
                if entry.active { document.message = AnyUIErrorText.describe(error) }
            }
        }
    }

    func consume(_ document: AnyDocumentPresentation, reviewDeferred: Bool = false) {
        attach(document)
        guard let entry = registration(document), entry.task == nil, !document.hasPendingEdits,
              let editor = document.surface as? AnyNativeEditorController,
              editor.presentedViewController == nil,
              let appID = AnyMiniAppsCodec.sourceAppID,
              let store = try? MiniAppBridgeStore(appGroupIdentifier: "group.com.itorah.shared"),
              let pending = try? store.pendingResults(sourceAppID: appID) else { return }
        if reviewDeferred { entry.deferred.removeAll() }
        for result in pending {
            guard !entry.deferred.contains(result.requestID), let request = try? store.request(id: result.requestID),
                  AnyMiniAppsCodec.matches(request, document: document) else { continue }
            entry.task = Task { [weak self, weak document, weak editor, weak entry] in
                guard let self, let document, let editor, let entry else { return }
                defer { entry.task = nil }
                do {
                    try await validateRead(entry, document: document)
                    if result.status == .cancelled {
                        _ = try store.acknowledgeResult(id: result.requestID, sourceAppID: request.source.appID)
                    } else if result.status == .error || result.operation == .display || result.operation == .custom {
                        let modal = PinkhaMiniAppsPresentation.makeResult(result: result, store: store,
                            title: "MiniApps",
                            attachmentTitle: AnyUIErrorText.text("קובץ מצורף", "Attachment"),
                            closeTitle: AnyUIErrorText.text("סגירה", "Close")) { [weak self, weak document, weak entry] in
                                guard let self, let document, let entry, entry.active, entry.task == nil else { return }
                                entry.task = Task {
                                    defer { entry.task = nil }
                                    do {
                                        try await self.validateRead(entry, document: document)
                                        _ = try store.acknowledgeResult(id: result.requestID, sourceAppID: request.source.appID)
                                    } catch { if entry.active { document.message = AnyUIErrorText.describe(error) } }
                                }
                            }
                        entry.modal = modal
                        editor.present(modal, animated: true)
                    } else {
                        if result.operation != request.operation {
                            let confirmation = PinkhaMiniAppsConfirmation()
                            entry.confirmation = confirmation
                            let approved = await confirmation.request(from: editor,
                                title: AnyUIErrorText.text("אישור פעולת MiniApps", "Confirm MiniApps action"),
                                message: AnyUIErrorText.text("הפעולה שהוחזרה שונה מהפעולה שנבחרה. להחיל אותה על המסמך: ", "The returned action differs from the action you chose. Apply it to: ") + document.title + "\n" + result.operation.rawValue,
                                applyTitle: AnyUIErrorText.text("החלה", "Apply"),
                                cancelTitle: AnyUIErrorText.text("שמירה לבדיקה מאוחרת", "Keep for later"))
                            entry.confirmation = nil
                            try require(entry, document: document)
                            guard approved else { entry.deferred.insert(result.requestID); return }
                        }
                        editor.view.endEditing(true)
                        let preserved = try await AnyMiniAppsResultApplier.apply(
                            request: request, result: result, document: document, store: store)
                        try require(entry, document: document)
                        if preserved {
                            document.message = AnyUIErrorText.text(
                                "התוכן השתנה. התוצאה נוספה לצד התוכן העדכני.",
                                "The content changed. The result was added alongside the current content.")
                        }
                    }
                } catch { if entry.active { document.message = AnyUIErrorText.describe(error) } }
            }
            // One real native operation may own a document at a time.
            break
        }
    }

    private func registration(_ document: AnyDocumentPresentation) -> Registration? {
        guard let value = registrations[ObjectIdentifier(document)],
              (try? require(value, document: document)) != nil else { return nil }
        return value
    }

    private func require(_ entry: Registration, document: AnyDocumentPresentation) throws {
        guard entry.active, entry.document === document, !Task.isCancelled else { throw AnyHostError.sessionClosed }
        try document.requireMounted(entry.owner)
    }

    private func validateRead(_ entry: Registration, document: AnyDocumentPresentation) async throws {
        try require(entry, document: document)
        let store = document.documents, id = document.objectID
        _ = try await document.nativeSession.perform { try await store.read(objectID: id, lease: $0) }
        try require(entry, document: document)
    }
}

extension AnyDocumentPresentation {
    public func presentMiniApps() { AnyNativeMiniAppsCoordinator.shared.present(self) }
    func consumeMiniAppsResults(reviewDeferred: Bool = false) {
        AnyNativeMiniAppsCoordinator.shared.consume(self, reviewDeferred: reviewDeferred)
    }
}
#endif
