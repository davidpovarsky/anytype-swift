import Foundation
import Combine

public final class AtomicPublishedStorage<Value: Sendable>: @unchecked Sendable {
    private let lock = NSLock()
    private var stored: Value
    public init(_ value: Value) { stored = value }
    public var value: Value {
        get {
            lock.lock()
            defer { lock.unlock() }
            return stored
        }
        set {
            lock.lock()
            stored = newValue
            lock.unlock()
        }
    }
    public var publisher: AnyPublisher<Value, Never> { AnyPublisher() }
}

public func anytypeAssertionFailure(
    _ message: String,
    domain: String? = nil,
    info: [String: String] = [:],
    tags: [String: String] = [:],
    file: StaticString = #file,
    function: String = #function,
    line: UInt = #line
) {}
