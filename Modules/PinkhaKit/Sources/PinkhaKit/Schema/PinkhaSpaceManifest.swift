import Foundation

/// Synced schema manifest for a Pinkha-enabled Anytype Space.
/// Maps logical Pinkha roles to concrete Anytype Property IDs and Type IDs.
public struct PinkhaSpaceManifest: Codable, Sendable, Equatable, Hashable {
    public static let currentSchemaVersion = 1

    public var schemaVersion: Int
    public var spaceId: String
    public var manifestObjectId: String?

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

    public init(
        schemaVersion: Int = currentSchemaVersion,
        spaceId: String,
        manifestObjectId: String? = nil,
        parentPropertyId: String,
        parentPropertyKey: String,
        orderPropertyId: String,
        orderPropertyKey: String,
        documentAssociationsPropertyId: String,
        documentAssociationsPropertyKey: String,
        folderTypeId: String,
        bookFolderTypeId: String,
        registeredDocumentTypes: [String: String]
    ) {
        self.schemaVersion = schemaVersion
        self.spaceId = spaceId
        self.manifestObjectId = manifestObjectId
        self.parentPropertyId = parentPropertyId
        self.parentPropertyKey = parentPropertyKey
        self.orderPropertyId = orderPropertyId
        self.orderPropertyKey = orderPropertyKey
        self.documentAssociationsPropertyId = documentAssociationsPropertyId
        self.documentAssociationsPropertyKey = documentAssociationsPropertyKey
        self.folderTypeId = folderTypeId
        self.bookFolderTypeId = bookFolderTypeId
        self.registeredDocumentTypes = registeredDocumentTypes
    }

    // MARK: - Query Helpers

    public func typeId(for role: String) -> String? {
        registeredDocumentTypes[role]
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
        return try decoder.decode(PinkhaSpaceManifest.self, from: data)
    }

    public static func fromJSONString(_ string: String) throws -> PinkhaSpaceManifest {
        guard let data = string.data(using: .utf8) else {
            throw DecodingError.dataCorrupted(DecodingError.Context(codingPath: [], debugDescription: "Invalid UTF-8 string"))
        }
        return try fromJSONData(data)
    }
}
