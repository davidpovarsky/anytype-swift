import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

/// A read-only prerequisite for extending the exact property namespace created
/// by an earlier completed migration. It is not a native authority token.
/// The original whole plan is retained as bytes, but none of its operations is
/// copied into or executed by the supplemental property plan.
public struct AnyDestinationImportedPropertyNamespace: Codable, Sendable {
    public static let contract = "pinkha-imported-property-namespace-prerequisite-v1"
    public let originalPlanBytes: Data
    public let mapping: AnyDestinationMigrationMapping
    public let source: AnyDestinationSourceBinding
    public let binding: AnyPreparedMigrationPlanBinding
    public let intent: AnyPreparedDefinitionIntent
    public let sourceObjectID: String
    public let originalNamespace: AnyDestinationRootDefinition
    public var ownerID: String { mapping.objectID }
    public var permitsDestinationWrites: Bool { false }

    public init(completedPlan: AnyDestinationMigrationPlan,
                mappings: [AnyDestinationMigrationMapping]) throws {
        guard completedPlan.importedPropertyNamespace == nil,
              mappings.count == completedPlan.items.count else {
            throw AnyDestinationMigrationError.invalidPlan("original property namespace checkpoint")
        }
        try completedPlan.requireExecutable()
        var matches: [Int] = []
        for (index, item) in completedPlan.items.enumerated() {
            guard case .collectionDefinition(let seed) = item.operation,
                  case .literal(let metadata) = seed.meta,
                  metadata["heartPropertyNamespace"] == .bool(true) else { continue }
            matches.append(index)
        }
        guard matches.count == 1, let index = matches.first else {
            throw AnyDestinationMigrationError.invalidPlan("one original imported property namespace")
        }
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        try self.init(originalPlanBytes: encoder.encode(completedPlan), mapping: mappings[index])
    }

    private init(originalPlanBytes: Data, mapping: AnyDestinationMigrationMapping) throws {
        guard !originalPlanBytes.isEmpty,
              originalPlanBytes.count <= AnyDestinationMigrationPlan.maximumPlanBytes + 1024 else {
            throw AnyDestinationMigrationError.invalidPlan("original namespace plan size")
        }
        // Refuse nested prerequisites before invoking the plan decoder. A
        // prerequisite may refer only to the original self-contained plan.
        let envelope = try JSONDecoder().decode(AnyJSON.self, from: originalPlanBytes)
        guard let content = envelope["content"]?.object,
              content["importedPropertyNamespace"] == nil else {
            throw AnyDestinationMigrationError.invalidPlan("nested property namespace prerequisite")
        }
        let plan = try AnyDestinationMigrationPlan.decode(originalPlanBytes)
        try plan.requireExecutable()
        guard plan.importedPropertyNamespace == nil,
              plan.source.definitionManifestBytes != nil,
              let index = plan.items.firstIndex(where: {
                  Data($0.sourceKey.utf8) == Data(mapping.sourceKey.utf8)
              }) else {
            throw AnyDestinationMigrationError.invalidPlan("original namespace plan membership")
        }
        let item = plan.items[index]
        guard case .collectionDefinition(let seed) = item.operation,
              seed.layout == nil, case .literal(let metadata) = seed.meta,
              let fields = metadata.object,
              Set(fields.keys) == Set(["heartSourceSpaceID", "heartCaptureSHA256", "heartPropertyNamespace"]),
              metadata["heartPropertyNamespace"] == .bool(true),
              metadata["heartSourceSpaceID"]?.string.map({ Data($0.utf8) }) == Data(plan.source.spaceID.utf8),
              metadata["heartCaptureSHA256"]?.string == plan.source.captureManifestSHA256,
              let member = plan.source.definitionMembers[Data(item.sourceObjectID.utf8)],
              member.nativeType == 521,
              item.expectedRecordCount == 1,
              Data(item.sourceObjectID.utf8) == Data(mapping.sourceObjectID.utf8),
              mapping.kind == "collectionDefinition", mapping.fileID == nil,
              AnyEditorBlock.validID(mapping.objectID),
              mapping.recordIDs.map({ Data($0.utf8) }) == [Data(mapping.objectID.utf8)],
              AnyDestinationPlanChecks.digest(mapping.intentID),
              AnyDestinationPlanChecks.digest(mapping.fingerprint),
              AnyDestinationPlanChecks.digest(mapping.currentReceiptSHA256),
              !mapping.signedChangeIDs.isEmpty,
              mapping.signedChangeIDs.allSatisfy(AnyEditorBlock.validID),
              Set(mapping.signedChangeIDs.map { Data($0.utf8) }).count == mapping.signedChangeIDs.count else {
            throw AnyDestinationMigrationError.invalidPlan("original namespace identity")
        }
        let candidates = plan.items.filter {
            guard case .collectionDefinition(let value) = $0.operation,
                  case .literal(let meta) = value.meta else { return false }
            return meta["heartPropertyNamespace"] == .bool(true)
        }
        guard candidates.count == 1 else {
            throw AnyDestinationMigrationError.invalidPlan("ambiguous original namespace")
        }
        let intent = try AnyPreparedDefinitionIntent.collection(binding: plan.binding,
            sourceKey: item.sourceKey, xKey: seed.xKey, name: seed.name,
            description: seed.description, iconCID: seed.iconCID,
            hidden: seed.hidden, meta: metadata)
        guard intent.intentID == mapping.intentID else {
            throw AnyDestinationMigrationError.changedIdentity(item.sourceKey)
        }
        self.originalPlanBytes = originalPlanBytes; self.mapping = mapping
        source = plan.source; binding = plan.binding; self.intent = intent
        sourceObjectID = item.sourceObjectID; originalNamespace = seed
    }

    private enum CodingKeys: String, CodingKey { case contract, originalPlanBytes, mapping }
    public init(from decoder: any Decoder) throws {
        let fields = try decoder.container(keyedBy: CodingKeys.self)
        guard try fields.decode(String.self, forKey: .contract) == Self.contract else {
            throw AnyDestinationMigrationError.invalidPlan("property namespace contract")
        }
        try self.init(originalPlanBytes: fields.decode(Data.self, forKey: .originalPlanBytes),
                      mapping: fields.decode(AnyDestinationMigrationMapping.self, forKey: .mapping))
    }
    public func encode(to encoder: any Encoder) throws {
        var fields = encoder.container(keyedBy: CodingKeys.self)
        try fields.encode(Self.contract, forKey: .contract)
        try fields.encode(originalPlanBytes, forKey: .originalPlanBytes)
        try fields.encode(mapping, forKey: .mapping)
    }

    /// Only a separate, explicitly scoped schema supplement may use this
    /// prerequisite. Arbitrary object updates, parts, files and new owners
    /// retain the original same-plan ownership rule.
    func requireSupplement(source candidate: AnyDestinationSourceBinding,
                           binding target: AnyPreparedMigrationPlanBinding,
                           items: [AnyDestinationMigrationItem]) throws {
        guard Data(target.workspace.accountID.utf8) == Data(binding.workspace.accountID.utf8),
              Data(target.workspace.spaceID.utf8) == Data(binding.workspace.spaceID.utf8),
              Data(target.storeID.utf8) == Data(binding.storeID.utf8),
              target.planID != binding.planID,
              Data(candidate.accountID.utf8) == Data(source.accountID.utf8),
              Data(candidate.spaceID.utf8) == Data(source.spaceID.utf8),
              candidate.captureManifestSHA256 == source.captureManifestSHA256,
              candidate.witnessSHA256 == source.witnessSHA256,
              candidate.definitionManifestBytes == source.definitionManifestBytes,
              !items.isEmpty, items.count == candidate.sourceObjectIDs.count,
              Set(candidate.sourceObjectIDs.map { Data($0.utf8) })
                .isSubset(of: Set(source.sourceObjectIDs.map { Data($0.utf8) })) else {
            throw AnyDestinationMigrationError.invalidPlan("external namespace source or destination scope")
        }
        var represented = Set<Data>()
        for item in items {
            guard item.expectedRecordCount == 1,
                  represented.insert(Data(item.sourceObjectID.utf8)).inserted,
                  let member = candidate.definitionMembers[Data(item.sourceObjectID.utf8)],
                  member.nativeType == 521,
                  case .propertyDefinition(.native(let owner), _, _, _, _, let scope, let format, _) = item.operation,
                  Data(owner.utf8) == Data(ownerID.utf8), scope == "synced",
                  case .literal(let value)? = format,
                  let origin = value["pinkhaHeart"],
                  origin["sourceObjectID"]?.string.map({ Data($0.utf8) }) == Data(item.sourceObjectID.utf8),
                  origin["sourceUniqueKey"]?.string.map({ Data($0.utf8) }) == Data(member.uniqueKey.utf8),
                  origin["snapshotSHA256"]?.string == member.snapshotSHA256,
                  origin["jsonViewSHA256"]?.string == member.viewSHA256 else {
                throw AnyDestinationMigrationError.invalidPlan("external namespace property scope")
            }
        }
        guard represented == Set(candidate.sourceObjectIDs.map { Data($0.utf8) }) else {
            throw AnyDestinationMigrationError.invalidPlan("external namespace source coverage")
        }
    }

    func requireCurrentReceipt(_ value: AnyJSON) throws -> AnyPreparedDefinitionReceipt {
        let receipt = try AnyPreparedDefinitionReceipt(value, intent: intent)
        guard value["accountId"]?.string.map({ Data($0.utf8) }) == Data(binding.workspace.accountID.utf8),
              value["spaceId"]?.string.map({ Data($0.utf8) }) == Data(binding.workspace.spaceID.utf8),
              value["storeId"]?.string.map({ Data($0.utf8) }) == Data(binding.storeID.utf8),
              receipt.stage == .complete,
              receipt.outcome == .committed || receipt.outcome == .committedModified,
              receipt.fingerprint == mapping.fingerprint,
              Data(receipt.objectID.utf8) == Data(ownerID.utf8),
              receipt.recordIDs.map({ Data($0.utf8) }) == mapping.recordIDs.map({ Data($0.utf8) }),
              mapping.signedChangeIDs.last.map({ Data($0.utf8) }) == Data(receipt.changeID.utf8) else {
            throw AnyDestinationMigrationError.changedIdentity(mapping.sourceKey)
        }
        return receipt
    }

    func requireCurrentRoot(_ value: AnyJSON) throws {
        guard let fields = value.object,
              fields["id"]?.string.map({ Data($0.utf8) }) == Data(ownerID.utf8),
              fields["xKey"]?.string.map({ Data($0.utf8) }) == Data(originalNamespace.xKey.utf8),
              fields["builtIn"] == nil || fields["builtIn"] == .bool(false),
              let metadata = fields["meta"]?.object,
              metadata["heartSourceSpaceID"]?.string.map({ Data($0.utf8) }) == Data(source.spaceID.utf8),
              metadata["heartCaptureSHA256"]?.string == source.captureManifestSHA256,
              metadata["heartPropertyNamespace"] == .bool(true) else {
            throw AnyDestinationMigrationError.changedIdentity(mapping.sourceKey)
        }
        _ = try AnyNativePropertyOwner(raw: value)
    }

    /// This is a sequence of current native observations. The native prepared
    /// write still authorizes its own durable effect; no atomic schema/ACL
    /// snapshot is inferred from these reads or from a persisted prerequisite.
    func observe(using driver: any AnyDestinationNativeDriving,
                 authorize: @escaping AnyDestinationAuthorization) async throws {
        try await authorize()
        let before = try requireCurrentReceipt(
            await driver.status(.definition(intent), authorize: authorize))
        let first = try await driver.importedPropertyNamespace(ownerID: ownerID, authorize: authorize)
        try requireCurrentRoot(first)
        let second = try await driver.importedPropertyNamespace(ownerID: ownerID, authorize: authorize)
        try requireCurrentRoot(second)
        guard try AnyDestinationDefinitionChecks.bytes(first) == AnyDestinationDefinitionChecks.bytes(second) else {
            throw AnyDestinationMigrationError.changedIdentity(mapping.sourceKey)
        }
        let after = try requireCurrentReceipt(
            await driver.status(.definition(intent), authorize: authorize))
        guard after == before else { throw AnyDestinationMigrationError.changedIdentity(mapping.sourceKey) }
        try await authorize(); try Task.checkCancellation()
    }
}
