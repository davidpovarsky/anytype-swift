import Foundation
import AnytypeCore
import Services
import ProtobufMessages
import SwiftProtobuf
import PinkhaHanlinCore

/// Converts the completed ORIGINAL Hanlin AST's canonical semantics through the
/// original Heart BlockInformation converter. No native call or permission is
/// made here. Unsupported fields/formatting are refused before native dispatch.
struct PinkhaHanlinHeartSaveBody: Sendable {
    static let markerField = "pinkhaHanlinSaveMessage"
    static let serializationContract = "pinkha-hanlin-heart-original-block-rpc-v1"
    let document: PinkhaHanlinSaveMessageDocument
    let manifest: PinkhaHanlinSaveMessageManifest
    let blocks: [BlockInformation]

    init(plan: PinkhaHanlinSaveMessagePlan, document: PinkhaHanlinSaveMessageDocument) throws {
        guard document.title.utf8.elementsEqual(plan.title.utf8) else {
            throw PinkhaHanlinSaveMessageError.conflictingReceipt
        }
        var originals: [BlockInformation] = []
        var nativeBytes: [Data] = []
        for (index, semantic) in document.blocks.enumerated() {
            let info = try Self.encode(semantic)
            guard let original = BlockInformationConverter.convert(information: info) else {
                throw PinkhaHanlinSaveMessageError.unsupportedDocument
            }
            let decoded = try Self.decode(original, ordinal: semantic.number, expectedMarker: nil)
            guard try Self.canonical(decoded) == Self.canonical(semantic) else {
                throw PinkhaHanlinSaveMessageError.unsupportedDocument
            }
            guard index < PinkhaHanlinSaveMessagePlan.maximumBlocks else {
                throw PinkhaHanlinSaveMessageError.unsupportedDocument
            }
            originals.append(info)
            nativeBytes.append(try original.serializedData())
        }
        struct Serialization: Encodable { let contract: String; let blocks: [Data] }
        let bytes = try Self.canonical(Serialization(contract: Self.serializationContract, blocks: nativeBytes))
        guard bytes.count <= 1_048_576 else { throw PinkhaHanlinSaveMessageError.unsupportedDocument }
        let manifest = try document.manifest(for: plan,
            nativeSerializationSHA256: PinkhaHanlinCreatePagePlan.digest(bytes))
        self.document = document; self.manifest = manifest
        blocks = try originals.enumerated().map { index, original in
            var fields = original.fields
            fields[Self.markerField] = Self.marker(manifest, index: index).protobufValue
            return BlockInformation(id: "hanlin-save-" + (try manifest.blockMutationID(at: index)),
                content: original.content, backgroundColor: original.backgroundColor,
                horizontalAlignment: original.horizontalAlignment, childrenIds: original.childrenIds,
                configurationData: original.configurationData, fields: fields)
        }
    }

    static func marker(_ manifest: PinkhaHanlinSaveMessageManifest, index: Int) -> String {
        manifest.identitySHA256 + ":" + manifest.bodyPlanSHA256 + ":" + String(index)
    }

    private static func encode(_ semantic: PinkhaHanlinSavedBlock) throws -> BlockInformation {
        guard semantic.parentIndex == nil else { throw PinkhaHanlinSaveMessageError.unsupportedDocument }
        let style: BlockText.Style
        switch semantic.kind {
        case .paragraph: style = .text
        case .heading:
            switch semantic.headingLevel {
            case 1: style = .header
            case 2: style = .header2
            case 3: style = .header3
            default: throw PinkhaHanlinSaveMessageError.unsupportedDocument
            }
        case .quote: style = .quote
        case .code: style = .code
        case .bulleted: style = .bulleted
        case .numbered: style = .numbered
        case .checkbox: style = .checkbox
        }
        var marks = Anytype_Model_Block.Content.Text.Marks()
        for run in semantic.text.runs {
            let attributes: [(PinkhaHanlinSavedText.Traits, Anytype_Model_Block.Content.Text.Mark.TypeEnum)] = [
                (.bold, .bold), (.italic, .italic), (.strike, .strikethrough), (.code, .keyboard)
            ]
            for (trait, type) in attributes where run.traits.contains(trait) {
                if semantic.kind == .code, trait == .code { continue } // The original code-block style supplies it.
                marks.marks.append(.with {
                    $0.range = .with { $0.from = Int32(run.offset); $0.to = Int32(run.offset + run.length) }
                    $0.type = type
                })
            }
            if let link = run.link {
                marks.marks.append(.with {
                    $0.range = .with { $0.from = Int32(run.offset); $0.to = Int32(run.offset + run.length) }
                    $0.type = .link; $0.param = link
                })
            }
        }
        let text = BlockText(text: semantic.text.text, marks: marks, color: nil,
            contentType: style, checked: semantic.checked ?? false, number: semantic.number ?? 1,
            iconEmoji: "", iconImage: "")
        let original = BlockInformation.empty(content: .text(text))
        var fields: BlockFields = [:]
        if let language = semantic.language {
            guard CodeLanguage(rawValue: language) != nil else {
                throw PinkhaHanlinSaveMessageError.unsupportedDocument
            }
            fields[CodeBlockFields.FieldName.codeLanguage] = language.protobufValue
        }
        return BlockInformation(id: original.id, content: original.content,
            backgroundColor: original.backgroundColor, horizontalAlignment: original.horizontalAlignment,
            childrenIds: original.childrenIds, configurationData: original.configurationData, fields: fields)
    }

    /// Decodes actual native protobuf bytes. It never reads the expected
    /// document or fills missing content/style from the original plan.
    static func decode(_ raw: Anytype_Model_Block, ordinal: Int?,
                       expectedMarker: String?) throws -> PinkhaHanlinSavedBlock {
        guard case .text(let text)? = raw.content,
              raw.childrenIds.isEmpty, raw.backgroundColor.isEmpty,
              raw.align == .left, raw.verticalAlign == .top,
              raw.unknownFields == SwiftProtobuf.UnknownStorage(),
              text.unknownFields == SwiftProtobuf.UnknownStorage(),
              text.color.isEmpty, text.iconEmoji.isEmpty, text.iconImage.isEmpty,
              text.marks.marks.count <= 5 * PinkhaHanlinSavedText.maximumRuns,
              Set(raw.fields.fields.keys).isSubset(of: [markerField, CodeBlockFields.FieldName.codeLanguage]) else {
            throw PinkhaHanlinSaveMessageError.unsupportedDocument
        }
        if let expectedMarker {
            guard case .stringValue(let actual)? = raw.fields.fields[markerField]?.kind,
                  actual.utf8.elementsEqual(expectedMarker.utf8) else {
                throw PinkhaHanlinSaveMessageError.conflictingReceipt
            }
        } else if raw.fields.fields[markerField] != nil {
            throw PinkhaHanlinSaveMessageError.conflictingReceipt
        }
        let kind: PinkhaHanlinSavedBlock.Kind
        let level: Int?
        switch text.style {
        case .paragraph: kind = .paragraph; level = nil
        case .header1: kind = .heading; level = 1
        case .header2: kind = .heading; level = 2
        case .header3: kind = .heading; level = 3
        case .quote: kind = .quote; level = nil
        case .code: kind = .code; level = nil
        case .marked: kind = .bulleted; level = nil
        case .numbered: kind = .numbered; level = nil
        case .checkbox: kind = .checkbox; level = nil
        default: throw PinkhaHanlinSaveMessageError.unsupportedDocument
        }
        guard kind == .checkbox || !text.checked else { throw PinkhaHanlinSaveMessageError.unsupportedDocument }
        let language: String?
        if let value = raw.fields.fields[CodeBlockFields.FieldName.codeLanguage] {
            guard kind == .code, case .stringValue(let name)? = value.kind,
                  CodeLanguage(rawValue: name) != nil else {
                throw PinkhaHanlinSaveMessageError.unsupportedDocument
            }
            language = name
        } else { language = nil }
        let savedText = try decodeText(text, implicitCode: kind == .code)
        return try .init(kind: kind, text: savedText, headingLevel: level,
            number: kind == .numbered ? ordinal : nil, checked: kind == .checkbox ? text.checked : nil,
            language: language)
    }

    private static func decodeText(_ text: Anytype_Model_Block.Content.Text,
                                   implicitCode: Bool) throws -> PinkhaHanlinSavedText {
        let count = text.text.utf16.count
        guard text.text.utf8.count <= PinkhaHanlinSaveMessagePlan.maximumMarkdownUTF8Bytes,
              text.marks.unknownFields == SwiftProtobuf.UnknownStorage() else {
            throw PinkhaHanlinSaveMessageError.unsupportedDocument
        }
        struct Change { let trait: Int?; let link: String?; let delta: Int }
        var changes: [Int: [Change]] = [0: []]
        changes[count] = []
        for mark in text.marks.marks {
            let lower = Int(mark.range.from), upper = Int(mark.range.to)
            guard mark.unknownFields == SwiftProtobuf.UnknownStorage(),
                  mark.range.unknownFields == SwiftProtobuf.UnknownStorage(),
                  lower >= 0, upper > lower, upper <= count else {
                throw PinkhaHanlinSaveMessageError.unsupportedDocument
            }
            let trait: Int?
            let link: String?
            switch mark.type {
            case .bold, .italic, .strikethrough, .keyboard:
                guard mark.param.isEmpty else { throw PinkhaHanlinSaveMessageError.unsupportedDocument }
                switch mark.type {
                case .bold: trait = 0
                case .italic: trait = 1
                case .strikethrough: trait = 2
                case .keyboard: trait = 3
                default: throw PinkhaHanlinSaveMessageError.unsupportedDocument
                }
                link = nil
            case .link:
                try PinkhaHanlinSavedText.validateLink(mark.param)
                trait = nil; link = mark.param
            default: throw PinkhaHanlinSaveMessageError.unsupportedDocument
            }
            changes[lower, default: []].append(.init(trait: trait, link: link, delta: 1))
            changes[upper, default: []].append(.init(trait: trait, link: link, delta: -1))
        }
        let points = changes.keys.sorted()
        guard points.count <= 2 * 5 * PinkhaHanlinSavedText.maximumRuns + 2 else {
            throw PinkhaHanlinSaveMessageError.unsupportedDocument
        }
        var runs: [PinkhaHanlinSavedText.Run] = []
        var counts = [0, 0, 0, 0]
        var links: [Data: (value: String, count: Int)] = [:]
        let flags: [PinkhaHanlinSavedText.Traits] = [.bold, .italic, .strike, .code]
        for (lower, upper) in zip(points, points.dropFirst()) where upper > lower {
            for change in changes[lower, default: []] {
                if let trait = change.trait {
                    counts[trait] += change.delta
                    guard counts[trait] >= 0 else { throw PinkhaHanlinSaveMessageError.unsupportedDocument }
                } else if let link = change.link {
                    let key = Data(link.utf8)
                    let total = (links[key]?.count ?? 0) + change.delta
                    guard total >= 0 else { throw PinkhaHanlinSaveMessageError.unsupportedDocument }
                    if total == 0 { links.removeValue(forKey: key) }
                    else { links[key] = (link, total) }
                }
            }
            guard links.count <= 1 else { throw PinkhaHanlinSaveMessageError.unsupportedDocument }
            var traits: PinkhaHanlinSavedText.Traits = implicitCode ? .code : []
            for index in counts.indices where counts[index] > 0 { traits.insert(flags[index]) }
            runs.append(.init(offset: lower, length: upper - lower, traits: traits, link: links.values.first?.value))
        }
        return try .init(text: text.text, runs: runs)
    }

    static func canonical<T: Encodable>(_ value: T) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(value)
    }
}

/// A complete actual Heart Object.Show read. Native header/layout blocks remain
/// native. A body may contain only the exact original flat marked text blocks;
/// unknown children/orphans/content are never hidden from the receipt.
struct PinkhaHanlinHeartSaveReadback {
    let objectReference: String
    let title: String
    let body: [Anytype_Model_Block]

    init(view: Anytype_Model_ObjectView, objectID: String, spaceID: String, typeID: String) throws {
        guard Self.validReference(objectID), view.rootID.utf8.elementsEqual(objectID.utf8), view.type == .page,
              !view.blocks.isEmpty, view.blocks.count <= 256,
              try view.serializedData().count <= 2_097_152 else {
            throw PinkhaHanlinSaveMessageError.conflictingReceipt
        }
        let detailsRows = view.details.filter { $0.id.utf8.elementsEqual(objectID.utf8) }
        guard detailsRows.count == 1, let row = detailsRows.first else {
            throw PinkhaHanlinSaveMessageError.conflictingReceipt
        }
        let details = ObjectDetails(id: row.id, values: row.details.fields)
        guard details.spaceId.utf8.elementsEqual(spaceID.utf8), details.type.utf8.elementsEqual(typeID.utf8),
              details.resolvedLayoutValue == .basic, !details.isDeleted, !details.isArchived,
              !details.isReadonly, !details.isHidden, !details.isTemplate else {
            throw PinkhaHanlinSaveMessageError.conflictingReceipt
        }
        var index: [Data: Anytype_Model_Block] = [:]
        for block in view.blocks {
            guard Self.validReference(block.id), index.updateValue(block, forKey: Data(block.id.utf8)) == nil else {
                throw PinkhaHanlinSaveMessageError.conflictingReceipt
            }
        }
        guard let root = index[Data(objectID.utf8)], case .smartblock? = root.content,
              root.childrenIds.first?.utf8.elementsEqual("header".utf8) == true,
              let header = index[Data("header".utf8)], case .layout? = header.content else {
            throw PinkhaHanlinSaveMessageError.unsupportedDocument
        }
        var pending = [objectID], seen = Set<Data>()
        while let id = pending.popLast() {
            let key = Data(id.utf8)
            guard seen.insert(key).inserted, let block = index[key] else {
                throw PinkhaHanlinSaveMessageError.conflictingReceipt
            }
            pending.append(contentsOf: block.childrenIds)
        }
        guard seen.count == index.count else { throw PinkhaHanlinSaveMessageError.conflictingReceipt }
        pending = ["header"]
        while let id = pending.popLast() {
            guard let block = index[Data(id.utf8)] else { throw PinkhaHanlinSaveMessageError.conflictingReceipt }
            switch block.content {
            case .layout?: break
            case .text(let text)?:
                guard text.style == .title || (text.style == .description_ && text.text.isEmpty) else {
                    throw PinkhaHanlinSaveMessageError.unsupportedDocument
                }
            case .featuredRelations?, .relation?, .icon?: break
            default: throw PinkhaHanlinSaveMessageError.unsupportedDocument
            }
            pending.append(contentsOf: block.childrenIds)
        }
        let body = try root.childrenIds.dropFirst().map { id in
            guard let block = index[Data(id.utf8)], block.childrenIds.isEmpty else {
                throw PinkhaHanlinSaveMessageError.unsupportedDocument
            }
            return block
        }
        guard body.count <= PinkhaHanlinSaveMessagePlan.maximumBlocks else {
            throw PinkhaHanlinSaveMessageError.unsupportedDocument
        }
        self.objectReference = objectID; self.title = details.name; self.body = body
    }

    func rootReadbackSHA256() throws -> String {
        try PinkhaHanlinSaveMessageDocument.rootReadbackSHA256(title: title)
    }

    func verifyPrefix(_ plan: PinkhaHanlinHeartSaveBody, count: Int) throws -> [String] {
        guard body.count == count, (0...plan.blocks.count).contains(count),
              try rootReadbackSHA256() == plan.manifest.expectedRootReadbackSHA256 else {
            throw PinkhaHanlinSaveMessageError.conflictingReceipt
        }
        var previousNumber = 0
        for (index, raw) in body.enumerated() {
            previousNumber = raw.text.style == .numbered ? previousNumber + 1 : 0
            let block = try PinkhaHanlinHeartSaveBody.decode(raw,
                ordinal: previousNumber == 0 ? nil : previousNumber,
                expectedMarker: PinkhaHanlinHeartSaveBody.marker(plan.manifest, index: index))
            guard try PinkhaHanlinSaveMessageDocument.blockReadbackSHA256(block, at: index)
                    == plan.manifest.blockSHA256[index] else {
                throw PinkhaHanlinSaveMessageError.conflictingReceipt
            }
        }
        return body.map(\.id)
    }

    func verifiedBody(_ plan: PinkhaHanlinHeartSaveBody) throws -> PinkhaHanlinSaveMessageBodyReadback {
        let references = try verifyPrefix(plan, count: plan.blocks.count)
        var number = 0
        let blocks = try body.enumerated().map { index, raw in
            number = raw.text.style == .numbered ? number + 1 : 0
            return try PinkhaHanlinHeartSaveBody.decode(raw, ordinal: number == 0 ? nil : number,
                expectedMarker: PinkhaHanlinHeartSaveBody.marker(plan.manifest, index: index))
        }
        let actual = try PinkhaHanlinSaveMessageDocument(title: title, blocks: blocks)
        return try actual.verifiedReadback(manifest: plan.manifest,
            objectReference: objectReference, blockReferences: references)
    }

    func blockReadbackSHA256(at index: Int, plan: PinkhaHanlinHeartSaveBody) throws -> String {
        guard body.indices.contains(index), plan.manifest.blockSHA256.indices.contains(index) else {
            throw PinkhaHanlinSaveMessageError.invalidProgress
        }
        var number = 0
        for raw in body.prefix(index + 1) { number = raw.text.style == .numbered ? number + 1 : 0 }
        let actual = try PinkhaHanlinHeartSaveBody.decode(body[index], ordinal: number == 0 ? nil : number,
            expectedMarker: PinkhaHanlinHeartSaveBody.marker(plan.manifest, index: index))
        return try PinkhaHanlinSaveMessageDocument.blockReadbackSHA256(actual, at: index)
    }

    private static func validReference(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 256 &&
            value.unicodeScalars.allSatisfy { !CharacterSet.controlCharacters.contains($0) }
    }
}
