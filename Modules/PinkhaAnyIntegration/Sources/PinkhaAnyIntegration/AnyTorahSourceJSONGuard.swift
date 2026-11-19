import Foundation
import PinkhaKit

public enum AnyTorahMigrationError: Error, Sendable, Equatable {
    case numericPrecisionWouldChange(path: String)
    case duplicateJSONKey(path: String)
    case unmappedReferencedObject(String)
    case malformedInternalNoteLink(itemID: String)
}

/// The existing domain deliberately models JSON numbers as Double. Refuse an
/// import when that representation would change an original number. This is
/// exact decimal comparison of JSON tokens, not a second floating-point parse.
enum AnyTorahSourceJSONGuard {
    static func validateRoundTrip(original: Data, encoded: Data) throws {
        var source = Scanner(bytes: Array(original))
        var result = Scanner(bytes: Array(encoded))
        let originalNumbers = try source.numbers()
        let encodedNumbers = try result.numbers()
        for (path, number) in originalNumbers {
            guard encodedNumbers[path] == number else {
                throw AnyTorahMigrationError.numericPrecisionWouldChange(path: path)
            }
        }
    }

    private struct Scanner {
        let bytes: [UInt8]
        var index = 0
        var values: [String: String] = [:]

        mutating func numbers() throws -> [String: String] {
            try value(path: "", depth: 0)
            whitespace()
            guard index == bytes.count else { throw malformed }
            return values
        }

        private var malformed: TorahAssociationPayloadCodecError { .malformedJSON }

        private mutating func value(path: String, depth: Int) throws {
            guard depth <= 512 else { throw malformed }
            whitespace()
            guard index < bytes.count else { throw malformed }
            switch bytes[index] {
            case 123:
                index += 1
                whitespace()
                if consume(125) { return }
                var keys = Set<String>()
                repeat {
                    whitespace()
                    let key = try string()
                    let pointer = path + "/" + key.replacingOccurrences(of: "~", with: "~0")
                        .replacingOccurrences(of: "/", with: "~1")
                    guard keys.insert(key).inserted else {
                        throw AnyTorahMigrationError.duplicateJSONKey(path: pointer)
                    }
                    whitespace()
                    guard consume(58) else { throw malformed }
                    try value(path: pointer, depth: depth + 1)
                    whitespace()
                    if consume(125) { return }
                    guard consume(44) else { throw malformed }
                } while true
            case 91:
                index += 1
                whitespace()
                if consume(93) { return }
                var offset = 0
                repeat {
                    try value(path: path + "/" + String(offset), depth: depth + 1)
                    offset += 1
                    whitespace()
                    if consume(93) { return }
                    guard consume(44) else { throw malformed }
                } while true
            case 34:
                _ = try string()
            case 116:
                try keyword([116, 114, 117, 101])
            case 102:
                try keyword([102, 97, 108, 115, 101])
            case 110:
                try keyword([110, 117, 108, 108])
            case 45, 48...57:
                values[path] = try number(path: path)
            default:
                throw malformed
            }
        }

        private mutating func string() throws -> String {
            let start = index
            guard consume(34) else { throw malformed }
            while index < bytes.count {
                if bytes[index] == 34 {
                    index += 1
                    return try JSONDecoder().decode(String.self, from: Data(bytes[start..<index]))
                }
                if bytes[index] == 92 {
                    index += 1
                    guard index < bytes.count else { throw malformed }
                }
                index += 1
            }
            throw malformed
        }

        private mutating func number(path: String) throws -> String {
            let negative = consume(45)
            var digits: [UInt8] = []
            if consume(48) {
                digits.append(48)
            } else {
                guard index < bytes.count, (49...57).contains(bytes[index]) else { throw malformed }
                while index < bytes.count, (48...57).contains(bytes[index]) {
                    digits.append(bytes[index]); index += 1
                }
            }
            var fractionCount = 0
            if consume(46) {
                let start = index
                while index < bytes.count, (48...57).contains(bytes[index]) {
                    digits.append(bytes[index]); index += 1
                }
                fractionCount = index - start
                guard fractionCount > 0 else { throw malformed }
            }
            var exponent = 0
            if consume(101) || consume(69) {
                let exponentNegative = consume(45)
                if !exponentNegative { _ = consume(43) }
                let start = index
                while index < bytes.count, (48...57).contains(bytes[index]) { index += 1 }
                guard index > start else { throw malformed }
                let significant = bytes[start..<index].drop(while: { $0 == 48 })
                if !digits.allSatisfy({ $0 == 48 }) {
                    guard significant.count <= 8,
                          let magnitude = Int(String(decoding: significant.isEmpty ? [48] : Array(significant), as: UTF8.self)) else {
                        throw AnyTorahMigrationError.numericPrecisionWouldChange(path: path)
                    }
                    exponent = exponentNegative ? -magnitude : magnitude
                }
            }
            let nonzero = digits.drop(while: { $0 == 48 })
            guard !nonzero.isEmpty else { return "0" }
            var coefficient = Array(nonzero)
            var scale = exponent - fractionCount
            while coefficient.last == 48 { coefficient.removeLast(); scale += 1 }
            return (negative ? "-" : "") + String(decoding: coefficient, as: UTF8.self) + "e" + String(scale)
        }

        private mutating func keyword(_ value: [UInt8]) throws {
            guard index + value.count <= bytes.count,
                  Array(bytes[index..<(index + value.count)]) == value else { throw malformed }
            index += value.count
        }

        private mutating func whitespace() {
            while index < bytes.count, [9, 10, 13, 32].contains(bytes[index]) { index += 1 }
        }

        private mutating func consume(_ byte: UInt8) -> Bool {
            guard index < bytes.count, bytes[index] == byte else { return false }
            index += 1
            return true
        }
    }
}
