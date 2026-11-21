import Foundation
import SwiftProtobuf

// These type fixtures let the ACTUAL Invocation.swift run on Windows without
// linking Lib. The synchronous native body is an explicit held/counting probe.
public protocol PortableRPCError: Swift.Error, Sendable {
    associatedtype ErrorCode: RawRepresentable where ErrorCode.RawValue == Int
    var code: ErrorCode { get }
    var isNull: Bool { get }
}
public protocol ResultWithError: Sendable {
    associatedtype Error: PortableRPCError
    var error: Error { get }
    var hasEvent: Bool { get }
    var event: Anytype_ResponseEvent { get }
}
public struct Anytype_ResponseEvent: Message {
    public let messages: [Int]
    public init(messages: [Int] = []) { self.messages = messages }
}
public struct InvocationMessage: Sendable {
    public let name: String
    public let requestJsonData: Data?
    public let responseJsonData: Data?
    public let responseError: (any Swift.Error)?
}
public protocol InvocationMesagesHandlerProtocol: Sendable {
    var isLogEnabled: Bool { get }
    func logHandler(message: InvocationMessage)
    func eventHandler(event: Anytype_ResponseEvent) async
    func assertationHandler(message: String, domain: String, info: [String: String], file: StaticString, function: String, line: UInt)
}
actor RequestIdStorage {
    static let shared = RequestIdStorage()
    private var value = 0
    func createId() -> Int { value += 1; return value }
}
extension Data { func parseMessages() -> String { "" } }

final class PortableControlLock: @unchecked Sendable {
    private let lock = NSLock()
    func withLock<Value>(_ operation: () -> Value) -> Value {
        lock.lock(); defer { lock.unlock() }; return operation()
    }
}
