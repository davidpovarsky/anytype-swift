import Foundation
import PinkhaAnyEngine

public enum AnyHeartInlineProjectionError: Error, Equatable, Sendable {
    case invalidBinding, invalidRange, limit
}

/// Decoded by the pinned native AnyBlock codec. This binds conversion input to
/// exact source bytes; it is not a capability or proof of a complete Space.
public struct AnyHeartInlineProjection: Equatable, Sendable {
    public struct Mark: Decodable, Equatable, Sendable {
        public enum Kind: String, Decodable, Sendable {
            case bold, italic, strike, code, link, object, mention
            case underline, textColor, backgroundColor
        }
        public let kind: Kind
        public let start: Int
        public let end: Int
        public let parameter: String
        public var range: NSRange { .init(location: start, length: end - start) }
    }

    private struct Payload: Decodable {
        let contract: String
        let codec: String
        let sourceSHA256: String
        let sourceUTF16: Int
        let literal: Bool
        let text: String
        let marks: [Mark]
    }

    public let sourceSHA256: String
    public let source: String
    public let text: String
    public let literal: Bool
    public let marks: [Mark]

    public init(source: String, nativeProjection: Data) throws {
        guard source.utf8.count <= 65_536, nativeProjection.count <= 1_048_576 else {
            throw AnyHeartInlineProjectionError.limit
        }
        let value = try JSONDecoder().decode(Payload.self, from: nativeProjection)
        guard value.contract == "pinkha-heart-inline-projection-v1",
              value.codec == "any-block/9906a7c36b68",
              value.sourceSHA256 == AnyContentDigest.sha256(Data(source.utf8)),
              value.sourceUTF16 == source.utf16.count else {
            throw AnyHeartInlineProjectionError.invalidBinding
        }
        guard value.text.utf8.count <= 65_536, value.marks.count <= 4096 else {
            throw AnyHeartInlineProjectionError.limit
        }
        let units = Array(value.text.utf16)
        func boundary(_ index: Int) -> Bool {
            guard index >= 0, index <= units.count else { return false }
            return index == 0 || index == units.count ||
                !((0xD800...0xDBFF).contains(units[index - 1]) && (0xDC00...0xDFFF).contains(units[index]))
        }
        for mark in value.marks {
            guard mark.start < mark.end, boundary(mark.start), boundary(mark.end),
                  mark.parameter.utf8.count <= 65_536 else { throw AnyHeartInlineProjectionError.invalidRange }
        }
        if value.literal {
            guard value.marks.isEmpty, value.text.utf8.elementsEqual(source.utf8) else {
                throw AnyHeartInlineProjectionError.invalidBinding
            }
        }
        self.source = source; sourceSHA256 = value.sourceSHA256
        text = value.text; literal = value.literal; marks = value.marks
    }
}
