import Foundation

/// Synced schema manifest for a Pinkha-enabled Anytype Space.
/// Maps logical Pinkha roles to concrete Anytype Property IDs and Type IDs.
public struct PinkhaSpaceManifest: Codable, Sendable, Equatable, Hashable {
    public static let currentSchemaVersion = 1

    public enum ProvisioningState: String, Codable, Sendable {
        case inProgress
        case complete
    }

    public var schemaVersion: Int
    public var spaceId: String
    public var manifestObjectId: String?
    public var provisioningState: ProvisioningState

    // Concrete Anytype Property IDs and keys
    public var parentPropertyId: String
    public var parentPropertyKey: String
    public var orderPropertyId: String
    public var orderPropertyKey: String
    public var documentAssociationsPropertyId: String
    public var documentAssociationsPropertyKey: String

    // Concrete Anytype Object Type IDs
    public var folderTypeId: String
    public var bookFolderTypeId: String

    // Logical role -> Concrete Type ID (e.g. "chiddush" -> "...", "article" -> "...")
    public var registeredDocumentTypes: [String: String]

    // Logical role -> Concrete Template ID (e.g. "chiddush" -> "tmpl_123")
    public var defaultTemplateIds: [String: String]

    public var createdAt: Date
    public var updatedAt: Date

    public init(
        schemaVersion: Int = currentSchemaVersion,
        spaceId: String,
        manifestObjectId: String? = nil,
        provisioningState: ProvisioningState = .complete,
        parentPropertyId: String = "",
        parentPropertyKey: String = "",
        orderPropertyId: String = "",
        orderPropertyKey: String = "",
        documentAssociationsPropertyId: String = "",
        documentAssociationsPropertyKey: String = "",
        folderTypeId: String = "",
        bookFolderTypeId: String = "",
        registeredDocumentTypes: [String: String] = [:],
        defaultTemplateIds: [String: String] = [:],
        createdAt: Date = Date(),
        updatedAt: Date = Date()
    ) {
        self.schemaVersion = schemaVersion
        self.spaceId = spaceId
        self.manifestObjectId = manifestObjectId
        self.provisioningState = provisioningState
        self.parentPropertyId = parentPropertyId
        self.parentPropertyKey = parentPropertyKey
        self.orderPropertyId = orderPropertyId
        self.orderPropertyKey = orderPropertyKey
        self.documentAssociationsPropertyId = documentAssociationsPropertyId
        self.documentAssociationsPropertyKey = documentAssociationsPropertyKey
        self.folderTypeId = folderTypeId
        self.bookFolderTypeId = bookFolderTypeId
        self.registeredDocumentTypes = registeredDocumentTypes
        self.defaultTemplateIds = defaultTemplateIds
        self.createdAt = createdAt
        self.updatedAt = updatedAt
    }

    /// Creates an initial in-progress manifest for a new space bootstrap.
    public static func initial(spaceId: String) -> PinkhaSpaceManifest {
        PinkhaSpaceManifest(
            schemaVersion: currentSchemaVersion,
            spaceId: spaceId,
            provisioningState: .inProgress,
            createdAt: Date(),
            updatedAt: Date()
        )
    }

    // MARK: - Codable (Backward-compatible)

    enum CodingKeys: String, CodingKey {
        case schemaVersion
        case spaceId
        case manifestObjectId
        case provisioningState
        case parentPropertyId
        case parentPropertyKey
        case orderPropertyId
        case orderPropertyKey
        case documentAssociationsPropertyId
        case documentAssociationsPropertyKey
        case folderTypeId
        case bookFolderTypeId
        case registeredDocumentTypes
        case defaultTemplateIds
        case createdAt
        case updatedAt
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        self.schemaVersion = try container.decode(Int.self, forKey: .schemaVersion)
        self.spaceId = try container.decode(String.self, forKey: .spaceId)
        self.manifestObjectId = try container.decodeIfPresent(String.self, forKey: .manifestObjectId)
        self.provisioningState = try container.decodeIfPresent(ProvisioningState.self, forKey: .provisioningState) ?? .complete

        self.parentPropertyId = try container.decodeIfPresent(String.self, forKey: .parentPropertyId) ?? ""
        self.parentPropertyKey = try container.decodeIfPresent(String.self, forKey: .parentPropertyKey) ?? ""
        self.orderPropertyId = try container.decodeIfPresent(String.self, forKey: .orderPropertyId) ?? ""
        self.orderPropertyKey = try container.decodeIfPresent(String.self, forKey: .orderPropertyKey) ?? ""
        self.documentAssociationsPropertyId = try container.decodeIfPresent(String.self, forKey: .documentAssociationsPropertyId) ?? ""
        self.documentAssociationsPropertyKey = try container.decodeIfPresent(String.self, forKey: .documentAssociationsPropertyKey) ?? ""

        self.folderTypeId = try container.decodeIfPresent(String.self, forKey: .folderTypeId) ?? ""
        self.bookFolderTypeId = try container.decodeIfPresent(String.self, forKey: .bookFolderTypeId) ?? ""
        self.registeredDocumentTypes = try container.decodeIfPresent([String: String].self, forKey: .registeredDocumentTypes) ?? [:]
        self.defaultTemplateIds = try container.decodeIfPresent([String: String].self, forKey: .defaultTemplateIds) ?? [:]

        self.createdAt = try container.decodeIfPresent(Date.self, forKey: .createdAt) ?? Date()
        self.updatedAt = try container.decodeIfPresent(Date.self, forKey: .updatedAt) ?? Date()
    }

    // MARK: - Query Helpers

    public var isComplete: Bool {
        provisioningState == .complete
    }

    public var allRequiredPropertiesPresent: Bool {
        !parentPropertyId.isEmpty && !parentPropertyKey.isEmpty &&
        !orderPropertyId.isEmpty && !orderPropertyKey.isEmpty &&
        !documentAssociationsPropertyId.isEmpty && !documentAssociationsPropertyKey.isEmpty
    }

    public var allRequiredTypesPresent: Bool {
        !folderTypeId.isEmpty && !bookFolderTypeId.isEmpty &&
        registeredDocumentTypes[PinkhaSchemaRoles.chiddushKey] != nil &&
        registeredDocumentTypes[PinkhaSchemaRoles.articleKey] != nil &&
        registeredDocumentTypes[PinkhaSchemaRoles.researchKey] != nil
    }

    public var allRequiredTemplatesPresent: Bool {
        defaultTemplateIds[PinkhaSchemaRoles.chiddushKey] != nil &&
        defaultTemplateIds[PinkhaSchemaRoles.articleKey] != nil &&
        defaultTemplateIds[PinkhaSchemaRoles.researchKey] != nil
    }

    public var isFullyProvisioned: Bool {
        isComplete && allRequiredPropertiesPresent && allRequiredTypesPresent && allRequiredTemplatesPresent
    }

    public func typeId(for role: String) -> String? {
        registeredDocumentTypes[role]
    }

    public func templateId(for role: String) -> String? {
        defaultTemplateIds[role]
    }

    public func role(forTypeId typeId: String) -> String? {
        registeredDocumentTypes.first(where: { $0.value == typeId })?.key
    }

    public func isRegisteredDocumentType(typeId: String) -> Bool {
        registeredDocumentTypes.values.contains(typeId)
    }

    public func isFolder(typeId: String) -> Bool {
        typeId == folderTypeId
    }

    public func isBookFolder(typeId: String) -> Bool {
        typeId == bookFolderTypeId
    }

    public func isAnyPinkhaType(typeId: String) -> Bool {
        isFolder(typeId: typeId) || isBookFolder(typeId: typeId) || isRegisteredDocumentType(typeId: typeId)
    }

    // MARK: - JSON Serialization

    public func toJSONData() throws -> Data {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        return try encoder.encode(self)
    }

    public func toJSONString() throws -> String {
        guard let string = String(data: try toJSONData(), encoding: .utf8) else {
            throw EncodingError.invalidValue(self, EncodingError.Context(codingPath: [], debugDescription: "Failed to convert JSON data to UTF-8 string"))
        }
        return string
    }

    public static func fromJSONData(_ data: Data) throws -> PinkhaSpaceManifest {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return try decoder.decode(PinkhaSpaceManifest.self, from: data)
    }

    public static func fromJSONString(_ string: String) throws -> PinkhaSpaceManifest {
        guard let data = string.data(using: .utf8) else {
            throw DecodingError.dataCorrupted(DecodingError.Context(codingPath: [], debugDescription: "Invalid UTF-8 string"))
        }
        return try fromJSONData(data)
    }

    // MARK: - Equatable & Hashable (comparing dates at second precision for ISO8601 stability)

    public static func == (lhs: PinkhaSpaceManifest, rhs: PinkhaSpaceManifest) -> Bool {
        lhs.schemaVersion == rhs.schemaVersion &&
        lhs.spaceId == rhs.spaceId &&
        lhs.manifestObjectId == rhs.manifestObjectId &&
        lhs.provisioningState == rhs.provisioningState &&
        lhs.parentPropertyId == rhs.parentPropertyId &&
        lhs.parentPropertyKey == rhs.parentPropertyKey &&
        lhs.orderPropertyId == rhs.orderPropertyId &&
        lhs.orderPropertyKey == rhs.orderPropertyKey &&
        lhs.documentAssociationsPropertyId == rhs.documentAssociationsPropertyId &&
        lhs.documentAssociationsPropertyKey == rhs.documentAssociationsPropertyKey &&
        lhs.folderTypeId == rhs.folderTypeId &&
        lhs.bookFolderTypeId == rhs.bookFolderTypeId &&
        lhs.registeredDocumentTypes == rhs.registeredDocumentTypes &&
        lhs.defaultTemplateIds == rhs.defaultTemplateIds &&
        Int(lhs.createdAt.timeIntervalSince1970) == Int(rhs.createdAt.timeIntervalSince1970) &&
        Int(lhs.updatedAt.timeIntervalSince1970) == Int(rhs.updatedAt.timeIntervalSince1970)
    }

    public func hash(into hasher: inout Hasher) {
        hasher.combine(schemaVersion)
        hasher.combine(spaceId)
        hasher.combine(manifestObjectId)
        hasher.combine(provisioningState)
        hasher.combine(parentPropertyId)
        hasher.combine(parentPropertyKey)
        hasher.combine(orderPropertyId)
        hasher.combine(orderPropertyKey)
        hasher.combine(documentAssociationsPropertyId)
        hasher.combine(documentAssociationsPropertyKey)
        hasher.combine(folderTypeId)
        hasher.combine(bookFolderTypeId)
        hasher.combine(registeredDocumentTypes)
        hasher.combine(defaultTemplateIds)
        hasher.combine(Int(createdAt.timeIntervalSince1970))
        hasher.combine(Int(updatedAt.timeIntervalSince1970))
    }
}

