import Foundation
import PinkhaAnyEngine

public enum AnyHeartNativeSnapshotViewError: Error, Equatable, Sendable {
    case invalidBinding, limit, invalidSnapshot, invalidHierarchy
    case unsupportedMark(Int64), invalidText
}

/// A bounded semantic view produced from one captured native protobuf snapshot.
/// Original protobuf bytes and every JSON field remain available. This view is
/// conversion input; its constructor grants no account authority or write access.
public struct AnyHeartNativeSnapshotView: Sendable {
    public struct Block: Sendable {
        public let id: String
        public let parentID: String?
        public let childIDs: [String]
        public let contentKind: String?
        public let content: AnyJSON?
        public let raw: AnyJSON

        /// Native text already contains visible Unicode and UTF16 mark ranges.
        /// It must not pass through an export Markdown parser a second time.
        public func inlineProjection() throws -> AnyHeartInlineProjection {
            guard contentKind == "text", let value = content?.object,
                  let text = value["text"]?.string,
                  let style = value["style"]?.integer else {
                throw AnyHeartNativeSnapshotViewError.invalidText
            }
            let rows: [AnyJSON]
            if value["marks"] == nil || value["marks"] == .null { rows = [] }
            else {
                guard let marks = value["marks"]?.object,
                      let actual = marks["marks"]?.array else {
                    throw AnyHeartNativeSnapshotViewError.invalidText
                }
                rows = actual
            }
            guard rows.count <= 4096 else { throw AnyHeartNativeSnapshotViewError.limit }
            let kinds: [Int64: AnyHeartInlineProjection.Mark.Kind] = [
                0: .strike, 1: .code, 2: .italic, 3: .bold, 4: .underline,
                5: .link, 6: .textColor, 7: .backgroundColor, 8: .mention,
                9: .emoji, 10: .object,
            ]
            let marks = try rows.map { row -> AnyHeartInlineProjection.Mark in
                guard let fields = row.object, Set(fields.keys) == ["type", "range", "param"],
                      let range = row["range"]?.object, Set(range.keys) == ["from", "to"],
                      let rawKind = row["type"]?.integer else {
                    throw AnyHeartNativeSnapshotViewError.invalidText
                }
                guard let kind = kinds[rawKind] else {
                    throw AnyHeartNativeSnapshotViewError.unsupportedMark(rawKind)
                }
                guard let start = row["range"]?["from"]?.integer,
                      let end = row["range"]?["to"]?.integer,
                      start >= 0, end >= 0, start <= Int64(Int.max), end <= Int64(Int.max),
                      let parameter = row["param"]?.string else {
                    throw AnyHeartNativeSnapshotViewError.invalidText
                }
                return .init(kind: kind, start: Int(start), end: Int(end), parameter: parameter)
            }
            return try .init(capturedNativeText: text, literal: style == 6, marks: marks)
        }
    }

    public struct Issue: Equatable, Sendable {
        public enum Kind: String, Sendable { case unknownSnapshotField, unknownBlockField, missingContent, unreachableBlock }
        public let kind: Kind
        public let blockID: String?
        public let field: String
    }

    public let sourceSpaceID: String
    public let sourceObjectID: String
    public let nativeType: Int64
    public let uniqueKey: String
    public let snapshotSHA256: String
    public let viewSHA256: String
    public let protobufBytes: Data
    public let jsonViewBytes: Data
    public let rawSnapshot: AnyJSON
    public let details: [String: AnyJSON]
    public let objectTypes: [String]
    public let relationLinks: [AnyJSON]
    public let blocks: [Block]
    public let depthFirstIDs: [String]
    public let issues: [Issue]

    public init(jsonView: Data, snapshotBytes: Data,
                sourceSpaceID: String, sourceObjectID: String) throws {
        guard jsonView.count <= 32 * 1024 * 1024,
              !snapshotBytes.isEmpty, snapshotBytes.count <= 8 * 1024 * 1024 else {
            throw AnyHeartNativeSnapshotViewError.limit
        }
        let root = try JSONDecoder().decode(AnyJSON.self, from: jsonView)
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: jsonView, encoded: encoder.encode(root))
        let hash = AnyContentDigest.sha256(snapshotBytes)
        guard root["Contract"]?.string == "pinkha-native-snapshot-json-v1",
              let space = root["SpaceID"]?.string, Self.validID(space),
              let object = root["ObjectID"]?.string, Self.validID(object),
              Data(space.utf8) == Data(sourceSpaceID.utf8),
              Data(object.utf8) == Data(sourceObjectID.utf8),
              let type = root["NativeType"]?.integer, type >= 0, type <= Int64(Int32.max),
              let key = root["UniqueKey"]?.string, key.utf8.count <= 4096,
              root["SnapshotSHA256"]?.string == hash,
              root["SnapshotBytes"]?.integer == Int64(snapshotBytes.count),
              let snapshot = root["Snapshot"], let raw = snapshot.object else {
            throw AnyHeartNativeSnapshotViewError.invalidBinding
        }
        guard let rows = raw["blocks"]?.array, rows.count <= 100_000,
              let types = raw["objectTypes"]?.array,
              let links = raw["relationLinks"]?.array, links.count <= 20_000 else {
            throw AnyHeartNativeSnapshotViewError.invalidSnapshot
        }
        let objectTypes = try Self.identifiers(types)
        let details: [String: AnyJSON]
        if raw["details"] == .null { details = [:] }
        else if let fields = raw["details"]?.object, fields.count <= 20_000 { details = fields }
        else { throw AnyHeartNativeSnapshotViewError.invalidSnapshot }
        var issues: [Issue] = []
        let snapshotFields: Set<String> = ["blocks", "details", "fileKeys", "extraRelations", "objectTypes",
            "collections", "removedCollectionKeys", "relationLinks", "key", "originalCreatedTimestamp", "fileInfo"]
        for field in Set(raw.keys).subtracting(snapshotFields).sorted() {
            issues.append(.init(kind: .unknownSnapshotField, blockID: nil, field: field))
        }
        let commonFields: Set<String> = ["id", "fields", "restrictions", "childrenIds", "backgroundColor", "align", "verticalAlign"]
        let contentFields: Set<String> = ["smartblock", "text", "file", "layout", "div", "bookmark", "icon", "link",
            "dataview", "relation", "featuredRelations", "latex", "tableOfContents", "table", "tableColumn", "tableRow", "widget", "chat"]
        var byID: [Data: AnyJSON] = [:], names: [Data: String] = [:], children: [Data: [String]] = [:]
        var contentKinds: [Data: String] = [:]
        var stringKeys = Set<String>()
        for row in rows {
            guard let fields = row.object, let id = fields["id"]?.string, Self.validID(id),
                  byID[Data(id.utf8)] == nil, stringKeys.insert(id).inserted,
                  let rawChildren = fields["childrenIds"]?.array else {
                throw AnyHeartNativeSnapshotViewError.invalidSnapshot
            }
            let bytes = Data(id.utf8)
            byID[bytes] = row; names[bytes] = id
            children[bytes] = try Self.identifiers(rawChildren)
            let content = Set(fields.keys).intersection(contentFields)
            guard content.count <= 1 else { throw AnyHeartNativeSnapshotViewError.invalidSnapshot }
            contentKinds[bytes] = content.first
            if content.isEmpty { issues.append(.init(kind: .missingContent, blockID: id, field: "content")) }
            for field in Set(fields.keys).subtracting(commonFields.union(contentFields)).sorted() {
                issues.append(.init(kind: .unknownBlockField, blockID: id, field: field))
            }
        }
        var parents: [Data: String] = [:]
        for (parent, childIDs) in children {
            for child in childIDs {
                let id = Data(child.utf8)
                guard byID[id] != nil, parents[id] == nil, id != Data(object.utf8) else {
                    throw AnyHeartNativeSnapshotViewError.invalidHierarchy
                }
                parents[id] = names[parent]
            }
        }
        var ordered: [String] = [], visited = Set<Data>()
        if !rows.isEmpty {
            guard byID[Data(object.utf8)] != nil else { throw AnyHeartNativeSnapshotViewError.invalidHierarchy }
            var pending = [object]
            while let id = pending.popLast() {
                let bytes = Data(id.utf8)
                guard visited.insert(bytes).inserted else { throw AnyHeartNativeSnapshotViewError.invalidHierarchy }
                ordered.append(id)
                pending.append(contentsOf: (children[bytes] ?? []).reversed())
            }
        }
        // Disconnected rows are retained and explicitly reported. They cannot
        // silently disappear from a later migration coverage decision.
        var checkedChains = visited
        for bytes in byID.keys.filter({ !visited.contains($0) }).sorted(by: { $0.lexicographicallyPrecedes($1) }) {
            issues.append(.init(kind: .unreachableBlock, blockID: names[bytes], field: "childrenIds"))
            var chain = Set<Data>(), cursor: Data? = bytes
            while let node = cursor, !checkedChains.contains(node) {
                guard chain.insert(node).inserted else { throw AnyHeartNativeSnapshotViewError.invalidHierarchy }
                cursor = parents[node].map { Data($0.utf8) }
            }
            checkedChains.formUnion(chain)
        }
        self.sourceSpaceID = space; self.sourceObjectID = object
        nativeType = type; uniqueKey = key; snapshotSHA256 = hash
        viewSHA256 = AnyContentDigest.sha256(jsonView)
        protobufBytes = snapshotBytes; jsonViewBytes = jsonView; rawSnapshot = snapshot
        self.details = details; self.objectTypes = objectTypes; relationLinks = links
        blocks = rows.map { row in
            let id = row["id"]!.string!, bytes = Data(id.utf8), kind = contentKinds[bytes]
            return .init(id: id, parentID: parents[bytes], childIDs: children[bytes]!,
                         contentKind: kind, content: kind.flatMap { row[$0] }, raw: row)
        }
        depthFirstIDs = ordered; self.issues = issues
    }

    private static func validID(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 4096 &&
        value.unicodeScalars.allSatisfy { !CharacterSet.controlCharacters.contains($0) }
    }
    private static func identifiers(_ values: [AnyJSON]) throws -> [String] {
        var exact = Set<Data>(), normalized = Set<String>()
        return try values.map { value in
            guard let id = value.string, validID(id), exact.insert(Data(id.utf8)).inserted,
                  normalized.insert(id).inserted else { throw AnyHeartNativeSnapshotViewError.invalidSnapshot }
            return id
        }
    }
}

extension AnyHeartInlineProjection {
    init(capturedNativeText: String, literal: Bool, marks: [Mark]) throws {
        guard capturedNativeText.utf8.count <= 65_536, marks.count <= 4096 else {
            throw AnyHeartInlineProjectionError.limit
        }
        let units = Array(capturedNativeText.utf16)
        func boundary(_ index: Int) -> Bool {
            guard index >= 0, index <= units.count else { return false }
            return index == 0 || index == units.count ||
                !((0xD800...0xDBFF).contains(units[index - 1]) && (0xDC00...0xDFFF).contains(units[index]))
        }
        for mark in marks {
            guard mark.start < mark.end, boundary(mark.start), boundary(mark.end),
                  mark.parameter.utf8.count <= 65_536 else {
                throw AnyHeartInlineProjectionError.invalidRange
            }
        }
        guard !literal || marks.isEmpty else { throw AnyHeartInlineProjectionError.invalidBinding }
        source = capturedNativeText; text = capturedNativeText
        sourceSHA256 = AnyContentDigest.sha256(Data(capturedNativeText.utf8))
        self.literal = literal; self.marks = marks
    }
}
