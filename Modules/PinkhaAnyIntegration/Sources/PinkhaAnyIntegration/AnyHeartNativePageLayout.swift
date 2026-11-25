import Foundation
import PinkhaAnyEngine

public enum AnyHeartNativePageLayoutError: Error, Equatable, Sendable {
    case incompleteGraph, unsupportedStructure, unsupportedMetadata, invalidTitleBinding, invalidProperty
}

/// Identifies the native Page's protected header without treating its empty
/// bound Title as document text. This is a source projection, not destination
/// admission: the caller must still map name, optional done, and the exact
/// featured-relation configuration through the captured definition catalog.
public struct AnyHeartNativePageLayout: Sendable {
    public let sourceSpaceID: String
    public let sourceObjectID: String
    public let snapshotSHA256: String
    public let viewSHA256: String
    public let contentSHA256: String
    public let headerBlockID: String
    public let titleBlockID: String
    public let featuredBlockID: String
    public let structuralBlockIDs: [String]
    public let bodyBlockIDs: [String]
    public let bodyRootIDs: [String]
    public let title: String?
    public let done: Bool?
    public let featuredRelations: [String]?
    public let originalStructuralBlocks: [AnyJSON]
    public let originalPropertyBindings: AnyJSON
    public var permitsDestinationWrites: Bool { false }

    public init(snapshot: AnyHeartNativeSnapshotView) throws {
        guard snapshot.nativeType == 16, snapshot.issues.isEmpty,
              snapshot.depthFirstIDs.count == snapshot.blocks.count else {
            throw AnyHeartNativePageLayoutError.incompleteGraph
        }
        let rows = Dictionary(uniqueKeysWithValues: snapshot.blocks.map { (Data($0.id.utf8), $0) })
        let rootID = Data(snapshot.sourceObjectID.utf8)
        guard let root = rows[rootID], root.parentID == nil,
              root.contentKind == "smartblock", root.content == .object([:]),
              snapshot.depthFirstIDs.first.map({ Data($0.utf8) }) == rootID,
              let headerID = root.childIDs.first, let header = rows[Data(headerID.utf8)],
              header.contentKind == "layout", header.content == .object(["style": .integer(3)]),
              header.childIDs.count == 2,
              let titleBlock = rows[Data(header.childIDs[0].utf8)],
              let featured = rows[Data(header.childIDs[1].utf8)],
              titleBlock.childIDs.isEmpty, featured.childIDs.isEmpty,
              featured.contentKind == "featuredRelations", featured.content == .object([:]) else {
            throw AnyHeartNativePageLayoutError.unsupportedStructure
        }
        try Self.metadata(root, restrictions: ["drag": false, "dropOn": false, "edit": false, "read": false, "remove": false])
        try Self.metadata(header, restrictions: ["drag": true, "dropOn": true, "edit": true, "read": false, "remove": true])
        let protected = ["drag": true, "dropOn": true, "edit": false, "read": false, "remove": true]
        try Self.metadata(titleBlock, restrictions: protected, boundTitle: true)
        try Self.metadata(featured, restrictions: protected)
        guard titleBlock.contentKind == "text", let text = titleBlock.content?.object,
              Set(text.keys) == ["text", "style", "marks", "checked", "color", "iconEmoji", "iconImage"],
              text["text"] == .string(""), text["style"] == .integer(7),
              text["checked"] == .bool(false), text["color"] == .string(""),
              text["iconEmoji"] == .string(""), text["iconImage"] == .string(""),
              text["marks"] == .null || text["marks"] == .object(["marks": .array([])]) else {
            throw AnyHeartNativePageLayoutError.invalidTitleBinding
        }
        let title: String?
        if let value = snapshot.details["name"] {
            guard let string = value.string, string.utf8.count <= 512 else {
                throw AnyHeartNativePageLayoutError.invalidProperty
            }
            title = string
        } else { title = nil }
        let done: Bool?
        if let value = snapshot.details["done"] {
            guard let flag = value.bool else { throw AnyHeartNativePageLayoutError.invalidProperty }
            done = flag
        } else { done = nil }
        let featuredRelations: [String]?
        if let value = snapshot.details["featuredRelations"] {
            guard let array = value.array, array.count <= 20_000 else {
                throw AnyHeartNativePageLayoutError.invalidProperty
            }
            var keys: [String] = [], bytes = Set<Data>(), normalized = Set<String>()
            for value in array {
                guard let key = value.string, !key.isEmpty, key.utf8.count <= 4096,
                      bytes.insert(Data(key.utf8)).inserted, normalized.insert(key).inserted else {
                    throw AnyHeartNativePageLayoutError.invalidProperty
                }
                keys.append(key)
            }
            featuredRelations = keys
        } else { featuredRelations = nil }
        let structural = [header.id, titleBlock.id, featured.id]
        let excluded = Set(structural.map { Data($0.utf8) })
        let body = snapshot.depthFirstIDs.dropFirst().filter { !excluded.contains(Data($0.utf8)) }
        guard body.count + structural.count + 1 == snapshot.blocks.count else {
            throw AnyHeartNativePageLayoutError.incompleteGraph
        }
        var present: [String: AnyJSON] = [:]
        for key in ["name", "done", "featuredRelations"] {
            if let value = snapshot.details[key] { present[key] = value }
        }
        let bindings: AnyJSON = .object([
            "boundTitleDetailKeys": .array([.string("name"), .string("done")]),
            "presentDetails": .object(present),
            "objectTypes": .array(snapshot.objectTypes.map(AnyJSON.string)),
            "relationLinks": .array(snapshot.relationLinks)
        ])
        let original = [root.raw, header.raw, titleBlock.raw, featured.raw]
        let material: AnyJSON = .object([
            "contract": .string("pinkha-heart-native-page-layout-v1"),
            "space": .string(snapshot.sourceSpaceID), "object": .string(snapshot.sourceObjectID),
            "snapshotSHA256": .string(snapshot.snapshotSHA256), "viewSHA256": .string(snapshot.viewSHA256),
            "structuralBlocks": .array(original), "propertyBindings": bindings,
            "bodyBlockIDs": .array(body.map(AnyJSON.string)),
            "bodyRootIDs": .array(root.childIDs.dropFirst().map(AnyJSON.string))
        ])
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let encoded = try encoder.encode(material)
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: encoded, encoded: encoded)
        sourceSpaceID = snapshot.sourceSpaceID; sourceObjectID = snapshot.sourceObjectID
        snapshotSHA256 = snapshot.snapshotSHA256; viewSHA256 = snapshot.viewSHA256
        contentSHA256 = AnyContentDigest.sha256(encoded)
        headerBlockID = header.id; titleBlockID = titleBlock.id; featuredBlockID = featured.id
        structuralBlockIDs = structural; bodyBlockIDs = Array(body); bodyRootIDs = Array(root.childIDs.dropFirst())
        self.title = title; self.done = done; self.featuredRelations = featuredRelations
        originalStructuralBlocks = original; originalPropertyBindings = bindings
    }

    private static func metadata(_ block: AnyHeartNativeSnapshotView.Block,
                                 restrictions: [String: Bool], boundTitle: Bool = false) throws {
        for key in ["backgroundColor", "align", "verticalAlign"] {
            let expected: AnyJSON = key == "backgroundColor" ? .string("") : .integer(0)
            guard block.raw[key] == expected else { throw AnyHeartNativePageLayoutError.unsupportedMetadata }
        }
        guard block.raw["restrictions"] == .object(restrictions.mapValues(AnyJSON.bool)) else {
            throw AnyHeartNativePageLayoutError.unsupportedMetadata
        }
        if boundTitle {
            guard block.raw["fields"] == .object(["_detailsKey": .array([.string("name"), .string("done")])]) else {
                throw AnyHeartNativePageLayoutError.invalidTitleBinding
            }
        } else {
            guard block.raw["fields"] == .null || block.raw["fields"] == .object([:]) else {
                throw AnyHeartNativePageLayoutError.unsupportedMetadata
            }
        }
    }
}
