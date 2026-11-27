import Foundation

/// Canonical, in-memory semantics shared by conversion and native readback.
/// Document content is never written to the protected metadata journal.
public struct PinkhaHanlinSavedText: Encodable, Equatable, Sendable {
    public struct Traits: OptionSet, Encodable, Equatable, Sendable {
        public let rawValue: UInt8
        public init(rawValue: UInt8) { self.rawValue = rawValue }
        public static let bold = Self(rawValue: 1)
        public static let italic = Self(rawValue: 2)
        public static let strike = Self(rawValue: 4)
        public static let code = Self(rawValue: 8)
    }

    public struct Run: Encodable, Equatable, Sendable {
        public let offset: Int
        public let length: Int
        public let traits: Traits
        public let link: String?

        public init(offset: Int, length: Int, traits: Traits = [], link: String? = nil) {
            self.offset = offset; self.length = length; self.traits = traits; self.link = link
        }
    }

    public static let maximumRuns = 4_096
    public let text: String
    /// Complete, contiguous UTF-16 coverage. Adjacent equal attributes coalesce;
    /// raw source ranges and redundant native mark segmentation do not affect a digest.
    public let runs: [Run]

    public init(text: String, runs: [Run]) throws {
        guard text.utf8.count <= PinkhaHanlinSaveMessagePlan.maximumMarkdownUTF8Bytes,
              runs.count <= PinkhaHanlinSaveMessagePlan.maximumMarkdownUTF8Bytes else {
            throw PinkhaHanlinSaveMessageError.unsupportedDocument
        }
        let units = Array(text.utf16)
        var next = 0
        var normalized: [Run] = []
        func isBoundary(_ offset: Int) -> Bool {
            offset == 0 || offset == units.count ||
                !(0xD800...0xDBFF).contains(units[offset - 1]) ||
                !(0xDC00...0xDFFF).contains(units[offset])
        }
        for run in runs {
            guard run.offset == next, run.length > 0, run.length <= units.count - next,
                  run.traits.rawValue & ~UInt8(15) == 0,
                  isBoundary(next), isBoundary(next + run.length) else {
                throw PinkhaHanlinSaveMessageError.unsupportedDocument
            }
            if let link = run.link { try Self.validateLink(link) }
            if let last = normalized.last, last.traits == run.traits,
               Self.equalLink(last.link, run.link) {
                normalized[normalized.count - 1] = .init(offset: last.offset,
                    length: last.length + run.length, traits: last.traits, link: last.link)
            } else {
                normalized.append(run)
            }
            next += run.length
        }
        guard next == units.count, normalized.count <= Self.maximumRuns else {
            throw PinkhaHanlinSaveMessageError.unsupportedDocument
        }
        self.text = text; self.runs = normalized
    }

    public static func plain(_ text: String, code: Bool = false) throws -> Self {
        try .init(text: text, runs: text.isEmpty ? [] : [
            .init(offset: 0, length: text.utf16.count, traits: code ? .code : [])
        ])
    }

    public static func validateLink(_ link: String) throws {
        guard !link.isEmpty, link.utf8.count <= 2_048,
              link.unicodeScalars.allSatisfy({ !CharacterSet.controlCharacters.contains($0) }),
              let url = URL(string: link), let scheme = url.scheme?.lowercased(),
              ["http", "https"].contains(scheme),
              url.absoluteString.utf8.elementsEqual(link.utf8),
              !(url.host ?? "").isEmpty else {
            // Citation, app, semantic-anchor, relative, and normalization-dependent
            // links require a separate qualified mapping; they are not plain text.
            throw PinkhaHanlinSaveMessageError.unsupportedDocument
        }
    }

    private static func equalLink(_ lhs: String?, _ rhs: String?) -> Bool {
        switch (lhs, rhs) {
        case (nil, nil): true
        case (.some(let lhs), .some(let rhs)): lhs.utf8.elementsEqual(rhs.utf8)
        default: false
        }
    }
}

public struct PinkhaHanlinSavedBlock: Encodable, Equatable, Sendable {
    public enum Kind: String, Encodable, Sendable {
        case paragraph, heading, quote, code, bulleted, numbered, checkbox
    }

    public let kind: Kind
    public let text: PinkhaHanlinSavedText
    public let headingLevel: Int?
    public let number: Int?
    public let checked: Bool?
    public let language: String?
    /// Version 1 accepts only root-level blocks. Keeping this explicit prevents
    /// a native reader from silently flattening unsupported hierarchy.
    public let parentIndex: Int?

    public init(kind: Kind, text: PinkhaHanlinSavedText, headingLevel: Int? = nil,
                number: Int? = nil, checked: Bool? = nil, language: String? = nil,
                parentIndex: Int? = nil) throws {
        guard parentIndex == nil,
              (kind == .heading ? headingLevel.map({ (1...3).contains($0) }) == true : headingLevel == nil),
              (kind == .numbered ? number.map({ (1...PinkhaHanlinSaveMessagePlan.maximumBlocks).contains($0) }) == true : number == nil),
              (kind == .checkbox ? checked != nil : checked == nil),
              kind == .code || language == nil else {
            throw PinkhaHanlinSaveMessageError.unsupportedDocument
        }
        if let language {
            guard !language.isEmpty, language.utf8.count <= 256,
                  language.unicodeScalars.allSatisfy({ !CharacterSet.whitespacesAndNewlines.contains($0) &&
                    !CharacterSet.controlCharacters.contains($0) }) else {
                throw PinkhaHanlinSaveMessageError.unsupportedDocument
            }
        }
        if kind == .code {
            guard text.runs.allSatisfy({ $0.traits == .code && $0.link == nil }) else {
                throw PinkhaHanlinSaveMessageError.unsupportedDocument
            }
        }
        self.kind = kind; self.text = text; self.headingLevel = headingLevel
        self.number = number; self.checked = checked; self.language = language; self.parentIndex = parentIndex
    }
}

public struct PinkhaHanlinSaveMessageDocument: Encodable, Equatable, Sendable {
    public static let semanticContract = "pinkha-hanlin-saved-document-semantics-v1"
    public let contract: String
    public let title: String
    public let blocks: [PinkhaHanlinSavedBlock]

    public init(title: String, blocks: [PinkhaHanlinSavedBlock]) throws {
        guard !title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              title.utf8.count <= PinkhaHanlinSaveMessagePlan.maximumTitleUTF8Bytes,
              (1...PinkhaHanlinSaveMessagePlan.maximumBlocks).contains(blocks.count),
              blocks.reduce(0, { $0 + $1.text.text.utf8.count }) <= PinkhaHanlinSaveMessagePlan.maximumMarkdownUTF8Bytes,
              blocks.reduce(0, { $0 + $1.text.runs.count }) <= PinkhaHanlinSavedText.maximumRuns else {
            throw PinkhaHanlinSaveMessageError.unsupportedDocument
        }
        var previousNumber = 0
        for block in blocks {
            if block.kind == .numbered {
                guard block.number == previousNumber + 1 else {
                    throw PinkhaHanlinSaveMessageError.unsupportedDocument
                }
                previousNumber += 1
            } else { previousNumber = 0 }
        }
        contract = Self.semanticContract; self.title = title; self.blocks = blocks
    }

    public func rootReadbackSHA256() throws -> String {
        try Self.rootReadbackSHA256(title: title)
    }

    public static func rootReadbackSHA256(title: String) throws -> String {
        guard !title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              title.utf8.count <= PinkhaHanlinSaveMessagePlan.maximumTitleUTF8Bytes else {
            throw PinkhaHanlinSaveMessageError.unsupportedDocument
        }
        struct Root: Encodable { let contract: String; let kind: String; let title: String }
        return PinkhaHanlinSaveMessagePlan.digest(try PinkhaHanlinSaveMessagePlan.canonicalBytes(
            Root(contract: Self.semanticContract + "/root", kind: "page", title: title)))
    }

    public func blockReadbackSHA256(at index: Int) throws -> String {
        guard blocks.indices.contains(index) else { throw PinkhaHanlinSaveMessageError.invalidProgress }
        return try Self.blockReadbackSHA256(blocks[index], at: index)
    }

    public static func blockReadbackSHA256(_ block: PinkhaHanlinSavedBlock, at index: Int) throws -> String {
        guard (0..<PinkhaHanlinSaveMessagePlan.maximumBlocks).contains(index) else {
            throw PinkhaHanlinSaveMessageError.invalidProgress
        }
        struct Block: Encodable { let contract: String; let index: Int; let block: PinkhaHanlinSavedBlock }
        return PinkhaHanlinSaveMessagePlan.digest(try PinkhaHanlinSaveMessagePlan.canonicalBytes(
            Block(contract: Self.semanticContract + "/block", index: index, block: block)))
    }

    public func bodyReadbackSHA256() throws -> String { try digest(self) }

    /// The body plan binds the native serialization as well as its semantics.
    /// Reconciliation reuses this manifest and the original mutation IDs.
    public func manifest(for plan: PinkhaHanlinSaveMessagePlan,
                         nativeSerializationSHA256: String,
                         bodyMode: PinkhaHanlinSaveMessageBodyMode? = nil) throws -> PinkhaHanlinSaveMessageManifest {
        guard title.utf8.elementsEqual(plan.title.utf8),
              PinkhaHanlinWriteIdentity.isDigest(nativeSerializationSHA256) else {
            throw PinkhaHanlinSaveMessageError.conflictingReceipt
        }
        struct Material: Encodable {
            let contract: String; let semanticSHA256: String; let nativeSerializationSHA256: String
        }
        let body = try bodyReadbackSHA256()
        return try .init(plan: plan, bodyPlanSHA256: digest(Material(
            contract: bodyMode == nil ? PinkhaHanlinSaveMessageManifest.conversionContract :
                PinkhaHanlinSaveMessageManifest.conditionalMarkdownContract,
            semanticSHA256: body, nativeSerializationSHA256: nativeSerializationSHA256)),
            expectedRootReadbackSHA256: rootReadbackSHA256(), expectedBodyReadbackSHA256: body,
            blockSHA256: blocks.indices.map { try blockReadbackSHA256(at: $0) }, bodyMode: bodyMode)
    }

    /// Call only with a document rebuilt from the actual current native root
    /// and ALL ordered body rows, never with the expected conversion as a substitute.
    public func verifiedReadback(manifest: PinkhaHanlinSaveMessageManifest,
                                 objectReference: String,
                                 blockReferences: [String],
                                 nativeVersionSHA256: String? = nil) throws -> PinkhaHanlinSaveMessageBodyReadback {
        try manifest.validate()
        guard PinkhaHanlinSaveMessagePlan.validReference(objectReference),
              blockReferences.count == blocks.count,
              blockReferences.allSatisfy(PinkhaHanlinSaveMessagePlan.validReference),
              Set(blockReferences.map { Data($0.utf8) }).count == blockReferences.count,
              !blockReferences.contains(where: { $0.utf8.elementsEqual(objectReference.utf8) }),
              (manifest.bodyMode == nil ? nativeVersionSHA256 == nil :
                nativeVersionSHA256.map(PinkhaHanlinWriteIdentity.isDigest) == true),
              try rootReadbackSHA256() == manifest.expectedRootReadbackSHA256,
              try bodyReadbackSHA256() == manifest.expectedBodyReadbackSHA256,
              try blocks.indices.map({ try blockReadbackSHA256(at: $0) }) == manifest.blockSHA256 else {
            throw PinkhaHanlinSaveMessageError.conflictingReceipt
        }
        return try .init(manifestSHA256: manifest.canonicalSHA256(), objectReference: objectReference,
            blockReferences: blockReferences, nativeReadbackSHA256: bodyReadbackSHA256(),
            nativeVersionSHA256: nativeVersionSHA256)
    }

    private func digest<T: Encodable>(_ value: T) throws -> String {
        PinkhaHanlinSaveMessagePlan.digest(try PinkhaHanlinSaveMessagePlan.canonicalBytes(value))
    }
}
