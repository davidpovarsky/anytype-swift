import Foundation
import TorahInspectorCore

/// A lossless, Sendable representation of an arbitrary JSON value.
public enum TorahJSONValue: Codable, Sendable, Equatable, Hashable {
    case null
    case bool(Bool)
    case number(Double)
    case string(String)
    case array([TorahJSONValue])
    case object([String: TorahJSONValue])

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() { self = .null }
        else if let value = try? container.decode(Bool.self) { self = .bool(value) }
        else if let value = try? container.decode(Double.self) { self = .number(value) }
        else if let value = try? container.decode(String.self) { self = .string(value) }
        else if let value = try? container.decode([TorahJSONValue].self) { self = .array(value) }
        else { self = .object(try container.decode([String: TorahJSONValue].self)) }
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .null: try container.encodeNil()
        case .bool(let value): try container.encode(value)
        case .number(let value): try container.encode(value)
        case .string(let value): try container.encode(value)
        case .array(let value): try container.encode(value)
        case .object(let value): try container.encode(value)
        }
    }
}

/// Semantic kind of Torah association.
public enum TorahAssociationKind: String, Codable, Sendable, CaseIterable {
    case ref
    case topic
    case word
}

/// Role/intent of the Torah association.
public enum TorahAssociationRole: String, Sendable, CaseIterable {
    case context
    case sourceQuote
}

extension TorahAssociationRole: Codable {
    public init(from decoder: Decoder) throws {
        let value = try decoder.singleValueContainer().decode(String.self)
        switch value {
        case Self.context.rawValue: self = .context
        case Self.sourceQuote.rawValue, "source_quote": self = .sourceQuote
        default:
            throw DecodingError.dataCorruptedError(
                in: try decoder.singleValueContainer(),
                debugDescription: "Unknown Torah association role: \(value)"
            )
        }
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        try container.encode(rawValue)
    }
}

/// Target of an association: entire object or a specific block.
public enum TorahAssociationTarget: Codable, Sendable, Equatable, Hashable {
    case object(objectId: String)
    case block(objectId: String, blockId: String)

    public var objectId: String {
        switch self {
        case .object(let id): id
        case .block(let id, _): id
        }
    }

    public var blockId: String? {
        switch self {
        case .object: nil
        case .block(_, let blockId): blockId
        }
    }
}

/// A single Torah association item. Optional provenance is never fabricated while decoding.
public struct TorahAssociationItem: Codable, Sendable, Identifiable, Equatable, Hashable {
    public var id: String
    public var kind: TorahAssociationKind
    public var role: TorahAssociationRole
    public var providerID: String
    public var externalID: String
    public var canonicalKey: String
    public var labelHe: String
    public var labelEn: String?
    public var rawInput: String?
    public var providerPayload: String?
    public var createdAt: Date?
    public var updatedAt: Date?
    public var customMetadata: [String: String]?
    public var unknownFields: [String: TorahJSONValue]

    public init(
        id: String = UUID().uuidString,
        kind: TorahAssociationKind,
        role: TorahAssociationRole,
        providerID: String,
        externalID: String,
        canonicalKey: String,
        labelHe: String,
        labelEn: String? = nil,
        rawInput: String? = nil,
        providerPayload: String? = nil,
        createdAt: Date? = nil,
        updatedAt: Date? = nil,
        customMetadata: [String: String]? = nil,
        unknownFields: [String: TorahJSONValue] = [:]
    ) {
        self.id = id
        self.kind = kind
        self.role = role
        self.providerID = providerID
        self.externalID = externalID
        self.canonicalKey = canonicalKey
        self.labelHe = labelHe
        self.labelEn = labelEn
        self.rawInput = rawInput
        self.providerPayload = providerPayload
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.customMetadata = customMetadata
        self.unknownFields = unknownFields
    }

    private static let knownKeys: Set<String> = [
        "id", "kind", "role", "providerID", "externalID", "canonicalKey",
        "labelHe", "labelEn", "rawInput", "providerPayload", "createdAt",
        "updatedAt", "customMetadata"
    ]

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: TorahDynamicCodingKey.self)
        id = try container.decode(String.self, forKey: .key("id"))
        kind = try container.decode(TorahAssociationKind.self, forKey: .key("kind"))
        role = try container.decode(TorahAssociationRole.self, forKey: .key("role"))
        providerID = try container.decode(String.self, forKey: .key("providerID"))
        externalID = try container.decode(String.self, forKey: .key("externalID"))
        canonicalKey = try container.decode(String.self, forKey: .key("canonicalKey"))
        labelHe = try container.decode(String.self, forKey: .key("labelHe"))
        labelEn = try container.decodeIfPresent(String.self, forKey: .key("labelEn"))
        rawInput = try container.decodeIfPresent(String.self, forKey: .key("rawInput"))
        providerPayload = try container.decodeIfPresent(String.self, forKey: .key("providerPayload"))
        createdAt = try container.decodeIfPresent(Date.self, forKey: .key("createdAt"))
        updatedAt = try container.decodeIfPresent(Date.self, forKey: .key("updatedAt"))
        customMetadata = try container.decodeIfPresent([String: String].self, forKey: .key("customMetadata"))
        unknownFields = try container.allKeys.reduce(into: [:]) { result, key in
            guard !Self.knownKeys.contains(key.stringValue) else { return }
            result[key.stringValue] = try container.decode(TorahJSONValue.self, forKey: key)
        }
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: TorahDynamicCodingKey.self)
        try container.encode(id, forKey: .key("id"))
        try container.encode(kind, forKey: .key("kind"))
        try container.encode(role, forKey: .key("role"))
        try container.encode(providerID, forKey: .key("providerID"))
        try container.encode(externalID, forKey: .key("externalID"))
        try container.encode(canonicalKey, forKey: .key("canonicalKey"))
        try container.encode(labelHe, forKey: .key("labelHe"))
        try container.encodeIfPresent(labelEn, forKey: .key("labelEn"))
        try container.encodeIfPresent(rawInput, forKey: .key("rawInput"))
        try container.encodeIfPresent(providerPayload, forKey: .key("providerPayload"))
        try container.encodeIfPresent(createdAt, forKey: .key("createdAt"))
        try container.encodeIfPresent(updatedAt, forKey: .key("updatedAt"))
        try container.encodeIfPresent(customMetadata, forKey: .key("customMetadata"))
        for (key, value) in unknownFields where !Self.knownKeys.contains(key) {
            try container.encode(value, forKey: .key(key))
        }
    }
}

/// Versioned payload for whole-document Torah associations.
public struct TorahDocumentAssociationsPayload: Codable, Sendable, Equatable {
    public static let currentVersion = 1

    public var version: Int
    public var items: [TorahAssociationItem]
    public var unknownFields: [String: TorahJSONValue]

    public init(
        version: Int = currentVersion,
        items: [TorahAssociationItem],
        unknownFields: [String: TorahJSONValue] = [:]
    ) {
        self.version = version
        self.items = items
        self.unknownFields = unknownFields
    }

    private enum CodingKeys: String, CodingKey { case version, items }

    public init(from decoder: Decoder) throws {
        let known = try decoder.container(keyedBy: CodingKeys.self)
        version = try known.decode(Int.self, forKey: .version)
        items = try known.decode([TorahAssociationItem].self, forKey: .items)
        let all = try decoder.container(keyedBy: TorahDynamicCodingKey.self)
        unknownFields = try all.allKeys.reduce(into: [:]) { result, key in
            guard CodingKeys(stringValue: key.stringValue) == nil else { return }
            result[key.stringValue] = try all.decode(TorahJSONValue.self, forKey: key)
        }
    }

    public func encode(to encoder: Encoder) throws {
        var known = encoder.container(keyedBy: CodingKeys.self)
        try known.encode(version, forKey: .version)
        try known.encode(items, forKey: .items)
        var all = encoder.container(keyedBy: TorahDynamicCodingKey.self)
        for (key, value) in unknownFields where CodingKeys(stringValue: key) == nil {
            try all.encode(value, forKey: .key(key))
        }
    }
}

/// Exact excerpt coordinates use UTF-16 offsets to match native text editing APIs.
public struct TorahSourceQuoteExcerpt: Codable, Sendable, Equatable, Hashable {
    public var selectedText: String
    public var segmentReference: String?
    public var segmentIndex: Int?
    public var utf16Offset: Int
    public var utf16Length: Int

    public init(
        selectedText: String,
        segmentReference: String? = nil,
        segmentIndex: Int? = nil,
        utf16Offset: Int,
        utf16Length: Int
    ) {
        self.selectedText = selectedText
        self.segmentReference = segmentReference
        self.segmentIndex = segmentIndex
        self.utf16Offset = utf16Offset
        self.utf16Length = utf16Length
    }
}

/// Rich capture-time provenance. It deliberately retains the unnormalized document and provider JSON.
public struct TorahSourceQuoteProvenance: Codable, Sendable, Equatable, Hashable {
    public var retrievedAt: Date
    public var canonicalRef: String
    public var providerID: String
    public var referenceProviderPayload: String?
    public var document: TorahTextDocument
    public var excerpt: TorahSourceQuoteExcerpt

    public init(
        retrievedAt: Date,
        canonicalRef: String,
        providerID: String,
        referenceProviderPayload: String? = nil,
        document: TorahTextDocument,
        excerpt: TorahSourceQuoteExcerpt
    ) {
        self.retrievedAt = retrievedAt
        self.canonicalRef = canonicalRef
        self.providerID = providerID
        self.referenceProviderPayload = referenceProviderPayload
        self.document = document
        self.excerpt = excerpt
    }
}

/// Versioned payload for block-level Torah source quotes.
public struct TorahSourceQuotePayload: Codable, Sendable, Equatable {
    public static let currentVersion = 2

    public var version: Int
    public var providerID: String
    public var externalID: String
    public var canonicalKey: String
    public var labelHe: String
    public var labelEn: String?
    public var segment: String?
    public var snapshotText: String?
    public var readOnly: Bool
    public var provenance: TorahSourceQuoteProvenance?
    public var unknownFields: [String: TorahJSONValue]

    public init(
        version: Int = currentVersion,
        providerID: String,
        externalID: String,
        canonicalKey: String,
        labelHe: String,
        labelEn: String? = nil,
        segment: String? = nil,
        snapshotText: String? = nil,
        readOnly: Bool = true,
        provenance: TorahSourceQuoteProvenance? = nil,
        unknownFields: [String: TorahJSONValue] = [:]
    ) {
        self.version = version
        self.providerID = providerID
        self.externalID = externalID
        self.canonicalKey = canonicalKey
        self.labelHe = labelHe
        self.labelEn = labelEn
        self.segment = segment
        self.snapshotText = snapshotText
        self.readOnly = readOnly
        self.provenance = provenance
        self.unknownFields = unknownFields
    }

    private enum CodingKeys: String, CodingKey {
        case version, providerID, externalID, canonicalKey, labelHe, labelEn
        case segment, snapshotText, readOnly, provenance
    }

    public init(from decoder: Decoder) throws {
        let known = try decoder.container(keyedBy: CodingKeys.self)
        version = try known.decode(Int.self, forKey: .version)
        providerID = try known.decode(String.self, forKey: .providerID)
        externalID = try known.decode(String.self, forKey: .externalID)
        canonicalKey = try known.decode(String.self, forKey: .canonicalKey)
        labelHe = try known.decode(String.self, forKey: .labelHe)
        labelEn = try known.decodeIfPresent(String.self, forKey: .labelEn)
        segment = try known.decodeIfPresent(String.self, forKey: .segment)
        snapshotText = try known.decodeIfPresent(String.self, forKey: .snapshotText)
        readOnly = try known.decode(Bool.self, forKey: .readOnly)
        provenance = try known.decodeIfPresent(TorahSourceQuoteProvenance.self, forKey: .provenance)
        let all = try decoder.container(keyedBy: TorahDynamicCodingKey.self)
        unknownFields = try all.allKeys.reduce(into: [:]) { result, key in
            guard CodingKeys(stringValue: key.stringValue) == nil else { return }
            result[key.stringValue] = try all.decode(TorahJSONValue.self, forKey: key)
        }
    }

    public func encode(to encoder: Encoder) throws {
        var known = encoder.container(keyedBy: CodingKeys.self)
        try known.encode(version, forKey: .version)
        try known.encode(providerID, forKey: .providerID)
        try known.encode(externalID, forKey: .externalID)
        try known.encode(canonicalKey, forKey: .canonicalKey)
        try known.encode(labelHe, forKey: .labelHe)
        try known.encodeIfPresent(labelEn, forKey: .labelEn)
        try known.encodeIfPresent(segment, forKey: .segment)
        try known.encodeIfPresent(snapshotText, forKey: .snapshotText)
        try known.encode(readOnly, forKey: .readOnly)
        try known.encodeIfPresent(provenance, forKey: .provenance)
        var all = encoder.container(keyedBy: TorahDynamicCodingKey.self)
        for (key, value) in unknownFields where CodingKeys(stringValue: key) == nil {
            try all.encode(value, forKey: .key(key))
        }
    }
}

struct TorahDynamicCodingKey: CodingKey {
    let stringValue: String
    let intValue: Int?

    init?(stringValue: String) {
        self.stringValue = stringValue
        intValue = nil
    }

    init?(intValue: Int) {
        stringValue = String(intValue)
        self.intValue = intValue
    }

    static func key(_ value: String) -> Self { Self(stringValue: value)! }
}
