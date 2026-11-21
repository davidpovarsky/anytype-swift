import Foundation

// Type-only portable test fixture. No protobuf transport or native engine.
public protocol Message: Sendable {
    func jsonUTF8Data() throws -> Data
}
public extension Message {
    func jsonUTF8Data() throws -> Data { Data() }
}
