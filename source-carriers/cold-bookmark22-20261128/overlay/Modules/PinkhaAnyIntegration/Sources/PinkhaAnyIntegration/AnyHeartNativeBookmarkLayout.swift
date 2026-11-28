import Foundation
import PinkhaAnyEngine

public enum AnyHeartNativeBookmarkLayoutError: Error, Equatable, Sendable {
    case incompleteGraph, unsupportedStructure, unsupportedMetadata, invalidBinding, invalidProperty
}

/// Projects Heart's Bookmark header as bound properties. The source remains a
/// native Page smartblock (16) with a separately verified Bookmark Type (11).
/// A description header is never appended to the editable body as duplicate text.
public struct AnyHeartNativeBookmarkLayout: Sendable {
    public let sourceSpaceID: String
    public let sourceObjectID: String
    public let snapshotSHA256: String
    public let viewSHA256: String
    public let contentSHA256: String
    public let headerBlockID: String
    public let titleBlockID: String
    public let descriptionBlockID: String
    public let featuredBlockID: String
    public let structuralBlockIDs: [String]
    public let bodyBlockIDs: [String]
    public let bodyRootIDs: [String]
    public let title: String?
    public let description: String?
    public let sourceURL: String?
    public let featuredRelations: [String]?
    /// Only Heart's closed default description-header binding is structural.
    /// Any other object-specific featured order still needs its own behavior.
    public let structuralDetailKeys: [String]
    public let originalStructuralBlocks: [AnyJSON]
    public let originalPropertyBindings: AnyJSON
    public var permitsDestinationWrites: Bool { false }

    public init(snapshot: AnyHeartNativeSnapshotView) throws {
        guard snapshot.nativeType == 16, snapshot.issues.isEmpty,
              snapshot.depthFirstIDs.count == snapshot.blocks.count else {
            throw AnyHeartNativeBookmarkLayoutError.incompleteGraph
        }
        let rows = Dictionary(uniqueKeysWithValues: snapshot.blocks.map { (Data($0.id.utf8), $0) })
        let rootID = Data(snapshot.sourceObjectID.utf8)
        guard let root = rows[rootID], root.parentID == nil,
              root.contentKind == "smartblock", root.content == .object([:]),
              snapshot.depthFirstIDs.first.map({ Data($0.utf8) }) == rootID,
              let headerID = root.childIDs.first, let header = rows[Data(headerID.utf8)],
              header.contentKind == "layout", header.content == .object(["style": .integer(3)]),
              header.childIDs.count == 3,
              let titleBlock = rows[Data(header.childIDs[0].utf8)],
              let descriptionBlock = rows[Data(header.childIDs[1].utf8)],
              let featured = rows[Data(header.childIDs[2].utf8)],
              titleBlock.childIDs.isEmpty, descriptionBlock.childIDs.isEmpty,
              featured.childIDs.isEmpty, featured.contentKind == "featuredRelations",
              featured.content == .object([:]) else {
            throw AnyHeartNativeBookmarkLayoutError.unsupportedStructure
        }
        try Self.metadata(root, restrictions: ["drag": false, "dropOn": false, "edit": false, "read": false, "remove": false])
        try Self.metadata(header, restrictions: ["drag": true, "dropOn": true, "edit": true, "read": false, "remove": true])
        let protected = ["drag": true, "dropOn": true, "edit": false, "read": false, "remove": true]
        try Self.metadata(titleBlock, restrictions: protected,
                          fields: .object(["_detailsKey": .array([.string("name"), .string("done")])]))
        try Self.metadata(descriptionBlock, restrictions: protected,
                          fields: .object(["_detailsKey": .string("description")]))
        try Self.metadata(featured, restrictions: protected)
        // Native models.proto: Title=7, Description=12. Empty model text is
        // bound to the property; literal text/marks would be distinct content.
        try Self.boundText(titleBlock, style: 7)
        try Self.boundText(descriptionBlock, style: 12)
        func string(_ key: String, maximum: Int) throws -> String? {
            guard let value = snapshot.details[key] else { return nil }
            guard let text = value.string, text.utf8.count <= maximum else {
                throw AnyHeartNativeBookmarkLayoutError.invalidProperty
            }
            return text
        }
        let title = try string("name", maximum: 512)
        let description = try string("description", maximum: 65_536)
        let sourceURL = try string("source", maximum: 65_536)
        if let done = snapshot.details["done"], done.bool == nil {
            throw AnyHeartNativeBookmarkLayoutError.invalidProperty
        }
        let featuredRelations: [String]?
        let structuralDetailKeys: [String]
        if let value = snapshot.details["featuredRelations"] {
            guard value == .array([.string("description")]) else {
                throw AnyHeartNativeBookmarkLayoutError.unsupportedMetadata
            }
            featuredRelations = ["description"]
            structuralDetailKeys = ["featuredRelations"]
        } else {
            featuredRelations = nil
            structuralDetailKeys = []
        }
        let structural = [header.id, titleBlock.id, descriptionBlock.id, featured.id]
        let excluded = Set(structural.map { Data($0.utf8) })
        let body = snapshot.depthFirstIDs.dropFirst().filter { !excluded.contains(Data($0.utf8)) }
        guard body.count + structural.count + 1 == snapshot.blocks.count else {
            throw AnyHeartNativeBookmarkLayoutError.incompleteGraph
        }
        var present: [String: AnyJSON] = [:]
        for key in ["name", "done", "description", "source", "featuredRelations"] {
            if let value = snapshot.details[key] { present[key] = value }
        }
        let bindings: AnyJSON = .object([
            "boundTitleDetailKeys": .array([.string("name"), .string("done")]),
            "boundDescriptionDetailKey": .string("description"),
            "presentDetails": .object(present),
            "objectTypes": .array(snapshot.objectTypes.map(AnyJSON.string)),
            "relationLinks": .array(snapshot.relationLinks)
        ])
        let original = [root.raw, header.raw, titleBlock.raw, descriptionBlock.raw, featured.raw]
        let material: AnyJSON = .object([
            "contract": .string("pinkha-heart-native-bookmark-layout-v1"),
            "space": .string(snapshot.sourceSpaceID), "object": .string(snapshot.sourceObjectID),
            "snapshotSHA256": .string(snapshot.snapshotSHA256), "viewSHA256": .string(snapshot.viewSHA256),
            "structuralBlocks": .array(original), "propertyBindings": bindings,
            "bodyBlockIDs": .array(body.map(AnyJSON.string)),
            "bodyRootIDs": .array(root.childIDs.dropFirst().map(AnyJSON.string))
        ])
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let bytes = try encoder.encode(material)
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: bytes, encoded: bytes)
        sourceSpaceID = snapshot.sourceSpaceID; sourceObjectID = snapshot.sourceObjectID
        snapshotSHA256 = snapshot.snapshotSHA256; viewSHA256 = snapshot.viewSHA256
        contentSHA256 = AnyContentDigest.sha256(bytes)
        headerBlockID = header.id; titleBlockID = titleBlock.id
        descriptionBlockID = descriptionBlock.id; featuredBlockID = featured.id
        structuralBlockIDs = structural; bodyBlockIDs = Array(body)
        bodyRootIDs = Array(root.childIDs.dropFirst())
        self.title = title; self.description = description; self.sourceURL = sourceURL
        self.featuredRelations = featuredRelations; self.structuralDetailKeys = structuralDetailKeys
        originalStructuralBlocks = original; originalPropertyBindings = bindings
    }

    private static func metadata(_ block: AnyHeartNativeSnapshotView.Block,
                                 restrictions: [String: Bool], fields: AnyJSON? = nil) throws {
        for key in ["backgroundColor", "align", "verticalAlign"] {
            let expected: AnyJSON = key == "backgroundColor" ? .string("") : .integer(0)
            guard block.raw[key] == expected else { throw AnyHeartNativeBookmarkLayoutError.unsupportedMetadata }
        }
        guard block.raw["restrictions"] == .object(restrictions.mapValues(AnyJSON.bool)) else {
            throw AnyHeartNativeBookmarkLayoutError.unsupportedMetadata
        }
        if let fields {
            guard block.raw["fields"] == fields else { throw AnyHeartNativeBookmarkLayoutError.invalidBinding }
        } else {
            guard block.raw["fields"] == .null || block.raw["fields"] == .object([:]) else {
                throw AnyHeartNativeBookmarkLayoutError.unsupportedMetadata
            }
        }
    }

    private static func boundText(_ block: AnyHeartNativeSnapshotView.Block, style: Int64) throws {
        guard block.contentKind == "text", let text = block.content?.object,
              Set(text.keys) == ["text", "style", "marks", "checked", "color", "iconEmoji", "iconImage"],
              text["text"] == .string(""), text["style"] == .integer(style),
              text["checked"] == .bool(false), text["color"] == .string(""),
              text["iconEmoji"] == .string(""), text["iconImage"] == .string(""),
              text["marks"] == .null || text["marks"] == .object(["marks": .array([])]) else {
            throw AnyHeartNativeBookmarkLayoutError.invalidBinding
        }
    }
}
