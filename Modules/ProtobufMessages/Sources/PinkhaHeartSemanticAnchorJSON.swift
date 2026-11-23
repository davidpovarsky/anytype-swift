import Foundation

/// Bounded grammar validation before Foundation decoding. This scanner preserves
/// duplicate-key and escaped UTF-16 evidence that a keyed decoder may discard.
enum HeartSemanticJSON {
    static func validate(_ data: Data, maximumBytes: Int) throws {
        guard !data.isEmpty, data.count <= maximumBytes else {
            throw PinkhaHeartSemanticAnchorError.limitExceeded
        }
        guard String(data: data, encoding: .utf8) != nil else {
            throw PinkhaHeartSemanticAnchorError.invalidReply
        }
        var scanner = Scanner(bytes: Array(data))
        try scanner.value(depth: 0)
        scanner.whitespace()
        guard scanner.index == scanner.bytes.count else {
            throw PinkhaHeartSemanticAnchorError.invalidReply
        }
    }

    private struct Scanner {
        let bytes: [UInt8]
        var index = 0

        mutating func whitespace() {
            while index < bytes.count && [9, 10, 13, 32].contains(bytes[index]) { index += 1 }
        }

        mutating func consume(_ byte: UInt8) throws {
            whitespace()
            guard index < bytes.count && bytes[index] == byte else {
                throw PinkhaHeartSemanticAnchorError.invalidReply
            }
            index += 1
        }

        mutating func value(depth: Int) throws {
            whitespace()
            guard depth <= 8, index < bytes.count else {
                throw PinkhaHeartSemanticAnchorError.invalidReply
            }
            switch bytes[index] {
            case 123: try object(depth: depth + 1)
            case 91: try array(depth: depth + 1)
            case 34: _ = try string()
            case 116: try literal(Array("true".utf8))
            case 102: try literal(Array("false".utf8))
            case 110: try literal(Array("null".utf8))
            case 45, 48...57: try number()
            default: throw PinkhaHeartSemanticAnchorError.invalidReply
            }
        }

        mutating func object(depth: Int) throws {
            try consume(123)
            whitespace()
            if index < bytes.count && bytes[index] == 125 { index += 1; return }
            var keys = Set<Data>()
            while true {
                whitespace()
                let key = Data(try string().utf8)
                guard keys.count < 32, keys.insert(key).inserted else {
                    throw PinkhaHeartSemanticAnchorError.invalidReply
                }
                try consume(58)
                try value(depth: depth)
                whitespace()
                guard index < bytes.count else { throw PinkhaHeartSemanticAnchorError.invalidReply }
                if bytes[index] == 125 { index += 1; return }
                try consume(44)
            }
        }

        mutating func array(depth: Int) throws {
            try consume(91)
            whitespace()
            if index < bytes.count && bytes[index] == 93 { index += 1; return }
            var count = 0
            while true {
                guard count < 2_048 else { throw PinkhaHeartSemanticAnchorError.invalidReply }
                count += 1
                try value(depth: depth)
                whitespace()
                guard index < bytes.count else { throw PinkhaHeartSemanticAnchorError.invalidReply }
                if bytes[index] == 93 { index += 1; return }
                try consume(44)
            }
        }

        mutating func string() throws -> String {
            let start = index
            guard index < bytes.count, bytes[index] == 34 else {
                throw PinkhaHeartSemanticAnchorError.invalidReply
            }
            index += 1
            while index < bytes.count {
                let byte = bytes[index]
                index += 1
                if byte == 34 {
                    return try JSONDecoder().decode(String.self, from: Data(bytes[start..<index]))
                }
                guard byte >= 0x20 else { throw PinkhaHeartSemanticAnchorError.invalidReply }
                if byte != 92 { continue }
                guard index < bytes.count else { throw PinkhaHeartSemanticAnchorError.invalidReply }
                let escape = bytes[index]
                index += 1
                switch escape {
                case 34, 92, 47, 98, 102, 110, 114, 116: break
                case 117:
                    let first = try word()
                    if (0xd800...0xdbff).contains(first) {
                        guard index + 2 <= bytes.count, bytes[index] == 92, bytes[index + 1] == 117 else {
                            throw PinkhaHeartSemanticAnchorError.invalidReply
                        }
                        index += 2
                        let second = try word()
                        guard (0xdc00...0xdfff).contains(second) else {
                            throw PinkhaHeartSemanticAnchorError.invalidReply
                        }
                    } else if (0xdc00...0xdfff).contains(first) {
                        throw PinkhaHeartSemanticAnchorError.invalidReply
                    }
                default: throw PinkhaHeartSemanticAnchorError.invalidReply
                }
            }
            throw PinkhaHeartSemanticAnchorError.invalidReply
        }

        mutating func word() throws -> UInt32 {
            guard index + 4 <= bytes.count else { throw PinkhaHeartSemanticAnchorError.invalidReply }
            var value: UInt32 = 0
            for _ in 0..<4 {
                let byte = bytes[index]
                index += 1
                let digit: UInt32
                switch byte {
                case 48...57: digit = UInt32(byte - 48)
                case 65...70: digit = UInt32(byte - 65 + 10)
                case 97...102: digit = UInt32(byte - 97 + 10)
                default: throw PinkhaHeartSemanticAnchorError.invalidReply
                }
                value = value * 16 + digit
            }
            return value
        }

        mutating func literal(_ expected: [UInt8]) throws {
            guard bytes[index...].starts(with: expected) else {
                throw PinkhaHeartSemanticAnchorError.invalidReply
            }
            index += expected.count
        }

        mutating func number() throws {
            if bytes[index] == 45 { index += 1 }
            guard index < bytes.count else { throw PinkhaHeartSemanticAnchorError.invalidReply }
            if bytes[index] == 48 {
                index += 1
            } else {
                guard (49...57).contains(bytes[index]) else {
                    throw PinkhaHeartSemanticAnchorError.invalidReply
                }
                digits()
            }
            // The reply schema has only integer version fields. Fractional
            // and exponent spellings must not be coerced to an integer by Foundation.

        }

        mutating func digits() {
            while index < bytes.count && (48...57).contains(bytes[index]) { index += 1 }
        }
    }
}
