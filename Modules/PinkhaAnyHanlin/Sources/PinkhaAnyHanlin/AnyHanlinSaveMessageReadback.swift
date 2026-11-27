import Foundation
import HanlinHostContracts
import PinkhaHanlinCore
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration

/// Rebuilds semantic content from actual native rows. It takes no expected
/// Markdown, expected block text, fabricated Heart projection, or fallback title.
public struct AnyHanlinSaveMessageReadback: Sendable {
    public let snapshot: AnyEditorSnapshot
    public let rootReadbackSHA256: String
    public let blocks: [PinkhaHanlinSavedBlock]
    public let blockReferences: [String]

    public init(snapshot: AnyEditorSnapshot, rootRecord: AnyJSON, workspace: AnyTorahWorkspace) throws {
        guard snapshot.spaceID.utf8.elementsEqual(workspace.spaceID.utf8),
              snapshot.dataset == "editor_blocks", snapshot.unreachableIDs.isEmpty,
              snapshot.blocks.count <= PinkhaHanlinSaveMessagePlan.maximumBlocks,
              snapshot.depthFirstIDs.count == snapshot.blocks.count else {
            throw PinkhaHanlinSaveMessageError.conflictingReceipt
        }
        let title = try Self.rootTitle(rootRecord, objectID: snapshot.objectID, workspace: workspace)
        guard title.utf8.elementsEqual(snapshot.title.utf8) else { throw PinkhaHanlinSaveMessageError.conflictingReceipt }
        let byID = Dictionary(uniqueKeysWithValues: snapshot.blocks.map { (Data($0.id.utf8), $0) })
        let blocks = try snapshot.depthFirstIDs.map { id -> PinkhaHanlinSavedBlock in
            guard let row = byID[Data(id.utf8)] else { throw PinkhaHanlinSaveMessageError.conflictingReceipt }
            return try Self.semanticBlock(row)
        }
        self.snapshot = snapshot
        self.rootReadbackSHA256 = try PinkhaHanlinSaveMessageDocument.rootReadbackSHA256(title: title)
        self.blocks = blocks; self.blockReferences = snapshot.depthFirstIDs
    }

    public static func rootTitle(_ record: AnyJSON, objectID: String, workspace: AnyTorahWorkspace) throws -> String {
        guard record["id"]?.string?.utf8.elementsEqual(objectID.utf8) == true,
              record["spaceId"]?.string?.utf8.elementsEqual(workspace.spaceID.utf8) == true,
              record["any"]?["type"]?.string == "page",
              let title = record["any"]?["name"]?.string,
              record["any"]?["collections"] == nil || record["any"]?["collections"]?.array != nil else {
            throw PinkhaHanlinSaveMessageError.conflictingReceipt
        }
        let collections = record["any"]?["collections"]?.array ?? []
        guard collections.allSatisfy({ $0.string != nil }),
              !collections.contains(.string("bin")), !collections.contains(.string("template")) else {
            throw PinkhaHanlinSaveMessageError.conflictingReceipt
        }
        _ = try PinkhaHanlinSaveMessageDocument.rootReadbackSHA256(title: title)
        return title
    }

    public func blockReadbackSHA256(at index: Int) throws -> String {
        guard blocks.indices.contains(index) else { throw PinkhaHanlinSaveMessageError.conflictingReceipt }
        return try PinkhaHanlinSaveMessageDocument.blockReadbackSHA256(blocks[index], at: index)
    }

    public func verifiedBody(manifest: PinkhaHanlinSaveMessageManifest,
                             nativeVersionSHA256: String? = nil,
                             nativeMarkdownSHA256: String? = nil,
                             nativeMarkdownUTF8Bytes: Int? = nil) throws -> PinkhaHanlinSaveMessageBodyReadback {
        let document = try PinkhaHanlinSaveMessageDocument(title: snapshot.title, blocks: blocks)
        let semantic = try document.verifiedReadback(manifest: manifest, objectReference: snapshot.objectID,
            blockReferences: blockReferences, nativeVersionSHA256: nativeVersionSHA256)
        return .init(manifestSHA256: semantic.manifestSHA256, objectReference: semantic.objectReference,
            blockReferences: semantic.blockReferences, nativeReadbackSHA256: semantic.nativeReadbackSHA256,
            nativeVersionSHA256: semantic.nativeVersionSHA256, nativeMarkdownSHA256: nativeMarkdownSHA256,
            nativeMarkdownUTF8Bytes: nativeMarkdownUTF8Bytes)
    }

    public static func semanticBlock(_ row: AnyEditorBlock) throws -> PinkhaHanlinSavedBlock {
        guard row.parentID.isEmpty, let fields = row.native.object,
              Set(fields.keys).isSubset(of: ["id", "type", "text", "style", "nav", "_ver"]),
              let nav = row.native["nav"]?.object, Set(nav.keys) == ["parentId", "pos"] else {
            throw PinkhaHanlinSaveMessageError.unsupportedDocument
        }
        let style = row.native["style"]?.object ?? [:]
        let kind: PinkhaHanlinSavedBlock.Kind
        var level: Int?, number: Int?, checked: Bool?, language: String?
        switch row.type {
        case "paragraph", "quote":
            guard style.isEmpty else { throw PinkhaHanlinSaveMessageError.unsupportedDocument }
            kind = row.type == "paragraph" ? .paragraph : .quote
        case "heading":
            guard Set(style.keys) == ["level"], let value = style["level"]?.integer, (1...3).contains(value) else {
                throw PinkhaHanlinSaveMessageError.unsupportedDocument
            }
            kind = .heading; level = Int(value)
        case "code":
            guard Set(style.keys).isSubset(of: ["lang"]), style["lang"] == nil || style["lang"]?.string != nil else {
                throw PinkhaHanlinSaveMessageError.unsupportedDocument
            }
            kind = .code; language = style["lang"]?.string
        case "list_item":
            guard let ordered = style["ordered"]?.bool else { throw PinkhaHanlinSaveMessageError.unsupportedDocument }
            if ordered {
                guard Set(style.keys) == ["ordered", "number"], let value = style["number"]?.integer,
                      (1...Int64(PinkhaHanlinSaveMessagePlan.maximumBlocks)).contains(value) else {
                    throw PinkhaHanlinSaveMessageError.unsupportedDocument
                }
                kind = .numbered; number = Int(value)
            } else {
                guard Set(style.keys) == ["ordered"] else { throw PinkhaHanlinSaveMessageError.unsupportedDocument }
                kind = .bulleted
            }
        case "check_list_item":
            guard Set(style.keys) == ["checked"], let value = style["checked"]?.bool else {
                throw PinkhaHanlinSaveMessageError.unsupportedDocument
            }
            kind = .checkbox; checked = value
        default: throw PinkhaHanlinSaveMessageError.unsupportedDocument
        }
        let projection = kind == .code ? AnyInlineMarkdown(literal: row.text) : AnyInlineMarkdown(row.text)
        guard projection.isEditable else { throw PinkhaHanlinSaveMessageError.unsupportedDocument }
        let text = try PinkhaHanlinSavedText(text: projection.display, runs: projection.runs.map {
            .init(offset: $0.displayRange.location, length: $0.displayRange.length,
                  traits: .init(rawValue: $0.traits.rawValue), link: $0.link?.absoluteString)
        })
        return try .init(kind: kind, text: text, headingLevel: level, number: number, checked: checked, language: language)
    }
}
