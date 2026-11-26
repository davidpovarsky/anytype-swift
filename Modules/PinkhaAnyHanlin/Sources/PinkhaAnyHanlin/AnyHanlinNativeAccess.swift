import Foundation
import HanlinHostContracts
import PinkhaAnyHost
import PinkhaHanlinCore

/// Actual Any HTTP/session I/O behind the same read-consent and SDK router used
/// by the Heart host. Source identity comes from the mounted native owner.
@MainActor
public final class AnyHanlinNativeAccess: PinkhaHanlinHostAccess {
    public let session: HanlinHostSession
    private weak var owner: (any AnyHanlinPresentationOwner)?
    private let native: AnyApplicationSession
    private let documents: AnyEditorDocumentStore
    private let original: AnyHanlinPresentationScope
    private let fence = PinkhaHanlinRevocationFence()
    private let navigationFence = PinkhaHanlinRevocationFence()
    private let consent = PinkhaHanlinReadConsentDecision()
    private let navigation: PinkhaHanlinNavigationLedger
    private var handoff: PinkhaHanlinNavigationHandoff?
    private var invalidation: (@MainActor () -> Void)?

    public init(native: AnyApplicationSession, documents: AnyEditorDocumentStore,
                owner: any AnyHanlinPresentationOwner, conversationID: UUID,
                locale: Locale = .current) throws {
        let scope = try owner.currentScope()
        guard scope.accountID.utf8.elementsEqual(native.workspace.accountID.utf8),
              scope.spaceID.utf8.elementsEqual(native.workspace.spaceID.utf8),
              documents.workspace == native.workspace else { throw HanlinHostError.invalidContext }
        let session = try AnyHanlinScope.makeSession(accountID: scope.accountID,
            spaceID: scope.spaceID, sceneID: scope.sceneID, conversationID: conversationID,
            snapshot: scope.document, selection: scope.selection, locale: locale)
        self.session = session; self.original = scope; self.native = native
        self.documents = documents; self.owner = owner
        self.navigation = PinkhaHanlinNavigationLedger(context: session.context)
        fence.onRevoke { [weak self] in
            Task { @MainActor in
                self?.consent.revoke()
                self?.owner?.dismissPendingPrompts()
                self?.invalidation?()
            }
        }
        let fence = fence, navigationFence = navigationFence
        try owner.install(session: session) { fence.revoke(); navigationFence.revoke() }
        try validate(session.context)
    }

    public func observeInvalidation(_ callback: @escaping @MainActor () -> Void) {
        invalidation = callback
        if fence.isRevoked { callback() }
    }

    public func invalidate() {
        fence.revoke(); consent.revoke()
        owner?.dismissPendingPrompts()
    }

    /// Scope/scene/account transitions must cancel a return handoff too.
    public func invalidateScope() {
        navigationFence.revoke(); handoff?.cancel(); invalidate()
    }

    public func validate(_ context: HanlinHostContext) throws {
        guard !fence.isRevoked else { throw HanlinHostError.staleContext }
        try validateOwner(context)
    }

    public func validateRead(_ context: HanlinHostContext) throws {
        try validate(context)
        guard original.document != nil, consent.authorized else { throw HanlinHostError.denied }
    }

    public func requestContextReadConsent() async throws {
        try validate(session.context)
        guard original.document != nil, let owner else { throw HanlinHostError.denied }
        if consent.authorized { return }
        try Task.checkCancellation()
        let fence = fence
        let allowed: Bool = await withTaskCancellationHandler {
          await withCheckedContinuation { continuation in
            guard !Task.isCancelled, consent.begin({ continuation.resume(returning: $0) }) else {
                continuation.resume(returning: false); return
            }
            do {
                try owner.presentReadConsent(context: session.context) { [weak self] answer in
                    guard let self else { return }
                    if answer {
                        self.consent.resolveAllow { try self.validate(self.session.context) }
                    } else { self.consent.resolve(false) }
                }
            } catch { consent.resolve(false) }
          }
        } onCancel: {
            fence.revoke()
        }
        try Task.checkCancellation()
        try validate(session.context)
        guard allowed else { throw HanlinHostError.denied }
    }

    public func read(_ context: HanlinHostContext) async throws -> PinkhaHanlinTextSnapshot {
        try validateRead(context)
        try Task.checkCancellation()
        guard let objectID = context.objectReference else { throw HanlinHostError.unknownTool }
        let documents = documents
        let read = try await native.perform { lease in
            try await documents.read(objectID: objectID, lease: lease)
        }
        try Task.checkCancellation()
        try validateRead(context)
        guard read.generation == native.generation,
              read.engineStartedAt.utf8.elementsEqual(native.engineStartedAt.utf8),
              read.snapshot.objectID.utf8.elementsEqual(objectID.utf8),
              read.snapshot.spaceID.utf8.elementsEqual(context.namespace.space.utf8),
              context.matchesRevision(read.snapshot.revision) else {
            throw HanlinHostError.staleContext
        }
        let result = try AnyHanlinPlainText.project(read.snapshot, selection: context.selectionReferences)
        try validateRead(context)
        return result
    }

    public func navigate(_ destination: HanlinHostDestination) throws -> HanlinHostNavigationResult {
        try validate(destination.context)
        try validateDestination(destination)
        _ = try navigation.enqueue(destination)
        return try navigation.result(for: destination)
    }

    public func acknowledgeMounted(_ destination: HanlinHostDestination) throws -> HanlinHostNavigationResult {
        try validate(destination.context)
        let result = try mountedResult(destination)
        try navigation.acknowledge(result, for: destination)
        return result
    }

    public func makeReturnHandoff(_ destination: HanlinHostDestination) throws -> PinkhaHanlinNavigationHandoff {
        try validate(destination.context)
        guard handoff == nil, !navigationFence.isRevoked, let owner else { throw HanlinHostError.staleContext }
        let value = try navigation.makeHandoff(for: destination) { [self, owner] in
          try withExtendedLifetime(owner) {
            guard !navigationFence.isRevoked else { throw HanlinHostError.staleContext }
            // The SDK presentation may already be revoked. Only this original
            // UI receipt can finish; no read/write entry point uses this path.
            try validateOwner(destination.context)
            return try mountedResult(destination)
          }
        }
        handoff = value
        return value
    }

    private func mountedResult(_ destination: HanlinHostDestination) throws -> HanlinHostNavigationResult {
        _ = try navigation.result(for: destination)
        try validateDestination(destination)
        guard let owner else { throw HanlinHostError.staleContext }
        try owner.validateMounted(destination)
        try validateOwner(destination.context)
        return .presented(requestID: destination.requestID, context: destination.context,
                          objectReference: destination.objectReference, blockReference: destination.blockReference)
    }

    private func validateDestination(_ destination: HanlinHostDestination) throws {
        guard let document = original.document,
              destination.objectReference.utf8.elementsEqual(document.objectID.utf8) else {
            throw HanlinHostError.denied
        }
        if let block = destination.blockReference {
            guard document.depthFirstIDs.contains(where: { $0.utf8.elementsEqual(block.utf8) }) else {
                throw HanlinHostError.resultMismatch
            }
        }
    }

    private func validateOwner(_ context: HanlinHostContext) throws {
        guard context == session.context,
              PinkhaHanlinAccountOwner.shared.isAvailable(namespace: context.namespace),
              let owner else { throw HanlinHostError.staleContext }
        let current = try owner.currentScope()
        guard current.ownerID == original.ownerID, current.sceneID == original.sceneID,
              current.accountID.utf8.elementsEqual(original.accountID.utf8),
              current.spaceID.utf8.elementsEqual(original.spaceID.utf8),
              current.selection.map({ Data($0.utf8) }) == original.selection.map({ Data($0.utf8) }),
              current.document?.objectID.data(using: .utf8) == original.document?.objectID.data(using: .utf8),
              current.document?.spaceID.data(using: .utf8) == original.document?.spaceID.data(using: .utf8),
              current.document?.revision.data(using: .utf8) == original.document?.revision.data(using: .utf8) else {
            throw HanlinHostError.staleContext
        }
    }
}
