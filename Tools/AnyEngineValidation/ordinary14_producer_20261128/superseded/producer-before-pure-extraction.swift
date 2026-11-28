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


/// A distinct result for the explicitly requested, finite Ordinary14 stage.
/// Each checkpoint comes from its own completed journal and native verifier.
/// The third locator and merged directory are routing evidence, not a lease.
public struct AnyHeartNativeOrdinaryMigrationCompletion: Sendable {
    public let preservation: AnyHeartNativeMigrationCompletion
    public let ordinaryCheckpoint: AnyDestinationSavedCheckpoint
    public let ordinaryVerification: AnyDestinationContentVerification
    public let ordinaryReference: AnyNativeImportedOrdinaryPropertyReference
    public let encodedOrdinaryReference: Data
    public let definitionDirectory: AnyNativeImportedDefinitionDirectory
    public let outsideSliceIssues: [AnyHeartNativeDefinitionPlan.Issue]
    public let outsideSliceRelationObjectIDs: [String]
    public var grantsNativeAuthority: Bool { false }
    public var sourceHistoryBecameTargetHistory: Bool { false }
    public var qualifiesWholeSourceBehavior: Bool { false }
}

/// One concrete migration lifetime around the ORIGINAL source account owner.
/// Pass the same presentation owner's destination-operation API as the adapter
/// to execute(..., inDestination:). Its callback supplies the real client/session/lease.
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

    // Retain both exact journal scope admissions until the complete destination
    // operation has returned. A pending callback cannot be entered a second time.
    private struct OrdinaryPrepared: Sendable {
        let completion: AnyHeartNativeOrdinaryMigrationCompletion
        let stage: AnyHeartNativeOrdinaryExecutionStage
        let preservationStorage: AnyHeartMigrationPrivateStorage
        let ordinaryStorage: AnyHeartMigrationPrivateStorage
    }
    private struct OrdinaryPending: Sendable {
        let ticket: UUID
        let prepared: OrdinaryPrepared?
    }
    private var ordinaryPending: OrdinaryPending?

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

    public typealias DestinationBody = @Sendable (
        AnyHTTPClient, AnyApplicationSession, AnyHostLease
    ) async throws -> AnyHeartNativeMigrationCompletion
    public typealias DestinationOperation = @Sendable (
        _ body: @escaping DestinationBody
    ) async throws -> AnyHeartNativeMigrationCompletion

    /// The App adapter invokes the ORIGINAL presentation-owned operation here.
    /// Registration surrounds that entire invocation, including its final async
    /// session validation and presentation delivery fence, not just our body.
    public func execute(_ request: AnyHeartNativeMigrationRequest,
                        inDestination: @escaping DestinationOperation) async throws -> AnyHeartNativeMigrationCompletion {
        try await withOwnedOperation { ticket in
            try await inDestination { client, session, lease in
                try await self.produce(request, client: client, session: session, lease: lease, ticket: ticket)
            }
        }
    }

    public typealias OrdinaryDestinationBody = @Sendable (
        AnyHTTPClient, AnyApplicationSession, AnyHostLease
    ) async throws -> AnyHeartNativeOrdinaryMigrationCompletion
    public typealias OrdinaryDestinationOperation = @Sendable (
        _ body: @escaping OrdinaryDestinationBody
    ) async throws -> AnyHeartNativeOrdinaryMigrationCompletion

    /// Explicitly execute the preservation/content stage, then only the strict
    /// fourteen-property supplement in the same existing destination operation.
    /// The original execute() remains the two-locator API. A failed second stage
    /// retains both journals; it is not rolled back or reported as completion.
    public func executeWithOrdinaryProperties(
        _ request: AnyHeartNativeMigrationRequest,
        inDestination: @escaping OrdinaryDestinationOperation
    ) async throws -> AnyHeartNativeOrdinaryMigrationCompletion {
        try await withOwnedOperation { ticket in
            do {
                let returned = try await inDestination { client, session, lease in
                    try await self.produceOrdinary(request, client: client, session: session,
                                                  lease: lease, ticket: ticket)
                }
                // Only synchronous storage/two-journal checks follow the
                // destination owner's last awaited validation and delivery fence.
                return try await self.finishOrdinary(returned, ticket: ticket)
            } catch {
                await self.discardOrdinary(ticket: ticket)
                throw error
            }
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
                         ticket: UUID, requiredDestinationRun: AnyNativeAccountRunBinding? = nil
    ) async throws -> AnyHeartNativeMigrationCompletion {
        try requireActive(ticket)
        guard Self.same(request.workspace, lease.workspace), Self.same(session.workspace, lease.workspace),
              Data(client.expectedAccountID.utf8) == Data(lease.workspace.accountID.utf8),
              session.generation == lease.generation,
              Data(session.engineStartedAt.utf8) == Data(lease.engineStartedAt.utf8) else {
            throw AnyHostError.wrongWorkspace
        }
        try await lease.validate()
        guard await session.isActive else { throw AnyHostError.sessionClosed }
        let run: AnyNativeAccountRunBinding
        if let requiredDestinationRun { run = requiredDestinationRun }
        else { run = try await client.nativeAccountRunBinding(expectedNetworkID: request.networkID) }
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
        // The real App namespace owner retains these private names without
        // relocation until the full producer operation drains. This scope pins
        // directory FDs and detects replacements; it is not an OS rename lock.
        let storage = try AnyHeartMigrationPrivateStorage(captureParent: captureParent,
            captureDirectory: review.descriptor.privateBundleDirectory,
            journalParent: request.journalParent, payloadParent: request.payloadParent,
            planBinding: plan.binding)
        let payload = try storage.materialize(archive)
        try requireActive(ticket)

        let sourceKey = preservation.archiveItemSourceKey
        let verify: @Sendable (AnyDestinationSourceBinding) async throws -> Void = { binding in
            try await self.verifySource(binding, ticket: ticket)
        }
        let authorize: @Sendable () async throws -> Void = {
            try await self.requireCurrentTicket(ticket)
            try storage.validate()
            try await destination.validate()
            try storage.validate()
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
        try storage.validate()
        try requireActive(ticket)
        try Task.checkCancellation()
        return .init(checkpoint: checkpoint, verification: verification, preservationReference: reference,
            contentReference: content, encodedPreservationReference: encodedReference,
            encodedContentReference: encodedContent, privateArchiveURL: payload, journalParent: request.journalParent)
    }

    private func produceOrdinary(
        _ request: AnyHeartNativeMigrationRequest, client: AnyHTTPClient,
        session: AnyApplicationSession, lease: AnyHostLease, ticket: UUID
    ) async throws -> AnyHeartNativeOrdinaryMigrationCompletion {
        try requireCurrentTicket(ticket)
        guard ordinaryPending == nil else { throw AnyHeartNativeMigrationProducerError.busy }
        ordinaryPending = .init(ticket: ticket, prepared: nil)

        guard Self.same(request.workspace, lease.workspace), Self.same(session.workspace, lease.workspace),
              Data(client.expectedAccountID.utf8) == Data(lease.workspace.accountID.utf8),
              session.generation == lease.generation,
              Data(session.engineStartedAt.utf8) == Data(lease.engineStartedAt.utf8) else {
            throw AnyHostError.wrongWorkspace
        }
        try await lease.validate()
        guard await session.isActive else { throw AnyHostError.sessionClosed }
        // Select one destination run before either stage. Both the unchanged
        // first-stage path and every supplemental admission require this run.
        let run = try await client.nativeAccountRunBinding(expectedNetworkID: request.networkID)
        let destination = AnyHeartMigrationDestinationAdmission(client: client, lease: lease, run: run)
        try await destination.validate()
        try requireCurrentTicket(ticket)
        let preservation = try await produce(request, client: client, session: session,
            lease: lease, ticket: ticket, requiredDestinationRun: run)
        let stage = try AnyHeartNativeOrdinaryExecutionStage(bundle: review.bundle,
            preservationReference: preservation.preservationReference,
            checkpoint: preservation.checkpoint)
        let plan = stage.supplement.plan
        try plan.requireExecutable()
        try await verifySource(stage.preservation.plan.source, ticket: ticket)
        try await destination.validate()
        try requireCurrentTicket(ticket)

        // Both original and new binding-specific journal paths are admitted.
        // The real App namespace owner still prevents relocation through drain.
        let preservationStorage = try AnyHeartMigrationPrivateStorage(captureParent: captureParent,
            captureDirectory: review.descriptor.privateBundleDirectory,
            journalParent: request.journalParent, payloadParent: request.payloadParent,
            planBinding: preservation.checkpoint.plan.binding)
        let ordinaryStorage = try AnyHeartMigrationPrivateStorage(captureParent: captureParent,
            captureDirectory: review.descriptor.privateBundleDirectory,
            journalParent: request.journalParent, payloadParent: request.payloadParent,
            planBinding: plan.binding)
        try stage.requirePreservation(AnyDestinationMigrationExecutor.readCompletedCheckpoint(
            journalDirectory: request.journalParent, binding: preservation.checkpoint.plan.binding))

        let verify: @Sendable (AnyDestinationSourceBinding) async throws -> Void = { supplied in
            // Refuse a foreign/changed subset before invoking the live verifier.
            // Its complete-census requirement is never weakened to fourteen IDs.
            let complete = try stage.completeCaptureSource(for: supplied)
            try await self.verifySource(complete, ticket: ticket)
        }
        let authorize: @Sendable () async throws -> Void = {
            try await self.requireCurrentTicket(ticket)
            try preservationStorage.validate(); try ordinaryStorage.validate()
            try await destination.validate()
            try preservationStorage.validate(); try ordinaryStorage.validate()
            try await self.requireCurrentTicket(ticket)
        }
        let executor = AnyDestinationMigrationExecutor(client: client, journalDirectory: request.journalParent)
        let progress = try await executor.execute(plan: plan, payloads: { key in
            // This plan is property-definition-only, with no payload operation.
            throw AnyDestinationMigrationError.payloadMismatch(key)
        }, verifySource: verify, authorize: authorize)
        let verification = try await AnyDestinationMigrationVerifier(client: client).verify(
            plan: plan, progress: progress, verifySource: verify, authorize: authorize)
        var checkpoint = try AnyDestinationMigrationExecutor.readCompletedCheckpoint(
            journalDirectory: request.journalParent, binding: plan.binding)
        try Self.requireCheckpoint(checkpoint, plan: plan, progress: progress)
        let reference = try stage.reference(checkpoint: checkpoint)
        let encoded = try reference.encoded()
        let directory = try stage.supplement.directory(mappings: checkpoint.mappings)
        try await verify(plan.source)
        try await authorize()
        checkpoint = try AnyDestinationMigrationExecutor.readCompletedCheckpoint(
            journalDirectory: request.journalParent, binding: plan.binding)
        try Self.requireCheckpoint(checkpoint, plan: plan, progress: progress)
        guard checkpoint.checkpointSHA256 == reference.supplementCheckpointSHA256 else {
            throw AnyHeartNativeMigrationProducerError.changedCheckpoint
        }
        try stage.requirePreservation(AnyDestinationMigrationExecutor.readCompletedCheckpoint(
            journalDirectory: request.journalParent, binding: preservation.checkpoint.plan.binding))
        try preservationStorage.validate(); try ordinaryStorage.validate()
        try requireCurrentTicket(ticket)
        let completion = AnyHeartNativeOrdinaryMigrationCompletion(preservation: preservation,
            ordinaryCheckpoint: checkpoint, ordinaryVerification: verification,
            ordinaryReference: reference, encodedOrdinaryReference: encoded,
            definitionDirectory: directory, outsideSliceIssues: stage.supplement.outsideSliceIssues,
            outsideSliceRelationObjectIDs: stage.supplement.outsideSliceRelationObjectIDs)
        ordinaryPending = .init(ticket: ticket, prepared: .init(completion: completion, stage: stage,
            preservationStorage: preservationStorage, ordinaryStorage: ordinaryStorage))
        return completion
    }

    private func finishOrdinary(_ returned: AnyHeartNativeOrdinaryMigrationCompletion,
                                ticket: UUID) throws -> AnyHeartNativeOrdinaryMigrationCompletion {
        try requireCurrentTicket(ticket)
        guard let pending = ordinaryPending, pending.ticket == ticket, let prepared = pending.prepared else {
            throw AnyHeartNativeMigrationProducerError.changedCheckpoint
        }
        let expected = prepared.completion
        guard returned.encodedOrdinaryReference == expected.encodedOrdinaryReference,
              returned.preservation.encodedPreservationReference == expected.preservation.encodedPreservationReference,
              returned.preservation.encodedContentReference == expected.preservation.encodedContentReference,
              returned.ordinaryCheckpoint.checkpointSHA256 == expected.ordinaryCheckpoint.checkpointSHA256,
              returned.preservation.checkpoint.checkpointSHA256 == expected.preservation.checkpoint.checkpointSHA256 else {
            throw AnyHeartNativeMigrationProducerError.changedCheckpoint
        }
        // The final live-source observation occurred inside the destination
        // callback. After its owner returns, this function has no suspension or
        // native I/O. App persistence still uses that owner's current validation;
        // these observations do not grant atomic remote or lasting authority.
        try prepared.preservationStorage.validate(); try prepared.ordinaryStorage.validate()
        let preservation = try AnyDestinationMigrationExecutor.readCompletedCheckpoint(
            journalDirectory: expected.preservation.journalParent,
            binding: prepared.stage.preservation.plan.binding)
        try prepared.stage.requirePreservation(preservation)
        let ordinary = try AnyDestinationMigrationExecutor.readCompletedCheckpoint(
            journalDirectory: expected.preservation.journalParent,
            binding: prepared.stage.supplement.plan.binding)
        let reference = try prepared.stage.reference(checkpoint: ordinary)
        guard ordinary.checkpointSHA256 == expected.ordinaryCheckpoint.checkpointSHA256,
              try reference.encoded() == expected.encodedOrdinaryReference,
              reference.preservationReferenceSHA256 ==
                AnyContentDigest.sha256(expected.preservation.encodedPreservationReference) else {
            throw AnyHeartNativeMigrationProducerError.changedCheckpoint
        }
        try prepared.preservationStorage.validate(); try prepared.ordinaryStorage.validate()
        try requireCurrentTicket(ticket)
        ordinaryPending = nil
        // Return this operation's retained result, never an adapter's substituted
        // verification/directory values. Locators still grant no native authority.
        return expected
    }

    private func discardOrdinary(ticket: UUID) {
        if ordinaryPending?.ticket == ticket { ordinaryPending = nil }
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


/// Exact source correspondence for this finite stage. The internal boundary is
/// separately testable without constructing a public native Completion.
struct AnyHeartNativeOrdinaryExecutionStage: Sendable {
    let bundle: AnyHeartNativeSpaceBundle
    let preservationReference: AnyNativeImportedContextReference
    let preservation: AnyDestinationSavedCheckpoint
    let supplement: AnyHeartNativeOrdinaryPropertySupplement

    init(bundle: AnyHeartNativeSpaceBundle, preservationReference: AnyNativeImportedContextReference,
         checkpoint: AnyDestinationSavedCheckpoint) throws {
        self.bundle = bundle; self.preservationReference = preservationReference
        preservation = checkpoint
        supplement = try AnyNativeImportedOrdinaryPropertyReference.supplement(
            preservationReference: preservationReference, bundle: bundle,
            plan: checkpoint.plan, mappings: checkpoint.mappings)
        try requirePreservation(checkpoint)
    }

    func completeCaptureSource(for supplied: AnyDestinationSourceBinding) throws -> AnyDestinationSourceBinding {
        try Task.checkCancellation()
        guard try AnyDestinationMigrationJournal.encoded(supplied) ==
                AnyDestinationMigrationJournal.encoded(supplement.plan.source) else {
            throw AnyDestinationMigrationError.changedSource
        }
        return preservation.plan.source
    }

    func requirePreservation(_ checkpoint: AnyDestinationSavedCheckpoint) throws {
        guard checkpoint.plan.canonicalBytes == preservation.plan.canonicalBytes,
              try AnyDestinationMigrationJournal.encoded(checkpoint.mappings) ==
                AnyDestinationMigrationJournal.encoded(preservation.mappings),
              checkpoint.checkpointSHA256 == preservationReference.checkpointSHA256,
              checkpoint.checkpointSHA256 == (try AnyDestinationSavedCheckpoint.fingerprint(
                plan: checkpoint.plan, mappings: checkpoint.mappings)),
              checkpoint.intents.count == preservation.intents.count else {
            throw AnyHeartNativeMigrationProducerError.changedCheckpoint
        }
        for (actual, expected) in zip(checkpoint.intents, preservation.intents) {
            guard actual.identity.id == expected.identity.id,
                  actual.identity.spec == expected.identity.spec,
                  actual.identity.sha == expected.identity.sha else {
                throw AnyHeartNativeMigrationProducerError.changedCheckpoint
            }
        }
        try Task.checkCancellation()
    }

    func reference(checkpoint: AnyDestinationSavedCheckpoint) throws
        -> AnyNativeImportedOrdinaryPropertyReference {
        try AnyNativeImportedOrdinaryPropertyReference(preservationReference: preservationReference,
            bundle: bundle, completedPreservationPlan: preservation.plan,
            completedPreservationMappings: preservation.mappings, checkpoint: checkpoint)
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
