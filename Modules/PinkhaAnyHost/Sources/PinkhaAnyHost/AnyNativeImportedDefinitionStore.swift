import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

public struct AnyNativeImportedChoiceOption: Sendable {
    public let id: String
    public let property: AnyNativePropertyKey
    public let name: String
    public let color: String
    public let position: String
    public let raw: AnyJSON

    init(id: String, property: AnyNativePropertyKey, raw: AnyJSON) throws {
        guard raw.object != nil,
              ["name", "color", "pos"].allSatisfy({ raw[$0] == nil || raw[$0]?.string != nil }) else {
            throw AnyNativeImportedDefinitionError.changedIdentity(id)
        }
        self.id = id; self.property = property; self.raw = raw
        name = raw["name"]?.string ?? ""; color = raw["color"]?.string ?? ""; position = raw["pos"]?.string ?? ""
    }
}

public enum AnyNativeImportedDefinitionValue: Sendable {
    case type(AnyNativePropertyOwner)
    case property(AnyNativePropertyDefinition)
    case option(AnyNativeImportedChoiceOption)
}

public struct AnyNativeImportedDefinitionSnapshot: Sendable {
    public let workspace: AnyTorahWorkspace
    public let generation: UUID
    public let engineStartedAt: String
    public let entry: AnyNativeImportedDefinitionEntry
    public let value: AnyNativeImportedDefinitionValue
    public let raw: AnyJSON
    /// A changed ordinary definition remains addressable through its original
    /// immutable native intent. This flag never promotes source admission.
    public let matchesOriginalDescriptor: Bool
    public let nativeCreationOutcome: String?
    public var permitsDestinationWrites: Bool { false }
}

/// Read-only resolution of actual imported native definitions. The current
/// account, Space, process lease and selected creation receipt are checked on
/// every read. Two equal ordinary reads bound this local observation; they are
/// not a global transactional schema snapshot or a cross-peer delivery proof.
public struct AnyNativeImportedDefinitionStore: Sendable {
    public let workspace: AnyTorahWorkspace
    private let client: AnyHTTPClient

    public init(client: AnyHTTPClient, workspace: AnyTorahWorkspace) throws {
        guard Data(client.expectedAccountID.utf8) == Data(workspace.accountID.utf8) else {
            throw AnyHostError.wrongWorkspace
        }
        self.client = client; self.workspace = workspace
    }

    public func read(sourceObjectID: String, directory: AnyNativeImportedDefinitionDirectory,
                     lease: AnyHostLease) async throws -> AnyNativeImportedDefinitionSnapshot {
        guard Data(directory.binding.workspace.accountID.utf8) == Data(workspace.accountID.utf8),
              Data(directory.binding.workspace.spaceID.utf8) == Data(workspace.spaceID.utf8),
              Data(lease.workspace.accountID.utf8) == Data(workspace.accountID.utf8),
              Data(lease.workspace.spaceID.utf8) == Data(workspace.spaceID.utf8) else {
            throw AnyHostError.wrongWorkspace
        }
        try await lease.validate()
        guard let entry = directory.definition(sourceObjectID: sourceObjectID) else {
            throw AnyNativeImportedDefinitionError.missingDefinition(sourceObjectID)
        }
        let migration: AnyNativePreparedDefinitionMigration?
        let beforeReceipt: AnyPreparedDefinitionReceipt?
        if let intent = entry.intent {
            let reader = try await AnyNativePreparedDefinitionMigration.open(client: client, workspace: workspace,
                authorize: { try await lease.validate() })
            let receipt = try await reader.status(intent, authorize: { try await lease.validate() })
            try Self.requireReceipt(receipt, entry: entry)
            migration = reader; beforeReceipt = receipt
        } else {
            guard entry.canonical, entry.mapping == nil else {
                throw AnyNativeImportedDefinitionError.changedIdentity(sourceObjectID)
            }
            migration = nil; beforeReceipt = nil
        }
        let first = try await raw(entry, lease: lease)
        try Self.requireCurrentOrigin(first, entry: entry)
        let second = try await raw(entry, lease: lease)
        guard try AnyDestinationDefinitionChecks.bytes(first) == AnyDestinationDefinitionChecks.bytes(second) else {
            throw AnyNativeImportedDefinitionError.changedDuringRead(sourceObjectID)
        }
        if let intent = entry.intent, let migration, let beforeReceipt {
            let after = try await migration.status(intent, authorize: { try await lease.validate() })
            try Self.requireReceipt(after, entry: entry)
            guard after == beforeReceipt else {
                throw AnyNativeImportedDefinitionError.changedDuringRead(sourceObjectID)
            }
        }
        let value: AnyNativeImportedDefinitionValue
        let projection: AnyJSON?
        switch entry.address {
        case .type:
            // Selecting this Type for a new document still requires the
            // existing native document-policy reader; this is its definition.
            value = .type(try .init(raw: first))
            projection = try? AnyDestinationContentProjection.root(first, type: true)
        case .property(_, let key):
            value = .property(try .init(ownerID: key.ownerID, raw: first))
            projection = try? AnyDestinationContentProjection.property(first)
        case .option(_, let key, let optionID):
            value = .option(try .init(id: optionID, property: key, raw: first))
            projection = first
        }
        let matches = try projection.map {
            try AnyDestinationDefinitionChecks.bytes($0) == AnyDestinationDefinitionChecks.bytes(entry.originalDescriptor)
        } ?? false
        if entry.canonical && !matches {
            throw AnyNativeImportedDefinitionError.changedIdentity(sourceObjectID)
        }
        try await lease.validate()
        return .init(workspace: workspace, generation: lease.generation, engineStartedAt: lease.engineStartedAt,
            entry: entry, value: value, raw: first, matchesOriginalDescriptor: matches,
            nativeCreationOutcome: beforeReceipt?.outcome.rawValue)
    }

    private func raw(_ entry: AnyNativeImportedDefinitionEntry, lease: AnyHostLease) async throws -> AnyJSON {
        let prefix = ["v1", "spaces", workspace.spaceID]
        switch entry.address {
        case .type(let id):
            let result = try await client.requestJSON(method: "GET", path: prefix + ["types", id],
                maximumResponseBytes: 262_144, authorize: { try await lease.validate() })
            guard result["id"]?.string.map({ Data($0.utf8) }) == Data(id.utf8) else {
                throw AnyNativeImportedDefinitionError.changedIdentity(entry.sourceObjectID)
            }
            return result
        case .property(let kind, let key), .option(let kind, let key, _):
            let result = try await client.requestJSON(method: "GET",
                path: prefix + [kind.rawValue, key.ownerID, "properties"], maximumResponseBytes: 2_097_152,
                authorize: { try await lease.validate() })
            guard let rows = result["properties"]?.array, rows.count <= 4096 else { throw AnyEngineError.readLimit }
            var seen = Set<Data>()
            for row in rows {
                guard let id = row["id"]?.string, AnyEditorBlock.validID(id),
                      seen.insert(Data(id.utf8)).inserted else {
                    throw AnyNativeImportedDefinitionError.changedIdentity(entry.sourceObjectID)
                }
            }
            guard let property = rows.first(where: { $0["id"]?.string.map({ Data($0.utf8) }) == Data(key.propertyID.utf8) }) else {
                throw AnyNativeImportedDefinitionError.missingDefinition(entry.sourceObjectID)
            }
            if case .option(_, _, let id) = entry.address {
                guard let expectedParent = entry.expectedParentProvenance,
                      let actualParent = property["xFormat"]?["pinkhaHeart"],
                      try AnyDestinationDefinitionChecks.bytes(expectedParent) == AnyDestinationDefinitionChecks.bytes(actualParent) else {
                    throw AnyNativeImportedDefinitionError.changedIdentity(entry.sourceObjectID)
                }
                guard property["kind"] == .string("array"), property["xFormat"]?["type"] == .string("choice"),
                      let option = property["xFormat"]?["options"]?.object?.first(where: { Data($0.key.utf8) == Data(id.utf8) })?.value else {
                    throw AnyNativeImportedDefinitionError.missingDefinition(entry.sourceObjectID)
                }
                return option
            }
            return property
        }
    }

    private static func requireReceipt(_ receipt: AnyPreparedDefinitionReceipt,
                                       entry: AnyNativeImportedDefinitionEntry) throws {
        guard let mapping = entry.mapping,
              receipt.stage == .complete,
              receipt.outcome == .committed || receipt.outcome == .committedModified,
              receipt.fingerprint == mapping.fingerprint,
              Data(receipt.objectID.utf8) == Data(mapping.objectID.utf8),
              receipt.recordIDs.map({ Data($0.utf8) }) == mapping.recordIDs.map({ Data($0.utf8) }),
              mapping.signedChangeIDs.last.map({ Data($0.utf8) }) == Data(receipt.changeID.utf8) else {
            throw AnyNativeImportedDefinitionError.changedIdentity(entry.sourceObjectID)
        }
    }

    private static func requireCurrentOrigin(_ value: AnyJSON, entry: AnyNativeImportedDefinitionEntry) throws {
        guard !entry.canonical else { return }
        guard let expected = entry.expectedProvenance else {
            throw AnyNativeImportedDefinitionError.changedIdentity(entry.sourceObjectID)
        }
        let actual: AnyJSON?
        switch entry.address {
        case .type:
            guard let expectedFields = expected.object, let metadata = value["meta"]?.object else {
                throw AnyNativeImportedDefinitionError.changedIdentity(entry.sourceObjectID)
            }
            var selected: [String: AnyJSON] = [:]
            for key in expectedFields.keys {
                guard let field = metadata[key] else { throw AnyNativeImportedDefinitionError.changedIdentity(entry.sourceObjectID) }
                selected[key] = field
            }
            actual = .object(selected)
        case .property: actual = value["xFormat"]?["pinkhaHeart"]
        case .option: actual = value["meta"]
        }
        guard let actual, try AnyDestinationDefinitionChecks.bytes(actual) == AnyDestinationDefinitionChecks.bytes(expected) else {
            throw AnyNativeImportedDefinitionError.changedIdentity(entry.sourceObjectID)
        }
    }
}
