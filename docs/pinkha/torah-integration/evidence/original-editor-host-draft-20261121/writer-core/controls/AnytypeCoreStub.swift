import Foundation
import Combine

// The actual AccountManager setter is compiled unchanged; only its unavailable
// package storage/publisher types are supplied by this explicit portable probe.
public final class AtomicPublishedStorage<Value: Sendable>: @unchecked Sendable {
    private let lock = NSLock()
    private var stored: Value
    public init(_ value: Value) { stored = value }
    public var value: Value {
        get { lock.lock(); defer { lock.unlock() }; return stored }
        set { lock.lock(); stored = newValue; lock.unlock() }
    }
    public var publisher: AnyPublisher<Value, Never> { .init() }
}
