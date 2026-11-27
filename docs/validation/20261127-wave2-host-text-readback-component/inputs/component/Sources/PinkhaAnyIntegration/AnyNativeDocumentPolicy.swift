import Foundation
import PinkhaKit
import PinkhaAnyEngine

/// Existing allowlists remain explicit for stock diagnostics. Native custom
/// document types require current compiled editor-definition proof.
public enum AnyTorahDocumentPolicy: Sendable, Equatable {
    case explicitTypeAllowlist
    case nativeCanonicalEditorV1
}

public enum AnyNativeDocumentPolicyError: Error, Sendable, Equatable {
    case unavailableContract
    case malformedProof
    case dependenciesChanged
}

public struct AnyNativeDocumentTypeProof: Sendable, Equatable {
    public static let policy = "canonical-editor-module-v1"
    public let spaceID: String
    public let typeID: String
    public let eligible: Bool
    public let readinessGeneration: String

    public init(response: AnyJSON, workspace: AnyTorahWorkspace, typeID: String) throws {
        let header = try Self.header(response, workspace: workspace)
        guard response["typeId"]?.string?.utf8.elementsEqual(typeID.utf8) == true else {
            throw AnyNativeDocumentPolicyError.malformedProof
        }
        self.spaceID = workspace.spaceID; self.typeID = typeID
        self.eligible = header.eligible; self.readinessGeneration = header.generation
    }

    static func header(_ response: AnyJSON, workspace: AnyTorahWorkspace) throws
        -> (eligible: Bool, generation: String) {
        guard response["contract"]?.string == AnyGuardedTorahCapabilities.contract,
              response["version"]?.integer == 1,
              response["policy"]?.string == policy,
              response["spaceId"]?.string?.utf8.elementsEqual(workspace.spaceID.utf8) == true,
              let type = response["typeId"]?.string, validID(type),
              let eligible = response["eligible"]?.bool,
              response["readiness"]?["version"]?.integer == 1,
              response["readiness"]?["state"]?.string == "ready-local-snapshot",
              let generation = response["readiness"]?["generation"]?.string,
              generation.utf8.count == 64,
              generation.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }),
              !eligible || response["canonicalEditorDataset"]?.string == "editor_blocks" else {
            throw AnyNativeDocumentPolicyError.malformedProof
        }
        return (eligible, generation)
    }
    static func validID(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 1024 && !value.utf8.contains(0)
    }
}

public struct AnyNativeDocumentTargetProof: Sendable, Equatable {
    public let spaceID: String
    public let objectID: String
    public let typeID: String
    public let collectionIDs: Set<String>
    public let canWrite: Bool
    public let readinessGeneration: String

    public init(response: AnyJSON, workspace: AnyTorahWorkspace, objectID: String,
                intent: AnyTorahTargetIntent = .read) throws {
        let header = try AnyNativeDocumentTypeProof.header(response, workspace: workspace)
        guard header.eligible, AnyNativeDocumentTypeProof.validID(objectID),
              response["objectId"]?.string?.utf8.elementsEqual(objectID.utf8) == true,
              let type = response["typeId"]?.string,
              let collections = response["collections"]?.array,
              collections.allSatisfy({ $0.string.map(AnyNativeDocumentTypeProof.validID) == true }),
              let canWrite = response["canWrite"]?.bool else {
            throw AnyNativeDocumentPolicyError.malformedProof
        }
        let ids = collections.compactMap(\.string)
        guard Set(ids).count == ids.count, Set(ids).isDisjoint(with: ["bin", "template"]) else {
            throw TorahAssociationRepositoryError.targetNotFound
        }
        if case .write = intent, !canWrite { throw TorahAssociationRepositoryError.permissionDenied }
        self.spaceID = workspace.spaceID; self.objectID = objectID; self.typeID = type
        self.collectionIDs = Set(ids); self.canWrite = canWrite
        self.readinessGeneration = header.generation
    }

    /// Proves only that these independently acquired values match the guarded
    /// metadata snapshot. Callers bracket reads with current native proof again.
    public func requireMatchingRecord(_ record: AnyJSON) throws {
        guard record["id"]?.string?.utf8.elementsEqual(objectID.utf8) == true,
              record["spaceId"]?.string?.utf8.elementsEqual(spaceID.utf8) == true,
              record["any"]?["type"]?.string?.utf8.elementsEqual(typeID.utf8) == true else {
            throw AnyNativeDocumentPolicyError.dependenciesChanged
        }
        let collections = record["any"]?["collections"] ?? .array([])
        guard let values = collections.array, values.allSatisfy({ $0.string != nil }),
              Set(values.compactMap(\.string)).count == values.count,
              Set(values.compactMap(\.string)) == collectionIDs else {
            throw AnyNativeDocumentPolicyError.dependenciesChanged
        }
    }
}

public struct AnyNativeDocumentPolicyClient: Sendable {
    public let workspace: AnyTorahWorkspace
    private let client: AnyHTTPClient
    public init(client: AnyHTTPClient, workspace: AnyTorahWorkspace) throws {
        guard client.expectedAccountID == workspace.accountID else { throw AnyEngineError.accountChanged }
        self.client = client; self.workspace = workspace
    }

    public func verifyCapabilities() async throws {
        let value = try await client.requestJSON(method: "GET", path: ["v1", "pinkha", "capabilities"])
        guard value["contract"]?.string == AnyGuardedTorahCapabilities.contract,
              value["nativeDocumentTypePolicy"]?.integer == 1,
              value["documentTypePolicy"]?.string == AnyNativeDocumentTypeProof.policy else {
            throw AnyNativeDocumentPolicyError.unavailableContract
        }
    }

    public func type(_ typeID: String) async throws -> AnyNativeDocumentTypeProof {
        guard AnyNativeDocumentTypeProof.validID(typeID) else { throw AnyNativeDocumentPolicyError.malformedProof }
        try await verifyCapabilities()
        let value = try await client.requestJSON(method: "GET",
            path: ["v1", "spaces", workspace.spaceID, "pinkha", "document-types", typeID])
        return try .init(response: value, workspace: workspace, typeID: typeID)
    }

    public func target(_ objectID: String, intent: AnyTorahTargetIntent = .read) async throws
        -> AnyNativeDocumentTargetProof {
        guard AnyNativeDocumentTypeProof.validID(objectID) else { throw AnyNativeDocumentPolicyError.malformedProof }
        try await verifyCapabilities()
        let value = try await client.requestJSON(method: "GET",
            path: ["v1", "spaces", workspace.spaceID, "pinkha", "document-targets", objectID])
        return try .init(response: value, workspace: workspace, objectID: objectID, intent: intent)
    }
}
