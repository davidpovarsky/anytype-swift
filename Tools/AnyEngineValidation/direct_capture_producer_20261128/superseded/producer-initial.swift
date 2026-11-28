import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

public enum AnyHeartNativeMigrationProducerError: Error, Equatable, Sendable {
    case inactive, busy, invalidRequest, changedCapture, changedCheckpoint, privateStorage
}

/// Explicit destination and private-storage selection supplied by the real App.
/// No account, Space, store, plan or path is inferred from a title or a default.
public struct AnyHeartNativeMigrationRequest: Sendable {
    public let networkID: String
    public let workspace: AnyTorahWorkspace
    public let storeID: String
    public let planID: String
    public let journalParent: URL
    public let payloadParent: URL
    public let supplementalCanonicalDefinitions: [AnyDestinationCanonicalPropertyBinding]

    public init(networkID: String, workspace: AnyTorahWorkspace, storeID: String, planID: String,
                journalParent: URL, payloadParent: URL,
                supplementalCanonicalDefinitions: [AnyDestinationCanonicalPropertyBinding] = []) throws {
        guard AnyPreparedMigrationPlanBinding.validOpaque(networkID, maximum: 4096),
              AnyPreparedMigrationPlanBinding.validOpaque(storeID, maximum: 4096),
              AnyDestinationPlanChecks.digest(planID), journalParent.isFileURL, payloadParent.isFileURL,
              supplementalCanonicalDefinitions.count <= 9 else {
            throw AnyHeartNativeMigrationProducerError.invalidRequest
        }
        self.networkID = networkID; self.workspace = workspace; self.storeID = storeID; self.planID = planID
        self.journalParent = journalParent; self.payloadParent = payloadParent
        self.supplementalCanonicalDefinitions = supplementalCanonicalDefinitions
    }
}

/// The actual executor, verifier and completed journal supply this value.
/// Store its private locators through the App's existing persistence owner.
/// This value is not Codable, contains no source token, and grants no new lease.
public struct AnyHeartNativeMigrationCompletion: Sendable {
    public let checkpoint: AnyDestinationSavedCheckpoint
    public let verification: AnyDestinationContentVerification
    public let preservationReference: AnyNativeImportedContextReference
    public let contentReference: AnyNativeImportedContentContextReference
    public let encodedPreservationReference: Data
    public let encodedContentReference: Data
    public let privateArchiveURL: URL
    public let journalParent: URL
    public var grantsNativeAuthority: Bool { false }
    public var sourceHistoryBecameTargetHistory: Bool { false }
    public var qualifiesWholeSourceBehavior: Bool { false }
}

/// One concrete migration lifetime around the ORIGINAL source account owner.
/// Invoke execute from the same presentation owner's destination-operation API;
/// the client/session/lease must be the triple supplied by that callback.
/// Once created, App account/Space/engine invalidation must call this owner's
/// invalidate and await it before releasing the source or transferring the UI.
/// No second engine, account session, executor implementation or replay path is
/// introduced here. Native coexistence still needs actual platform qualification.
public actor AnyHeartNativeMigrationProducer {
    private struct Registered: Sendable {
        let id: UUID
        let cancel: @Sendable () -> Void
        let join: @Sendable () async -> Void
    }
    private let source: AnyHeartNativeSourceAccountController
    private let review: AnyHeartNativeSourceCaptureReview
    private let captureParent: URL
    private var active: Registered?
    private var invalidated = false
    private var cleanup: Task<Void, Error>?
    private var cleanupID: UUID?

    public init(source: AnyHeartNativeSourceAccountController,
                review: AnyHeartNativeSourceCaptureReview, privateCaptureParent: URL) throws {
        guard privateCaptureParent.isFileURL,
              review.descriptor.manifestSHA256 == review.bundle.manifestSHA256,
              review.descriptor.sourceRowsSHA256 == review.bundle.sourceRows.sha256,
              Data(review.descriptor.sourceAccountID.utf8) == Data(review.bundle.sourceAccountID.utf8),
              Data(review.descriptor.sourceSpaceID.utf8) == Data(review.bundle.sourceSpaceID.utf8) else {
            throw AnyHeartNativeMigrationProducerError.changedCapture
        }
        self.source = source; self.review = review; captureParent = privateCaptureParent
    }

    public func execute(_ request: AnyHeartNativeMigrationRequest, client: AnyHTTPClient,
                        session: AnyApplicationSession, lease: AnyHostLease) async throws -> AnyHeartNativeMigrationCompletion {
        try await withOwnedOperation { ticket in
            try await self.produce(request, client: client, session: session, lease: lease, ticket: ticket)
        }
    }

    /// Invalidate synchronously before any suspension. Original native cleanup
    /// never awaits the producer, so revalidate failure cannot form a join cycle.
    /// A native close error remains retryable and blocks caller ownership transfer.
    public func invalidate(reason: AnyHeartNativeSourceCaptureCoordinator.InvalidationReason) async throws {
        invalidated = true
        active?.cancel()
        if let cleanup { try await cleanup.value; return }
        let owned = active, source = self.source, id = UUID()
        cleanupID = id
        let task = Task {
            let native = Task { try await source.invalidate(reason: reason) }
            // Join both paths, including a late destination completion, even
            // when closing the source token failed. Neither error means drain.
            let nativeResult = await native.result
            if let owned { await owned.join() }
            try nativeResult.get()
        }
        cleanup = task
        do {
            try await task.value
            if cleanupID == id { cleanup = nil; cleanupID = nil }
        } catch {
            if cleanupID == id { cleanup = nil; cleanupID = nil }
            throw error
        }
    }

    public func cancel() async throws { try await invalidate(reason: .userCancelled) }
    public func release() async throws { try await invalidate(reason: .released) }

    /// Shared ownership core. Internal visibility permits bounded cancellation
    /// tests without manufacturing a native migration completion.
    func withOwnedOperation<Value: Sendable>(
        _ operation: @escaping @Sendable (UUID) async throws -> Value
    ) async throws -> Value {
        guard !invalidated, cleanup == nil else { throw AnyHeartNativeMigrationProducerError.inactive }
        guard active == nil else { throw AnyHeartNativeMigrationProducerError.busy }
        try Task.checkCancellation()
        let ticket = UUID()
        let task = Task<Value, Error> { try await operation(ticket) }
        active = .init(id: ticket, cancel: { task.cancel() }, join: { _ = await task.result })
        do {
            let value = try await withTaskCancellationHandler {
                try await task.value
            } onCancel: { task.cancel() }
            try requireActive(ticket)
            try Task.checkCancellation()
            active = nil
            return value
        } catch {
            let original = error
            if active?.id == ticket { active = nil }
            // This is the outer caller after the owned task is terminal. It
            // may join native cleanup; internal verifySource never joins itself.
            if Task.isCancelled { try await invalidate(reason: .userCancelled) }
            throw original
        }
    }

    private func requireActive(_ ticket: UUID) throws {
        guard !invalidated, active?.id == ticket else { throw AnyHeartNativeMigrationProducerError.inactive }
    }

    private func verifySource(_ binding: AnyDestinationSourceBinding, ticket: UUID) async throws {
        try requireActive(ticket)
        try Task.checkCancellation()
        try await source.revalidate(source: binding)
        try requireActive(ticket)
        try Task.checkCancellation()
    }

    private func produce(_ request: AnyHeartNativeMigrationRequest, client: AnyHTTPClient,
                         session: AnyApplicationSession, lease: AnyHostLease,
                         ticket: UUID) async throws -> AnyHeartNativeMigrationCompletion {
        try requireActive(ticket)
        guard Self.same(request.workspace, lease.workspace), Self.same(session.workspace, lease.workspace),
              Data(client.expectedAccountID.utf8) == Data(lease.workspace.accountID.utf8),
              session.generation == lease.generation,
              Data(session.engineStartedAt.utf8) == Data(lease.engineStartedAt.utf8) else {
            throw AnyHostError.wrongWorkspace
        }
        try await lease.validate()
        guard await session.isActive else { throw AnyHostError.sessionClosed }
        let run = try await client.nativeAccountRunBinding(expectedNetworkID: request.networkID)
        let destination = AnyHeartMigrationDestinationAdmission(client: client, lease: lease, run: run)
        try await destination.validate()
        try requireActive(ticket)

        // Reading the retained capture is evidence preparation, not migration
        // authority. The real live checkpoint is validated before any new
        // payload/journal output or native destination mutation.
        let captured = try review.descriptor.loadPreservationSource(under: captureParent)
        guard captured.bundle.manifestBytes == review.bundle.manifestBytes else {
            throw AnyHeartNativeMigrationProducerError.changedCapture
        }
        let archive = try AnyHeartNativePreservationArchive(capturedBundle: captured.bundle,
            memberData: captured.capturedMemberData)
        let preservation = try AnyHeartNativeSourcePreservation(capturedBundle: captured.bundle, archive: archive)
        let plan = try preservation.preservationPlan(workspace: request.workspace,
            storeID: request.storeID, planID: request.planID)
        try plan.requireExecutable()
        // Both C22 references address a native file intent, not an inline-file
        // substitute. Refuse before a journal or destination effect is created.
        guard archive.bytes.count >= 4096 else { throw AnyHeartNativeMigrationProducerError.invalidRequest }
        try await verifySource(plan.source, ticket: ticket)
        try await destination.validate()
        try requireActive(ticket)
        try AnyHeartMigrationPrivatePayload.requireParent(request.journalParent,
            excludingCapture: review.descriptor.privateBundleDirectory)
        let payload = try AnyHeartMigrationPrivatePayload.materialize(archive, under: request.payloadParent,
            excludingCapture: review.descriptor.privateBundleDirectory)
        try requireActive(ticket)

        let sourceKey = preservation.archiveItemSourceKey
        let verify: @Sendable (AnyDestinationSourceBinding) async throws -> Void = { binding in
            try await self.verifySource(binding, ticket: ticket)
        }
        let authorize: @Sendable () async throws -> Void = {
            try await self.requireCurrentTicket(ticket)
            try await destination.validate()
            try await self.requireCurrentTicket(ticket)
        }
        let executor = AnyDestinationMigrationExecutor(client: client, journalDirectory: request.journalParent)
        let progress = try await executor.execute(plan: plan, payloads: { key in
            guard Data(key.utf8) == Data(sourceKey.utf8) else {
                throw AnyDestinationMigrationError.payloadMismatch(key)
            }
            return payload
        }, verifySource: verify, authorize: authorize)
        let verification = try await AnyDestinationMigrationVerifier(client: client).verify(
            plan: plan, progress: progress, verifySource: verify, authorize: authorize)
        var checkpoint = try AnyDestinationMigrationExecutor.readCompletedCheckpoint(
            journalDirectory: request.journalParent, binding: plan.binding)
        try Self.requireCheckpoint(checkpoint, plan: plan, progress: progress)
        let reference = try AnyNativeImportedContextReference(networkID: request.networkID,
            preservation: preservation, checkpoint: checkpoint,
            supplementalCanonicalDefinitions: request.supplementalCanonicalDefinitions)
        let content = try AnyNativeImportedContentContextReference(preservationReference: reference,
            preservation: preservation, checkpoint: checkpoint)
        let encodedReference = try reference.encoded(), encodedContent = try content.encoded()
        try await verify(plan.source)
        try await authorize()
        // Synchronous final read follows all native/source awaits. The outer
        // presentation session then performs its own final lease/delivery fence.
        checkpoint = try AnyDestinationMigrationExecutor.readCompletedCheckpoint(
            journalDirectory: request.journalParent, binding: plan.binding)
        try Self.requireCheckpoint(checkpoint, plan: plan, progress: progress)
        guard checkpoint.checkpointSHA256 == reference.checkpointSHA256 else {
            throw AnyHeartNativeMigrationProducerError.changedCheckpoint
        }
        try requireActive(ticket)
        try Task.checkCancellation()
        return .init(checkpoint: checkpoint, verification: verification, preservationReference: reference,
            contentReference: content, encodedPreservationReference: encodedReference,
            encodedContentReference: encodedContent, privateArchiveURL: payload, journalParent: request.journalParent)
    }

    private func requireCurrentTicket(_ ticket: UUID) throws {
        try requireActive(ticket); try Task.checkCancellation()
    }
    private static func requireCheckpoint(_ checkpoint: AnyDestinationSavedCheckpoint,
                                          plan: AnyDestinationMigrationPlan,
                                          progress: AnyDestinationMigrationProgress) throws {
        guard checkpoint.plan.canonicalBytes == plan.canonicalBytes,
              checkpoint.mappings.count == plan.items.count,
              try AnyDestinationMigrationJournal.encoded(checkpoint.mappings) ==
                AnyDestinationMigrationJournal.encoded(progress.mappings),
              checkpoint.checkpointSHA256 == (try AnyDestinationSavedCheckpoint.fingerprint(
                plan: plan, mappings: progress.mappings)) else {
            throw AnyHeartNativeMigrationProducerError.changedCheckpoint
        }
    }
    private static func same(_ a: AnyTorahWorkspace, _ b: AnyTorahWorkspace) -> Bool {
        Data(a.accountID.utf8) == Data(b.accountID.utf8) && Data(a.spaceID.utf8) == Data(b.spaceID.utf8)
    }
}

private struct AnyHeartMigrationDestinationAdmission: Sendable {
    let client: AnyHTTPClient
    let lease: AnyHostLease
    let run: AnyNativeAccountRunBinding

    func validate() async throws {
        guard Data(run.accountID.utf8) == Data(lease.workspace.accountID.utf8),
              Data(client.expectedAccountID.utf8) == Data(lease.workspace.accountID.utf8) else {
            throw AnyHostError.wrongWorkspace
        }
        try await lease.validate()
        try await client.requireNativeAccountRun(run)
        let member = try await client.requestJSON(method: "GET",
            path: ["v1", "spaces", lease.workspace.spaceID, "members", "me"],
            maximumResponseBytes: 65_536, authorize: { try await lease.validate() })
        guard member["identity"]?.string.map({ Data($0.utf8) }) == Data(lease.workspace.accountID.utf8) else {
            throw AnyHostError.wrongWorkspace
        }
        // Current account READ is checked here. Every original prepared native
        // mutation separately enforces Writer at its original atomic boundary.
        try AnyHTTPTorahTargetAccess.validateMember(member, workspace: lease.workspace, intent: .read)
        try await client.requireNativeAccountRun(run)
        try await lease.validate()
    }
}
