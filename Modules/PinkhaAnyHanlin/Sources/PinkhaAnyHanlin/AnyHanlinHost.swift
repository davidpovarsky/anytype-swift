import Foundation
import HanlinHostContracts
import HanlinPlatformContracts
import PinkhaHanlinCore
import PinkhaAnyHost

public struct AnyHanlinCreationServices: Sendable {
    public let creator: AnyNativeObjectCreator
    public let authority: AnyHanlinCreationAuthority
    public init(creator: AnyNativeObjectCreator, authority: AnyHanlinCreationAuthority) throws {
        guard creator.workspace == authority.workspace else { throw HanlinHostError.invalidContext }
        self.creator = creator; self.authority = authority
    }
}

/// Native application presentation. The real app supplies a mounted UI owner;
/// model requests only reach the canonical shared Hanlin router. Missing native
/// confirmation or protected journals makes the writable catalog unavailable.
@MainActor
public final class AnyHanlinHost: HanlinHostIntegration, PinkhaHanlinOwnedPresentation {
    public nonisolated let apiVersion = HanlinAPIVersion(major: 1, minor: 0)
    public let session: HanlinHostSession
    public let access: AnyHanlinNativeAccess
    private let router: PinkhaHanlinHostRouter
    private let binding: AnyHanlinCreateBinding?
    private var invalidated = false
    private var mountedOwnerWasBound = false
    private weak var mountedOwner: (any PinkhaHanlinOwnedPresentation)?
    private var invalidation: (@MainActor () -> Void)?

    public init(native: AnyApplicationSession, documents: AnyEditorDocumentStore,
                owner: any AnyHanlinPresentationOwner, conversationID: UUID,
                locale: Locale = .current, creation: AnyHanlinCreationServices? = nil) throws {
        guard PinkhaHanlinAccountOwner.shared.isAvailable(account: native.workspace.accountID) else {
            throw HanlinHostError.staleContext
        }
        let access = try AnyHanlinNativeAccess(native: native, documents: documents, owner: owner,
                                               conversationID: conversationID, locale: locale)
        let binding: AnyHanlinCreateBinding?
        if let creation {
            guard let writableOwner = owner as? any AnyHanlinCreationPresentationOwner else {
                throw HanlinHostError.invalidContext
            }
            binding = try AnyHanlinCreateBinding(access: access, native: native,
                creator: creation.creator, authority: creation.authority, owner: writableOwner)
        } else { binding = nil }
        let read = try PinkhaHanlinHostAdapter(access: access)
        self.session = access.session; self.access = access; self.binding = binding
        self.router = try PinkhaHanlinHostRouter(read: read, session: access.session, write: binding)
        try PinkhaHanlinAccountOwner.shared.register(self)
        binding?.attach(self)
        access.observeInvalidation { [weak self] in self?.invalidate() }
    }

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

    public func close() async {
        invalidate()
        await router.invalidate()
        PinkhaHanlinAccountOwner.shared.unregister(session.id)
    }
}
