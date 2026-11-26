import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

/// Imports the supported current content and preserves every original native
/// head in an immutable, typed source catalog backed by a reversible file.
/// This deliberately does not activate unused types, replace native ACLs,
/// transplant source history into target history, or admit unsupported layouts.
public struct AnyHeartNativeSourcePreservation: Sendable {
    public static let contract = "pinkha-heart-native-source-preservation-v1"
    public static let datasetKey = "heart_source_catalog"
    public struct Record: Sendable {
        public let sourceHeadID: String
        public let role: String
        public let sourceKey: String
        public let snapshotSHA256: String?
        public let jsonViewSHA256: String?
    }
    public let bundle: AnyHeartNativeSpaceBundle
    public let recoveredDefinitions: AnyHeartNativeRecoveredDefinitions
    public let currentContent: AnyHeartNativeContentComposition
    public let archive: AnyHeartNativePreservationArchive
    public let records: [Record]
    public let uninstantiatedDefinitionIDs: [String]
    public let preservedContextIDs: [String]
    public let items: [AnyDestinationMigrationItem]
    public let coverage: [AnyDestinationCoverage]
    public let contentSHA256: String
    public let archiveItemSourceKey: String
    public let catalogObjectSourceKey: String
    public let catalogTypeSourceKey: String
    public var allImportedTypesUsable: Bool { false }
    public var permitsWholeSourceAdmission: Bool { false }
    public var changesDestinationACL: Bool { false }
    public var sourceHistoryBecameTargetHistory: Bool { false }

    public init(bundle: AnyHeartNativeSpaceBundle, recoveredDefinitions: AnyHeartNativeRecoveredDefinitions,
                archive: AnyHeartNativePreservationArchive) throws {
        let catalog = try AnyHeartNativeDefinitionCatalog(bundle: bundle, recoveredDefinitions: recoveredDefinitions)
        guard archive.binding == (try .init(bundle: bundle, recovered: recoveredDefinitions)),
              let context = bundle.nativeStoreContext, let census = context.headCensus,
              context.unmappedCollectionNames.isEmpty, bundle.sourceGaps.isEmpty,
              bundle.resolverUnmapped.isEmpty, bundle.fileVariants.isEmpty, bundle.fileReferences.isEmpty,
              bundle.issues.allSatisfy({
                  $0.code == "compiled-definition-descriptors-not-captured" && $0.field == "BundledDefinitionsUsed"
              }) else { throw AnyDestinationMigrationError.invalidPlan("full preservation source contract") }
        // Reconstruct every member from the actual file, including the original
        // native witness and the separately qualified recovery evidence.
        let decoded = try AnyHeartNativePreservationArchive.restore(archive.bytes, expected: archive.binding)
        guard decoded.bundle.manifestBytes == bundle.manifestBytes,
              decoded.recoveredDefinitions.manifestBytes == recoveredDefinitions.manifestBytes else {
            throw AnyDestinationMigrationError.changedSource
        }
        let current = try AnyHeartNativeContentComposition(bundle: bundle)
        _ = try current.definitions.admittedSchemaItems()
        for page in current.pages { _ = try page.admittedSelectedItems(current.selection) }
        let activeIDs = Set(current.selection.executedSourceObjectIDs.map { Data($0.utf8) })
        let contentIDs = Set(current.selection.objects.map { Data($0.sourceObjectID.utf8) })
        let selectedTypeIDs = Set(current.definitions.types.map { Data($0.definition.objectID.utf8) })
        let byID = Dictionary(uniqueKeysWithValues: bundle.objects.map { (Data($0.sourceObjectID.utf8), $0) })
        let trees = Dictionary(uniqueKeysWithValues: bundle.trees.map { (Data($0.objectID.utf8), $0) })
        let definitionIDs = Set((catalog.types.map(\.objectID) + catalog.relations.map(\.objectID) +
                                 catalog.options.map(\.objectID)).map { Data($0.utf8) })
        let unused = definitionIDs.subtracting(activeIDs)
        // Only actual content instances participate in this proof. Definition
        // objects use their own meta-types; empty Home/Archive/Workspace/Widgets
        // are preserved as source context, never invented destination objects.
        for object in current.selection.objects {
            guard let captured = byID[Data(object.sourceObjectID.utf8)],
                  captured.objectTypes.count == 1,
                  let type = catalog.type(url: captured.objectTypes[0]),
                  selectedTypeIDs.contains(Data(type.objectID.utf8)),
                  !unused.contains(Data(type.objectID.utf8)) else {
                throw AnyDestinationMigrationError.invalidPlan("uninstantiated definition proof")
            }
        }
        var contexts: [String] = []
        for object in bundle.objects {
            let id = Data(object.sourceObjectID.utf8)
            if definitionIDs.contains(id) || contentIDs.contains(id) { continue }
            let known: [Int64: String] = [32: "home", 48: "archive", 518: "ws", 112: "widget"]
            guard known[object.nativeType].map({ Data($0.utf8) == Data(object.uniqueKey.utf8) }) == true,
                  object.blocks.count == 1, object.blocks[0].contentKind == "smartblock",
                  object.blocks[0].childIDs.isEmpty, object.issues.isEmpty else {
                throw AnyDestinationMigrationError.incompleteCoverage("unsupported instantiated source object")
            }
            contexts.append(object.sourceObjectID)
        }
        guard byID.count == bundle.objects.count, let anchor = current.selection.objects.first else {
            throw AnyDestinationMigrationError.invalidPlan("source catalog anchor")
        }
        let suffix = AnyContentDigest.sha256(AnyPreparedMigrationPlanBinding.material([
            Self.contract, bundle.manifestSHA256, recoveredDefinitions.manifestSHA256,
        ]))
        let typeKey = "heart-source-catalog-type:" + suffix
        let objectKey = "heart-source-catalog-object:" + suffix
        let fileKey = "heart-source-catalog-file:" + suffix
        let owner = AnyDestinationReference.mapped(sourceKey: typeKey, slot: .objectID, encoding: .rawID)
        let object = AnyDestinationReference.mapped(sourceKey: objectKey, slot: .objectID, encoding: .rawID)
        let ordinaryStrings = ["sourceHeadID", "sourceRole", "sourceNativeType", "sourceUniqueKey",
            "sourceTreeJSON", "sourceSnapshotBase64", "sourceViewJSON", "sourceSnapshotSHA256",
            "sourceViewSHA256", "sourceCaptureManifestSHA256", "sourceRecoveryManifestSHA256", "archiveURI"]
        let fields: [AnyJSON] = ordinaryStrings.map {
            .object(["key": .string($0), "kind": .string("string"), "required": .bool(true)])
        } + [.object(["key": .string("snapshotPresent"), "kind": .string("boolean"), "required": .bool(true)]),
             .object(["key": .string("importedBy"), "stamp": .string("creator")]),
             .object(["key": .string("importedAt"), "stamp": .string("createTime")])]
        var added: [AnyDestinationMigrationItem] = [
            .init(sourceKey: typeKey, sourceObjectID: anchor.sourceObjectID, operation: .typeDefinition(.init(
                xKey: "heart_source_catalog_" + suffix, name: "Original Heart source catalog",
                description: "Immutable source definitions, context and provenance; unsupported types remain inactive.",
                meta: .literal(.object(["preservationContract": .string(Self.contract),
                    "sourceCaptureManifestSHA256": .string(bundle.manifestSHA256),
                    "sourceRecoveryManifestSHA256": .string(recoveredDefinitions.manifestSHA256)]))))),
            .init(sourceKey: typeKey + ":records-part", sourceObjectID: anchor.sourceObjectID,
                expectedRecordCount: fields.count + 2,
                operation: .partDefinition(owner: owner, draft: .literal(.object([
                    "key": .string(Self.datasetKey), "name": .string("Original source records"),
                    "datasets": .array([.object(["key": .string(Self.datasetKey), "module": .string("records"),
                        "deleteBy": .string("none"), "fields": .array(fields)])]),
                ])))),
            .init(sourceKey: objectKey, sourceObjectID: anchor.sourceObjectID,
                operation: .object(type: owner, collections: [], initialProperties: .literal(.object([
                    "any": .object(["name": .string("Original Heart source")]),
                ])))),
            .init(sourceKey: fileKey, sourceObjectID: anchor.sourceObjectID,
                operation: .file(owner: object, name: "Original Heart source.pinkha-heart-source",
                    mime: AnyHeartNativePreservationArchive.mimeType, size: Int64(archive.bytes.count),
                    contentSHA256: archive.sha256)),
        ]
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        func jsonText(_ value: AnyJSON) throws -> String {
            String(decoding: try encoder.encode(value), as: UTF8.self)
        }
        var records: [Record] = []
        let headIDs = census.sourceHeadIDs.sorted { Data($0.utf8).lexicographicallyPrecedes(Data($1.utf8)) }
        guard Set(headIDs.map { Data($0.utf8) }).count == headIDs.count else {
            throw AnyDestinationMigrationError.invalidPlan("duplicate native source head")
        }
        for id in headIDs {
            let rawID = Data(id.utf8), snapshot = byID[Data(id.utf8)], tree = trees[Data(id.utf8)]
            let role: String
            if let snapshot {
                guard tree != nil else { throw AnyDestinationMigrationError.invalidPlan("snapshot without native tree") }
                if contentIDs.contains(rawID) { role = "active-current-content" }
                else if definitionIDs.contains(rawID) {
                    let base: String
                    switch snapshot.nativeType {
                    case 521: base = "relation-definition"
                    case 528: base = "type-definition"
                    case 529: base = "relation-option"
                    default: throw AnyDestinationMigrationError.invalidPlan("definition native kind")
                    }
                    role = (unused.contains(rawID) ? "uninstantiated-" : "active-schema-") + base
                } else if contexts.contains(where: { Data($0.utf8) == rawID }) {
                    role = "source-context"
                } else { throw AnyDestinationMigrationError.incompleteCoverage(id) }
            } else if let tree {
                guard tree.nativeType == -1, tree.status == "space-settings-retained" else {
                    throw AnyDestinationMigrationError.incompleteCoverage("unrepresented native source tree")
                }
                role = "original-space-settings"
            } else if rawID == Data(census.nativeACLID.utf8), census.capturedACLRowCount > 0 {
                role = "original-native-acl"
            } else if census.defaultKeyValueID.map({ Data($0.utf8) == rawID }) == true,
                      context.classification(named: id)?.kind == .emptyDefaultKeyValue {
                role = "original-empty-native-kv"
            } else { throw AnyDestinationMigrationError.incompleteCoverage("unrepresented native source head") }
            let recordKey = "heart-source-catalog-record:" + AnyContentDigest.sha256(
                AnyPreparedMigrationPlanBinding.material([suffix, id]))
            let literals: [String: AnyJSON] = [
                "sourceHeadID": .string(id), "sourceRole": .string(role),
                "sourceNativeType": .string(tree.map { String($0.nativeType) } ?? ""),
                "sourceUniqueKey": .string(snapshot?.uniqueKey ?? ""),
                "sourceTreeJSON": .string(try jsonText(tree?.raw ?? .null)),
                "snapshotPresent": .bool(snapshot != nil),
                "sourceSnapshotBase64": .string(snapshot?.protobufBytes.base64EncodedString() ?? ""),
                "sourceViewJSON": .string(snapshot.map { String(decoding: $0.jsonViewBytes, as: UTF8.self) } ?? ""),
                "sourceSnapshotSHA256": .string(snapshot?.snapshotSHA256 ?? ""),
                "sourceViewSHA256": .string(snapshot?.viewSHA256 ?? ""),
                "sourceCaptureManifestSHA256": .string(bundle.manifestSHA256),
                "sourceRecoveryManifestSHA256": .string(recoveredDefinitions.manifestSHA256),
            ]
            // Stay below the existing native immutable-record request bound,
            // including the actual resolved file URI and JSON envelope.
            guard try encoder.encode(AnyJSON.object(literals)).count <= 192 * 1024 else {
                throw AnyDestinationMigrationError.invalidPlan("preserved source row size")
            }
            let values = AnyDestinationValue.object(literals.keys.sorted().map {
                .init(key: .native($0), value: .literal(literals[$0]!))
            } + [.init(key: .native("archiveURI"),
                value: .reference(.mapped(sourceKey: fileKey, slot: .fileID, encoding: .fileURI)))])
            added.append(.init(sourceKey: recordKey, sourceObjectID: id,
                operation: .immutableRecord(object: object, ownerType: owner, datasetKey: Self.datasetKey, values: values)))
            records.append(.init(sourceHeadID: id, role: role, sourceKey: recordKey,
                snapshotSHA256: snapshot?.snapshotSHA256, jsonViewSHA256: snapshot?.viewSHA256))
        }
        guard Set(bundle.objects.map { Data($0.sourceObjectID.utf8) }).isSubset(of: Set(headIDs.map { Data($0.utf8) })) else {
            throw AnyDestinationMigrationError.invalidPlan("snapshot outside native source census")
        }
        let items = (current.items + added).enumerated().sorted {
            let left = $0.element.operation.phase, right = $1.element.operation.phase
            return left == right ? $0.offset < $1.offset : left < right
        }.map(\.element)
        let activeCoverage = Dictionary(uniqueKeysWithValues:
            current.coverage.map { (Data($0.sourceObjectID.utf8), $0.disposition) })
        let coverage = headIDs.map { id -> AnyDestinationCoverage in
            let keys = items.filter { Data($0.sourceObjectID.utf8) == Data(id.utf8) }.map(\.sourceKey)
            let disposition: AnyDestinationCoverage.Disposition
            switch activeCoverage[Data(id.utf8)] {
            case .canonicalProperty(let binding):
                disposition = .preservedCanonicalProperty(binding, immutableItemSourceKeys: keys)
            case .embeddedOption(let propertyKey, let evidence, let descriptorSHA256):
                disposition = .preservedEmbeddedOption(propertySourceKey: propertyKey, evidence: evidence,
                    descriptorSHA256: descriptorSHA256, immutableItemSourceKeys: keys)
            default: disposition = .mapped(itemSourceKeys: keys)
            }
            return .init(sourceObjectID: id, disposition: disposition)
        }
        struct Material: Encodable {
            let contract: String
            let sourceManifestSHA256: String
            let recoveredManifestSHA256: String
            let currentContentSHA256: String
            let archiveSHA256: String
            let unusedDefinitionIDs: [String]
            let sourceContextIDs: [String]
            let allImportedTypesUsable: Bool
            let items: [AnyDestinationMigrationItem]
            let coverage: [AnyDestinationCoverage]
        }
        let unusedIDs = unused.map { String(decoding: $0, as: UTF8.self) }.sorted {
            Data($0.utf8).lexicographicallyPrecedes(Data($1.utf8))
        }
        contexts.sort { Data($0.utf8).lexicographicallyPrecedes(Data($1.utf8)) }
        let material = try encoder.encode(Material(contract: Self.contract,
            sourceManifestSHA256: bundle.manifestSHA256, recoveredManifestSHA256: recoveredDefinitions.manifestSHA256,
            currentContentSHA256: current.contentSHA256, archiveSHA256: archive.sha256,
            unusedDefinitionIDs: unusedIDs, sourceContextIDs: contexts,
            allImportedTypesUsable: false, items: items, coverage: coverage))
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: material, encoded: material)
        self.bundle = bundle; self.recoveredDefinitions = recoveredDefinitions; currentContent = current
        self.archive = archive; self.records = records; uninstantiatedDefinitionIDs = unusedIDs
        preservedContextIDs = contexts; self.items = items; self.coverage = coverage
        contentSHA256 = AnyContentDigest.sha256(material)
        archiveItemSourceKey = fileKey; catalogObjectSourceKey = objectKey; catalogTypeSourceKey = typeKey
    }

    /// Explicit full-source preservation scope. The live-source coordinator's
    /// existing semantic admission remains unchanged and cannot accept this as
    /// a claim that every retained source type/layout is usable.
    public func preservationPlan(workspace: AnyTorahWorkspace, storeID: String,
                                 planID: String) throws -> AnyDestinationMigrationPlan {
        // Independently reconstruct the accepted active-content source/coverage
        // contract; do not replace canonical property proofs with catalog rows.
        _ = try currentContent.currentContentPlan(workspace: workspace, storeID: storeID,
                                                  planID: planID)
        return try .init(source: .init(bundle: bundle, semanticPlanSHA256: contentSHA256),
            workspace: workspace, storeID: storeID, planID: planID, coverage: coverage, items: items)
    }
}
