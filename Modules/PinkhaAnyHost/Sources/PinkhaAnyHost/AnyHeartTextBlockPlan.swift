import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

public enum AnyHeartTextBlockPlanError: Error, Equatable, Sendable {
    case missingObject, unsupportedObject, unboundProjection, unsupportedBlock(String)
    case unsupportedMetadata(String), invalidMetadata(String), invalidHierarchy
}

/// Converts a single inspected object's supported text blocks. This is a
/// semantic conversion stage, not full-Space source admission or an executor.
/// The owning archive retains every original entry and every inspection issue.
public struct AnyHeartTextBlockPlan: Sendable {
    public typealias Identity = AnyHeartSpaceMigrationDryRun.Identity
    public struct Entry: Sendable {
        public let identity: Identity
        public let parent: Identity?
        public let type: String
        public let text: String
        public let style: AnyJSON
        public let position: String
        public let originalNative: AnyJSON
        public let inlineSourceSHA256: String
    }
    public let sourceSpaceID: String
    public let sourceObjectID: String
    public let archiveSHA256: String
    public let entries: [Entry]
    public let contentSHA256: String
    public var permitsDestinationWrites: Bool { false }

    public init(archive: AnyHeartSpaceArchive, sourceObjectID: String,
                projections: [Identity: AnyHeartInlineProjection]) throws {
        guard let object = archive.objects.first(where: { $0.sourceID.utf8.elementsEqual(sourceObjectID.utf8) }) else {
            throw AnyHeartTextBlockPlanError.missingObject
        }
        guard object.kind == "page" else { throw AnyHeartTextBlockPlanError.unsupportedObject }
        func identity(_ id: String) -> Identity {
            .init(kind: .block, sourceSpaceID: archive.sourceSpaceID, sourceObjectID: sourceObjectID, sourceID: id)
        }
        let expectedKeys = Set(object.blocks.map { identity($0.sourceID) })
        guard expectedKeys.count == object.blocks.count, expectedKeys == Set(projections.keys) else {
            throw AnyHeartTextBlockPlanError.unboundProjection
        }
        var rows: [Entry] = [], visited = Set<Identity>()
        var positions: [Data: String] = [:]
        var listCounts: [Data: Int64] = [:]
        for block in object.blocks {
            let key = identity(block.sourceID)
            let parent = block.parentSourceID.map(identity)
            guard parent.map({ visited.contains($0) }) ?? true,
                  visited.insert(key).inserted else { throw AnyHeartTextBlockPlanError.invalidHierarchy }
            guard let projection = projections[key],
                  projection.source.utf8.elementsEqual((block.native["text"]?.string ?? "").utf8),
                  projection.literal == (block.type == "code"),
                  block.native["text"] == nil || block.native["text"]?.string != nil else {
                throw AnyHeartTextBlockPlanError.unboundProjection
            }
            var accepted: Set<String> = ["id", "type", "indent", "text"]
            let type: String
            var style: [String: AnyJSON] = [:]
            let parentKey = block.parentSourceID.map { Data($0.utf8) } ?? Data()
            switch block.type {
            case "paragraph", "quote": type = block.type
            case "heading_1", "heading_2", "heading_3":
                type = "heading"
                style["level"] = .integer(Int64(block.type.suffix(1))!)
            case "bulleted_list_item":
                type = "list_item"; style["ordered"] = .bool(false)
            case "numbered_list_item":
                type = "list_item"; style["ordered"] = .bool(true)
                let number = (listCounts[parentKey] ?? 0) + 1
                style["number"] = .integer(number); listCounts[parentKey] = number
            case "checkbox":
                type = "check_list_item"; accepted.insert("checked")
                guard block.native["checked"] == nil || block.native["checked"]?.bool != nil else {
                    throw AnyHeartTextBlockPlanError.invalidMetadata("checked")
                }
                style["checked"] = .bool(block.native["checked"]?.bool ?? false)
            case "code":
                type = "code"; accepted.insert("language")
                if let language = block.native["language"] {
                    guard let value = language.string, value.utf8.count <= 256 else {
                        throw AnyHeartTextBlockPlanError.invalidMetadata("language")
                    }
                    style["lang"] = .string(value)
                }
            default: throw AnyHeartTextBlockPlanError.unsupportedBlock(block.type)
            }
            if block.type != "numbered_list_item" { listCounts[parentKey] = 0 }
            guard let native = block.native.object else { throw AnyHeartTextBlockPlanError.invalidMetadata("block") }
            if let field = Set(native.keys).subtracting(accepted).sorted().first {
                throw AnyHeartTextBlockPlanError.unsupportedMetadata(field)
            }
            let text = try AnyHeartInlineConversion(projection).inlineMarkdown
            let position = try AnyLexicographicPosition.between(after: positions[parentKey], before: nil)
            positions[parentKey] = position
            rows.append(.init(identity: key, parent: parent, type: type, text: text,
                style: .object(style), position: position, originalNative: block.native,
                inlineSourceSHA256: projection.sourceSHA256))
        }
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let material: AnyJSON = .object([
            "contract": .string("pinkha-heart-text-block-plan-v1"),
            "archiveSHA256": .string(archive.contentSHA256),
            "sourceSpaceID": .string(archive.sourceSpaceID), "sourceObjectID": .string(sourceObjectID),
            "blocks": .array(rows.map { row in .object([
                "sourceKey": .string(row.identity.symbolicKey),
                "parentKey": row.parent.map { .string($0.symbolicKey) } ?? .null,
                "type": .string(row.type), "text": .string(row.text), "style": row.style,
                "position": .string(row.position), "inlineSourceSHA256": .string(row.inlineSourceSHA256)
            ]) })
        ])
        self.sourceSpaceID = archive.sourceSpaceID; self.sourceObjectID = sourceObjectID
        archiveSHA256 = archive.contentSHA256; entries = rows
        contentSHA256 = AnyContentDigest.sha256(try encoder.encode(material))
    }
}
