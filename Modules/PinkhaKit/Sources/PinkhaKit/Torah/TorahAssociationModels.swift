import Foundation

/// Semantic kind of Torah association.
public enum TorahAssociationKind: String, Codable, Sendable, CaseIterable {
    case ref = "ref"
    case topic = "topic"
    case word = "word"
}

/// Role/intent of the Torah association.
public enum TorahAssociationRole: String, Codable, Sendable, CaseIterable {
    case context = "context"
    case sourceQuote = "sourceQuote"
}

/// Target of an association: entire object or specific block.
public enum TorahAssociationTarget: Codable, Sendable, Equatable, Hashable {
    case object(objectId: String)
    case block(objectId: String, blockId: String)

    public var objectId: String {
        switch self {
        case .object(let id): return id
        case .block(let id, _): return id
        }
    }

    public var blockId: String? {
        switch self {
        case .object: return nil
        case .block(_, let bId): return bId
        }
    }
}

/// A single Torah association item.
public struct TorahAssociationItem: Codable, Sendable, Identifiable, Equatable, Hashable {
    public var id: String
    public var kind: TorahAssociationKind
    public var role: TorahAssociationRole
    public var providerID: String
    public var externalID: String
    public var canonicalKey: String
    public var labelHe: String
    public var labelEn: String
    public var customMetadata: [String: String]?

    public init(
        id: String = UUID().uuidString,
        kind: TorahAssociationKind,
        role: TorahAssociationRole,
        providerID: String,
        externalID: String,
        canonicalKey: String,
        labelHe: String,
        labelEn: String,
        customMetadata: [String: String]? = nil
    ) {
        self.id = id
        self.kind = kind
        self.role = role
        self.providerID = providerID
        self.externalID = externalID
        self.canonicalKey = canonicalKey
        self.labelHe = labelHe
        self.labelEn = labelEn
        self.customMetadata = customMetadata
    }
}

/// Versioned payload for whole-document Torah associations.
public struct TorahDocumentAssociationsPayload: Codable, Sendable, Equatable {
    public static let currentVersion = 1

    public var version: Int
    public var items: [TorahAssociationItem]

    public init(version: Int = currentVersion, items: [TorahAssociationItem]) {
        self.version = version
        self.items = items
    }
}

/// Versioned payload for block-level Torah source quotes.
public struct TorahSourceQuotePayload: Codable, Sendable, Equatable {
    public static let currentVersion = 1

    public var version: Int
    public var providerID: String
    public var externalID: String
    public var canonicalKey: String
    public var labelHe: String
    public var labelEn: String
    public var segment: String?
    public var snapshotText: String?
    public var readOnly: Bool

    public init(
        version: Int = currentVersion,
        providerID: String,
        externalID: String,
        canonicalKey: String,
        labelHe: String,
        labelEn: String,
        segment: String? = nil,
        snapshotText: String? = nil,
        readOnly: Bool = true
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
    }
}
