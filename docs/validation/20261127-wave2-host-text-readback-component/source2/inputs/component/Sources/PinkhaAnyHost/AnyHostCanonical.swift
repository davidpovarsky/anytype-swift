import Foundation
import PinkhaAnyEngine

/// Stable typed bytes for local intent/revision identity, never a replacement
/// for the native SDK's signed operation canonicalization.
enum AnyHostCanonical {
    static func bytes(_ value: AnyJSON, maximumBytes: Int = 1_048_576) throws -> Data {
        var output = Data()
        func append(_ token: String) throws {
            let data = Data(token.utf8)
            guard data.count <= maximumBytes, output.count <= maximumBytes - data.count - 24 else {
                throw AnyEngineError.readLimit
            }
            output.append(contentsOf: String(data.count).utf8)
            output.append(0x3a); output.append(data)
        }
        func visit(_ value: AnyJSON, depth: Int) throws {
            guard depth <= 32 else { throw AnyEngineError.readLimit }
            switch value {
            case .null: try append("null")
            case .bool(let value): try append(value ? "true" : "false")
            case .integer(let value): try append("integer"); try append(String(value))
            case .number(let value):
                guard value.isFinite else { throw AnyEngineError.invalidOperation("nonfinite value") }
                try append("double"); try append(String(value.bitPattern, radix: 16))
            case .string(let value): try append("string"); try append(value)
            case .array(let values):
                try append("array"); try append(String(values.count))
                for value in values { try visit(value, depth: depth + 1) }
            case .object(let values):
                try append("object"); try append(String(values.count))
                for key in values.keys.sorted(by: { $0.utf8.lexicographicallyPrecedes($1.utf8) }) {
                    try append(key); try visit(values[key]!, depth: depth + 1)
                }
            }
        }
        try visit(value, depth: 0)
        return output
    }

    static func nativeVersions(_ value: AnyJSON, depth: Int = 0) throws {
        guard depth <= 32 else { throw AnyEngineError.readLimit }
        switch value {
        case .string(let version):
            guard !version.isEmpty, version.utf8.count <= 1024 else {
                throw AnyHostError.invalidDocument("native version stamp")
            }
        case .object(let entries):
            guard entries.count <= 1024 else { throw AnyEngineError.readLimit }
            for (key, value) in entries {
                guard !key.isEmpty, key.utf8.count <= 1024 else {
                    throw AnyHostError.invalidDocument("native version path")
                }
                try nativeVersions(value, depth: depth + 1)
            }
        default: throw AnyHostError.invalidDocument("native version tree")
        }
    }
}
