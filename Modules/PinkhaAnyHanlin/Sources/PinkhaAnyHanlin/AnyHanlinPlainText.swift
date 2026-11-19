import Foundation
import Markdown
import HanlinHostContracts
import PinkhaHanlinCore
import PinkhaAnyHost

/// Converts native inline Markdown to the existing SDK's plain-text contract.
/// The pinned CommonMark parser handles escapes, entities and nested inline
/// formatting. Raw HTML/custom directives are rejected rather than leaked as
/// alleged visible text. Code blocks are already literal native text.
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
        let document = Document(parsing: source, options: [.disableSmartOpts])
        enum Item { case node(any Markup, Int); case separator(String) }
        var stack: [Item] = [.node(document, 0)]
        var result = ""
        var count = 0
        func append(_ value: String) throws {
            guard result.utf8.count + value.utf8.count <= 24_576 else {
                throw HanlinHostError.outputLimitExceeded
            }
            result.append(value)
        }
        while let item = stack.popLast() {
            switch item {
            case .separator(let value):
                try append(value)
            case .node(let node, let depth):
                count += 1
                guard depth <= 128, count <= 8_192 else { throw HanlinHostError.outputLimitExceeded }
                if let text = node as? Markdown.Text { try append(text.string); continue }
                if let code = node as? InlineCode { try append(code.code); continue }
                if let code = node as? CodeBlock { try append(code.code); continue }
                if node is SoftBreak || node is LineBreak { try append("\n"); continue }
                if node is ThematicBreak { try append("\n"); continue }
                guard node is Document || node is Paragraph || node is Heading ||
                      node is Emphasis || node is Strong || node is Strikethrough ||
                      node is Link || node is Image || node is BlockQuote ||
                      node is OrderedList || node is UnorderedList || node is ListItem else {
                    throw HanlinHostError.invalidRecord
                }
                let children = Array(node.children)
                let separatesBlocks = node is Document || node is BlockQuote ||
                    node is OrderedList || node is UnorderedList || node is ListItem
                for index in children.indices.reversed() {
                    stack.append(.node(children[index], depth + 1))
                    if separatesBlocks && index > 0 { stack.append(.separator("\n")) }
                }
            }
        }
        return result
    }
}
