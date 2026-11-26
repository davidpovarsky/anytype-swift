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

/// The original bootstrap claim/state storage, shared with the application
/// adapter so its failure-recovery and stale-completion rules are testable.
public final class PinkhaBootstrapStateStorage: @unchecked Sendable {
    private struct Entry {
        let state: PinkhaSpaceBootstrapState
        let claim: UUID
    }
    private let lock = NSLock()
    private var states: [String: Entry] = [:]

    public init() {}

    public func state(for spaceId: String) -> PinkhaSpaceBootstrapState {
        lock.lock()
        defer { lock.unlock() }
        return states[spaceId]?.state ?? .uninitialized
    }

    public func setState(_ state: PinkhaSpaceBootstrapState, for spaceId: String) {
        lock.lock()
        defer { lock.unlock() }
        states[spaceId] = Entry(state: state, claim: UUID())
    }

    @discardableResult
    public func setState(_ state: PinkhaSpaceBootstrapState, for spaceId: String, claim: UUID) -> Bool {
        lock.lock()
        defer { lock.unlock() }
        guard states[spaceId]?.claim == claim else { return false }
        states[spaceId] = Entry(state: state, claim: claim)
        return true
    }

    public func resetForAccountChange() {
        lock.lock()
        defer { lock.unlock() }
        states.removeAll(keepingCapacity: true)
    }

    /// A new explicit Space activation may retry a finished failure. There is
    /// no timer, automatic retry loop or permission to overlap an active writer.
    public func beginProvisioningClaim(spaceId: String) -> UUID? {
        lock.lock()
        defer { lock.unlock() }
        switch states[spaceId]?.state ?? .uninitialized {
        case .provisioning, .ready:
            return nil
        case .uninitialized, .failed:
            let claim = UUID()
            states[spaceId] = Entry(state: .provisioning, claim: claim)
            return claim
        }
    }
}
