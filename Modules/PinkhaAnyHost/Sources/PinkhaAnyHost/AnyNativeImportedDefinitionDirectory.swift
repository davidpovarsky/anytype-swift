import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

public enum AnyNativeImportedDefinitionError: Error, Equatable, Sendable {
    case invalidMappings
    case invalidOrigin(String)
    case missingDefinition(String)
    case changedIdentity(String)
    case changedDuringRead(String)
}

public enum AnyNativeImportedDefinitionOwnerKind: String, Sendable {
    case type = "types", collection = "collections"
}

/// A canonical schema correspondence does not equate source and destination
/// values. In particular, destination signers/clocks remain destination facts.
public enum AnyNativeCanonicalValueSemantics: String, Sendable {
    case ordinaryProperty
    case translatedIdentity
    case destinationDerived
}

/// These addresses are deliberately different. An embedded choice option is
/// not a newly allocated native object and does not have an object endpoint.
public enum AnyNativeImportedDefinitionAddress: Equatable, Sendable {
    case type(objectID: String)
    case property(ownerKind: AnyNativeImportedDefinitionOwnerKind, key: AnyNativePropertyKey)
    case option(ownerKind: AnyNativeImportedDefinitionOwnerKind, key: AnyNativePropertyKey, optionID: String)

    public static func == (left: Self, right: Self) -> Bool {
        func same(_ a: AnyNativePropertyKey, _ b: AnyNativePropertyKey) -> Bool {
            Data(a.ownerID.utf8) == Data(b.ownerID.utf8) && Data(a.propertyID.utf8) == Data(b.propertyID.utf8)
        }
        switch (left, right) {
        case (.type(let a), .type(let b)): return Data(a.utf8) == Data(b.utf8)
        case (.property(let ak, let a), .property(let bk, let b)): return ak == bk && same(a, b)
        case (.option(let ak, let a, let ai), .option(let bk, let b, let bi)):
            return ak == bk && same(a, b) && Data(ai.utf8) == Data(bi.utf8)
        default: return false
        }
    }
}

public struct AnyNativeImportedDefinitionEntry: Sendable {
    public let sourceSpaceID: String
    public let sourceObjectID: String
    public let sourceUniqueKey: String
    public let sourceSnapshotSHA256: String
    public let sourceJSONViewSHA256: String
    public let address: AnyNativeImportedDefinitionAddress
    public let originalDescriptor: AnyJSON
    public var canonicalValueSemantics: AnyNativeCanonicalValueSemantics? {
        guard canonical, case .property(.type, let key) = address,
              Data(key.ownerID.utf8) == Data("any".utf8) else { return nil }
        switch key.propertyID {
        case "name", "description": return .ordinaryProperty
        case "id", "spaceId", "type": return .translatedIdentity
        case "author", "createdAt", "modifiedAt", "modifiedBy": return .destinationDerived
        default: return nil
        }
    }
    /// The source binding and current native status still own their respective
    /// authority. Resolving an address cannot admit a whole source migration.
    public var permitsDestinationWrites: Bool { false }
    let intent: AnyPreparedDefinitionIntent?
    let mapping: AnyDestinationMigrationMapping?
    let expectedProvenance: AnyJSON?
    let expectedParentProvenance: AnyJSON?
    let canonical: Bool
}

/// Source identities are joined to the exact saved plan, never to a display
/// name or an xKey search. Persisted mapping JSON is only a routing hint: the
/// store rechecks the selected immutable native intent before exposing data.
/// Archive-only Types and the imported-property namespace are not original
/// Heart Type/Property objects and therefore receive no directory entry.
public struct AnyNativeImportedDefinitionDirectory: Sendable {
    public let binding: AnyPreparedMigrationPlanBinding
    public let source: AnyDestinationSourceBinding
    public let entries: [AnyNativeImportedDefinitionEntry]
    /// Full original protobuf/JSON provenance for newly resolved canonical
    /// definitions outside the saved plan's current-content selection. This
    /// material is retained separately from the current native descriptor.
    public let supplementalCanonicalDefinitions: [AnyDestinationCanonicalPropertyBinding]
    public let unresolvedSourceDefinitionIDs: [String]
    /// Separate completed property plans retain their own creation bindings.
    /// The original preservation binding and source identity remain unchanged.
    public let supplementalPropertyBindings: [AnyPreparedMigrationPlanBinding]
    private let namespacePrerequisite: AnyDestinationImportedPropertyNamespace?
    public var permitsSourceAdmission: Bool { false }
    private let byID: [Data: AnyNativeImportedDefinitionEntry]

    public init(plan: AnyDestinationMigrationPlan, mappings: [AnyDestinationMigrationMapping],
                supplementalCanonicalDefinitions: [AnyDestinationCanonicalPropertyBinding] = []) throws {
        guard mappings.count == plan.items.count, !plan.source.definitionMembers.isEmpty,
              supplementalCanonicalDefinitions.count <= 9 else {
            throw AnyNativeImportedDefinitionError.invalidMappings
        }
        var keyed: [Data: AnyDestinationMigrationMapping] = [:]
        for (item, mapping) in zip(plan.items, mappings) {
            guard Data(item.sourceKey.utf8) == Data(mapping.sourceKey.utf8),
                  Data(item.sourceObjectID.utf8) == Data(mapping.sourceObjectID.utf8),
                  item.operation.kind == mapping.kind,
                  mapping.recordIDs.count == item.expectedRecordCount,
                  AnyEditorBlock.validID(mapping.objectID),
                  mapping.recordIDs.allSatisfy(AnyEditorBlock.validID),
                  Set(mapping.recordIDs.map { Data($0.utf8) }).count == mapping.recordIDs.count,
                  AnyDestinationPlanChecks.digest(mapping.intentID),
                  AnyDestinationPlanChecks.digest(mapping.fingerprint),
                  AnyDestinationPlanChecks.digest(mapping.currentReceiptSHA256),
                  !mapping.signedChangeIDs.isEmpty,
                  mapping.signedChangeIDs.allSatisfy(AnyEditorBlock.validID),
                  Set(mapping.signedChangeIDs.map { Data($0.utf8) }).count == mapping.signedChangeIDs.count,
                  keyed.updateValue(mapping, forKey: Data(item.sourceKey.utf8)) == nil else {
                throw AnyNativeImportedDefinitionError.invalidMappings
            }
        }
        let immutableMappings = keyed
        let resolved = try plan.items.map { item in
            try item.operation.resolved(destinationSpaceID: plan.binding.workspace.spaceID) { reference in
                try AnyDestinationMigrationVerifier.resolve(reference, in: immutableMappings,
                    destinationSpaceID: plan.binding.workspace.spaceID)
            }
        }
        var ownerKinds: [Data: AnyNativeImportedDefinitionOwnerKind] = [:]
        if let namespace = plan.importedPropertyNamespace {
            try namespace.requireSupplement(source: plan.source, binding: plan.binding, items: plan.items)
            ownerKinds[Data(namespace.ownerID.utf8)] = .collection
        }
        for (index, operation) in resolved.enumerated() {
            let kind: AnyNativeImportedDefinitionOwnerKind?
            switch operation {
            case .typeDefinition: kind = .type
            case .collectionDefinition: kind = .collection
            default: kind = nil
            }
            if let kind {
                let mapping = mappings[index]
                guard mapping.recordIDs.count == 1,
                      Data(mapping.recordIDs[0].utf8) == Data(mapping.objectID.utf8),
                      ownerKinds.updateValue(kind, forKey: Data(mapping.objectID.utf8)) == nil else {
                    throw AnyNativeImportedDefinitionError.invalidMappings
                }
            }
        }
        var entries: [Data: AnyNativeImportedDefinitionEntry] = [:]
        var propertyEntries: [Data: AnyNativeImportedDefinitionEntry] = [:]
        func add(_ entry: AnyNativeImportedDefinitionEntry) throws {
            guard entries.updateValue(entry, forKey: Data(entry.sourceObjectID.utf8)) == nil else {
                throw AnyNativeImportedDefinitionError.invalidOrigin(entry.sourceObjectID)
            }
        }
        for (index, operation) in resolved.enumerated() {
            let item = plan.items[index], mapping = mappings[index]
            guard let member = plan.source.definitionMembers[Data(item.sourceObjectID.utf8)] else { continue }
            switch operation {
            case .typeDefinition(let seed):
                let metadata = try AnyDestinationMigrationVerifier.literal(seed.meta)
                // Source preservation has its own native Type. Its archive
                // metadata must never masquerade as an imported original Type.
                guard metadata["heartSourceObjectID"] != nil else { continue }
                try Self.requireOrigin(metadata, sourceID: item.sourceObjectID, member: member,
                    nativeType: 528, sourceKey: "heartSourceObjectID", uniqueKey: "heartUniqueKey",
                    snapshotKey: "heartSnapshotSHA256", viewKey: "heartJSONViewSHA256")
                let intent = try AnyPreparedDefinitionIntent.type(binding: plan.binding, sourceKey: item.sourceKey,
                    xKey: seed.xKey, name: seed.name, description: seed.description, iconCID: seed.iconCID,
                    layout: seed.layout.map(AnyDestinationMigrationVerifier.literal), hidden: seed.hidden, meta: metadata)
                try Self.requireIntent(intent, mapping: mapping)
                let originKeys = ["heartSourceObjectID", "heartUniqueKey", "heartSnapshotSHA256",
                    "heartJSONViewSHA256", "heartDefinitionJSON"]
                var origin: [String: AnyJSON] = [:]
                for key in originKeys {
                    guard let value = metadata[key] else { throw AnyNativeImportedDefinitionError.invalidOrigin(item.sourceObjectID) }
                    origin[key] = value
                }
                try add(.init(sourceSpaceID: plan.source.spaceID, sourceObjectID: item.sourceObjectID,
                    sourceUniqueKey: member.uniqueKey, sourceSnapshotSHA256: member.snapshotSHA256,
                    sourceJSONViewSHA256: member.viewSHA256, address: .type(objectID: mapping.objectID),
                    originalDescriptor: try AnyDestinationContentProjection.root(seed, id: mapping.objectID, type: true),
                    intent: intent, mapping: mapping, expectedProvenance: .object(origin),
                    expectedParentProvenance: nil, canonical: false))
            case .propertyDefinition(let owner, let kind, let name, let xKey, let description, let scope, let format, let index):
                let formatValue = try format.map(AnyDestinationMigrationVerifier.literal)
                guard let provenance = formatValue?["pinkhaHeart"] else { continue }
                try Self.requireOrigin(provenance, sourceID: item.sourceObjectID, member: member,
                    nativeType: 521, sourceKey: "sourceObjectID", uniqueKey: "sourceUniqueKey",
                    snapshotKey: "snapshotSHA256", viewKey: "jsonViewSHA256")
                let ownerID = try AnyDestinationMigrationVerifier.native(owner)
                guard let ownerKind = ownerKinds[Data(ownerID.utf8)],
                      Data(mapping.objectID.utf8) == Data(ownerID.utf8),
                      let propertyKind = AnyPreparedDefinitionIntent.PropertyKind(rawValue: kind),
                      let propertyScope = AnyPreparedDefinitionIntent.PropertyScope(rawValue: scope) else {
                    throw AnyNativeImportedDefinitionError.invalidMappings
                }
                let key = try AnyNativePropertyKey(ownerID: ownerID, propertyID: mapping.recordIDs[0])
                let intent = try AnyPreparedDefinitionIntent.property(binding: plan.binding, sourceKey: item.sourceKey,
                    ownerID: ownerID, kind: propertyKind, name: name, xKey: xKey,
                    description: description, scope: propertyScope, xFormat: formatValue, index: index)
                try Self.requireIntent(intent, mapping: mapping)
                let entry = AnyNativeImportedDefinitionEntry(sourceSpaceID: plan.source.spaceID,
                    sourceObjectID: item.sourceObjectID, sourceUniqueKey: member.uniqueKey,
                    sourceSnapshotSHA256: member.snapshotSHA256, sourceJSONViewSHA256: member.viewSHA256,
                    address: .property(ownerKind: ownerKind, key: key),
                    originalDescriptor: try AnyDestinationContentProjection.property(id: key.propertyID,
                        kind: kind, name: name, xKey: xKey, description: description, scope: scope, format: format, index: index),
                    intent: intent, mapping: mapping, expectedProvenance: provenance,
                    expectedParentProvenance: nil, canonical: false)
                try add(entry); propertyEntries[Data(item.sourceKey.utf8)] = entry
            default: continue
            }
        }
        for coverage in plan.coverage {
            switch coverage.disposition {
            case .canonicalProperty(let canonical), .preservedCanonicalProperty(let canonical, _):
                try canonical.requireSource(plan.source, objectID: coverage.sourceObjectID)
                try canonical.validate()
                let evidence = canonical.evidence
                try add(.init(sourceSpaceID: evidence.sourceSpaceID, sourceObjectID: evidence.sourceObjectID,
                    sourceUniqueKey: evidence.snapshot.uniqueKey, sourceSnapshotSHA256: evidence.snapshotSHA256,
                    sourceJSONViewSHA256: evidence.viewSHA256,
                    address: .property(ownerKind: .type, key: .init(ownerID: canonical.ownerID, propertyID: canonical.propertyID)),
                    originalDescriptor: try AnyDestinationContentProjection.property(canonical.expectedNativeDescriptor),
                    intent: nil, mapping: nil, expectedProvenance: nil, expectedParentProvenance: nil, canonical: true))
            case .embeddedOption(let propertyKey, let evidence, let digest),
                 .preservedEmbeddedOption(let propertyKey, let evidence, let digest, _):
                try evidence.requireSource(plan.source, objectID: coverage.sourceObjectID)
                guard let property = propertyEntries[Data(propertyKey.utf8)],
                      case .property(let ownerKind, let key) = property.address,
                      let descriptor = property.originalDescriptor["xFormat"]?["options"]?.object?.first(where: {
                          Data($0.key.utf8) == Data(evidence.sourceObjectID.utf8)
                      })?.value,
                      try AnyDestinationDefinitionChecks.digest(descriptor) == digest else {
                    throw AnyNativeImportedDefinitionError.invalidOrigin(coverage.sourceObjectID)
                }
                try add(.init(sourceSpaceID: evidence.sourceSpaceID, sourceObjectID: evidence.sourceObjectID,
                    sourceUniqueKey: evidence.snapshot.uniqueKey, sourceSnapshotSHA256: evidence.snapshotSHA256,
                    sourceJSONViewSHA256: evidence.viewSHA256,
                    address: .option(ownerKind: ownerKind, key: key, optionID: evidence.sourceObjectID),
                    originalDescriptor: descriptor, intent: property.intent, mapping: property.mapping,
                    expectedProvenance: descriptor["meta"], expectedParentProvenance: property.expectedProvenance,
                    canonical: false))
            default: continue
            }
        }
        for canonical in supplementalCanonicalDefinitions {
            // The strict binding has a closed native mapping. Callers supply
            // exact captured evidence, never a chosen native alias or value.
            try canonical.validate()
            let evidence = canonical.evidence
            try canonical.requireSource(plan.source, objectID: evidence.sourceObjectID)
            let address = AnyNativeImportedDefinitionAddress.property(ownerKind: .type,
                key: try .init(ownerID: canonical.ownerID, propertyID: canonical.propertyID))
            guard !entries.values.contains(where: { $0.canonical && $0.address == address }) else {
                throw AnyNativeImportedDefinitionError.invalidOrigin(evidence.sourceObjectID)
            }
            try add(.init(sourceSpaceID: evidence.sourceSpaceID, sourceObjectID: evidence.sourceObjectID,
                sourceUniqueKey: evidence.snapshot.uniqueKey, sourceSnapshotSHA256: evidence.snapshotSHA256,
                sourceJSONViewSHA256: evidence.viewSHA256, address: address,
                originalDescriptor: try AnyDestinationContentProjection.property(canonical.expectedNativeDescriptor),
                intent: nil, mapping: nil, expectedProvenance: nil, expectedParentProvenance: nil, canonical: true))
        }
        self.supplementalCanonicalDefinitions = supplementalCanonicalDefinitions
        self.supplementalPropertyBindings = []
        self.namespacePrerequisite = plan.importedPropertyNamespace
        binding = plan.binding; source = plan.source; byID = entries
        self.entries = entries.values.sorted { Data($0.sourceObjectID.utf8).lexicographicallyPrecedes(Data($1.sourceObjectID.utf8)) }
        unresolvedSourceDefinitionIDs = plan.source.sourceObjectIDs.filter {
            guard let member = plan.source.definitionMembers[Data($0.utf8)] else { return false }
            return [528, 521, 529].contains(member.nativeType) && entries[Data($0.utf8)] == nil
        }.sorted { Data($0.utf8).lexicographicallyPrecedes(Data($1.utf8)) }
    }

    /// Join one completed property-only supplement to the original preservation
    /// directory. Every new entry retains its own intent; the ordinary reader
    /// rechecks that current native receipt before returning its descriptor.
    /// A persisted mapping alone never authorizes use or native writes.
    public init(preservation: AnyNativeImportedDefinitionDirectory,
                propertySupplement: AnyNativeImportedDefinitionDirectory) throws {
        guard preservation.namespacePrerequisite == nil,
              preservation.supplementalPropertyBindings.isEmpty,
              propertySupplement.supplementalPropertyBindings.isEmpty,
              propertySupplement.supplementalCanonicalDefinitions.isEmpty,
              let namespace = propertySupplement.namespacePrerequisite,
              Data(preservation.binding.workspace.accountID.utf8) == Data(propertySupplement.binding.workspace.accountID.utf8),
              Data(preservation.binding.workspace.spaceID.utf8) == Data(propertySupplement.binding.workspace.spaceID.utf8),
              Data(preservation.binding.storeID.utf8) == Data(propertySupplement.binding.storeID.utf8),
              Data(namespace.binding.workspace.accountID.utf8) == Data(preservation.binding.workspace.accountID.utf8),
              Data(namespace.binding.workspace.spaceID.utf8) == Data(preservation.binding.workspace.spaceID.utf8),
              Data(namespace.binding.storeID.utf8) == Data(preservation.binding.storeID.utf8),
              namespace.binding.planID == preservation.binding.planID,
              namespace.binding.planSHA256 == preservation.binding.planSHA256,
              Data(preservation.source.accountID.utf8) == Data(propertySupplement.source.accountID.utf8),
              Data(preservation.source.spaceID.utf8) == Data(propertySupplement.source.spaceID.utf8),
              preservation.source.captureManifestSHA256 == propertySupplement.source.captureManifestSHA256,
              preservation.source.witnessSHA256 == propertySupplement.source.witnessSHA256,
              preservation.source.definitionManifestBytes == propertySupplement.source.definitionManifestBytes,
              !propertySupplement.entries.isEmpty,
              propertySupplement.entries.count == propertySupplement.source.sourceObjectIDs.count,
              propertySupplement.unresolvedSourceDefinitionIDs.isEmpty else {
            throw AnyNativeImportedDefinitionError.invalidMappings
        }
        var merged = preservation.byID
        var addresses = preservation.entries.map(\.address)
        let originalIDs = Set(preservation.source.sourceObjectIDs.map { Data($0.utf8) })
        for entry in propertySupplement.entries {
            guard originalIDs.contains(Data(entry.sourceObjectID.utf8)),
                  case .property(.collection, let key) = entry.address,
                  Data(key.ownerID.utf8) == Data(namespace.ownerID.utf8),
                  !entry.canonical, entry.intent != nil, entry.mapping != nil,
                  !addresses.contains(entry.address),
                  merged.updateValue(entry, forKey: Data(entry.sourceObjectID.utf8)) == nil else {
                throw AnyNativeImportedDefinitionError.invalidOrigin(entry.sourceObjectID)
            }
            addresses.append(entry.address)
        }
        binding = preservation.binding; source = preservation.source; byID = merged
        entries = merged.values.sorted {
            Data($0.sourceObjectID.utf8).lexicographicallyPrecedes(Data($1.sourceObjectID.utf8))
        }
        supplementalCanonicalDefinitions = preservation.supplementalCanonicalDefinitions
        supplementalPropertyBindings = [propertySupplement.binding]
        namespacePrerequisite = nil
        unresolvedSourceDefinitionIDs = source.sourceObjectIDs.filter {
            guard let member = source.definitionMembers[Data($0.utf8)] else { return false }
            return [528, 521, 529].contains(member.nativeType) && merged[Data($0.utf8)] == nil
        }.sorted { Data($0.utf8).lexicographicallyPrecedes(Data($1.utf8)) }
    }

    public func definition(sourceObjectID: String) -> AnyNativeImportedDefinitionEntry? {
        byID[Data(sourceObjectID.utf8)]
    }

    private static func requireIntent(_ intent: AnyPreparedDefinitionIntent, mapping: AnyDestinationMigrationMapping) throws {
        guard intent.intentID == mapping.intentID, intent.kind.rawValue == mapping.kind else {
            throw AnyNativeImportedDefinitionError.invalidMappings
        }
    }

    private static func requireOrigin(_ metadata: AnyJSON, sourceID: String, member: AnyDestinationDefinitionMember,
                                      nativeType: Int64, sourceKey: String, uniqueKey: String,
                                      snapshotKey: String, viewKey: String) throws {
        guard member.nativeType == nativeType,
              metadata[sourceKey]?.string.map({ Data($0.utf8) }) == Data(sourceID.utf8),
              metadata[uniqueKey]?.string.map({ Data($0.utf8) }) == Data(member.uniqueKey.utf8),
              metadata[snapshotKey]?.string == member.snapshotSHA256,
              metadata[viewKey]?.string == member.viewSHA256 else {
            throw AnyNativeImportedDefinitionError.invalidOrigin(sourceID)
        }
    }
}
