import Foundation

public enum PinkhaSemanticTextAnchorError: Error, Sendable, Equatable {
    case invalidIdentity
    case invalidMarker
    case unsupportedVersion
    case wrongDocument
    case invalidRange
    case overlappingMarkers
    case selectionAlreadyLinked
    case changedText
    case limitExceeded
}

/// The durable identity lives in native link markup, never in a saved text offset.
/// Space and document ownership are encoded in the marker so pasted foreign
/// markup cannot acquire the current document's associations.
public struct PinkhaSemanticTextAnchor: Codable, Sendable, Hashable {
    public static let currentVersion = 1
    public static let markerScheme = "pinkha-anchor"
    public let version: Int
    public let spaceID: String
    public let objectID: String
    public let id: UUID

    public init(spaceID: String, objectID: String, id: UUID = UUID()) throws {
        guard Self.validIdentity(spaceID), Self.validIdentity(objectID) else {
            throw PinkhaSemanticTextAnchorError.invalidIdentity
        }
        version = Self.currentVersion
        self.spaceID = spaceID
        self.objectID = objectID
        self.id = id
    }

    private enum CodingKeys: String, CodingKey { case version, spaceID, objectID, id }

    public init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        guard try values.decode(Int.self, forKey: .version) == Self.currentVersion else {
            throw PinkhaSemanticTextAnchorError.unsupportedVersion
        }
        try self.init(spaceID: values.decode(String.self, forKey: .spaceID),
                      objectID: values.decode(String.self, forKey: .objectID),
                      id: values.decode(UUID.self, forKey: .id))
    }

    public var markerString: String {
        "\(Self.markerScheme)://v1/\(Self.component(spaceID))/\(Self.component(objectID))/\(id.uuidString.lowercased())"
    }

    public func markerURL() throws -> URL {
        guard let result = URL(string: markerString) else { throw PinkhaSemanticTextAnchorError.invalidMarker }
        return result
    }

    public init(markerURL: URL) throws {
        guard Self.isReservedMarkerURL(markerURL), let components = URLComponents(url: markerURL, resolvingAgainstBaseURL: false),
              components.user == nil, components.password == nil, components.port == nil,
              components.query == nil, components.fragment == nil else {
            throw PinkhaSemanticTextAnchorError.invalidMarker
        }
        guard components.host == "v1" else { throw PinkhaSemanticTextAnchorError.unsupportedVersion }
        let path = components.path.split(separator: "/", omittingEmptySubsequences: false)
        guard path.count == 4, path[0].isEmpty,
              let spaceID = Self.identity(String(path[1])), let objectID = Self.identity(String(path[2])),
              let id = UUID(uuidString: String(path[3])) else {
            throw PinkhaSemanticTextAnchorError.invalidMarker
        }
        try self.init(spaceID: spaceID, objectID: objectID, id: id)
        guard markerString.utf8.elementsEqual(markerURL.absoluteString.utf8) else {
            throw PinkhaSemanticTextAnchorError.invalidMarker
        }
    }

    /// Invalid/future reserved markers must be handled locally, never opened as
    /// an ordinary external URL or silently interpreted as a block association.
    public static func isReservedMarkerURL(_ url: URL) -> Bool {
        url.scheme?.lowercased() == markerScheme
    }

    public func belongsTo(spaceID: String, objectID: String) -> Bool {
        self.spaceID.utf8.elementsEqual(spaceID.utf8) && self.objectID.utf8.elementsEqual(objectID.utf8)
    }

    public static func == (left: Self, right: Self) -> Bool {
        left.version == right.version && left.id == right.id &&
        left.belongsTo(spaceID: right.spaceID, objectID: right.objectID)
    }

    public func hash(into hasher: inout Hasher) {
        hasher.combine(version)
        hasher.combine(id)
        hasher.combine(Data(spaceID.utf8))
        hasher.combine(Data(objectID.utf8))
    }

    private static func validIdentity(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 1_024 && !value.contains("\0")
    }

    private static func component(_ value: String) -> String {
        Data(value.utf8).base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")
    }

    private static func identity(_ component: String) -> String? {
        guard !component.isEmpty, component.utf8.count <= 1_366,
              component.utf8.allSatisfy({ (65...90).contains($0) || (97...122).contains($0) ||
                  (48...57).contains($0) || $0 == 45 || $0 == 95 }) else { return nil }
        var encoded = component.replacingOccurrences(of: "-", with: "+").replacingOccurrences(of: "_", with: "/")
        encoded += String(repeating: "=", count: (4 - encoded.utf8.count % 4) % 4)
        guard let data = Data(base64Encoded: encoded), let value = String(data: data, encoding: .utf8),
              validIdentity(value), Self.component(value) == component else { return nil }
        return value
    }
}

/// A current native-mark projection. Ranges are transient native/editor data;
/// this type intentionally has no Codable conformance or durable offset store.
public struct PinkhaSemanticText: Sendable, Equatable {
    public struct Mark: Sendable, Equatable {
        public let anchor: PinkhaSemanticTextAnchor
        public let range: NSRange

        public init(anchor: PinkhaSemanticTextAnchor, range: NSRange) {
            self.anchor = anchor
            self.range = range
        }
    }

    public static let maximumUTF8Bytes = 65_536
    public static let maximumMarks = 1_024
    public let text: String
    public let marks: [Mark]

    public init(text: String, marks: [Mark] = []) throws {
        guard text.utf8.count <= Self.maximumUTF8Bytes, marks.count <= Self.maximumMarks else {
            throw PinkhaSemanticTextAnchorError.limitExceeded
        }
        self.text = text
        var normalized: [Mark] = []
        for mark in marks.sorted(by: { $0.range.location < $1.range.location }) {
            try Self.validate(mark.range, in: text, nonempty: true)
            if let previous = normalized.last, NSMaxRange(previous.range) >= mark.range.location {
                if previous.anchor == mark.anchor {
                    normalized[normalized.count - 1] = .init(anchor: mark.anchor, range: NSUnionRange(previous.range, mark.range))
                    continue
                }
                guard NSMaxRange(previous.range) == mark.range.location else {
                    throw PinkhaSemanticTextAnchorError.overlappingMarkers
                }
            }
            normalized.append(mark)
        }
        self.marks = normalized
    }

    public static func == (left: Self, right: Self) -> Bool {
        left.text.utf8.elementsEqual(right.text.utf8) && left.marks == right.marks
    }

    public func capturing(_ anchor: PinkhaSemanticTextAnchor, range: NSRange,
                          occupiedLinkRanges: [NSRange] = []) throws -> PinkhaSemanticTextEdit {
        try Self.validate(range, in: text, nonempty: true, graphemeBoundaries: true)
        for occupied in occupiedLinkRanges {
            try Self.validate(occupied, in: text, nonempty: true)
        }
        guard !marks.contains(where: { NSIntersectionRange($0.range, range).length > 0 }) &&
              !occupiedLinkRanges.contains(where: { NSIntersectionRange($0, range).length > 0 }) else {
            throw PinkhaSemanticTextAnchorError.selectionAlreadyLinked
        }
        return .init(before: self, after: try .init(text: text, marks: marks + [.init(anchor: anchor, range: range)]))
    }

    /// The same ordinary text-input rule serves both adapters: nonempty
    /// replacements inherit the first selected character's mark; an insertion
    /// inherits only strictly inside a mark, never immediately before/after it.
    /// Clipboard marker identities are deliberately absent from this API.
    public func replacing(_ range: NSRange, with text: String) throws -> PinkhaSemanticTextEdit {
        try Self.validate(range, in: self.text)
        let replacementLength = text.utf16.count
        let end = NSMaxRange(range), delta = replacementLength - range.length
        let inherited = marks.first {
            range.length == 0
                ? $0.range.location < range.location && range.location < NSMaxRange($0.range)
                : $0.range.location <= range.location && range.location < NSMaxRange($0.range)
        }?.anchor
        var result: [Mark] = []
        for mark in marks {
            let beforeEnd = min(NSMaxRange(mark.range), range.location)
            if mark.range.location < beforeEnd {
                result.append(.init(anchor: mark.anchor,
                    range: .init(location: mark.range.location, length: beforeEnd - mark.range.location)))
            }
            let afterStart = max(mark.range.location, end)
            if afterStart < NSMaxRange(mark.range) {
                result.append(.init(anchor: mark.anchor,
                    range: .init(location: afterStart + delta, length: NSMaxRange(mark.range) - afterStart)))
            }
        }
        if let inherited, replacementLength > 0 {
            result.append(.init(anchor: inherited, range: .init(location: range.location, length: replacementLength)))
        }
        let updated = (self.text as NSString).replacingCharacters(in: range, with: text)
        return .init(before: self, after: try .init(text: updated, marks: result))
    }

    public func removing(_ anchor: PinkhaSemanticTextAnchor) throws -> PinkhaSemanticTextEdit {
        .init(before: self, after: try .init(text: text, marks: marks.filter { $0.anchor != anchor }))
    }

    public func split(at offset: Int) throws -> (before: Self, after: Self) {
        try Self.validate(.init(location: offset, length: 0), in: text, graphemeBoundaries: true)
        let length = text.utf16.count
        let left = NSRange(location: 0, length: offset), right = NSRange(location: offset, length: length - offset)
        func fragment(_ range: NSRange) throws -> Self {
            let projected = marks.compactMap { mark -> Mark? in
                let intersection = NSIntersectionRange(mark.range, range)
                guard intersection.length > 0 else { return nil }
                return .init(anchor: mark.anchor,
                             range: .init(location: intersection.location - range.location, length: intersection.length))
            }
            return try .init(text: (text as NSString).substring(with: range), marks: projected)
        }
        return (try fragment(left), try fragment(right))
    }

    public func merging(_ next: Self, separator: String = "") throws -> Self {
        let leftLength = text.utf16.count, separatorLength = separator.utf16.count
        var merged = marks + next.marks.map {
            Mark(anchor: $0.anchor, range: .init(location: leftLength + separatorLength + $0.range.location,
                                               length: $0.range.length))
        }
        if separatorLength > 0, let left = marks.last, let right = next.marks.first,
           NSMaxRange(left.range) == leftLength, right.range.location == 0, left.anchor == right.anchor {
            merged.append(.init(anchor: left.anchor, range: .init(location: leftLength, length: separatorLength)))
        }
        return try .init(text: text + separator + next.text, marks: merged)
    }

    /// Plain clipboard payload intentionally carries no internal anchor URL.
    /// A cut's native edit and Undo remain separate, source-fenced operations.
    public func clipboardText(in range: NSRange) throws -> String {
        try Self.validate(range, in: text, nonempty: true, graphemeBoundaries: true)
        return (text as NSString).substring(with: range)
    }

    public static func validate(_ range: NSRange, in text: String, nonempty: Bool = false,
                                graphemeBoundaries: Bool = false) throws {
        let units = Array(text.utf16)
        guard range.location >= 0, range.length >= (nonempty ? 1 : 0),
              range.location <= units.count, range.length <= units.count - range.location else {
            throw PinkhaSemanticTextAnchorError.invalidRange
        }
        let end = range.location + range.length
        func scalarBoundary(_ offset: Int) -> Bool {
            offset == 0 || offset == units.count ||
            !(0xD800...0xDBFF).contains(units[offset - 1]) || !(0xDC00...0xDFFF).contains(units[offset])
        }
        guard scalarBoundary(range.location), scalarBoundary(end) else {
            throw PinkhaSemanticTextAnchorError.invalidRange
        }
        if graphemeBoundaries {
            let boundaries = Set(text.indices.map { $0.utf16Offset(in: text) } + [units.count])
            guard boundaries.contains(range.location), boundaries.contains(end) else {
                throw PinkhaSemanticTextAnchorError.invalidRange
            }
        }
    }
}

/// An adapter may submit the inverse only after its native version/owner fence
/// accepts the current snapshot. A stale local Undo cannot overwrite new text.
public struct PinkhaSemanticTextEdit: Sendable, Equatable {
    public let before: PinkhaSemanticText
    public let after: PinkhaSemanticText

    public func inverse(current: PinkhaSemanticText) throws -> Self {
        guard current == after else { throw PinkhaSemanticTextAnchorError.changedText }
        return .init(before: after, after: before)
    }
}

public enum PinkhaSemanticTextAnchorResolver {
    public struct Block: Sendable, Equatable {
        public let id: String
        public let content: PinkhaSemanticText

        public init(id: String, content: PinkhaSemanticText) {
            self.id = id
            self.content = content
        }
    }

    public struct Fragment: Sendable, Equatable {
        public let blockID: String
        public let range: NSRange
        public let text: String
    }

    public enum Resolution: Sendable, Equatable {
        case resolved([Fragment])
        case missing
        case ambiguous
    }

    /// Callers supply the complete current document in native order after their
    /// read/ACL/owner fence. No quote search, old offset or old block-ID fallback.
    public static func resolve(_ anchor: PinkhaSemanticTextAnchor, spaceID: String, objectID: String,
                               blocks: [Block]) throws -> Resolution {
        guard anchor.belongsTo(spaceID: spaceID, objectID: objectID) else {
            throw PinkhaSemanticTextAnchorError.wrongDocument
        }
        guard blocks.count <= 10_000 else { throw PinkhaSemanticTextAnchorError.limitExceeded }
        guard blocks.allSatisfy({ !$0.id.isEmpty && $0.id.utf8.count <= 1_024 && !$0.id.contains("\0") }),
              Set(blocks.map(\.id)).count == blocks.count else {
            throw PinkhaSemanticTextAnchorError.invalidIdentity
        }
        var matched: [(index: Int, fragment: Fragment)] = []
        for (index, block) in blocks.enumerated() {
            let marks = block.content.marks.filter { $0.anchor == anchor }
            guard marks.count <= 1 else { return .ambiguous }
            if let mark = marks.first {
                matched.append((index, .init(blockID: block.id, range: mark.range,
                    text: (block.content.text as NSString).substring(with: mark.range))))
            }
        }
        guard !matched.isEmpty else { return .missing }
        for pair in zip(matched, matched.dropFirst()) {
            guard pair.1.index == pair.0.index + 1,
                  NSMaxRange(pair.0.fragment.range) == blocks[pair.0.index].content.text.utf16.count,
                  pair.1.fragment.range.location == 0 else { return .ambiguous }
        }
        return .resolved(matched.map(\.fragment))
    }
}
