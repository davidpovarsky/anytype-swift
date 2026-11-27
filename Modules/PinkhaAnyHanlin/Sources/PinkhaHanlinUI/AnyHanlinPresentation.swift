#if canImport(UIKit)
import Foundation
import UIKit
import HanlinHostContracts
import PinkhaHanlinCore
import PinkhaAnyHanlin
import PinkhaAnyEngine
import PinkhaAnyHost

/// Implemented by the actual native editor/home coordinator. Scope validation
/// covers the real source owner, foreground scene, account, Space and selected
/// block IDs. Merely covering the source with its owned chat sheet is allowed;
/// navigation/removal/selection changes must synchronously invalidate it.
@MainActor
public protocol AnyHanlinSourcePresentationOwner: AnyObject, Sendable {
    var spaceDisplayName: String? { get }
    func currentScope() throws -> AnyHanlinPresentationScope
    func install(session: HanlinHostSession, invalidate: @escaping @Sendable () -> Void) throws
    /// Proves actual visible native source/block after the SDK sheet is closed.
    func validateMounted(_ destination: HanlinHostDestination) throws
}
extension AnyHanlinSourcePresentationOwner {
    public var spaceDisplayName: String? { nil }
}

@MainActor
public enum AnyHanlinPresentation {
    /// Presents the same canonical chat/composer and shared presentation logic
    /// used by the retained application. No provider credentials are discovered.
    @discardableResult
    public static func present(
        from presenter: UIViewController, native: AnyApplicationSession,
        documents: AnyEditorDocumentStore,
        sourceOwner: any AnyHanlinSourcePresentationOwner,
        conversationID: UUID, locale: Locale = .autoupdatingCurrent,
        creation: AnyHanlinCreationServices? = nil
    ) throws -> PinkhaHanlinChatController {
        try present(from: presenter, sourceOwner: sourceOwner) { owner in
            try AnyHanlinHost(native: native, documents: documents, owner: owner,
                conversationID: conversationID, locale: locale, creation: creation)
        }
    }

    #if DEBUG
    /// Real original-parser/native acceptance path only. No production call,
    /// settings switch, model argument or launch argument alone can select this path.
    @discardableResult
    public static func presentForSaveMessageAcceptance(
        from presenter: UIViewController, native: AnyApplicationSession,
        documents: AnyEditorDocumentStore, client: AnyHTTPClient,
        sourceOwner: any AnyHanlinSourcePresentationOwner,
        conversationID: UUID, locale: Locale = .autoupdatingCurrent,
        creation: AnyHanlinCreationServices,
        hooks: PinkhaHanlinPresentationHooks = .init()
    ) throws -> PinkhaHanlinChatController {
        let services = AnyHanlinSaveMessageServices(client: client) {
            try await PinkhaHanlinOriginalMarkdownSavePlanner.convert($0)
        }
        return try present(from: presenter, sourceOwner: sourceOwner, hooks: hooks) { owner in
            try AnyHanlinHost.makeForSaveMessageAcceptance(native: native, documents: documents,
                owner: owner, conversationID: conversationID, locale: locale,
                creation: creation, saveServices: services)
        }
    }
    #endif

    private static func present(from presenter: UIViewController,
        sourceOwner: any AnyHanlinSourcePresentationOwner,
        hooks: PinkhaHanlinPresentationHooks = .init(),
        makeHost: @MainActor (AnyHanlinUIKitOwner) throws -> AnyHanlinHost
    ) throws -> PinkhaHanlinChatController {
        guard presenter.presentedViewController == nil,
              let scene = presenter.viewIfLoaded?.window?.windowScene,
              scene.activationState == .foregroundActive,
              !presenter.isBeingDismissed, !presenter.isMovingFromParent else {
            throw HanlinHostError.staleContext
        }
        let owner = AnyHanlinUIKitOwner(source: sourceOwner, presenter: presenter, scene: scene)
        let host = try makeHost(owner)
        do {
            let adapter = AnyHanlinUIPresentationHost(host: host, owner: owner)
            let presentation = try PinkhaHanlinChatPresentation(host: adapter, presenter: presenter, hooks: hooks)
            let controller = PinkhaHanlinChatController(presentation: presentation)
            presenter.present(controller, animated: true) { [weak controller, weak presentation] in
                if controller?.viewIfLoaded?.window == nil { presentation?.invalidate() }
            }
            return controller
        } catch {
            host.invalidate()
            Task { await host.close() }
            throw error
        }
    }
}

@MainActor
private final class AnyHanlinUIPresentationHost: PinkhaHanlinPresentationHost {
    let host: AnyHanlinHost
    let owner: AnyHanlinUIKitOwner
    init(host: AnyHanlinHost, owner: AnyHanlinUIKitOwner) {
        self.host = host; self.owner = owner
    }
    var session: HanlinHostSession { host.session }
    var integration: any HanlinHostIntegration { host }
    func install(_ presentation: PinkhaHanlinChatPresentation,
                 controller: PinkhaHanlinChatController) throws {
        try owner.attach(presentation: presentation, controller: controller)
        try host.bindMountedPresentation(presentation)
    }
    func observeInvalidation(_ callback: @escaping @MainActor () -> Void) { host.observeInvalidation(callback) }
    func requestContextReadConsent() async throws { try await host.requestContextReadConsent() }
    func makeReturnHandoff(_ destination: HanlinHostDestination,
                          controller: PinkhaHanlinChatController) throws -> PinkhaHanlinNavigationHandoff {
        try owner.validateSDKPresentation(for: session)
        guard owner.controller === controller else { throw HanlinHostError.staleContext }
        return try host.makeReturnHandoff(destination)
    }
    func revokePresentation() { host.invalidate() }
    func invalidate() async { await host.close() }
}

/// Owns only UIKit presentation and per-sheet completion. The shared native
/// access/binding revalidates every answer; this controller cannot grant a tool.
@MainActor
private final class AnyHanlinUIKitOwner: AnyHanlinSaveMessagePresentationOwner {
    private weak var source: (any AnyHanlinSourcePresentationOwner)?
    private weak var presenter: UIViewController?
    private weak var scene: UIWindowScene?
    private weak var presentation: PinkhaHanlinChatPresentation?
    fileprivate weak var controller: PinkhaHanlinChatController?
    private var installedSession: HanlinHostSession?
    private var mountedOwnerWasBound = false
    private var pending: (decision: PinkhaHanlinReadConsentDecision, controller: PinkhaHanlinConsentController)?

    init(source: any AnyHanlinSourcePresentationOwner, presenter: UIViewController, scene: UIWindowScene) {
        self.source = source; self.presenter = presenter; self.scene = scene
    }

    func currentScope() throws -> AnyHanlinPresentationScope {
        guard let source, let presenter, let scene,
              scene.activationState == .foregroundActive,
              presenter.viewIfLoaded?.window?.windowScene === scene,
              !presenter.isBeingDismissed, !presenter.isMovingFromParent else {
            throw HanlinHostError.staleContext
        }
        return try source.currentScope()
    }

    func install(session: HanlinHostSession, invalidate: @escaping @Sendable () -> Void) throws {
        guard installedSession == nil, let source else { throw HanlinHostError.staleContext }
        _ = try currentScope()
        try source.install(session: session, invalidate: invalidate)
        installedSession = session
    }

    func attach(presentation: PinkhaHanlinChatPresentation, controller: PinkhaHanlinChatController) throws {
        guard installedSession == presentation.session,
              controller.presentation === presentation,
              !mountedOwnerWasBound || self.presentation === presentation else {
            throw HanlinHostError.staleContext
        }
        mountedOwnerWasBound = true
        self.presentation = presentation; self.controller = controller
        try validateSDKPresentation(for: presentation.session)
    }

    func validateSDKPresentation(for session: HanlinHostSession) throws {
        _ = try currentScope()
        guard installedSession == session, let presentation, let controller, let scene,
              controller.presentation === presentation, presentation.session == session,
              PinkhaHanlinAccountOwner.shared.owns(presentation),
              PinkhaHanlinAccountOwner.shared.isAvailable(namespace: session.context.namespace),
              controller.presentingViewController != nil,
              controller.viewIfLoaded?.window?.windowScene === scene,
              !controller.isBeingDismissed else { throw HanlinHostError.staleContext }
        try presentation.validateInstallation(for: session)
    }

    func validateMounted(_ destination: HanlinHostDestination) throws {
        _ = try currentScope()
        guard installedSession?.context == destination.context, let source else {
            throw HanlinHostError.staleContext
        }
        try source.validateMounted(destination)
    }

    func presentReadConsent(context: HanlinHostContext,
                            answer: @escaping @MainActor (Bool) -> Void) throws {
        guard let session = installedSession, session.context == context else {
            throw HanlinHostError.staleContext
        }
        let hebrew = Locale(identifier: context.localeIdentifier).language.languageCode?.identifier == "he"
        try presentDecision(session: session, purpose: .readContext,
            title: hebrew ? "לאפשר קריאת טקסט?" : "Allow document text access?",
            explanation: hebrew
                ? "לאפשר לצ׳אט הזה לקרוא טקסט מהמסמך הנוכחי או מהבלוקים שנבחרו? יצירת דף חדש דורשת אישור נפרד."
                : "Allow this chat presentation to read plain text from the current document or selected text blocks? Creating a new page requires a separate confirmation.",
            allowTitle: hebrew ? "לאפשר לצ׳אט הזה" : "Allow for this presentation",
            cancelTitle: hebrew ? "ביטול" : "Cancel", answer: answer)
    }

    func presentCreatePageConfirmation(_ prompt: AnyHanlinCreatePagePrompt,
                                      answer: @escaping @MainActor (Bool) -> Void) throws {
        guard installedSession == prompt.session,
              prompt.spaceID.utf8.elementsEqual(prompt.session.context.namespace.space.utf8) else {
            throw HanlinHostError.staleContext
        }
        let hebrew = Locale(identifier: prompt.session.context.localeIdentifier).language.languageCode?.identifier == "he"
        let name = source?.spaceDisplayName
        let destination = [name, prompt.spaceID].compactMap { $0 }.filter { !$0.isEmpty }.joined(separator: "\n")
        try presentDecision(session: prompt.session, purpose: .createPage,
            title: hebrew ? "ליצור דף חדש?" : "Create a new page?",
            explanation: prompt.title + "\n\n" + destination,
            allowTitle: hebrew ? "יצירת דף" : "Create page",
            cancelTitle: hebrew ? "ביטול" : "Cancel", answer: answer)
    }

    func presentSaveMessageConfirmation(_ prompt: AnyHanlinSaveMessagePrompt,
                                       answer: @escaping @MainActor (Bool) -> Void) throws {
        guard installedSession == prompt.session,
              prompt.spaceID.utf8.elementsEqual(prompt.session.context.namespace.space.utf8),
              (1...PinkhaHanlinSaveMessagePlan.maximumTitleUTF8Bytes).contains(prompt.title.utf8.count),
              (1...PinkhaHanlinSaveMessagePlan.maximumMarkdownUTF8Bytes).contains(prompt.markdown.utf8.count) else {
            throw HanlinHostError.staleContext
        }
        let hebrew = Locale(identifier: prompt.session.context.localeIdentifier).language.languageCode?.identifier == "he"
        let destination = [source?.spaceDisplayName, prompt.spaceID]
            .compactMap { $0 }.filter { !$0.isEmpty }.joined(separator: "\n")
        try presentDecision(session: prompt.session, purpose: .saveMessage,
            title: hebrew ? "לשמור את ההודעה בדף חדש?" : "Save the message in a new page?",
            explanation: prompt.title + "\n\n" + destination + "\n\n" + prompt.markdown,
            allowTitle: hebrew ? "שמירת ההודעה" : "Save message",
            cancelTitle: hebrew ? "ביטול" : "Cancel", answer: answer)
    }

    private func presentDecision(
        session: HanlinHostSession, purpose: PinkhaHanlinConsentController.Purpose,
        title: String, explanation: String, allowTitle: String, cancelTitle: String,
        answer: @escaping @MainActor (Bool) -> Void
    ) throws {
        try validateSDKPresentation(for: session)
        guard pending == nil, let controller, controller.presentedViewController == nil else {
            throw HanlinHostError.denied
        }
        let decision = PinkhaHanlinReadConsentDecision()
        guard decision.begin({ [weak self, weak decision] allowed in
            if let self, let decision, self.pending?.decision === decision { self.pending = nil }
            answer(allowed)
        }) else { throw HanlinHostError.denied }
        let prompt = PinkhaHanlinConsentController(purpose: purpose, title: title, explanation: explanation,
            allowTitle: allowTitle, cancelTitle: cancelTitle, decision: decision) { [weak self] in
                guard let self else { throw HanlinHostError.staleContext }
                try self.validateSDKPresentation(for: session)
        }
        pending = (decision, prompt)
        controller.present(prompt, animated: true) { [weak decision, weak prompt] in
            if prompt?.viewIfLoaded?.window == nil { decision?.resolve(false) }
        }
    }

    func dismissPendingPrompts() {
        let owned = pending
        pending = nil
        owned?.decision.revoke()
        owned?.controller.dismiss(animated: false)
    }
}
#endif
