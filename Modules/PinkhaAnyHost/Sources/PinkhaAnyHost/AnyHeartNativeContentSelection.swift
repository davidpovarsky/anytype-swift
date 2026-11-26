import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

public enum AnyHeartNativeContentSelectionError: Error, Equatable, Sendable {
    case sourceBinding, noCurrentPages, unknownType(String), unknownProperty(String)
    case unsupportedType(String), changedSnapshot(String)
}

/// The exact dependency closure of all captured native Page instances. An
/// unused definition is retained in the original catalogue, not reclassified
/// as a Page or granted the behavior of a different native type.
public struct AnyHeartNativeContentSelection: Sendable {
    public struct Object: Equatable, Sendable {
        public let sourceObjectID: String
        public let snapshotSHA256: String
        public let jsonViewSHA256: String
        public let typeObjectID: String
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
        var objects: [Object] = []
        for page in pages {
            guard page.objectTypes.count == 1, let type = catalog.type(url: page.objectTypes[0]) else {
                throw AnyHeartNativeContentSelectionError.unknownType(page.sourceObjectID)
            }
            requiredTypes.insert(Data(type.objectID.utf8))
            for key in page.details.keys {
                guard let property = catalog.relation(key: key) else {
                    throw AnyHeartNativeContentSelectionError.unknownProperty(key)
                }
                requiredProperties.insert(Data(property.objectID.utf8))
            }
            // relationLinks carry native format identity even if no current
            // value is present. They are not discarded as display metadata.
            for link in page.relationLinks {
                guard let fields = link.object, Set(fields.keys) == ["key", "format"],
                      let key = fields["key"]?.string, let format = fields["format"]?.integer,
                      let property = catalog.relation(key: key), property.rawFormat == format else {
                    throw AnyHeartNativeContentSelectionError.unknownProperty(page.sourceObjectID)
                }
                requiredProperties.insert(Data(property.objectID.utf8))
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
                guard type.recommendedLayout == 0 else {
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
        sourceAccountID = bundle.sourceAccountID; sourceSpaceID = bundle.sourceSpaceID
        captureManifestSHA256 = bundle.manifestSHA256; sourceWitnessSHA256 = bundle.sourceWitnessSHA256
        catalogSHA256 = catalog.contentSHA256; self.objects = objects
        typeObjectIDs = types; relationObjectIDs = relations; optionObjectIDs = options
        remainingDefinitionObjectIDs = allDefinitions.filter { !selectedDefinitions.contains(Data($0.utf8)) }
        remainingSourceObjectIDs = headCensus.sourceHeadIDs.filter { !executed.contains(Data($0.utf8)) }
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
