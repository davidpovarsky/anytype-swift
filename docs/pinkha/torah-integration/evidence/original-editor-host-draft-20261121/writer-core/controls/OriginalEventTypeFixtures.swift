import Foundation

// Portable type fixtures only. The actual original EventBunchSubscribtion and
// EventsBunch bodies, and original asyncForEach helper, are compiled unchanged.
public protocol Cancellable { func cancel() }
public final class AnyCancellable: Cancellable, @unchecked Sendable {
    private let body: () -> Void
    public init(_ value: some Cancellable) { body = value.cancel }
    public func cancel() { body() }
    deinit { cancel() }
}

typealias MiddlewareEventMessage = Int
enum LocalEvent: Sendable { case general }
struct Anytype_Event: Message {
    let contextID: String
    let messages: [Int]
}
extension Anytype_ResponseEvent { var contextID: String { "owned" } }
extension Optional { var isNil: Bool { if case .none = self { return true }; return false } }
