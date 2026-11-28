import Foundation
import HanlinHostContracts
import HanlinPlatformContracts
import PinkhaHanlinCore
import PinkhaAnyEngine
import PinkhaAnyHost

public struct AnyHanlinCreationServices: Sendable {
    public let creator: AnyNativeObjectCreator
    public let authority: AnyHanlinCreationAuthority
    public init(creator: AnyNativeObjectCreator, authority: AnyHanlinCreationAuthority) throws {
        guard creator.workspace == authority.workspace else { throw HanlinHostError.invalidContext }
        self.creator = creator; self.authority = authority
    }
}

/// Pure original-parser conversion plus one original native HTTP client. The
/// Markdown adapter is constructed from that same client, so a separate account
/// endpoint cannot be hidden in a caller-supplied body adapter.
public struct AnyHanlinSaveMessageServices: Sendable {
    public let client: AnyHTTPClient
    public let body: AnyNativeMarkdownBody
    public let convert: @MainActor @Sendable (PinkhaHanlinSaveMessagePlan) async throws -> PinkhaHanlinMarkdownSaveConversion

    public init(client: AnyHTTPClient,
        convert: @escaping @MainActor @Sendable (PinkhaHanlinSaveMessagePlan) async throws -> PinkhaHanlinMarkdownSaveConversion) {
        self.client = client; self.body = AnyNativeMarkdownBody(client: client); self.convert = convert
    }
}

/// Native application presentation. The real app supplies a mounted UI owner;
/// model requests only reach the canonical shared Hanlin router. Missing native
/// confirmation or protected journals makes the writable catalog unavailable.
@MainActor
public final class AnyHanlinHost: HanlinHostCancellationDrainSource, PinkhaHanlinOwnedPresentation {
    public nonisolated let apiVersion = HanlinAPIVersion(major: 1, minor: 0)
    public let session: HanlinHostSession
    public let access: AnyHanlinNativeAccess
    private let router: PinkhaHanlinHostRouter
    private let binding: AnyHanlinCreateBinding?
    private let saveBinding: AnyHanlinSaveBinding?
    private var invalidated = false
    private var mountedOwnerWasBound = false
    private weak var mountedOwner: (any PinkhaHanlinOwnedPresentation)?
    private var invalidation: (@MainActor () -> Void)?

    public convenience init(native: AnyApplicationSession, documents: AnyEditorDocumentStore,
                owner: any AnyHanlinPresentationOwner, conversationID: UUID,
                locale: Locale = .current, creation: AnyHanlinCreationServices? = nil) throws {
        try self.init(native: native, documents: documents, owner: owner,
            conversationID: conversationID, locale: locale, creation: creation, saveServices: nil)
    }

    private init(native: AnyApplicationSession, documents: AnyEditorDocumentStore,
        owner: any AnyHanlinPresentationOwner, conversationID: UUID, locale: Locale,
        creation: AnyHanlinCreationServices?, saveServices: AnyHanlinSaveMessageServices?) throws {
        guard PinkhaHanlinAccountOwner.shared.isAvailable(account: native.workspace.accountID,
            app: PinkhaHanlinEngineNamespace.any) else {
            throw HanlinHostError.staleContext
        }
        // Reject a foreign body client or missing full-message UI capability
        // before installing even the provisional original source presentation.
        if let saveServices {
            guard creation != nil, owner is any AnyHanlinSaveMessagePresentationOwner,
                  saveServices.client.expectedAccountID.utf8.elementsEqual(native.workspace.accountID.utf8) else {
                throw HanlinHostError.invalidContext
            }
        }
        let access = try AnyHanlinNativeAccess(native: native, documents: documents, owner: owner,
                                               conversationID: conversationID, locale: locale)
        let binding: AnyHanlinCreateBinding?
        let saveBinding: AnyHanlinSaveBinding?
        if let creation {
            guard let writableOwner = owner as? any AnyHanlinCreationPresentationOwner else {
                throw HanlinHostError.invalidContext
            }
            let context = try AnyHanlinWriteContext(access: access, native: native,
                creator: creation.creator, authority: creation.authority, owner: writableOwner)
            binding = try AnyHanlinCreateBinding(context: context)
            if let saveServices {
                saveBinding = try AnyHanlinSaveBinding(context: context, documents: documents, services: saveServices)
            } else { saveBinding = nil }
        } else { binding = nil; saveBinding = nil }
        let read = try PinkhaHanlinHostAdapter(access: access)
        self.session = access.session; self.access = access; self.binding = binding
        self.saveBinding = saveBinding
        self.router = try PinkhaHanlinHostRouter(read: read, session: access.session, write: binding, saveMessage: saveBinding)
        try PinkhaHanlinAccountOwner.shared.register(self)
        binding?.attach(self)
        saveBinding?.attach(self)
        access.observeInvalidation { [weak self] in self?.invalidate() }
    }

    /// Explicit full-message composition for the original native services.
    /// The mounted presentation, current authority, consent and protected
    /// journal still determine whether the shared router can expose a save.
    /// Ordinary initialization remains read/create-only until its separately
    /// reviewed production entry is admitted.
    public static func makeForSavingMessages(native: AnyApplicationSession,
        documents: AnyEditorDocumentStore, owner: any AnyHanlinPresentationOwner,
        conversationID: UUID, locale: Locale = .current, creation: AnyHanlinCreationServices,
        saveServices: AnyHanlinSaveMessageServices) throws -> AnyHanlinHost {
        try .init(native: native, documents: documents, owner: owner, conversationID: conversationID,
                  locale: locale, creation: creation, saveServices: saveServices)
    }

    #if DEBUG
    /// The acceptance route exercises the same explicit production composition.
    /// Its fixture and native readback admission remain with the existing caller.
    public static func makeForSaveMessageAcceptance(native: AnyApplicationSession,
        documents: AnyEditorDocumentStore, owner: any AnyHanlinPresentationOwner,
        conversationID: UUID, locale: Locale = .current, creation: AnyHanlinCreationServices,
        saveServices: AnyHanlinSaveMessageServices) throws -> AnyHanlinHost {
        try makeForSavingMessages(native: native, documents: documents, owner: owner,
            conversationID: conversationID, locale: locale, creation: creation, saveServices: saveServices)
    }
    #endif

    /// The real chat presentation replaces this host's provisional account-owner
    /// registration. Exactly one mounted owner can bind; dismissal cannot rearm
    /// the same SDK session with another presentation.
    public func bindMountedPresentation(_ presentation: any PinkhaHanlinOwnedPresentation) throws {
        guard !invalidated, presentation.session == session,
              PinkhaHanlinAccountOwner.shared.owns(presentation),
              !mountedOwnerWasBound || mountedOwner === presentation else {
            throw HanlinHostError.staleContext
        }
        try access.validate(session.context)
        mountedOwnerWasBound = true
        mountedOwner = presentation
        binding?.attach(presentation)
        saveBinding?.attach(presentation)
    }

    public var missingWriteInstallation: [PinkhaHanlinWriteInstallationRequirement] {
        router.missingWriteInstallation
    }
    public func observeInvalidation(_ callback: @escaping @MainActor () -> Void) {
        invalidation = callback
        if invalidated { callback() }
    }
    public func context(for session: HanlinHostSession) async throws -> HanlinHostContext {
        try await router.context(for: session)
    }
    public func catalog(for context: HanlinHostContext) async throws -> HanlinHostCatalog {
        try await router.catalog(for: context)
    }
    public func execute(_ invocation: HanlinHostInvocation,
                        progress: @escaping HanlinHostProgressHandler) async throws -> HanlinHostExecutionResult {
        try await router.execute(invocation, progress: progress)
    }
    public func cancel(_ id: HanlinToolInvocationID) async { await router.cancel(id) }
    public func drainCancelledInvocation(_ id: HanlinToolInvocationID) async -> HanlinHostExecutionResult? {
        await router.drainCancelledInvocation(id)
    }
    public func open(_ destination: HanlinHostDestination) async throws -> HanlinHostNavigationResult {
        try await router.open(destination)
    }
    public func requestContextReadConsent() async throws {
        try router.validateCurrentSession(session)
        try await access.requestContextReadConsent()
        try router.validateCurrentSession(session)
    }
    public func metadataReceipt(for id: HanlinToolInvocationID) -> HanlinHostExecutionResult? {
        router.metadataReceipt(for: id)
    }
    public func makeReturnHandoff(_ destination: HanlinHostDestination) throws -> PinkhaHanlinNavigationHandoff {
        try router.validateCurrentSession(session)
        return try access.makeReturnHandoff(destination)
    }
    public func acknowledgeMounted(_ destination: HanlinHostDestination) throws -> HanlinHostNavigationResult {
        try router.validateCurrentSession(session)
        return try access.acknowledgeMounted(destination)
    }

    /// Revocation is synchronous before cancellation can suspend. This retains
    /// original-scope write metadata and permits no new SDK work.
    public func invalidate() {
        guard !invalidated else { return }
        invalidated = true
        router.revokePresentation()
        access.invalidate()
        invalidation?()
        Task { @MainActor [router] in await router.invalidate() }
    }

    public func revokeAndDrain() async { await close() }

    public func close() async {
        invalidate()
        await router.invalidate()
        let owner = PinkhaHanlinAccountOwner.shared
        if owner.owns(self) { owner.unregister(session.id) }
    }
}
