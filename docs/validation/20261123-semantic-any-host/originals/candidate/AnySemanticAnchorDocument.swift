import Foundation
import PinkhaKit

/// A capture is transient UI intent tied to one actual native read/run. The
/// only durable representation is the canonical marker in the block's native
/// inline-Markdown field plus the association's semantic-target metadata.
public struct AnySemanticAnchorCapture: Sendable {
    public let anchor: PinkhaSemanticTextAnchor
    public let blockID: String
    public let replacement: String
    public let expected: PinkhaSemanticText
    private let original: AnyEditorRead
    private let block: AnyEditorBlock

    public init(read: AnyEditorRead, blockID: String, range: NSRange,
                anchor: PinkhaSemanticTextAnchor) throws {
        guard anchor.belongsTo(spaceID: read.snapshot.spaceID, objectID: read.snapshot.objectID),
              read.snapshot.depthFirstIDs.contains(blockID),
              let block = read.snapshot.blocks.first(where: { $0.id == blockID }),
              ["paragraph", "heading", "list_item", "check_list_item", "quote"].contains(block.type) else {
            throw AnyHostError.invalidSelection
        }
        guard try AnySemanticAnchorDocument.resolve(anchor, read: read) == .missing else {
            throw PinkhaSemanticTextAnchorError.selectionAlreadyLinked
        }
        let projection = AnyInlineMarkdown(block.text)
        let replacement = try projection.capturing(anchor, displayRange: range)
        self.anchor = anchor
        self.blockID = blockID
        self.original = read
        self.block = block
        self.replacement = replacement
        self.expected = try AnyInlineMarkdown(replacement).semanticText()
    }

    /// Stale text is never searched for or retargeted by a saved offset. The
    /// existing conditional PATCH also checks this native version at dispatch.
    public func prepare(current: AnyEditorRead, documents: AnyEditorDocumentStore) throws -> AnyPreparedBlockEdit {
        guard current.generation == original.generation,
              current.engineStartedAt.utf8.elementsEqual(original.engineStartedAt.utf8),
              current.nativeVersion.utf8.elementsEqual(original.nativeVersion.utf8),
              current.snapshot.spaceID.utf8.elementsEqual(original.snapshot.spaceID.utf8),
              current.snapshot.objectID.utf8.elementsEqual(original.snapshot.objectID.utf8),
              current.snapshot.dataset == original.snapshot.dataset,
              current.snapshot.depthFirstIDs.contains(blockID),
              let actual = current.snapshot.blocks.first(where: { $0.id == blockID }),
              actual.native == block.native, actual.text.utf8.elementsEqual(block.text.utf8) else {
            throw AnyHostError.changedDocument
        }
        guard try AnySemanticAnchorDocument.resolve(anchor, read: current) == .missing else {
            throw AnyHostError.changedDocument
        }
        return try documents.prepareTextEdit(current, blockID: blockID, inlineMarkdown: replacement)
    }

    public func verifyReadback(_ current: AnyEditorRead) throws {
        guard current.generation == original.generation,
              current.engineStartedAt.utf8.elementsEqual(original.engineStartedAt.utf8),
              current.snapshot.dataset == original.snapshot.dataset,
              anchor.belongsTo(spaceID: current.snapshot.spaceID, objectID: current.snapshot.objectID),
              current.snapshot.depthFirstIDs.contains(blockID),
              let actual = current.snapshot.blocks.first(where: { $0.id == blockID }),
              actual.text.utf8.elementsEqual(replacement.utf8),
              try AnyInlineMarkdown(actual.text).semanticText() == expected else {
            throw AnyHostError.writeUncertain
        }
        // A capture creates exactly one fragment. A copy elsewhere cannot be
        // acknowledged as this new capture, even if the fragment resolver could
        // otherwise interpret adjacent boundary-aligned copies as a split.
        guard case .resolved(let fragments) = try AnySemanticAnchorDocument.resolve(anchor, read: current),
              fragments.count == 1, fragments[0].blockID == blockID,
              fragments[0].range == expected.marks.first(where: { $0.anchor == anchor })?.range else {
            throw AnyHostError.writeUncertain
        }
    }
}

public enum AnySemanticAnchorDocument {
    /// Input must come from the current session's bracketed/authorized native
    /// read. Unreachable/unsupported native copies cannot silently be discarded
    /// to turn a duplicated identity into a seemingly unique selection.
    public static func resolve(_ anchor: PinkhaSemanticTextAnchor,
                               read: AnyEditorRead) throws -> PinkhaSemanticTextAnchorResolver.Resolution {
        let byID = Dictionary(uniqueKeysWithValues: read.snapshot.blocks.map { ($0.id, $0) })
        for id in read.snapshot.unreachableIDs {
            if byID[id]?.text.contains(anchor.markerString) == true { return .ambiguous }
        }
        let blocks = try read.snapshot.depthFirstIDs.map { id -> PinkhaSemanticTextAnchorResolver.Block in
            guard let block = byID[id] else { throw AnyHostError.incompleteDocument }
            let projection = block.type == "code" ? AnyInlineMarkdown(literal: block.text) : AnyInlineMarkdown(block.text)
            if projection.isEditable {
                return .init(id: id, content: try projection.semanticText())
            }
            guard !block.text.lowercased().contains(PinkhaSemanticTextAnchor.markerScheme + ":") else {
                throw AnyHostError.invalidDocument("unsupported semantic marker markup")
            }
            return .init(id: id, content: try .init(text: block.text))
        }
        return try PinkhaSemanticTextAnchorResolver.resolve(anchor,
            spaceID: read.snapshot.spaceID, objectID: read.snapshot.objectID, blocks: blocks)
    }
}
