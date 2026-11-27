import Foundation
import HanlinHostContracts
import HanlinPlatformContracts

/// Concrete product ownership requirements, never model/user-selectable permission switches.
public enum PinkhaHanlinWriteInstallationRequirement: String, CaseIterable, Sendable {
    case presentingAppLifetimeHook
    case accountRemovalAndMetadataRetentionHook
    case appSDKUIAndReceiptOwner

    public static var missing: [Self] { [.presentingAppLifetimeHook, .accountRemovalAndMetadataRetentionHook, .appSDKUIAndReceiptOwner] }
}

/// The native composition owner supplies confirmation and original-scope I/O.
/// Model arguments cannot construct this owner or change its readiness checks.
@MainActor
public protocol PinkhaHanlinWriteBinding: AnyObject, Sendable {
    var missingInstallation: [PinkhaHanlinWriteInstallationRequirement] { get }
    func observeInvalidation(_ callback: @escaping @MainActor () -> Void)
    func catalogTool() async throws -> HanlinHostTool?
    func execute(_ invocation: HanlinHostInvocation, cancellation: PinkhaHanlinRevocationFence,
                 progress: @escaping HanlinHostProgressHandler) async throws -> HanlinHostExecutionResult
    func cancel(_ id: HanlinToolInvocationID) async
    func drainCancelledInvocation(_ id: HanlinToolInvocationID) async -> HanlinHostExecutionResult?
    func invalidate()
    func requestContextReadConsent() async throws
    func metadataReceipt(for id: HanlinToolInvocationID) -> HanlinHostExecutionResult?
}

/// Typed composition of the real reviewed host components. No SDK dispatcher/provider/authority fork.
/// Writes require the real mounted SDK presentation and application account/metadata owner.
@MainActor
public final class PinkhaHanlinHostRouter: HanlinHostCancellationDrainSource {
    public nonisolated let apiVersion = HanlinAPIVersion(major: 1, minor: 0)
    public let session: HanlinHostSession
    private let read: PinkhaHanlinHostAdapter
    private let write: (any PinkhaHanlinWriteBinding)?
    private let revision = HanlinCatalogRevision(1) // Both actual delegated validators consume revision1; no DTO rewriting.
    private let readLogical: HanlinLogicalToolID
    private let readDescriptor: HanlinDescriptorRevision
    private var invalidated = false
    private var calls: [HanlinToolInvocationID: Call] = [:]
    private var providerCalls: [ProviderCall: HanlinToolInvocationID] = [:]
    private var cancelled = Set<HanlinToolInvocationID>()

    private enum Route: Sendable { case read, createPage }
    private struct ProviderCall: Hashable {
        let run: UUID
        let step: Int
        let opaqueID: Data
    }
    private struct Call {
        let route: Route
        let provider: ProviderCall
        let fingerprint: String
        let cancellation: PinkhaHanlinRevocationFence
    }

    public init(read: PinkhaHanlinHostAdapter, session: HanlinHostSession,
                 write: (any PinkhaHanlinWriteBinding)?) throws {
        self.read = read; self.session = session; self.write = write
        self.readLogical = .init(providerInstanceID: try .init(validating: "anytype.host"),
                                 localToolID: try .init(validating: "read-context-text"))
        self.readDescriptor = try .init(1)
    }


    public var missingWriteInstallation: [PinkhaHanlinWriteInstallationRequirement] {
        write?.missingInstallation ?? PinkhaHanlinWriteInstallationRequirement.missing
    }

    public func observeInvalidation(_ callback: @escaping @MainActor () -> Void) {
        write?.observeInvalidation(callback)
    }

    /// Synchronous revoke precedes cancellation's first await so no queued native write can start.
    public func revokePresentation() {
        invalidated = true
        write?.invalidate()
        for call in calls.values { call.cancellation.revoke() }
    }

    public func context(for session: HanlinHostSession) async throws -> HanlinHostContext {
        try validateLocal(session)
        let result = try await read.context(for: session)
        try validateLocal(session)
        guard result == self.session.context else { throw HanlinHostError.staleContext }
        return result
    }

    public func catalog(for context: HanlinHostContext) async throws -> HanlinHostCatalog {
        guard context == session.context else { throw HanlinHostError.staleContext }
        _ = try await self.context(for: session)
        let original = try await read.catalog(for: context)
        try original.validate()
        guard original.context == context, original.revision == revision,
              original.tools.count <= 1,
              original.tools.allSatisfy({
                  $0.route.alias.utf8.elementsEqual("anytype_read_context_text".utf8)
                    && $0.route.logicalToolID == readLogical && $0.route.descriptorRevision == readDescriptor
                    && $0.writeGuarantee == .readOnly
              }) else { throw HanlinHostError.resultMismatch }
        var tools = original.tools
        if let tool = try await write?.catalogTool() { tools.append(tool) }
        _ = try await self.context(for: session) // All delegated readiness operations are awaits.
        let result = HanlinHostCatalog(revision: revision, context: context, tools: tools)
        try result.validate()
        return result
    }

    public func execute(_ invocation: HanlinHostInvocation,
                 progress: @escaping HanlinHostProgressHandler) async throws -> HanlinHostExecutionResult {
        // A known call keeps its original disposition even after consent, deadline or lifetime changes.
        try rejectClaimedIdentity(invocation)
        // This block is PRE-dispatch only. Never map a delegated write exception to notDispatched.
        let route: Route
        do {
            try validateLocal(invocation.session)
            guard !cancelled.contains(invocation.request.id) else { throw HanlinHostError.cancelled }
            try validateEnvelope(invocation)
            let current = try await catalog(for: invocation.session.context)
            try validateLocal(invocation.session)
            guard !cancelled.contains(invocation.request.id),
                  let tool = current.tools.first(where: {
                      $0.route.alias.utf8.elementsEqual(invocation.request.aliasUsed.utf8)
                        && $0.route.logicalToolID == invocation.request.logicalToolID
                        && $0.route.descriptorRevision == invocation.request.descriptorRevision
                        && $0.writeGuarantee == invocation.writeGuarantee
                  }) else { throw HanlinHostError.unknownTool }
            if tool.writeGuarantee == .readOnly {
                guard case .object(let members) = invocation.request.arguments, members.isEmpty else {
                    throw HanlinHostError.invalidArguments
                }
                route = .read
            } else {
                _ = try PinkhaHanlinCreatePagePlan(invocation: invocation)
                guard write != nil else { throw HanlinHostError.denied }
                route = .createPage
            }
        } catch {
            // catalog() awaited: another attempt may have claimed this identity while we suspended.
            try rejectClaimedIdentity(invocation)
            if error is CancellationError || cancelled.contains(invocation.request.id) { throw HanlinHostError.cancelled }
            return refusal(invocation)
        }
        let provider = ProviderCall(run: invocation.runID, step: invocation.step, opaqueID: Data(invocation.providerCallID.utf8))
        // Bounded validated arguments only; no raw request/result is retained or persisted here.
        // This cross-route guard rejects replay BEFORE another approval prompt or delegate dispatch.
        try rejectClaimedIdentity(invocation)
        let fingerprint = try boundedFingerprint(invocation, route: route)
        guard calls.count < 256 else { throw HanlinHostError.outputLimitExceeded }
        let call = Call(route: route, provider: provider, fingerprint: fingerprint, cancellation: PinkhaHanlinRevocationFence())
        calls[invocation.request.id] = call; providerCalls[provider] = invocation.request.id
        guard !call.cancellation.isRevoked else { throw HanlinHostError.cancelled }
        let fence = call.cancellation
        return try await withTaskCancellationHandler {
            let result: HanlinHostExecutionResult
            switch route {
            case .read:
                result = try await read.execute(invocation, progress: progress)
            case .createPage:
                guard let write else { throw HanlinHostError.denied }
                result = try await write.execute(invocation, cancellation: fence, progress: progress)
            }
            // Delegates preserve ORIGINAL metadata before this stale/cancelled delivery check.
            _ = try await context(for: invocation.session)
            guard !fence.isRevoked, !cancelled.contains(invocation.request.id) else { throw HanlinHostError.cancelled }
            return result
        } onCancel: {
            fence.revoke()
            Task { @MainActor in await self.cancel(invocation.request.id) }
        }
    }

    public func cancel(_ id: HanlinToolInvocationID) async {
        if cancelled.count < 256 || cancelled.contains(id) { cancelled.insert(id) }
        else { await invalidate(); return }
        guard let call = calls[id] else { return } // Pre-dispatch cancellation is checked before a route can be claimed.
        call.cancellation.revoke()
        switch call.route {
        case .read: await read.cancel(id)
        case .createPage: await write?.cancel(id)
        }
    }

    public func drainCancelledInvocation(_ id: HanlinToolInvocationID) async -> HanlinHostExecutionResult? {
        guard let call = calls[id] else { return nil }
        // Deliberately no current-account validation: only the worker retained
        // by this original router can settle its original invocation metadata.
        switch call.route {
        case .read: return read.receipt(for: id)?.metadataReceipt()
        case .createPage: return await write?.drainCancelledInvocation(id)?.metadataReceipt()
        }
    }

    public func open(_ destination: HanlinHostDestination) async throws -> HanlinHostNavigationResult {
        guard destination.context == session.context else { throw HanlinHostError.staleContext }
        _ = try await context(for: session)
        let result = try await read.open(destination) // Actual original-object navigation + queued/ACK semantics.
        _ = try await context(for: session)
        try result.validate(for: destination)
        return result
    }

    public func requestContextReadConsent() async throws {
        try validateLocal(session)
        guard let write else { throw HanlinHostError.denied }
        try await write.requestContextReadConsent()
    }

    public func metadataReceipt(for id: HanlinToolInvocationID) -> HanlinHostExecutionResult? {
        guard let call = calls[id] else { return nil }
        switch call.route {
        case .read: return read.receipt(for: id)?.metadataReceipt()
        case .createPage: return write?.metadataReceipt(for: id)
        }
    }

    public func invalidate() async {
        revokePresentation()
        for (id, call) in calls {
            call.cancellation.revoke()
            switch call.route {
            case .read: await read.cancel(id)
            case .createPage: await write?.cancel(id)
            }
        }
        for id in calls.keys { _ = await drainCancelledInvocation(id) }
    }

    public func validateCurrentSession(_ session: HanlinHostSession) throws { try validateLocal(session) }

    private func validateLocal(_ session: HanlinHostSession) throws {
        try Task.checkCancellation()
        guard !invalidated, session == self.session else { throw HanlinHostError.staleContext }
    }

    private func rejectClaimedIdentity(_ invocation: HanlinHostInvocation) throws {
        let boundedProvider = invocation.step >= 0 && !invocation.providerCallID.isEmpty
            && invocation.providerCallID.utf8.count <= 1_024
        if let existing = calls[invocation.request.id] {
            guard invocation.session == session else { throw HanlinHostError.staleContext }
            guard boundedProvider else { throw HanlinHostError.idempotencyConflict }
            let provider = ProviderCall(run: invocation.runID, step: invocation.step, opaqueID: Data(invocation.providerCallID.utf8))
            guard existing.provider == provider,
                  let fingerprint = try? boundedFingerprint(invocation, route: existing.route),
                  fingerprint == existing.fingerprint else { throw HanlinHostError.idempotencyConflict }
            throw HanlinHostError.duplicateInvocation
        }
        guard boundedProvider else { return } // A genuinely new malformed attempt still uses normal preflight.
        let provider = ProviderCall(run: invocation.runID, step: invocation.step, opaqueID: Data(invocation.providerCallID.utf8))
        if providerCalls[provider] != nil {
            guard invocation.session == session else { throw HanlinHostError.staleContext }
            throw HanlinHostError.idempotencyConflict // No argument encoding is needed for a reminted provider identity.
        }
    }

    /// Static bounded shape only, intentionally independent of live catalog/consent/deadline freshness.
    /// Invalid changes to a known call become conflict without encoding arbitrary business arguments.
    private func boundedFingerprint(_ invocation: HanlinHostInvocation, route: Route) throws -> String {
        let request = invocation.request
        let alias = route == .read ? "anytype_read_context_text" : PinkhaHanlinCreatePagePlan.alias
        guard request.aliasUsed.utf8.elementsEqual(alias.utf8), invocation.expectedRevision == nil,
              invocation.writeGuarantee == (route == .read ? .readOnly : .independentObjectCreation),
              request.origin == .assistantModel, request.grantIDs.isEmpty,
              request.appSessionID == nil, request.runtimeSessionID == nil, PinkhaHanlinInvocationEnvelope.acceptsSDKIdentity(request),
              request.deadline.map({ $0.timeIntervalSinceReferenceDate.isFinite }) ?? true,
              case .object(let members) = request.arguments else { throw HanlinHostError.invalidArguments }
        switch route {
        case .read:
            guard members.isEmpty else { throw HanlinHostError.invalidArguments }
        case .createPage:
            guard members.count == 1, let value = members["title"], case .string(let title) = value,
                  title.utf8.count <= 512 else { throw HanlinHostError.invalidArguments }
        }
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return PinkhaHanlinCreatePagePlan.digest(try encoder.encode(request))
    }

    private func validateEnvelope(_ invocation: HanlinHostInvocation) throws {
        let request = invocation.request
        guard invocation.expectedRevision == nil,
              invocation.writeGuarantee == .readOnly || invocation.writeGuarantee == .independentObjectCreation,
              request.routingTableRevision == revision,
              request.origin == .assistantModel, request.grantIDs.isEmpty,
              request.appSessionID == nil, request.runtimeSessionID == nil, PinkhaHanlinInvocationEnvelope.acceptsSDKIdentity(request),
              invocation.step >= 0, !invocation.providerCallID.isEmpty, invocation.providerCallID.utf8.count <= 1_024,
              request.limits.timeoutMilliseconds > 0, request.limits.timeoutMilliseconds <= 30_000,
              request.limits.maximumOutputBytes > 0, request.limits.maximumOutputBytes <= 8 * 1_048_576,
              let deadline = request.deadline, deadline > .now, deadline.timeIntervalSinceNow <= 30 else {
            throw HanlinHostError.invalidArguments
        }
    }

    private func refusal(_ invocation: HanlinHostInvocation) -> HanlinHostExecutionResult {
        .init(result: .init(invocationID: invocation.request.id, logicalToolID: invocation.request.logicalToolID,
            outcome: .failed(.init(code: .operationUnavailable, userMessage: "Host capability unavailable")), completedAt: .now),
            effectState: .notDispatched, context: invocation.session.context)
    }
}
