import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

public enum AnyNativeTypeReferenceError: Error, Equatable, Sendable {
    case wrongSource
    case missingSourceDefinition(String)
    case ambiguousSourceDefinition(String)
    case invalidDescriptor
    case unmappedType(String)
    case unavailableReference(String)
    case changedCurrentDefinition(String)
}

/// A source recommendation is an identity, not a property-name guess. These
/// cases intentionally cannot be flattened into one owner/property namespace.
public enum AnyNativeTypeReferenceTarget: Sendable {
    case property(AnyNativeTypePropertyReference)
    case computed(AnyHeartNativeComputedRelationBinding)
    case unresolved(Reason)

    public enum Reason: String, Sendable {
        case noQualifiedNativeBinding
        case capturedProviderContractMismatch
    }
}

public struct AnyNativeTypePropertyReference: Sendable {
    public let entry: AnyNativeImportedDefinitionEntry
    public let ownerKind: AnyNativeImportedDefinitionOwnerKind
    public let key: AnyNativePropertyKey
    public var canonicalValueSemantics: AnyNativeCanonicalValueSemantics? { entry.canonicalValueSemantics }
    public var permitsDestinationWrites: Bool { false }
}

public struct AnyNativeTypeReference: Sendable {
    public let evidence: AnyDestinationDefinitionEvidence
    public let relationKey: String
    public let sourceHidden: Bool?
    public let target: AnyNativeTypeReferenceTarget
    public var sourceObjectID: String { evidence.sourceObjectID }
    public var permitsDestinationWrites: Bool { false }
    public var isExecutable: Bool {
        if case .unresolved = target { return false }
        return true
    }

    /// Used by an explicit new consumer; it is not an old property visibility
    /// key and does not change the existing visibility mutation API.
    public var referenceKey: String {
        "heart-reference:v1:\(evidence.sourceSpaceID.utf8.count):\(evidence.sourceSpaceID):" +
        "\(sourceObjectID.utf8.count):\(sourceObjectID)"
    }

    public var descriptor: AnyJSON {
        let destination: AnyJSON
        switch target {
        case .property(let binding):
            let key = binding.key
            var value: [String: AnyJSON] = ["kind": .string("property"),
                "ownerKind": .string(binding.ownerKind.rawValue), "ownerID": .string(key.ownerID),
                "propertyID": .string(key.propertyID)]
            if let semantics = binding.canonicalValueSemantics {
                value["canonicalValueSemantics"] = .string(semantics.rawValue)
            }
            destination = .object(value)
        case .computed(let binding):
            destination = .object(["kind": .string("computed"),
                "contract": .string(binding.readContract), "role": .string(binding.role.rawValue)])
        case .unresolved(let reason):
            destination = .object(["kind": .string("unresolved"), "reason": .string(reason.rawValue)])
        }
        var value: [String: AnyJSON] = ["sourceObjectID": .string(sourceObjectID),
            "sourceUniqueKey": .string(evidence.snapshot.uniqueKey), "relationKey": .string(relationKey),
            "snapshotSHA256": .string(evidence.snapshotSHA256), "jsonViewSHA256": .string(evidence.viewSHA256),
            "target": destination]
        if let sourceHidden { value["sourceHidden"] = .bool(sourceHidden) }
        return .object(value)
    }
}

/// The four original recommendation fields retain their own order and presence.
/// In particular, absence, an empty list, and repeated source IDs are distinct.
public struct AnyNativeTypeReferenceGroup: Sendable {
    public enum Field: String, CaseIterable, Sendable {
        case recommended = "recommendedRelations"
        case featured = "recommendedFeaturedRelations"
        case hidden = "recommendedHiddenRelations"
        case files = "recommendedFileRelations"
    }
    public let field: Field
    public let isPresent: Bool
    public let references: [AnyNativeTypeReference]
}

public struct AnyNativeTypeReferencePresentation: Sendable {
    public static let contract = "pinkha-heart-type-references-v1"
    public let sourceType: AnyDestinationDefinitionEvidence
    public let sourceTypeKey: String
    public let sourceName: String
    public let sourceDescription: String
    public let sourceRecommendedLayout: Int64?
    public let groups: [AnyNativeTypeReferenceGroup]
    public let definitionHidden: [AnyNativeTypeReference]
    /// nil remains nil for an archived-only source Type. No catalog archive,
    /// property namespace or display label substitutes for a native Type ID.
    public let currentNativeTypeID: String?
    public let descriptor: AnyJSON
    public let fingerprint: String
    public var permitsDestinationWrites: Bool { false }
    public var qualifiesOriginalFamilyBehavior: Bool { false }
    public var isMaterializedType: Bool { currentNativeTypeID != nil }

    /// First-occurrence display ordering is separate from the complete ordered
    /// source lists in groups. Unresolved and computed entries stay in both.
    public var orderedReferences: [AnyNativeTypeReference] {
        var seen = Set<Data>(), result: [AnyNativeTypeReference] = []
        for field in [AnyNativeTypeReferenceGroup.Field.featured, .recommended, .files, .hidden] {
            for reference in groups.first(where: { $0.field == field })?.references ?? [] {
                if seen.insert(Data(reference.sourceObjectID.utf8)).inserted { result.append(reference) }
            }
        }
        return result
    }

    public var unresolvedSourceDefinitionIDs: [String] {
        var seen = Set<Data>()
        return (groups.flatMap(\.references) + definitionHidden).filter {
            !$0.isExecutable && seen.insert(Data($0.sourceObjectID.utf8)).inserted
        }.map(\.sourceObjectID)
    }

    /// An externally retained descriptor is data, never an authority token.
    /// Rebuild from the same admitted source+directory, then compare its full
    /// canonical UTF-8 bytes. Unknown fields, version and altered addresses fail.
    public func requireExactDescriptor(_ value: AnyJSON) throws {
        guard try AnyHostCanonical.bytes(value, maximumBytes: 262_144) ==
            AnyHostCanonical.bytes(descriptor, maximumBytes: 262_144) else {
            throw AnyNativeTypeReferenceError.invalidDescriptor
        }
    }
}

/// Additive to the original page-v2 and Bookmark-v1 presentation contracts.
/// It represents every captured Type/recommendation, including a precise
/// unresolved entry where no qualified native property/provider exists yet.
/// Existing plans, Type layouts and immutable creation fingerprints are not
/// rewritten. A new consumer must explicitly choose this versioned read model.
public struct AnyHeartNativeTypeReferencePlan: Sendable {
    public let directory: AnyNativeImportedDefinitionDirectory
    public let sourceCatalogSHA256: String
    public let presentations: [AnyNativeTypeReferencePresentation]
    public var permitsSourceAdmission: Bool { false }
    public var permitsDestinationWrites: Bool { false }
    private let byID: [Data: Int]

    public init(catalog: AnyHeartNativeDefinitionCatalog,
                directory: AnyNativeImportedDefinitionDirectory) throws {
        let source = directory.source
        guard Data(catalog.sourceAccountID.utf8) == Data(source.accountID.utf8),
              Data(catalog.sourceSpaceID.utf8) == Data(source.spaceID.utf8),
              catalog.captureManifestSHA256 == source.captureManifestSHA256,
              catalog.sourceWitnessSHA256 == source.witnessSHA256,
              !source.definitionMembers.isEmpty, catalog.types.count <= 512,
              catalog.relations.count <= 4096, catalog.options.count <= 4096 else {
            throw AnyNativeTypeReferenceError.wrongSource
        }
        // A correct outer identity cannot turn an omitted Type or relation
        // into a complete presentation. Compare the entire captured definition
        // census, including options even though they are not reference kinds.
        for (nativeType, ids) in [(Int64(528), catalog.types.map(\.objectID)),
                                  (Int64(521), catalog.relations.map(\.objectID)),
                                  (Int64(529), catalog.options.map(\.objectID))] {
            let expected = Set(source.definitionMembers.filter { $0.value.nativeType == nativeType }.map(\.key))
            let actual = Set(ids.map { Data($0.utf8) })
            guard actual.count == ids.count, actual == expected else {
                throw AnyNativeTypeReferenceError.wrongSource
            }
        }
        for option in catalog.options {
            try AnyDestinationDefinitionEvidence(snapshot: option.snapshot)
                .requireSource(source, objectID: option.objectID)
        }
        self.directory = directory
        sourceCatalogSHA256 = catalog.contentSHA256

        var references: [Data: AnyNativeTypeReference] = [:]
        var nativeAddresses = Set<Data>()
        for relation in catalog.relations {
            let id = relation.objectID
            guard catalog.relation(objectID: id)?.objectID.utf8.elementsEqual(id.utf8) == true,
                  catalog.relation(key: relation.relationKey)?.objectID.utf8.elementsEqual(id.utf8) == true,
                  references[Data(id.utf8)] == nil else {
                throw AnyNativeTypeReferenceError.ambiguousSourceDefinition(id)
            }
            let evidence = try AnyDestinationDefinitionEvidence(snapshot: relation.snapshot)
            try evidence.requireSource(source, objectID: id)
            guard relation.snapshot.details["isHidden"] == nil || relation.snapshot.details["isHidden"]?.bool != nil else {
                throw AnyNativeTypeReferenceError.invalidDescriptor
            }
            let target: AnyNativeTypeReferenceTarget
            if let entry = directory.definition(sourceObjectID: id) {
                try Self.requireEntry(entry, evidence: evidence)
                guard case .property(let kind, let key) = entry.address,
                      AnyHeartNativeComputedRelationBinding.Role(rawValue: relation.relationKey) == nil else {
                    throw AnyNativeTypeReferenceError.invalidDescriptor
                }
                let identity = try AnyHostCanonical.bytes(.array([
                    .string(kind.rawValue), .string(key.ownerID), .string(key.propertyID)]), maximumBytes: 8192)
                guard nativeAddresses.insert(identity).inserted else {
                    throw AnyNativeTypeReferenceError.ambiguousSourceDefinition(id)
                }
                target = .property(.init(entry: entry, ownerKind: kind, key: key))
            } else if AnyHeartNativeComputedRelationBinding.Role(rawValue: relation.relationKey) != nil {
                if let binding = try? AnyHeartNativeComputedRelationBinding(evidence: evidence) {
                    try binding.requireSource(source, objectID: id)
                    target = .computed(binding)
                } else {
                    // A captured override must remain unresolved; its familiar
                    // name cannot select a provider with different semantics.
                    target = .unresolved(.capturedProviderContractMismatch)
                }
            } else {
                target = .unresolved(.noQualifiedNativeBinding)
            }
            references[Data(id.utf8)] = .init(evidence: evidence, relationKey: relation.relationKey,
                sourceHidden: relation.snapshot.details["isHidden"]?.bool, target: target)
        }
        let hiddenDefinitions = references.values.filter { $0.sourceHidden == true }.sorted {
            Data($0.sourceObjectID.utf8).lexicographicallyPrecedes(Data($1.sourceObjectID.utf8))
        }
        var result: [AnyNativeTypeReferencePresentation] = [], index: [Data: Int] = [:]
        for type in catalog.types {
            guard catalog.type(objectID: type.objectID)?.objectID.utf8.elementsEqual(type.objectID.utf8) == true,
                  catalog.type(key: type.typeKey)?.objectID.utf8.elementsEqual(type.objectID.utf8) == true,
                  index[Data(type.objectID.utf8)] == nil else {
                throw AnyNativeTypeReferenceError.ambiguousSourceDefinition(type.objectID)
            }
            let evidence = try AnyDestinationDefinitionEvidence(snapshot: type.snapshot)
            try evidence.requireSource(source, objectID: type.objectID)
            var groups: [AnyNativeTypeReferenceGroup] = [], wireGroups: [String: AnyJSON] = [:]
            for field in AnyNativeTypeReferenceGroup.Field.allCases {
                let value = type.snapshot.details[field.rawValue]
                let ids: [String]
                if let value {
                    guard let array = value.array, array.count <= 512 else { throw AnyNativeTypeReferenceError.invalidDescriptor }
                    ids = try array.map {
                        guard let id = $0.string else { throw AnyNativeTypeReferenceError.invalidDescriptor }
                        return id
                    }
                } else { ids = [] }
                // map is intentional: a missing source relation fails closed;
                // an unsupported native role is retained as an unresolved row.
                let resolved = try ids.map { id -> AnyNativeTypeReference in
                    guard let reference = references[Data(id.utf8)] else {
                        throw AnyNativeTypeReferenceError.missingSourceDefinition(id)
                    }
                    return reference
                }
                groups.append(.init(field: field, isPresent: value != nil, references: resolved))
                wireGroups[field.rawValue] = .object(["present": .bool(value != nil),
                    "references": .array(resolved.map(\.descriptor))])
            }
            let nativeTypeID: String?
            if let entry = directory.definition(sourceObjectID: type.objectID) {
                try Self.requireEntry(entry, evidence: evidence)
                guard case .type(let id) = entry.address else { throw AnyNativeTypeReferenceError.invalidDescriptor }
                nativeTypeID = id
            } else { nativeTypeID = nil }
            let sourceIdentity: [String: AnyJSON] = ["accountID": .string(source.accountID),
                "spaceID": .string(source.spaceID), "captureManifestSHA256": .string(source.captureManifestSHA256),
                "witnessSHA256": .string(source.witnessSHA256), "catalogSHA256": .string(catalog.contentSHA256),
                "objectID": .string(type.objectID), "uniqueKey": .string(type.snapshot.uniqueKey),
                "snapshotSHA256": .string(evidence.snapshotSHA256), "jsonViewSHA256": .string(evidence.viewSHA256)]
            // Original descriptor data is kept whole. Smartblock family,
            // layout, icons, setOf, unknown fields and absent values are not
            // rewritten into claims about destination application behavior.
            let descriptor: AnyJSON = .object(["contract": .string(AnyNativeTypeReferencePresentation.contract),
                "source": .object(sourceIdentity), "originalDetails": .object(type.snapshot.details),
                "destinationType": nativeTypeID.map { .object(["objectID": .string($0)]) } ?? .null,
                "groups": .object(wireGroups),
                "definitionHidden": .array(hiddenDefinitions.map(\.descriptor))])
            let bytes = try AnyHostCanonical.bytes(descriptor, maximumBytes: 262_144)
            index[Data(type.objectID.utf8)] = result.count
            result.append(.init(sourceType: evidence, sourceTypeKey: type.typeKey, sourceName: type.name,
                sourceDescription: type.description, sourceRecommendedLayout: type.recommendedLayout,
                groups: groups, definitionHidden: hiddenDefinitions, currentNativeTypeID: nativeTypeID,
                descriptor: descriptor, fingerprint: AnyContentDigest.sha256(bytes)))
        }
        presentations = result; byID = index
    }

    public func presentation(sourceTypeObjectID: String) -> AnyNativeTypeReferencePresentation? {
        byID[Data(sourceTypeObjectID.utf8)].map { presentations[$0] }
    }

    private static func requireEntry(_ entry: AnyNativeImportedDefinitionEntry,
                                     evidence: AnyDestinationDefinitionEvidence) throws {
        guard Data(entry.sourceSpaceID.utf8) == Data(evidence.sourceSpaceID.utf8),
              Data(entry.sourceObjectID.utf8) == Data(evidence.sourceObjectID.utf8),
              Data(entry.sourceUniqueKey.utf8) == Data(evidence.snapshot.uniqueKey.utf8),
              entry.sourceSnapshotSHA256 == evidence.snapshotSHA256,
              entry.sourceJSONViewSHA256 == evidence.viewSHA256 else {
            throw AnyNativeTypeReferenceError.wrongSource
        }
    }
}
