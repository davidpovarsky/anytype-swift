import Foundation
import Lib
import SwiftProtobuf
import os

/// Adapts interface of private framework.
public protocol ServiceEventsHandlerProtocol: AnyObject {
    func handle(_ event: Anytype_Event) async
}

/// Provides the following functionality
/// - Receive events from `Lib` and transfer them to a wrapped value.
///
/// In a nutshell, it do the following.
///
/// - It consumes ( with a weak ownership ) a value which adopts public interface.
/// - Subscribes as event handler to library events stream.
/// - Transfer events from library to a value.
///
public class ServiceMessageHandlerAdapter: @unchecked Sendable {
    
    private let lock = OSAllocatedUnfairLock()

    private var handlers: [WeakHandler] = []
    private var listener: ServiceMessageHandler?
    
    public static let shared = ServiceMessageHandlerAdapter()
    
    private init() {
        listen()
    }
    
    public func addHandler(handler: ServiceEventsHandlerProtocol) {
        lock.lock()
        defer { lock.unlock() }
        handlers.removeAll { $0.value == nil }
        handlers.append(WeakHandler(handler))
    }

    /// Waits only for callbacks already accepted by the original FIFO.
    /// This is not native account/import shutdown or future-event authority.
    public func waitForPendingEventDelivery() async throws {
        let listener = currentListener()
        guard let listener else { throw OriginalEventDeliveryFence.Failure.ended }
        try await listener.waitForPendingEventDelivery()
        try Task.checkCancellation()
    }

    private func currentListener() -> ServiceMessageHandler? {
        lock.lock()
        defer { lock.unlock() }
        return listener
    }

    private func currentHandlers() -> [WeakHandler] {
        lock.lock()
        defer { lock.unlock() }
        return handlers
    }

    private func listen() {
        lock.lock()
        defer { lock.unlock() }
        listener = ServiceMessageHandler { [weak self] event in
            guard let self else { return }
            // Snapshot under the lock and release it before awaiting: reading
            // `handlers` unsynchronized races with `addHandler`, and the lock
            // must not be held across the suspension point.
            for handler in currentHandlers() {
                await handler.value?.handle(event)
            }
        }
        Lib.ServiceSetEventHandlerMobile(listener)
    }
}

/// Private `ServiceMessageHandlerProtocol` adoption.
fileprivate final class ServiceMessageHandler: NSObject, Sendable, ServiceMessageHandlerProtocol {

    // A Task per incoming chunk gives no FIFO guarantee — reordered events
    // (e.g. subscriptionAdd after the amend that follows it) corrupt storages.
    // Chunks are buffered in arrival order and drained by a single consumer.
    private let continuation: AsyncStream<Data>.Continuation
    private let consumer: Task<Void, Never>
    private let deliveryFence: OriginalEventDeliveryFence

    init(handler: @escaping @Sendable (_: Anytype_Event) async -> Void) {
        let (stream, continuation) = AsyncStream.makeStream(of: Data.self)
        self.continuation = continuation
        let deliveryFence = OriginalEventDeliveryFence()
        self.deliveryFence = deliveryFence
        self.consumer = Task {
            defer { deliveryFence.end() }
            for await data in stream {
                defer { deliveryFence.didDeliverOne() }
                guard let event = try? Anytype_Event(serializedBytes: data) else { continue }
                Self.log(event: event)
                await handler(event)
            }
        }
    }

    deinit {
        continuation.finish()
        consumer.cancel()
    }

    public func handle(_ data: Data?) {
        guard let data else { return }
        deliveryFence.enqueue(data, into: continuation)
    }

    func waitForPendingEventDelivery() async throws {
        try await deliveryFence.waitForCurrentFrontier()
    }

    private static func log(event: Anytype_Event) {
        guard let handler = InvocationSettings.handler, handler.isLogEnabled else { return }

        let responseJsonData = try? event.jsonUTF8Data()
        let messageNames = responseJsonData?.parseMessages() ?? ""

        let message = InvocationMessage(
            name: "Events:\(messageNames)",
            requestJsonData: nil,
            responseJsonData: responseJsonData,
            responseError: nil
        )
        handler.logHandler(message: message)
    }
}

/// Completion frontier for the existing one-consumer stream. No event bytes,
/// event identities, account tokens or second buffer are stored here.
private final class OriginalEventDeliveryFence: @unchecked Sendable {
    enum Failure: Error { case ended, counterExhausted, invalidCompletion }
    private let lock = NSLock()
    private var accepted: UInt64 = 0
    private var delivered: UInt64 = 0
    private var failure: Failure?
    private var waiters: [(target: UInt64, continuation: CheckedContinuation<Void, Error>)] = []

    func enqueue(_ data: Data, into continuation: AsyncStream<Data>.Continuation) {
        lock.lock()
        var failed: [CheckedContinuation<Void, Error>] = []
        if failure == nil {
            if accepted == UInt64.max {
                failed = failLocked(.counterExhausted)
            } else {
                accepted += 1
            }
        }
        // Counter order and the original stream's enqueue order share this
        // lock. The original consumer/handler cannot acknowledge beforehand.
        switch continuation.yield(data) {
        case .enqueued:
            break
        case .dropped, .terminated:
            failed += failLocked(.ended)
        @unknown default:
            failed += failLocked(.ended)
        }
        let reason = failure
        lock.unlock()
        if let reason { for waiter in failed { waiter.resume(throwing: reason) } }
    }

    func didDeliverOne() {
        lock.lock()
        guard failure == nil else { lock.unlock(); return }
        guard delivered < accepted else {
            let failed = failLocked(.invalidCompletion)
            lock.unlock()
            for waiter in failed { waiter.resume(throwing: Failure.invalidCompletion) }
            return
        }
        delivered += 1
        let completed = waiters.filter { $0.target <= delivered }.map(\.continuation)
        waiters.removeAll { $0.target <= delivered }
        lock.unlock()
        for waiter in completed { waiter.resume() }
    }

    func waitForCurrentFrontier() async throws {
        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
            lock.lock()
            if let failure {
                lock.unlock()
                continuation.resume(throwing: failure)
            } else if delivered == accepted {
                lock.unlock()
                continuation.resume()
            } else {
                waiters.append((accepted, continuation))
                lock.unlock()
            }
        }
    }

    func end() {
        lock.lock()
        let failed = failLocked(.ended)
        lock.unlock()
        for waiter in failed { waiter.resume(throwing: Failure.ended) }
    }

    private func failLocked(_ reason: Failure) -> [CheckedContinuation<Void, Error>] {
        if failure == nil { failure = reason }
        let failed = waiters.map(\.continuation)
        waiters.removeAll()
        return failed
    }
}
