import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

public enum AnyHeartNativeTextBlockPlanError: Error, Equatable, Sendable {
    case invalidRoot
    case incompleteGraph
    case unsupportedContent(String, String)
    case unsupportedStyle(String, Int64)
    case unsupportedMetadata(String, String)
    case limit
}

/// Converts the supported native text graph directly from its bound PB/JSON
/// view. This component does not convert the object's properties, settings,
/// file references or history and cannot authorize destination execution.
public struct AnyHeartNativeTextBlockPlan: Sendable {
    public struct Entry: Sendable {
        public let sourceBlockID: String
        public let sourceKey: String
        public let parentSourceKey: String?
        public let type: String
        public let text: String
        public let style: AnyJSON
        public let position: String
        public let originalNative: AnyJSON
    }

    public let sourceSpaceID: String
    public let sourceObjectID: String
    public let snapshotSHA256: String
    public let viewSHA256: String
    public let contentSHA256: String
    public let entries: [Entry]
    public var permitsDestinationWrites: Bool { false }

    public init(snapshot: AnyHeartNativeSnapshotView) throws {
        guard snapshot.issues.isEmpty,
              snapshot.depthFirstIDs.count == snapshot.blocks.count else {
            throw AnyHeartNativeTextBlockPlanError.incompleteGraph
        }
        let rows = Dictionary(uniqueKeysWithValues: snapshot.blocks.map { (Data($0.id.utf8), $0) })
        let rootID = Data(snapshot.sourceObjectID.utf8)
        guard let root = rows[rootID], root.parentID == nil,
              root.contentKind == "smartblock", root.content?.object?.isEmpty == true,
              snapshot.depthFirstIDs.first.map({ Data($0.utf8) }) == rootID else {
            throw AnyHeartNativeTextBlockPlanError.invalidRoot
        }
        _ = try Self.checkMetadata(root, code: false)

        func key(_ id: String) -> String {
            let identity = AnyHeartSpaceMigrationDryRun.Identity(kind: .block,
                sourceSpaceID: snapshot.sourceSpaceID, sourceObjectID: snapshot.sourceObjectID, sourceID: id)
            return "heart-native-block:" + identity.symbolicKey
        }
        var entries: [Entry] = []
        var visited: Set<Data> = [rootID]
        var positions: [Data: String] = [:]
        var counters: [Data: Int64] = [:]
        for id in snapshot.depthFirstIDs.dropFirst() {
            guard let row = rows[Data(id.utf8)], let parent = row.parentID,
                  visited.contains(Data(parent.utf8)), visited.insert(Data(id.utf8)).inserted else {
                throw AnyHeartNativeTextBlockPlanError.incompleteGraph
            }
            guard row.contentKind == "text", let content = row.content?.object,
                  let nativeStyle = content["style"]?.integer else {
                throw AnyHeartNativeTextBlockPlanError.unsupportedContent(id, row.contentKind ?? "absent")
            }
            let known: Set<String> = ["text", "style", "marks", "checked", "color", "iconEmoji", "iconImage"]
            if let unknown = Set(content.keys).subtracting(known).sorted().first {
                throw AnyHeartNativeTextBlockPlanError.unsupportedMetadata(id, "text." + unknown)
            }
            for name in ["color", "iconEmoji", "iconImage"] {
                if let value = content[name], value != .string("") {
                    throw AnyHeartNativeTextBlockPlanError.unsupportedMetadata(id, "text." + name)
                }
            }
            if let checked = content["checked"] {
                guard checked.bool != nil, nativeStyle == 8 || checked == .bool(false) else {
                    throw AnyHeartNativeTextBlockPlanError.unsupportedMetadata(id, "text.checked")
                }
            }
            let language = try Self.checkMetadata(row, code: nativeStyle == 6)
            let parentID = Data(parent.utf8)
            let type: String
            var style: [String: AnyJSON] = [:]
            // Exact BlockContentTextStyle values from the bound native model:
            // Paragraph0, Header1/2/3, Quote5, Code6, Checkbox8, Marked9, Numbered10.
            switch nativeStyle {
            case 0: type = "paragraph"
            case 1...3: type = "heading"; style["level"] = .integer(nativeStyle)
            case 5: type = "quote"
            case 6:
                type = "code"
                if let language { style["lang"] = .string(language) }
            case 8:
                type = "check_list_item"; style["checked"] = .bool(content["checked"]?.bool ?? false)
            case 9:
                type = "list_item"; style["ordered"] = .bool(false)
            case 10:
                type = "list_item"; style["ordered"] = .bool(true)
                let number = (counters[parentID] ?? 0) + 1
                counters[parentID] = number; style["number"] = .integer(number)
            default:
                throw AnyHeartNativeTextBlockPlanError.unsupportedStyle(id, nativeStyle)
            }
            if nativeStyle != 10 { counters[parentID] = 0 }
            let projection = try row.inlineProjection()
            let text = try AnyHeartInlineConversion(projection).inlineMarkdown
            guard text.utf8.count <= 65_536 else { throw AnyHeartNativeTextBlockPlanError.limit }
            let position = try AnyLexicographicPosition.between(after: positions[parentID], before: nil)
            positions[parentID] = position
            entries.append(.init(sourceBlockID: id, sourceKey: key(id),
                parentSourceKey: parentID == rootID ? nil : key(parent), type: type,
                text: text, style: .object(style), position: position, originalNative: row.raw))
        }
        let material: AnyJSON = .object([
            "contract": .string("pinkha-heart-native-text-block-plan-v1"),
            "space": .string(snapshot.sourceSpaceID), "object": .string(snapshot.sourceObjectID),
            "snapshotSHA256": .string(snapshot.snapshotSHA256), "viewSHA256": .string(snapshot.viewSHA256),
            "entries": .array(entries.map { entry in .object([
                "sourceBlockID": .string(entry.sourceBlockID), "sourceKey": .string(entry.sourceKey),
                "parentSourceKey": entry.parentSourceKey.map(AnyJSON.string) ?? .null,
                "type": .string(entry.type), "text": .string(entry.text), "style": entry.style,
                "position": .string(entry.position), "originalNative": entry.originalNative
            ]) })
        ])
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let bytes = try encoder.encode(material)
        guard bytes.count <= AnyDestinationMigrationPlan.maximumPlanBytes else {
            throw AnyHeartNativeTextBlockPlanError.limit
        }
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: bytes, encoded: bytes)
        sourceSpaceID = snapshot.sourceSpaceID; sourceObjectID = snapshot.sourceObjectID
        snapshotSHA256 = snapshot.snapshotSHA256; viewSHA256 = snapshot.viewSHA256
        contentSHA256 = AnyContentDigest.sha256(bytes); self.entries = entries
    }

    /// The owner must be an earlier ordinary object item in the enclosing
    /// destination plan. That plan independently checks all reference phases,
    /// dataset capability, source coverage and the full source/target binding.
    public func destinationItems(ownerSourceKey: String, dataset: String = "editor_blocks")
        -> [AnyDestinationMigrationItem] {
        entries.map { entry in
            .init(sourceKey: entry.sourceKey, sourceObjectID: sourceObjectID,
                operation: .editorBlock(owner: .mapped(sourceKey: ownerSourceKey, slot: .objectID, encoding: .rawID),
                    dataset: dataset, type: entry.type, text: entry.text, style: .literal(entry.style),
                    parent: entry.parentSourceKey.map { .mapped(sourceKey: $0, slot: .record(index: 0), encoding: .rawID) },
                    position: entry.position))
        }
    }

    @discardableResult
    private static func checkMetadata(_ block: AnyHeartNativeSnapshotView.Block, code: Bool) throws -> String? {
        for name in ["backgroundColor", "align", "verticalAlign", "restrictions"] {
            if let value = block.raw[name], !isDefault(value) {
                throw AnyHeartNativeTextBlockPlanError.unsupportedMetadata(block.id, name)
            }
        }
        guard let fields = block.raw["fields"], fields != .null else { return nil }
        guard let object = fields.object else {
            throw AnyHeartNativeTextBlockPlanError.unsupportedMetadata(block.id, "fields")
        }
        guard !object.isEmpty else { return nil }
        guard code, Set(object.keys) == ["lang"], let language = object["lang"]?.string,
              language.utf8.count <= 256 else {
            throw AnyHeartNativeTextBlockPlanError.unsupportedMetadata(block.id, "fields")
        }
        return language
    }

    private static func isDefault(_ value: AnyJSON) -> Bool {
        switch value {
        case .null: true
        case .bool(let value): !value
        case .integer(let value): value == 0
        case .number(let value): value == 0
        case .string(let value): value.isEmpty
        case .array(let values): values.isEmpty
        case .object(let fields): fields.values.allSatisfy(isDefault)
        }
    }
}
