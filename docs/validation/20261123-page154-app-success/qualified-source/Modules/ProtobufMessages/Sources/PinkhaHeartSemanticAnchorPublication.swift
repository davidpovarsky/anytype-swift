#if PINKHA_NATIVE_T2_AUTHORIZED_READ_V1
import Foundation
import SwiftProtobuf

/// An ordinary Invocation event may cross actors and GCD before it reaches a
/// document. This task context adds an owner witness without replacing that route.
public enum PinkhaHeartSemanticAnchorPublication {
    @TaskLocal public static var current: PinkhaHeartSemanticAnchorPublicationFence?
}

/// Constructed only from the actual current lease by the typed capture client.
/// Consumers must explicitly carry this value across non-task scheduling hops.
@MainActor
public final class PinkhaHeartSemanticAnchorPublicationFence: PinkhaNativeReadLeaseObserver {
    public nonisolated let accountID: String
    public nonisolated let spaceID: String
    public nonisolated let objectID: String
    public nonisolated let generation: UUID
    private let lease: PinkhaNativeReadLease
    private nonisolated let eventBytes: Data
    private nonisolated let state = HeartSemanticPublicationState()

    init(lease: PinkhaNativeReadLease, objectID: String, event: Anytype_ResponseEvent) throws {
        try lease.validate()
        guard !objectID.isEmpty, objectID.utf8.count <= 1_024, !objectID.utf8.contains(0) else {
            throw PinkhaHeartSemanticAnchorError.invalidRequest
        }
        self.lease = lease
        eventBytes = try event.serializedData()
        accountID = lease.accountID
        spaceID = lease.spaceID
        generation = lease.generation
        self.objectID = objectID
        try lease.observeRetirement(self)
    }

    public func nativeReadLeaseDidRetire() { state.retire() }

    public nonisolated func matches(spaceID: String, objectID: String) -> Bool {
        heartBytesEqual(self.spaceID, spaceID) && heartBytesEqual(self.objectID, objectID)
    }

    /// Task context must never attach this owner to a different nested RPC event.
    public nonisolated func matches(event: Anytype_ResponseEvent) -> Bool {
        guard heartBytesEqual(event.contextID, objectID),
              event.messages.allSatisfy({ heartBytesEqual($0.spaceID, spaceID) }),
              let bytes = try? event.serializedData() else { return false }
        return bytes == eventBytes
    }

    /// Only bounded synchronous document conversion/storage belongs in this
    /// closure. Never await, call a subscriber, or synchronously wait on main.
    /// Retirement and this state mutation cannot interleave.
    public nonisolated func withCurrentDocumentState<Value>(
        spaceID: String, objectID: String, _ body: () throws -> Value
    ) rethrows -> Value? {
        guard matches(spaceID: spaceID, objectID: objectID) else { return nil }
        return try state.withCurrent(body)
    }

    /// Recheck after a queued hop, at the synchronous mounted/main consumer.
    /// No lock is held while the consumer or Combine subscribers are called.
    @discardableResult
    public func withCurrentMainDelivery(spaceID: String, objectID: String, _ body: () -> Void) -> Bool {
        guard matches(spaceID: spaceID, objectID: objectID), state.isCurrent,
              (try? lease.validate()) != nil else { return false }
        body()
        return true
    }
}

private final class HeartSemanticPublicationState: @unchecked Sendable {
    private let lock = NSLock()
    private var active = true

    var isCurrent: Bool {
        lock.lock()
        defer { lock.unlock() }
        return active
    }

    func retire() {
        lock.lock()
        active = false
        lock.unlock()
    }

    func withCurrent<Value>(_ body: () throws -> Value) rethrows -> Value? {
        lock.lock()
        defer { lock.unlock() }
        guard active else { return nil }
        return try body()
    }
}
#endif
