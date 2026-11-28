import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

public enum AnyHeartNativeContentSelectionError: Error, Equatable, Sendable {
    case sourceBinding, noCurrentPages, unknownType(String), unknownProperty(String)
    case unsupportedType(String), changedSnapshot(String)
    case unsupportedSource, compiledDefinitionDependency(String)
}

/// The exact dependency closure of supported captured native Page smartblocks.
/// Basic and Bookmark layouts retain their distinct composition contracts. An
/// unused definition is retained in the original catalogue, not reclassified
/// as a Page or granted the behavior of a different native type.
public struct AnyHeartNativeContentSelection: Sendable {
    public struct Object: Equatable, Sendable {
        public let sourceObjectID: String
        public let snapshotSHA256: String
        public let jsonViewSHA256: String
        public let typeObjectID: String
    }
    public struct AbsentDeclaration: Codable, Equatable, Sendable {
        public let sourceObjectID: String
        public let jsonViewSHA256: String
        public let relationObjectID: String
        public let relationKey: String
        public let nativeFormat: Int64
    }

    public let sourceAccountID: String
    public let sourceSpaceID: String
    public let captureManifestSHA256: String
    public let sourceWitnessSHA256: String
    public let catalogSHA256: String
    public let objects: [Object]
    public let typeObjectIDs: [String]
    public let relationObjectIDs: [String]
    public let optionObjectIDs: [String]
    /// A native relationLinks row declares an available field; it is not a
    /// present property value. Unused declarations remain explicitly bound to
    /// the exact source JSON/PB in the immutable facts record, not installed as
    /// invented writable values or removed from the full-source obligations.
    public let retainedAbsentDeclarations: [AbsentDeclaration]
    /// These compiled property descriptors were used elsewhere by the source
    /// capture. Their generic property semantics are not available to this
    /// selected graph; the exact original whole-source blockers stay retained.
    public let retainedCompiledDefinitionIDs: [String]
    public let retainedWholeSourceIssues: [String]
    public let remainingDefinitionObjectIDs: [String]
    /// Includes native heads without a current decoded object. It remains a
    /// separate full-source obligation even when every current Page qualifies.
    public let remainingSourceObjectIDs: [String]
    public var permitsWholeSourceAdmission: Bool { false }

    public var definitionObjectIDs: [String] { typeObjectIDs + relationObjectIDs + optionObjectIDs }
    public var executedSourceObjectIDs: [String] { definitionObjectIDs + objects.map(\.sourceObjectID) }

    public init(bundle: AnyHeartNativeSpaceBundle, catalog: AnyHeartNativeDefinitionCatalog) throws {
        guard Data(bundle.sourceAccountID.utf8) == Data(catalog.sourceAccountID.utf8),
              Data(bundle.sourceSpaceID.utf8) == Data(catalog.sourceSpaceID.utf8),
              bundle.manifestSHA256 == catalog.captureManifestSHA256,
              bundle.sourceWitnessSHA256 == catalog.sourceWitnessSHA256,
              let headCensus = bundle.nativeStoreContext?.headCensus else {
            throw AnyHeartNativeContentSelectionError.sourceBinding
        }
        let pages = bundle.objects.filter { $0.nativeType == 16 }
        guard !pages.isEmpty else { throw AnyHeartNativeContentSelectionError.noCurrentPages }
        let typeByID = Dictionary(uniqueKeysWithValues: catalog.types.map { (Data($0.objectID.utf8), $0) })
        let propertyByID = Dictionary(uniqueKeysWithValues: catalog.relations.map { (Data($0.objectID.utf8), $0) })
        var requiredTypes = Set<Data>(), requiredProperties = Set<Data>()
        var objects: [Object] = [], absentDeclarations: [AbsentDeclaration] = []
        for page in pages {
            guard page.objectTypes.count == 1, let type = catalog.type(url: page.objectTypes[0]) else {
                throw AnyHeartNativeContentSelectionError.unknownType(page.sourceObjectID)
            }
            requiredTypes.insert(Data(type.objectID.utf8))
            let structuralKeys: Set<String>
            if type.recommendedLayout == 11 {
                let layout = try AnyHeartNativeBookmarkLayout(snapshot: page)
                structuralKeys = Set(layout.structuralDetailKeys)
                guard let description = catalog.relation(key: "description") else {
                    throw AnyHeartNativeContentSelectionError.unknownProperty("description")
                }
                requiredProperties.insert(Data(description.objectID.utf8))
            } else {
                structuralKeys = []
            }
            for key in page.details.keys where !structuralKeys.contains(key) {
                guard let property = catalog.relation(key: key) else {
                    throw AnyHeartNativeContentSelectionError.unknownProperty(key)
                }
                requiredProperties.insert(Data(property.objectID.utf8))
            }
            // Validate every declaration, including native format identity.
            // Present values and actual Type roles supply execution dependency
            // edges. Absent global field declarations remain original facts.
            var linkBytes = Set<Data>(), linkNames = Set<String>()
            for link in page.relationLinks {
                guard let fields = link.object, Set(fields.keys) == ["key", "format"],
                      let key = fields["key"]?.string, let format = fields["format"]?.integer,
                      linkBytes.insert(Data(key.utf8)).inserted, linkNames.insert(key).inserted,
                      let property = catalog.relation(key: key), property.rawFormat == format else {
                    throw AnyHeartNativeContentSelectionError.unknownProperty(page.sourceObjectID)
                }
                if page.details[key] == nil {
                    absentDeclarations.append(.init(sourceObjectID: page.sourceObjectID,
                        jsonViewSHA256: page.viewSHA256, relationObjectID: property.objectID,
                        relationKey: key, nativeFormat: format))
                }
            }
            objects.append(.init(sourceObjectID: page.sourceObjectID, snapshotSHA256: page.snapshotSHA256,
                jsonViewSHA256: page.viewSHA256, typeObjectID: type.objectID))
        }
        // Include ordered recommendations, explicit hidden/file roles and
        // every target type of a writable object relation. The fixed point
        // handles real cyclic/self relations without creating placeholder IDs.
        var inspectedTypes = Set<Data>(), inspectedProperties = Set<Data>()
        while inspectedTypes != requiredTypes || inspectedProperties != requiredProperties {
            for id in requiredTypes.subtracting(inspectedTypes) {
                guard let type = typeByID[id] else {
                    throw AnyHeartNativeContentSelectionError.unknownType(String(decoding: id, as: UTF8.self))
                }
                guard type.recommendedLayout == 0 || type.recommendedLayout == 11 else {
                    throw AnyHeartNativeContentSelectionError.unsupportedType(type.objectID)
                }
                for relationID in type.recommendedRelations + type.featuredRelations + type.hiddenRelations + type.fileRelations {
                    guard propertyByID[Data(relationID.utf8)] != nil else {
                        throw AnyHeartNativeContentSelectionError.unknownProperty(relationID)
                    }
                    requiredProperties.insert(Data(relationID.utf8))
                }
                inspectedTypes.insert(id)
            }
            for id in requiredProperties.subtracting(inspectedProperties) {
                guard let property = propertyByID[id] else {
                    throw AnyHeartNativeContentSelectionError.unknownProperty(String(decoding: id, as: UTF8.self))
                }
                // Canonical identity/author fields validate their captured
                // target evidence in the ordinary strict native binding. Their
                // target vocabulary is not a new writable document Type.
                let canonical = AnyHeartNativeDefinitionPlan.isNativeCanonicalIdentity(property)
                if !canonical, property.format == .object {
                    for target in property.targetTypeIDs {
                        guard typeByID[Data(target.utf8)] != nil else {
                            throw AnyHeartNativeContentSelectionError.unknownType(target)
                        }
                        requiredTypes.insert(Data(target.utf8))
                    }
                }
                inspectedProperties.insert(id)
            }
        }
        let relationKeys = Set(catalog.relations.filter { requiredProperties.contains(Data($0.objectID.utf8)) }
            .map { Data($0.relationKey.utf8) })
        let types = catalog.types.filter { requiredTypes.contains(Data($0.objectID.utf8)) }.map(\.objectID)
        let relations = catalog.relations.filter { requiredProperties.contains(Data($0.objectID.utf8)) }.map(\.objectID)
        let options = catalog.options.filter { relationKeys.contains(Data($0.relationKey.utf8)) }.map(\.objectID)
        let allDefinitions = catalog.types.map(\.objectID) + catalog.relations.map(\.objectID) + catalog.options.map(\.objectID)
        let selectedDefinitions = Set((types + relations + options).map { Data($0.utf8) })
        let executed = selectedDefinitions.union(objects.map { Data($0.sourceObjectID.utf8) })
        let headIDs = Set(headCensus.sourceHeadIDs.map { Data($0.utf8) })
        guard executed.isSubset(of: headIDs) else { throw AnyHeartNativeContentSelectionError.sourceBinding }
        let compiled = try Self.unusedCompiledDefinitions(bundle.bundledDefinitionsUsed,
                                                          selectedRelationKeys: relationKeys)
        // This boundary only separates unused compiled property definitions.
        // Every actual source gap, unknown field, snapshot problem, resolver
        // omission or unmapped native collection still refuses this scope.
        guard bundle.sourceGaps.isEmpty, bundle.resolverUnmapped.isEmpty,
              bundle.nativeStoreContext?.unmappedCollectionNames.isEmpty == true,
              bundle.issues.allSatisfy({
                  $0.code == "compiled-definition-descriptors-not-captured" && $0.sourceID == nil &&
                      $0.field == "BundledDefinitionsUsed" && !compiled.isEmpty
              }) else { throw AnyHeartNativeContentSelectionError.unsupportedSource }
        var retainedIssues = bundle.issues.map { "bundle:" + $0.code + ":" + $0.field }
        if !compiled.isEmpty { retainedIssues.append("bundled-definition-fallback") }
        sourceAccountID = bundle.sourceAccountID; sourceSpaceID = bundle.sourceSpaceID
        captureManifestSHA256 = bundle.manifestSHA256; sourceWitnessSHA256 = bundle.sourceWitnessSHA256
        catalogSHA256 = catalog.contentSHA256; self.objects = objects
        typeObjectIDs = types; relationObjectIDs = relations; optionObjectIDs = options
        retainedAbsentDeclarations = absentDeclarations.filter { !requiredProperties.contains(Data($0.relationObjectID.utf8)) }
        retainedCompiledDefinitionIDs = compiled
        retainedWholeSourceIssues = retainedIssues
        remainingDefinitionObjectIDs = allDefinitions.filter { !selectedDefinitions.contains(Data($0.utf8)) }
        remainingSourceObjectIDs = headCensus.sourceHeadIDs.filter { !executed.contains(Data($0.utf8)) }
    }

    /// A Type's captured orderId or a captured property's format fields are
    /// typed definition metadata handled by their existing exact adapters.
    /// This never supplies the missing generic property definition, a value
    /// address or a default. A selected property dependency on one refuses.
    static func unusedCompiledDefinitions(_ identities: [String], selectedRelationKeys: Set<Data>) throws -> [String] {
        var seen = Set<Data>(), normalized = Set<String>()
        for identity in identities {
            guard identity.hasPrefix("property:"),
                  seen.insert(Data(identity.utf8)).inserted, normalized.insert(identity).inserted else {
                throw AnyHeartNativeContentSelectionError.compiledDefinitionDependency(identity)
            }
            let key = String(identity.dropFirst("property:".count))
            guard !key.isEmpty, !key.contains(":"),
                  !key.unicodeScalars.contains(where: CharacterSet.controlCharacters.contains),
                  !selectedRelationKeys.contains(Data(key.utf8)) else {
                throw AnyHeartNativeContentSelectionError.compiledDefinitionDependency(identity)
            }
        }
        return identities
    }

    func require(_ catalog: AnyHeartNativeDefinitionCatalog) throws {
        guard Data(sourceAccountID.utf8) == Data(catalog.sourceAccountID.utf8),
              Data(sourceSpaceID.utf8) == Data(catalog.sourceSpaceID.utf8),
              captureManifestSHA256 == catalog.captureManifestSHA256,
              sourceWitnessSHA256 == catalog.sourceWitnessSHA256,
              catalogSHA256 == catalog.contentSHA256 else {
            throw AnyHeartNativeContentSelectionError.sourceBinding
        }
    }

    func require(_ snapshot: AnyHeartNativeSnapshotView) throws {
        guard Data(sourceSpaceID.utf8) == Data(snapshot.sourceSpaceID.utf8),
              let expected = objects.first(where: { Data($0.sourceObjectID.utf8) == Data(snapshot.sourceObjectID.utf8) }),
              expected.snapshotSHA256 == snapshot.snapshotSHA256,
              expected.jsonViewSHA256 == snapshot.viewSHA256 else {
            throw AnyHeartNativeContentSelectionError.changedSnapshot(snapshot.sourceObjectID)
        }
    }
}
