import Foundation

/// Swift String dictionary keys use Unicode canonical equivalence; the native
/// Go protobuf maps use exact UTF-8 keys. Check every reachable native map before
/// SwiftProtobuf decoding so two distinct original keys cannot collapse. The
/// field paths below come from the same pinned original .proto files as the
/// wrapper views. Unknown message fields are preserved by SwiftProtobuf instead.
internal enum OriginalAnnotationNativeMapKeyGuard {
    enum Failure: Error, Sendable, Equatable {
        case malformedWire
        case ambiguousMapKey
        case duplicateMessageFragment
        case unsupportedMapEntry
        case depthLimit
    }

    private enum Kind {
        case wrapper, snapshot, fileKeys, base, block, link, dataview, view
        case sort, filter, relation, structure, value, list, stringMap, valueMap
    }

    static func validate(_ bytes: Data) throws {
        try visit(bytes, kind: .wrapper, depth: 0)
    }

    private static func child(_ kind: Kind, field: Int) -> (Kind, repeated: Bool)? {
        switch (kind, field) {
        case (.wrapper, 2): return (.snapshot, false)
        case (.snapshot, 1): return (.stringMap, true)
        case (.snapshot, 2): return (.base, false)
        case (.snapshot, 3): return (.fileKeys, true)
        case (.fileKeys, 2): return (.stringMap, true)
        case (.base, 1): return (.block, true)
        case (.base, 2), (.base, 3), (.base, 6): return (.structure, false)
        case (.base, 4): return (.relation, true)
        case (.block, 2): return (.structure, false)
        case (.block, 20): return (.link, false)
        case (.block, 21): return (.dataview, false)
        case (.link, 3): return (.structure, false)
        case (.dataview, 2): return (.view, true)
        case (.dataview, 4): return (.relation, true)
        case (.view, 4): return (.sort, true)
        case (.view, 5): return (.filter, true)
        case (.sort, 3): return (.value, true)
        case (.filter, 4), (.relation, 4): return (.value, false)
        case (.filter, 10): return (.filter, true)
        case (.structure, 1): return (.valueMap, true)
        case (.value, 5): return (.structure, false)
        case (.value, 6): return (.list, false)
        case (.list, 1): return (.value, true)
        case (.valueMap, 2): return (.value, false)
        default: return nil
        }
    }

    @discardableResult
    private static func visit(_ data: Data, kind: Kind, depth: Int) throws -> String? {
        guard depth < 100 else { throw Failure.depthLimit }
        let bytes = Array(data)
        var cursor = 0
        var singular = Set<Int>()
        var mapKeys: [Int: Set<String>] = [:]
        var key: String?
        var hasMapValue = false
        while cursor < bytes.count {
            let tag = try varint(bytes, cursor: &cursor)
            let field = Int(tag >> 3), wire = tag & 7
            guard field > 0, field <= 536_870_911 else { throw Failure.malformedWire }
            if kind == .stringMap || kind == .valueMap {
                // The pinned SwiftProtobuf map decoder does not retain unknown
                // entry fields. Refuse them before decoding instead of making
                // two distinct original protobuf bodies compare equal.
                guard (field == 1 || field == 2), wire == 2 else {
                    throw Failure.unsupportedMapEntry
                }
                if field == 2 {
                    guard !hasMapValue else { throw Failure.unsupportedMapEntry }
                    hasMapValue = true
                }
            }
            var payload: Data?
            switch wire {
            case 0: _ = try varint(bytes, cursor: &cursor)
            case 1:
                guard cursor <= bytes.count - 8 else { throw Failure.malformedWire }
                cursor += 8
            case 2:
                let length = try varint(bytes, cursor: &cursor)
                guard length <= UInt64(bytes.count - cursor) else { throw Failure.malformedWire }
                let end = cursor + Int(length)
                payload = Data(bytes[cursor..<end])
                cursor = end
            case 5:
                guard cursor <= bytes.count - 4 else { throw Failure.malformedWire }
                cursor += 4
            default: throw Failure.malformedWire
            }
            if (kind == .stringMap || kind == .valueMap), field == 1 {
                guard key == nil, let payload,
                      let text = String(data: payload, encoding: .utf8),
                      Data(text.utf8) == payload else { throw Failure.ambiguousMapKey }
                key = text
            }
            if let (next, repeated) = child(kind, field: field) {
                guard let payload else { throw Failure.malformedWire }
                if !repeated, !singular.insert(field).inserted {
                    throw Failure.duplicateMessageFragment
                }
                let nestedKey = try visit(payload, kind: next, depth: depth + 1)
                if next == .stringMap || next == .valueMap {
                    // A protobuf map's omitted key is the empty string.
                    guard mapKeys[field, default: []].insert(nestedKey ?? "").inserted else {
                        throw Failure.ambiguousMapKey
                    }
                }
            }
        }
        return key
    }

    private static func varint(_ bytes: [UInt8], cursor: inout Int) throws -> UInt64 {
        var result: UInt64 = 0
        for index in 0..<10 {
            guard cursor < bytes.count else { throw Failure.malformedWire }
            let byte = bytes[cursor]
            cursor += 1
            guard index < 9 || byte <= 1 else { throw Failure.malformedWire }
            result |= UInt64(byte & 0x7f) << (index * 7)
            if byte & 0x80 == 0 { return result }
        }
        throw Failure.malformedWire
    }
}
