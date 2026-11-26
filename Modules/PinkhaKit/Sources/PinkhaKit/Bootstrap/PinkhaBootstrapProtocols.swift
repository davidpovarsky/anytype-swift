import Foundation

public enum PinkhaBootstrapError: Error, Equatable, Sendable, LocalizedError {
    case disabled
    case propertyCreationFailed(String)
    case typeCreationFailed(String)
    case templateCreationFailed(String)
    case manifestStoreError(String)
    case migrationError(PinkhaSchemaMigrationError)
    case invalidManifest(String)

    public var errorDescription: String? {
        switch self {
        case .disabled:
            return "Pinkha bootstrap is disabled."
        case .propertyCreationFailed(let reason), .typeCreationFailed(let reason),
             .templateCreationFailed(let reason), .manifestStoreError(let reason),
             .invalidManifest(let reason):
            return reason
        case .migrationError(let error):
            return error.localizedDescription
        }
    }
}

public enum PinkhaSpaceBootstrapState: Equatable, Sendable {
    case uninitialized
    case provisioning
    case ready(PinkhaSpaceManifest)
    case failed(String)
}

public enum PinkhaSchemaMigrationError: Error, Equatable, Sendable, LocalizedError {
    case unsupportedVersion(Int)
    case migrationFailed(String)

    public var errorDescription: String? {
        switch self {
        case .unsupportedVersion(let version):
            return "Unsupported Pinkha schema version: \(version)."
        case .migrationFailed(let reason):
            return reason
        }
    }
}

public protocol PinkhaSpaceManifestStoreProtocol: Sendable {
    func loadManifest(spaceId: String) async throws -> PinkhaSpaceManifest?
    func saveManifest(_ manifest: PinkhaSpaceManifest) async throws -> PinkhaSpaceManifest
    func discoverManifestObjectId(spaceId: String) async throws -> String?
}

public struct PinkhaPropertyDescriptor: Sendable, Equatable {
    public let id: String
    public let key: String
    public let name: String

    public init(id: String, key: String, name: String) {
        self.id = id
        self.key = key
        self.name = name
    }
}

public protocol PinkhaPropertyServiceProtocol: Sendable {
    func createProperty(name: String, format: String, isHidden: Bool, spaceId: String) async throws -> PinkhaPropertyDescriptor
    func validatePropertyExists(propertyId: String, spaceId: String) async throws -> Bool
}

public struct PinkhaTypeDescriptor: Sendable, Equatable {
    public let id: String
    public let name: String

    public init(id: String, name: String) {
        self.id = id
        self.name = name
    }
}

public protocol PinkhaTypeServiceProtocol: Sendable {
    func createType(name: String, pluralName: String, spaceId: String) async throws -> PinkhaTypeDescriptor
    func validateTypeExists(typeId: String, spaceId: String) async throws -> Bool
}

public protocol PinkhaTemplateServiceProtocol: Sendable {
    func createAndAssignDefaultTemplate(typeId: String, spaceId: String) async throws -> String
    func validateTemplateExists(templateId: String, spaceId: String) async throws -> Bool
}
