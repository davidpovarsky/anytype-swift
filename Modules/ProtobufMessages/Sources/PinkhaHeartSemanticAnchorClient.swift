#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1
import Foundation
import SwiftProtobuf

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
    fileprivate var applyTrace = PinkhaHeartSemanticAnchorApplyObservation()

    public var marker: String { plan.request.marker }
    public var applyObservation: PinkhaHeartSemanticAnchorApplyObservation { applyTrace }

    #if DEBUG && targetEnvironment(simulator)
    /// Read-only bytes from the actual calls of the owned mounted diagnostic.
    /// These are never used as authority, a reply, or an alternate I/O path.
    public private(set) var mountedDiagnosticSnapshots: [String: Data] = [:]

    fileprivate func observeMountedBoundary(_ name: String, data: @autoclosure () throws -> Data) {
        guard ProcessInfo.processInfo.environment["PINKHA_SEMANTIC_MOUNTED_UI"] == "1",
              ["preflight", "nativeReply", "readback"].contains(name),
              mountedDiagnosticSnapshots[name] == nil,
              let bytes = try? data(), !bytes.isEmpty, bytes.count <= 4 * 1_024 * 1_024 else { return }
        mountedDiagnosticSnapshots[name] = bytes
    }
    #endif

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

    /// Read-only resolution uses a new normal authorized ObjectShow, fenced by
    /// the original account/space lease before and after every suspension. No
    /// prepared capture, event replay or publication is involved.
    public func readCurrentDocument(spaceID: String, objectID: String,
                                    lease: PinkhaNativeReadLease) async throws
        -> PinkhaHeartSemanticAnchorDocument {
        try Task.checkCancellation()
        do { try lease.validate() }
        catch { throw PinkhaHeartSemanticAnchorError.retiredOwner }
        guard heartBytesEqual(spaceID, lease.spaceID) else {
            throw PinkhaHeartSemanticAnchorError.retiredOwner
        }
        guard !objectID.isEmpty, objectID.utf8.count <= 1_024, !objectID.contains("\0") else {
            throw PinkhaHeartSemanticAnchorError.invalidRequest
        }
        let version = try await io.runtimeVersion()
        do { try lease.validate() }
        catch { throw PinkhaHeartSemanticAnchorError.retiredOwner }
        guard heartBytesEqual(version, PinkhaHeartSemanticAnchorProfile.runtimeVersion) else {
            throw PinkhaHeartSemanticAnchorError.unsupportedRuntime
        }
        try Task.checkCancellation()
        let current = try await io.read(spaceID, objectID)
        do { try lease.validate() }
        catch { throw PinkhaHeartSemanticAnchorError.retiredOwner }
        try Task.checkCancellation()
        return try .init(response: current, spaceID: spaceID, objectID: objectID)
    }

    public func apply(_ pending: PinkhaHeartSemanticAnchorPending) async throws
        -> PinkhaHeartSemanticAnchorVerifiedCapture {
        pending.applyTrace.record(.checkingPreflight)
        try Task.checkCancellation()
        try pending.validateUnconsumed()
        try pending.validateOwner()
        guard io.canPublish() else { throw PinkhaHeartSemanticAnchorError.unavailablePublication }
        pending.applyTrace.record(.readingRuntime)
        let version = try await io.runtimeVersion()
        pending.applyTrace.record(.checkingRuntime)
        try pending.validateOwner()
        guard heartBytesEqual(version, PinkhaHeartSemanticAnchorProfile.runtimeVersion) else {
            throw PinkhaHeartSemanticAnchorError.unsupportedRuntime
        }
        pending.applyTrace.record(.readingCurrent)
        let current = try await io.read(pending.plan.request.spaceID, pending.plan.request.objectID)
        pending.applyTrace.record(.checkingCurrent)
        try pending.validateOwner()
        try pending.plan.verifyCurrent(current)
        #if DEBUG && targetEnvironment(simulator)
        pending.observeMountedBoundary("preflight", data: try current.serializedData())
        #endif
        try Task.checkCancellation()
        guard io.canPublish() else { throw PinkhaHeartSemanticAnchorError.unavailablePublication }
        try pending.consume()
        pending.applyTrace.record(.consumed)
        // This is deliberately an owned, unstructured task. Cancelling the
        // caller after dispatch must not cancel normal ObjectShow readback.
        return try await Task { @MainActor in
            try await self.finishQueuedCapture(pending, preflight: current)
        }.value
    }

    private func finishQueuedCapture(_ pending: PinkhaHeartSemanticAnchorPending,
                                     preflight: Anytype_Rpc.Object.Show.Response) async throws
        -> PinkhaHeartSemanticAnchorVerifiedCapture {
        do {
            pending.applyTrace.record(.checkingQueuedOwner)
            try pending.validateOwner()
            pending.applyTrace.record(.invokingNative)
            let raw = try await io.capture(pending.plan.request.encodedRequest())
            #if DEBUG && targetEnvironment(simulator)
            pending.observeMountedBoundary("nativeReply", data: raw)
            #endif
            pending.applyTrace.recordNativeReply(bytes: raw.count)
            pending.applyTrace.record(.checkingCapturedOwner)
            try pending.validateOwner()
            pending.applyTrace.record(.decodingReply)
            let reply = try PinkhaHeartSemanticAnchorAppliedReply.decode(raw, request: pending.plan.request)
            pending.applyTrace.recordDecodedReply(eventBytes: reply.responseEvent.count)
            // Apply may create local derived metadata that did not exist in
            // preflight. The already-required native readback is authority for
            // that projection and must pass before publishing the native event.
            pending.applyTrace.record(.readingReadback)
            let readback = try await io.read(pending.plan.request.spaceID, pending.plan.request.objectID)
            #if DEBUG && targetEnvironment(simulator)
            pending.observeMountedBoundary("readback", data: try readback.serializedData())
            #endif
            pending.applyTrace.record(.checkingReadbackOwner)
            try pending.validateOwner()
            pending.applyTrace.record(.validatingReadback)
            try pending.plan.verifyReadback(readback, receipt: reply.receipt)
            pending.applyTrace.record(.validatingEvent)
            let event = try pending.plan.validatedEvent(reply, preflight: preflight, readback: readback)
            pending.applyTrace.record(.checkingEventOwner)
            try pending.validateOwner()
            // Publish the unchanged returned native event through the original
            // Invocation handler. No synthetic reducer event is manufactured.
            pending.applyTrace.record(.creatingPublicationFence)
            let fence = try PinkhaHeartSemanticAnchorPublicationFence(
                lease: pending.lease, objectID: pending.plan.request.objectID, event: event)
            pending.applyTrace.record(.publishing)
            let published = await PinkhaHeartSemanticAnchorPublication.$current.withValue(fence) {
                await io.publish(event)
            }
            pending.applyTrace.recordPublication(published)
            guard published else { throw PinkhaHeartSemanticAnchorError.uncertain }
            pending.applyTrace.record(.checkingPublishedOwner)
            try pending.validateOwner()
            pending.applyTrace.record(.verified)
            return .init(receipt: reply.receipt, generation: pending.generation)
        } catch let error as PinkhaHeartSemanticAnchorError {
            pending.applyTrace.recordFailure(error)
            if case .nativeRefusal = error { throw error }
            throw PinkhaHeartSemanticAnchorError.uncertain
        } catch {
            pending.applyTrace.recordFailure(error)
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
