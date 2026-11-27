import Foundation
import Markdown
import PinkhaHanlinCore
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration

/// Uses the original Hanlin parser's completed AST. This is a downstream
/// persistence conversion, not a replacement Markdown parser or native authority.
public struct PinkhaHanlinMarkdownSaveConversion: Sendable {
    public static let hanlinMarkdownRevision = "5cbb4b6c950051f98f02a0b0ae56756f5174a9b8"
    public static let swiftMarkdownRevision = "25cb61d3482054b09ae76ca4f281b1bfe7fe5a43"
    public static let originalParserBlob = "17c3e2302f18d183048f38ab200c0d6c5824e9aa"

    public struct NativeBlock: Sendable {
        public let semantic: PinkhaHanlinSavedBlock
        public let type: String
        public let text: String
        public let style: AnyJSON
        public let position: String
    }

    public let document: PinkhaHanlinSaveMessageDocument
    public let blocks: [NativeBlock]
    public let manifest: PinkhaHanlinSaveMessageManifest

    /// `originalDocument` and the two provenance fields must come from ONE
    /// original MarkdownParserImpl.parse result. Never reconstruct them from
    /// tool JSON, a renderer's plainText, or a speculative streaming preview.
    public init(plan: PinkhaHanlinSaveMessagePlan, originalDocument: Markdown.Document,
                originalSourceText: String?, speculativeRewritten: Bool,
                citationMarker: String, citationMarkerQueryParam: String) throws {
        guard !speculativeRewritten,
              let originalSourceText, originalSourceText.utf8.elementsEqual(plan.markdown.utf8),
              !citationMarker.isEmpty, citationMarker.utf8.count <= 256,
              !citationMarkerQueryParam.isEmpty, citationMarkerQueryParam.utf8.count <= 256 else {
            // In particular, original LaTeX preprocessing changes source bytes.
            // Refuse it until native math persistence is separately qualified.
            throw PinkhaHanlinSaveMessageError.unsupportedDocument
        }
        var builder = Builder(citationMarker: citationMarker, citationMarkerQueryParam: citationMarkerQueryParam)
        for child in originalDocument.children { try builder.append(child) }
        let document = try PinkhaHanlinSaveMessageDocument(title: plan.title, blocks: builder.rows.map(\.semantic))
        let serialization: AnyJSON = .object([
            "contract": .string(PinkhaHanlinSaveMessageManifest.conversionContract),
            "hanlinMarkdownRevision": .string(Self.hanlinMarkdownRevision),
            "swiftMarkdownRevision": .string(Self.swiftMarkdownRevision),
            "originalParserBlob": .string(Self.originalParserBlob),
            "citationMarker": .string(citationMarker), "citationMarkerQueryParam": .string(citationMarkerQueryParam),
            "blocks": .array(builder.rows.map { .object([
                "type": .string($0.type), "text": .string($0.text), "style": $0.style,
                "parentIndex": .null, "position": .string($0.position)
            ]) })
        ])
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let bytes = try encoder.encode(serialization)
        guard bytes.count <= 262_144 else { throw PinkhaHanlinSaveMessageError.unsupportedDocument }
        self.manifest = try document.manifest(for: plan,
            nativeSerializationSHA256: PinkhaHanlinCreatePagePlan.digest(bytes))
        self.document = document; self.blocks = builder.rows
    }

    private struct Inline {
        var source = ""
        var text = ""
        var runs: [PinkhaHanlinSavedText.Run] = []

        mutating func append(_ value: String, source: String,
                             traits: PinkhaHanlinSavedText.Traits, link: String?) throws {
            guard text.utf8.count + value.utf8.count <= PinkhaHanlinSaveMessagePlan.maximumMarkdownUTF8Bytes,
                  self.source.utf8.count + source.utf8.count <= PinkhaHanlinSaveMessagePlan.maximumMarkdownUTF8Bytes else {
                throw PinkhaHanlinSaveMessageError.unsupportedDocument
            }
            if !value.isEmpty { runs.append(.init(offset: text.utf16.count, length: value.utf16.count,
                                                 traits: traits, link: link)) }
            text += value; self.source += source
        }

        mutating func append(_ other: Inline) throws {
            guard text.utf8.count + other.text.utf8.count <= PinkhaHanlinSaveMessagePlan.maximumMarkdownUTF8Bytes,
                  source.utf8.count + other.source.utf8.count <= PinkhaHanlinSaveMessagePlan.maximumMarkdownUTF8Bytes else {
                throw PinkhaHanlinSaveMessageError.unsupportedDocument
            }
            let offset = text.utf16.count
            runs += other.runs.map { .init(offset: offset + $0.offset, length: $0.length, traits: $0.traits, link: $0.link) }
            source += other.source; text += other.text
        }
    }

    private struct Builder {
        let citationMarker: String
        let citationMarkerQueryParam: String
        var rows: [NativeBlock] = []

        mutating func append(_ node: any Markup) throws {
            switch node {
            case let paragraph as Paragraph:
                try appendInline(paragraph, kind: .paragraph)
            case let heading as Heading:
                try appendInline(heading, kind: .heading, level: heading.level)
            case let quote as BlockQuote:
                guard quote.childCount == 1, let paragraph = quote.child(at: 0) as? Paragraph else {
                    throw PinkhaHanlinSaveMessageError.unsupportedDocument
                }
                try appendInline(paragraph, kind: .quote)
            case let code as CodeBlock:
                let language = code.language.flatMap { $0.isEmpty ? nil : $0 }
                guard language?.hasPrefix("hanlin-math-") != true else {
                    throw PinkhaHanlinSaveMessageError.unsupportedDocument
                }
                let semantic = try PinkhaHanlinSavedBlock(kind: .code,
                    text: .plain(code.code, code: true), language: language)
                try add(semantic, source: code.code)
            case let list as UnorderedList:
                for child in list.children {
                    guard let item = child as? ListItem, item.childCount == 1,
                          let paragraph = item.child(at: 0) as? Paragraph else {
                        throw PinkhaHanlinSaveMessageError.unsupportedDocument
                    }
                    switch item.checkbox {
                    case .checked?: try appendInline(paragraph, kind: .checkbox, checked: true)
                    case .unchecked?: try appendInline(paragraph, kind: .checkbox, checked: false)
                    case nil: try appendInline(paragraph, kind: .bulleted)
                    }
                }
            case let list as OrderedList:
                guard list.startIndex == 1 else { throw PinkhaHanlinSaveMessageError.unsupportedDocument }
                for (index, child) in list.children.enumerated() {
                    guard let item = child as? ListItem, item.checkbox == nil, item.childCount == 1,
                          let paragraph = item.child(at: 0) as? Paragraph else {
                        throw PinkhaHanlinSaveMessageError.unsupportedDocument
                    }
                    try appendInline(paragraph, kind: .numbered, number: index + 1)
                }
            default:
                // Tables, images, raw HTML, embedded/directive nodes, thematic
                // breaks, nested containers and unknown future nodes are refused.
                throw PinkhaHanlinSaveMessageError.unsupportedDocument
            }
        }

        mutating func appendInline(_ node: any Markup, kind: PinkhaHanlinSavedBlock.Kind,
                                   level: Int? = nil, number: Int? = nil, checked: Bool? = nil) throws {
            let inline = try children(node, traits: [], link: nil, depth: 0)
            let expected = try PinkhaHanlinSavedText(text: inline.text, runs: inline.runs)
            let projection = AnyInlineMarkdown(inline.source)
            guard projection.isEditable else { throw PinkhaHanlinSaveMessageError.unsupportedDocument }
            let projected = try PinkhaHanlinSavedText(text: projection.display, runs: projection.runs.map {
                .init(offset: $0.displayRange.location, length: $0.displayRange.length,
                      traits: .init(rawValue: $0.traits.rawValue), link: $0.link?.absoluteString)
            })
            // Compare the complete canonical form, not visible text alone.
            let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
            guard try encoder.encode(projected) == encoder.encode(expected) else {
                throw PinkhaHanlinSaveMessageError.unsupportedDocument
            }
            try add(.init(kind: kind, text: expected, headingLevel: level, number: number, checked: checked),
                    source: inline.source)
        }

        mutating func add(_ semantic: PinkhaHanlinSavedBlock, source: String) throws {
            guard rows.count < PinkhaHanlinSaveMessagePlan.maximumBlocks,
                  source.utf8.count <= PinkhaHanlinSaveMessagePlan.maximumMarkdownUTF8Bytes else {
                throw PinkhaHanlinSaveMessageError.unsupportedDocument
            }
            let type: String
            var style: [String: AnyJSON] = [:]
            switch semantic.kind {
            case .paragraph: type = "paragraph"
            case .heading: type = "heading"; style["level"] = .integer(Int64(semantic.headingLevel!))
            case .quote: type = "quote"
            case .code:
                type = "code"
                if let language = semantic.language { style["lang"] = .string(language) }
            case .bulleted: type = "list_item"; style["ordered"] = .bool(false)
            case .numbered:
                type = "list_item"; style["ordered"] = .bool(true)
                style["number"] = .integer(Int64(semantic.number!))
            case .checkbox: type = "check_list_item"; style["checked"] = .bool(semantic.checked!)
            }
            let position = try AnyLexicographicPosition.between(after: rows.last?.position, before: nil)
            rows.append(.init(semantic: semantic, type: type, text: source, style: .object(style), position: position))
        }

        func children(_ node: any Markup, traits: PinkhaHanlinSavedText.Traits,
                      link: String?, depth: Int) throws -> Inline {
            guard depth <= 24 else { throw PinkhaHanlinSaveMessageError.unsupportedDocument }
            var result = Inline()
            for child in node.children { try result.append(inline(child, traits: traits, link: link, depth: depth + 1)) }
            return result
        }

        func inline(_ node: any Markup, traits: PinkhaHanlinSavedText.Traits,
                    link: String?, depth: Int) throws -> Inline {
            guard depth <= 24 else { throw PinkhaHanlinSaveMessageError.unsupportedDocument }
            var result = Inline()
            switch node {
            case let text as Markdown.Text:
                try result.append(text.string, source: AnyInlineMarkdown.escapeLiteral(text.string), traits: traits, link: link)
            case is SoftBreak, is LineBreak:
                // This matches the original Hanlin renderer's conversion of BOTH
                // node types; their presentation is one newline, not a space.
                try result.append("\n", source: "\n", traits: traits, link: link)
            case let code as InlineCode:
                guard !code.code.isEmpty, !code.code.contains("`"), !code.code.contains("\n"),
                      !code.code.hasPrefix(" "), !code.code.hasSuffix(" "),
                      !code.code.hasPrefix("<hanlin-math-") else {
                    throw PinkhaHanlinSaveMessageError.unsupportedDocument
                }
                try result.append(code.code, source: "`" + code.code + "`", traits: traits.union(.code), link: link)
            case is Strong:
                result = try children(node, traits: traits.union(.bold), link: link, depth: depth)
                result.source = "**" + result.source + "**"
            case is Emphasis:
                result = try children(node, traits: traits.union(.italic), link: link, depth: depth)
                // Different delimiters permit original nested bold+italic while
                // the destination's full projection remains the final guard.
                result.source = "_" + result.source + "_"
            case is Strikethrough:
                result = try children(node, traits: traits.union(.strike), link: link, depth: depth)
                result.source = "~~" + result.source + "~~"
            case let original as Link:
                guard link == nil, original.title == nil, let destination = original.destination else {
                    throw PinkhaHanlinSaveMessageError.unsupportedDocument
                }
                try PinkhaHanlinSavedText.validateLink(destination)
                if original.plainText.utf8.elementsEqual(citationMarker.utf8),
                   URLComponents(string: destination)?.queryItems?.contains(where: {
                       $0.name.utf8.elementsEqual(citationMarkerQueryParam.utf8) && $0.value?.utf8.elementsEqual(citationMarker.utf8) == true
                   }) == true { throw PinkhaHanlinSaveMessageError.unsupportedDocument }
                result = try children(original, traits: traits, link: destination, depth: depth)
                result.source = "[" + result.source + "](" + destination + ")"
            default:
                throw PinkhaHanlinSaveMessageError.unsupportedDocument
            }
            guard result.source.utf8.count <= PinkhaHanlinSaveMessagePlan.maximumMarkdownUTF8Bytes else {
                throw PinkhaHanlinSaveMessageError.unsupportedDocument
            }
            return result
        }
    }
}
