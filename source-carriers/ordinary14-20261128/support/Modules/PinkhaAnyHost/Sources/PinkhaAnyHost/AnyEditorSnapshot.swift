import Foundation
import Crypto
import PinkhaAnyEngine

public enum AnyWritingDirection: String, Codable, Sendable { case natural, leftToRight, rightToLeft }
public enum AnyTextAlignment: String, Codable, Sendable { case natural, left, center, right, justified }

/// Keeps native structural identity and the complete received block. Rendering
/// must not round-trip unknown style keys through a reduced UI DTO.
public struct AnyEditorBlock: Sendable, Equatable {
    public let id: String
    public let type: String
    public let text: String
    public let parentID: String
    public let position: String
    public let native: AnyJSON

    public init(native: AnyJSON) throws {
        let id = try native.requireString("id")
        let type = try native.requireString("type")
        guard Self.validID(id), !type.isEmpty, type.utf8.count <= 64,
              let parent = native["nav"]?["parentId"]?.string,
              parent.isEmpty || Self.validID(parent),
              let position = native["nav"]?["pos"]?.string,
              !position.isEmpty, position.utf8.count <= 1024,
              (native["text"] == nil || native["text"]?.string != nil),
              (native["text"]?.string ?? "").utf8.count <= 65_536,
              native["style"] == nil || native["style"]?.object != nil,
              native["_ver"]?.object != nil else {
            throw AnyHostError.invalidDocument("block shape")
        }
        self.id = id; self.type = type; self.text = native["text"]?.string ?? ""
        self.parentID = parent; self.position = position; self.native = native
    }

    public var direction: AnyWritingDirection? {
        native["style"]?["pinkhaWritingDirection"]?.string.flatMap(AnyWritingDirection.init(rawValue:))
    }
    public var alignment: AnyTextAlignment? {
        native["style"]?["pinkhaTextAlignment"]?.string.flatMap(AnyTextAlignment.init(rawValue:))
    }

    public static func validID(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 1024 &&
        value.utf8.allSatisfy { $0 >= 0x21 && $0 <= 0x7e }
    }
}

public struct AnyEditorTextSnapshot: Codable, Sendable, Equatable {
    public struct Block: Codable, Sendable, Equatable {
        public let reference: String
        /// Native inline markdown. Never advertised as stripped plain text.
        public let inlineMarkdown: String
    }
    public let objectReference: String
    public let spaceReference: String
    public let sourceRevision: String
    public let title: String
    public let blocks: [Block]
    public let coverage: String
}

/// A complete bounded native block set. Unreachable blocks remain represented
/// for recovery, but cannot silently enter source associations or AI reads.
public struct AnyEditorSnapshot: Sendable, Equatable {
    public let spaceID: String
    public let objectID: String
    public let dataset: String
    public let title: String
    public let blocks: [AnyEditorBlock]
    public let depthFirstIDs: [String]
    public let unreachableIDs: [String]
    public let revision: String

    public init(spaceID: String, objectID: String, title: String,
                response: AnyJSON, limit: Int = 10_000, dataset: String = "editor_blocks") throws {
        guard AnyEditorBlock.validID(spaceID), AnyEditorBlock.validID(objectID), AnyEditorBlock.validID(dataset),
              (1...10_000).contains(limit), title.utf8.count <= 16_384,
              let records = response["records"]?.array,
              let total = response["total"]?.integer,
              total == Int64(records.count), records.count <= limit,
              response["hasNext"]?.bool == false else {
            throw AnyHostError.incompleteDocument
        }
        let blocks = try records.map(AnyEditorBlock.init(native:))
        guard Set(blocks.map(\.id)).count == blocks.count else {
            throw AnyHostError.invalidDocument("duplicate block identity")
        }
        let byID = Dictionary(uniqueKeysWithValues: blocks.map { ($0.id, $0) })
        var children: [String: [AnyEditorBlock]] = [:]
        for block in blocks { children[block.parentID, default: []].append(block) }
        for key in Array(children.keys) {
            children[key]?.sort { lhs, rhs in
                lhs.position.utf8.elementsEqual(rhs.position.utf8) ? lhs.id < rhs.id : lhs.position.utf8.lexicographicallyPrecedes(rhs.position.utf8)
            }
        }
        var stack = Array((children[""] ?? []).reversed()).map(\.id)
        var ordered: [String] = []
        var visited = Set<String>()
        while let id = stack.popLast() {
            guard byID[id] != nil, visited.insert(id).inserted else {
                throw AnyHostError.invalidDocument("cyclic block tree")
            }
            ordered.append(id)
            stack.append(contentsOf: (children[id] ?? []).reversed().map(\.id))
        }
        self.spaceID = spaceID; self.objectID = objectID; self.dataset = dataset; self.title = title
        self.blocks = blocks
        self.depthFirstIDs = ordered
        self.unreachableIDs = blocks.map(\.id).filter { !visited.contains($0) }.sorted()

        // Version identity uses all blocks, including unrendered style and
        // orphan changes, through native per-field version stamps. This
        // prevents a stable-looking text preview from masking native changes.
        var bytes = Data()
        func append(_ value: String) {
            let field = Data(value.utf8)
            bytes.append(contentsOf: String(field.count).utf8)
            bytes.append(0x3a); bytes.append(field)
        }
        append("pinkha-any-editor/v2"); append(spaceID); append(objectID); append(dataset); append(title)
        for block in blocks.sorted(by: { $0.id < $1.id }) {
            append(block.id); append(block.type); append(block.parentID)
            append(block.position); append(block.text)
            guard let versions = block.native["_ver"] else {
                throw AnyHostError.invalidDocument("native version stamps")
            }
            try AnyHostCanonical.nativeVersions(versions)
            let versionBytes = try AnyHostCanonical.bytes(versions, maximumBytes: 65_536)
            append(String(decoding: versionBytes, as: UTF8.self))
        }
        self.revision = SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
    }

    public func boundedText(selection: [String] = [], maximumBlocks: Int = 128,
                            maximumBytes: Int = 24_576) throws -> AnyEditorTextSnapshot {
        guard unreachableIDs.isEmpty else { throw AnyHostError.incompleteDocument }
        guard maximumBlocks > 0, maximumBlocks <= 128, maximumBytes > 0,
              maximumBytes <= 24_576, title.utf8.count <= 512,
              Set(selection).count == selection.count else { throw AnyHostError.invalidSelection }
        let index = Dictionary(uniqueKeysWithValues: blocks.map { ($0.id, $0) })
        let selected = Set(selection)
        guard selected.isSubset(of: Set(depthFirstIDs)) else { throw AnyHostError.invalidSelection }
        let textTypes: Set<String> = ["paragraph", "heading", "list_item", "check_list_item", "code", "quote"]
        var result: [AnyEditorTextSnapshot.Block] = []
        var bytes = 0
        for id in depthFirstIDs {
            guard let block = index[id] else { throw AnyHostError.incompleteDocument }
            if !selected.isEmpty && !selected.contains(id) { continue }
            guard textTypes.contains(block.type) else {
                if selected.contains(id) { throw AnyHostError.invalidSelection }
                continue
            }
            bytes += block.text.utf8.count
            guard bytes <= maximumBytes, result.count < maximumBlocks else {
                throw AnyEngineError.readLimit
            }
            result.append(.init(reference: id, inlineMarkdown: block.text))
        }
        guard selected.isEmpty || Set(result.map(\.reference)) == selected else {
            throw AnyHostError.invalidSelection
        }
        return .init(objectReference: objectID, spaceReference: spaceID,
                     sourceRevision: revision, title: title, blocks: result,
                     coverage: selected.isEmpty ? "documentTextBlocksInlineMarkdownOnly" : "selectedTextBlocksInlineMarkdownOnly")
    }
}
