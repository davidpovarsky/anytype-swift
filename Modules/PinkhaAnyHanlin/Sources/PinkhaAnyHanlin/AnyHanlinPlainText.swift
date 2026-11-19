import Foundation
import HanlinHostContracts
import PinkhaHanlinCore
import PinkhaAnyHost

/// Converts native inline Markdown through the exact projection used by the
/// editor. Block-looking punctuation, whitespace and Unicode remain visible
/// characters; no document-level Markdown parser can reinterpret them.
/// Unsupported inline syntax fails the read explicitly. Native code blocks
/// already contain literal text and remain unchanged.
public enum AnyHanlinPlainText {
    public static func project(_ snapshot: AnyEditorSnapshot, selection: [String]) throws -> PinkhaHanlinTextSnapshot {
        let bounded = try snapshot.boundedText(selection: selection)
        let types = Dictionary(uniqueKeysWithValues: snapshot.blocks.map { ($0.id, $0.type) })
        var total = 0
        let blocks: [PinkhaHanlinTextSnapshot.Block] = try bounded.blocks.map { block in
            let text = try render(block.inlineMarkdown, literalCode: types[block.reference] == "code")
            total += text.utf8.count
            guard total <= 24_576 else { throw HanlinHostError.outputLimitExceeded }
            return .init(reference: block.reference, text: text)
        }
        return .init(objectReference: bounded.objectReference, spaceReference: bounded.spaceReference,
                     sourceRevision: bounded.sourceRevision, title: bounded.title, blocks: blocks,
                     coverage: selection.isEmpty ? "documentTextBlocksOnly" : "selectedTextBlocksOnly")
    }

    public static func render(_ source: String, literalCode: Bool = false) throws -> String {
        guard source.utf8.count <= 24_576 else { throw HanlinHostError.outputLimitExceeded }
        if literalCode { return source }
        let projection = AnyInlineMarkdown(source)
        guard projection.isEditable else { throw HanlinHostError.invalidRecord }
        guard projection.display.utf8.count <= 24_576 else { throw HanlinHostError.outputLimitExceeded }
        return projection.display
    }
}
