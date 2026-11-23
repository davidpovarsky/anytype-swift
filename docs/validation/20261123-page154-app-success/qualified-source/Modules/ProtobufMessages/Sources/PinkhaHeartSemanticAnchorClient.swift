#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1
import Foundation

/// Internal injection is for focused controls. Product construction is available
/// only through the separately gated native page154 factory.
@MainActor
struct PinkhaHeartSemanticAnchorIO {
    let runtimeVersion: @MainActor @Sendable () async throws -> String
    let read: @MainActor @Sendable (String, String) async throws -> Anytype_Rpc.Object.Show.Response
    let capture: @MainActor @Sendable (Data) async throws -> Data
    let canPublish: @MainActor @Sendable () -> Bool
    let publish: @MainActor @Sendable (Anytype_ResponseEvent) async -> Bool
}

@MainActor
public final class PinkhaHeartSemanticAnchorPending {
    fileprivate let plan: PinkhaHeartSemanticAnchorPlan
    fileprivate let lease: PinkhaNativeReadLease
    fileprivate let accountID: String
    fileprivate let generation: UUID
    private var consumed = false

    public var marker: String { plan.request.marker }

    fileprivate init(plan: PinkhaHeartSemanticAnchorPlan, lease: PinkhaNativeReadLease) {
        self.plan = plan; self.lease = lease
        accountID = lease.accountID; generation = lease.generation
    }

    fileprivate func validateOwner() throws {
        do { try lease.validate() }
        catch { throw PinkhaHeartSemanticAnchorError.retiredOwner }
        guard generation == lease.generation, heartBytesEqual(accountID, lease.accountID),
              heartBytesEqual(plan.request.spaceID, lease.spaceID) else {
            throw PinkhaHeartSemanticAnchorError.retiredOwner
        }
    }

    fileprivate func validateUnconsumed() throws {
        guard !consumed else { throw PinkhaHeartSemanticAnchorError.invalidRequest }
    }

    fileprivate func consume() throws {
        try validateUnconsumed()
        consumed = true
    }
}

public struct PinkhaHeartSemanticAnchorVerifiedCapture: Sendable {
    public let receipt: PinkhaHeartSemanticAnchorReceipt
    public let generation: UUID
    fileprivate init(receipt: PinkhaHeartSemanticAnchorReceipt, generation: UUID) {
        self.receipt = receipt; self.generation = generation
    }
}

/// The app lease is an owner/generation fence, not native write permission.
/// Only the qualified Heart service acquires the native writer lifetime and ACL.
///
/// Cancellation is honored before the mutation is queued. Once queued, the
/// operation completes publication/readback in an owned task; it is never retried.
@MainActor
public final class PinkhaHeartSemanticAnchorClient {
    private let io: PinkhaHeartSemanticAnchorIO

    init(io: PinkhaHeartSemanticAnchorIO) { self.io = io }

    public func prepare(_ plan: PinkhaHeartSemanticAnchorPlan,
                        lease: PinkhaNativeReadLease) throws -> PinkhaHeartSemanticAnchorPending {
        let pending = PinkhaHeartSemanticAnchorPending(plan: plan, lease: lease)
        try pending.validateOwner()
        return pending
    }

    /// Prepare a visible selection against a complete current native block.
    /// This performs reads only. A later explicit apply rechecks the same CAS.
    public func prepareVisibleSelection(
        spaceID: String, objectID: String, blockID: String, anchorID: String,
        visibleText: String, range: NSRange, lease: PinkhaNativeReadLease
    ) async throws -> PinkhaHeartSemanticAnchorPending {
        try Task.checkCancellation()
        do { try lease.validate() }
        catch { throw PinkhaHeartSemanticAnchorError.retiredOwner }
        guard heartBytesEqual(spaceID, lease.spaceID) else {
            throw PinkhaHeartSemanticAnchorError.retiredOwner
        }
        guard io.canPublish() else { throw PinkhaHeartSemanticAnchorError.unavailablePublication }
        let version = try await io.runtimeVersion()
        do { try lease.validate() }
        catch { throw PinkhaHeartSemanticAnchorError.retiredOwner }
        guard heartBytesEqual(version, PinkhaHeartSemanticAnchorProfile.runtimeVersion) else {
            throw PinkhaHeartSemanticAnchorError.unsupportedRuntime
        }
        let current = try await io.read(spaceID, objectID)
        do { try lease.validate() }
        catch { throw PinkhaHeartSemanticAnchorError.retiredOwner }
        try Task.checkCancellation()
        guard let block = current.objectView.blocks.first(where: { heartBytesEqual($0.id, blockID) }) else {
            throw PinkhaHeartSemanticAnchorError.changedDocument
        }
        let plan = try PinkhaHeartSemanticAnchorPlan(
            spaceID: spaceID, objectID: objectID, anchorID: anchorID, range: range, nativeBlock: block)
        guard heartBytesEqual(plan.request.expected.text, visibleText) else {
            throw PinkhaHeartSemanticAnchorError.changedDocument
        }
        try plan.verifyCurrent(current)
        return try prepare(plan, lease: lease)
    }

    public func apply(_ pending: PinkhaHeartSemanticAnchorPending) async throws
        -> PinkhaHeartSemanticAnchorVerifiedCapture {
        try Task.checkCancellation()
        try pending.validateUnconsumed()
        try pending.validateOwner()
        guard io.canPublish() else { throw PinkhaHeartSemanticAnchorError.unavailablePublication }
        let version = try await io.runtimeVersion()
        try pending.validateOwner()
        guard heartBytesEqual(version, PinkhaHeartSemanticAnchorProfile.runtimeVersion) else {
            throw PinkhaHeartSemanticAnchorError.unsupportedRuntime
        }
        let current = try await io.read(pending.plan.request.spaceID, pending.plan.request.objectID)
        try pending.validateOwner()
        try pending.plan.verifyCurrent(current)
        try Task.checkCancellation()
        guard io.canPublish() else { throw PinkhaHeartSemanticAnchorError.unavailablePublication }
        try pending.consume()
        // This is deliberately an owned, unstructured task. Cancelling the
        // caller after dispatch must not cancel normal ObjectShow readback.
        return try await Task { @MainActor in
            try await self.finishQueuedCapture(pending)
        }.value
    }

    private func finishQueuedCapture(_ pending: PinkhaHeartSemanticAnchorPending) async throws
        -> PinkhaHeartSemanticAnchorVerifiedCapture {
        do {
            try pending.validateOwner()
            let raw = try await io.capture(pending.plan.request.encodedRequest())
            try pending.validateOwner()
            let reply = try PinkhaHeartSemanticAnchorAppliedReply.decode(raw, request: pending.plan.request)
            let event = try pending.plan.validatedEvent(reply)
            try pending.validateOwner()
            // Publish the unchanged returned native event through the original
            // Invocation handler. No synthetic reducer event is manufactured.
            let fence = try PinkhaHeartSemanticAnchorPublicationFence(
                lease: pending.lease, objectID: pending.plan.request.objectID, event: event)
            let published = await PinkhaHeartSemanticAnchorPublication.$current.withValue(fence) {
                await io.publish(event)
            }
            guard published else { throw PinkhaHeartSemanticAnchorError.uncertain }
            try pending.validateOwner()
            let readback = try await io.read(pending.plan.request.spaceID, pending.plan.request.objectID)
            try pending.validateOwner()
            try pending.plan.verifyReadback(readback, receipt: reply.receipt)
            return .init(receipt: reply.receipt, generation: pending.generation)
        } catch let error as PinkhaHeartSemanticAnchorError {
            if case .nativeRefusal = error { throw error }
            throw PinkhaHeartSemanticAnchorError.uncertain
        } catch {
            throw PinkhaHeartSemanticAnchorError.uncertain
        }
    }
}
enum PinkhaHeartSemanticAnchorNativePublication {
    static func send(_ event: Anytype_ResponseEvent) async -> Bool {
        guard let handler = InvocationSettings.handler else { return false }
        await handler.eventHandler(event: event)
        return true
    }
}
#endif
