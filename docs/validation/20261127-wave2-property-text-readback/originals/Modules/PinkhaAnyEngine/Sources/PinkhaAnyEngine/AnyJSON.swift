import Foundation

/// Lossless for the typed integers and opaque base64 strings in the claim contract.
public enum AnyJSON: Codable, Equatable, Sendable {
    case null
    case bool(Bool)
    case integer(Int64)
    case number(Double)
    case string(String)
    case array([AnyJSON])
    case object([String: AnyJSON])

    public init(from decoder: any Decoder) throws {
        let c = try decoder.singleValueContainer()
        if c.decodeNil() { self = .null }
        else if let v = try? c.decode(Bool.self) { self = .bool(v) }
        else if let v = try? c.decode(Int64.self) { self = .integer(v) }
        else if let v = try? c.decode(Double.self), v.isFinite { self = .number(v) }
        else if let v = try? c.decode(String.self) { self = .string(v) }
        else if let v = try? c.decode([AnyJSON].self) { self = .array(v) }
        else { self = .object(try c.decode([String: AnyJSON].self)) }
    }

    public func encode(to encoder: any Encoder) throws {
        var c = encoder.singleValueContainer()
        switch self {
        case .null: try c.encodeNil()
        case .bool(let v): try c.encode(v)
        case .integer(let v): try c.encode(v)
        case .number(let v): try c.encode(v)
        case .string(let v): try c.encode(v)
        case .array(let v): try c.encode(v)
        case .object(let v): try c.encode(v)
        }
    }

    public subscript(_ key: String) -> AnyJSON? {
        guard case .object(let v) = self else { return nil }
        return v[key]
    }
    public var string: String? { if case .string(let v) = self { v } else { nil } }
    public var array: [AnyJSON]? { if case .array(let v) = self { v } else { nil } }
    public var object: [String: AnyJSON]? { if case .object(let v) = self { v } else { nil } }
    public var bool: Bool? { if case .bool(let v) = self { v } else { nil } }
    public var integer: Int64? { if case .integer(let v) = self { v } else { nil } }

    public func requireString(_ key: String) throws -> String {
        guard let v = self[key]?.string else { throw AnyEngineError.malformedResponse(key) }
        return v
    }
}

public enum AnyEngineError: Error, Equatable, Sendable {
    case invalidEndpoint
    case invalidIdentity(String)
    case invalidOperation(String)
    case accountChanged
    case malformedResponse(String)
    case http(status: Int, code: String)
    case writeRejected([String])
    case incompatibleSchema(String)
    case collision(String)
    case readLimit
    case invalidClaim(String)
    case writeUncertain
    case unverifiedWrite
    case unsupportedEngine(String)
}
