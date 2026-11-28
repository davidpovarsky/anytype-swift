import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

public enum AnyHeartNativeDefinitionPlanError: Error, Equatable, Sendable {
    case unsupported(String, String)
    case missingDefinition(String)
    case invalidValue(String, String)
    case wrongSource
}

/// Converts the captured definition vocabulary into prepared native drafts.
/// These drafts remain preview data until all reported semantic gaps have
/// explicit coverage in the enclosing destination plan.
public struct AnyHeartNativeDefinitionPlan: Sendable {
    public struct Issue: Equatable, Sendable {
        public let sourceObjectID: String
        public let field: String
        public let reason: String
    }
    public struct PropertyBinding: Sendable {
        public let relation: AnyHeartNativeDefinitionCatalog.Relation
        public let sourceKey: String
        public let kind: String
        public let format: String
        public let xKey: String
        public let owner: AnyDestinationReference
        public let record: AnyDestinationReference
        public let canonicalBinding: AnyDestinationCanonicalPropertyBinding?
        public var isCanonicalName: Bool { canonicalBinding?.propertyID == "name" }
        /// nil preserves absence; a captured true value is represented in the
        /// type's separate definitionHidden list, never in the title content.
        public var sourceHidden: Bool? { relation.snapshot.details["isHidden"]?.bool }
        public var address: AnyDestinationValue {
            .object([.init(key: .native("ownerId"), value: .reference(owner)),
                     .init(key: .native("propertyId"), value: .reference(record))])
        }
    }
    public struct TypeBinding: Sendable {
        public let definition: AnyHeartNativeDefinitionCatalog.TypeDefinition
        public let sourceKey: String
        public let xKey: String
        public var object: AnyDestinationReference {
            .mapped(sourceKey: sourceKey, slot: .objectID, encoding: .rawID)
        }
    }
    public struct ObjectBinding: Sendable {
        public let sourceObjectID: String
        public let destinationSourceKey: String
        public init(sourceObjectID: String, destinationSourceKey: String) {
            self.sourceObjectID = sourceObjectID; self.destinationSourceKey = destinationSourceKey
        }
    }
    public struct ValueGroup: Sendable {
        public let owner: AnyDestinationReference
        public let fields: AnyDestinationValue
        public let sourceRelationKeys: [String]
    }
    public struct Values: Sendable {
        /// Scalar/choice values can be part of immutable object creation.
        public let initialGroups: [ValueGroup]
        /// Object identities are translated only after all objects exist.
        public let deferredGroups: [ValueGroup]
        public let initialRelationKeys: [String]
        public let deferredRelationKeys: [String]
        /// Present source identities consumed by native object/space/type
        /// correspondence. They never enter a property-write payload.
        public let nativeIdentityRelationKeys: [String]
        /// Captured historical facts that must be represented separately by
        /// the enclosing immutable source-fact operation. They are deliberately
        /// absent from initial/deferred writes to the current native object.
        public let nativeDerivedSourceValues: [DerivedSourceValue]
        public let originalDetailsSHA256: String
        public var initialProperties: AnyDestinationValue {
            .object(initialGroups.map { .init(key: $0.owner, value: $0.fields) })
        }
    }

    public struct DerivedSourceValue: Sendable {
        public let sourceObjectID: String
        public let sourceRelationKey: String
        public let destinationPropertyID: String
        public let originalValue: AnyJSON
        public let snapshotSHA256: String
        public let jsonViewSHA256: String
    }

    public let catalog: AnyHeartNativeDefinitionCatalog
    /// A current-content dependency closure is explicitly narrower than the
    /// complete source vocabulary. The original full-catalogue initializer
    /// keeps its existing strict behavior when this value is nil.
    public let contentSelection: AnyHeartNativeContentSelection?
    public let catalogSourceKey: String?
    public let properties: [PropertyBinding]
    public let types: [TypeBinding]
    public let schemaItems: [AnyDestinationMigrationItem]
    /// Closed coverage for canonical properties and embedded option identities.
    /// Every ordinary schema item still requires its normal mapped coverage.
    public let definitionCoverage: [AnyDestinationCoverage]
    public let issues: [Issue]
    public let deferredDefinitionIssues: [Issue]
    public var permitsDestinationWrites: Bool { false }
    public var propertyOwner: AnyDestinationReference? {
        catalogSourceKey.map { .mapped(sourceKey: $0, slot: .objectID, encoding: .rawID) }
    }

    public init(catalog: AnyHeartNativeDefinitionCatalog,
                contentSelection: AnyHeartNativeContentSelection? = nil) throws {
        self.catalog = catalog
        self.contentSelection = contentSelection
        try contentSelection?.require(catalog)
        let selectedDefinitionIDs = contentSelection.map { Set($0.definitionObjectIDs.map { Data($0.utf8) }) }
        let allCatalogIssues = catalog.issues.map {
            Issue(sourceObjectID: $0.sourceObjectID, field: $0.field, reason: "captured-" + $0.kind.rawValue)
        }
        var issues = allCatalogIssues.filter { selectedDefinitionIDs?.contains(Data($0.sourceObjectID.utf8)) ?? true }
        deferredDefinitionIssues = allCatalogIssues.filter { selectedDefinitionIDs?.contains(Data($0.sourceObjectID.utf8)) == false }
        let selectedTypes = contentSelection.map { selection in
            let ids = Set(selection.typeObjectIDs.map { Data($0.utf8) })
            return catalog.types.filter { ids.contains(Data($0.objectID.utf8)) }
        } ?? catalog.types
        let selectedRelations = contentSelection.map { selection in
            let ids = Set(selection.relationObjectIDs.map { Data($0.utf8) })
            return catalog.relations.filter { ids.contains(Data($0.objectID.utf8)) }
        } ?? catalog.relations
        func key(_ kind: String, _ id: String) -> String {
            "heart-native-" + kind + ":" + Self.identity(catalog.sourceSpaceID, id, kind)
        }
        let types = selectedTypes.map {
            TypeBinding(definition: $0, sourceKey: key("type", $0.objectID),
                        xKey: "heart_type_" + Self.identity(catalog.sourceSpaceID, $0.objectID, "type-handle"))
        }
        let typesByID = Dictionary(uniqueKeysWithValues: types.map { (Data($0.definition.objectID.utf8), $0) })
        var items: [AnyDestinationMigrationItem] = [], properties: [PropertyBinding] = []
        var definitionCoverage: [AnyDestinationCoverage] = []
        let namespaceAnchor = selectedRelations.first { !Self.isNativeCanonicalIdentity($0) }
        let ownerKey = namespaceAnchor.map { key("property-catalog", $0.objectID) }
        if let ownerKey, let first = namespaceAnchor {
            // This is the destination property namespace. It does not claim
            // that a Heart Collection document has become an Any Collection.
            items.append(.init(sourceKey: ownerKey, sourceObjectID: first.objectID,
                operation: .collectionDefinition(.init(
                    xKey: "heart_properties_" + Self.identity(catalog.sourceSpaceID, "", "property-catalog"),
                    name: "Imported Heart properties", meta: .literal(.object([
                        "heartSourceSpaceID": .string(catalog.sourceSpaceID),
                        "heartCaptureSHA256": .string(catalog.captureManifestSHA256),
                        "heartPropertyNamespace": .bool(true),
                    ]))))))
        }
        for relation in selectedRelations {
            if Self.isNativeCanonicalIdentity(relation) {
                do {
                    let targetTypeEvidence: AnyDestinationDefinitionEvidence?
                    if ["spaceId", "type", "creator", "lastModifiedBy"].contains(relation.relationKey),
                       relation.targetTypeIDs.count == 1,
                       let target = catalog.types.first(where: {
                           Data($0.objectID.utf8) == Data(relation.targetTypeIDs[0].utf8)
                       }) {
                        targetTypeEvidence = try .init(snapshot: target.snapshot)
                    } else { targetTypeEvidence = nil }
                    let canonical = try AnyDestinationCanonicalPropertyBinding(
                        evidence: .init(snapshot: relation.snapshot), targetTypeEvidence: targetTypeEvidence)
                    guard catalog.relation(key: canonical.sourceRelationKey)?.objectID == relation.objectID else {
                        throw AnyHeartNativeDefinitionPlanError.missingDefinition(relation.objectID)
                    }
                    properties.append(.init(relation: relation, sourceKey: key("canonical-property", relation.objectID),
                        kind: canonical.derivedRole?.isTimestamp == true ? "datetime" : "string",
                        format: canonical.derivedRole.map { $0.isTimestamp ? "datetime" : "identity" } ??
                            (canonical.identityRole != nil ? "identity" : (canonical.propertyID == "name" ? "text" : "longtext")),
                        xKey: canonical.propertyID, owner: .native("any"), record: .native(canonical.propertyID),
                        canonicalBinding: canonical))
                    definitionCoverage.append(.init(sourceObjectID: relation.objectID, disposition: .canonicalProperty(canonical)))
                } catch {
                    // An overridden canonical definition is not copied to a
                    // second mutable field or silently treated as the builtin.
                    issues.append(.init(sourceObjectID: relation.objectID, field: "canonical-" + relation.relationKey,
                        reason: "captured-definition-does-not-match-qualified-native-contract"))
                }
                continue
            }
            guard let ownerKey else { throw AnyHeartNativeDefinitionPlanError.missingDefinition(relation.objectID) }
            if let hidden = relation.snapshot.details["isHidden"], hidden.bool == nil {
                issues.append(.init(sourceObjectID: relation.objectID, field: "isHidden",
                    reason: "invalid-definition-visibility-state")); continue
            }
            var inactive = false
            for field in ["isArchived", "isReadonly"] {
                if let state = relation.snapshot.details[field], state != .bool(false) {
                    issues.append(.init(sourceObjectID: relation.objectID, field: field,
                        reason: "definition-state-not-represented-by-mutable-native-property")); inactive = true
                }
            }
            if inactive { continue }
            guard let shape = Self.shape(relation) else {
                issues.append(.init(sourceObjectID: relation.objectID, field: "relationFormat",
                                    reason: "unsupported-native-format:\(relation.rawFormat)"))
                continue
            }
            var format: [String: AnyJSON] = ["type": .string(shape.format)]
            if relation.format == .file {
                format = AnyNativeFilePropertyFormat.descriptor(multiple: relation.maximumCount != 1)
                if !relation.targetTypeIDs.isEmpty {
                    issues.append(.init(sourceObjectID: relation.objectID, field: "relationFormatObjectTypes",
                        reason: "native-file-type-restriction-not-qualified"))
                }
            }
            var source: [String: AnyJSON] = [
                "sourceObjectID": .string(relation.objectID), "sourceUniqueKey": .string(relation.snapshot.uniqueKey),
                "relationKey": .string(relation.relationKey), "snapshotSHA256": .string(relation.snapshot.snapshotSHA256),
                "jsonViewSHA256": .string(relation.snapshot.viewSHA256),
                "definitionJSON": .string(try Self.jsonString(.object(relation.snapshot.details))),
            ]
            if let original = relation.sourceProvenance.originalAddedDate {
                source["sourceAddedDateSeconds"] = original
                source["sourceAddedDateContract"] = .string("pinkha-heart-source-added-date-seconds-v1")
            }
            if let value = relation.defaultValue {
                source["defaultValueJSON"] = .string(try Self.jsonString(value))
                if value != .null {
                    if AnyNativeImportedDefaultMetadata.qualifies(relation) {
                        source["defaultBehaviorContract"] = .string(AnyNativeImportedDefaultMetadata.contract)
                    } else {
                        issues.append(.init(sourceObjectID: relation.objectID, field: "relationDefaultValue",
                            reason: "default-retained; destination-new-object-default-behavior-not-qualified"))
                    }
                }
            }
            if relation.readonlyValue == true {
                issues.append(.init(sourceObjectID: relation.objectID, field: "relationReadonlyValue",
                    reason: "destination-property-is-not-a-native-derived-field"))
            }
            if let max = relation.maximumCount, max < 0 || max > 1 {
                issues.append(.init(sourceObjectID: relation.objectID, field: "relationMaxCount",
                    reason: "exact-positive-cardinality-not-represented-by-multiple-flag"))
            }
            if ["choice", "relation"].contains(shape.format) {
                let multiple = relation.maximumCount.map { $0 != 1 } ?? (relation.format != .status)
                format["config"] = .object(["multiple": .bool(multiple)])
            }
            if shape.format == "choice" {
                var options: [String: AnyJSON] = [:]
                for option in catalog.options(relationKey: relation.relationKey) {
                    guard Self.descriptorKey(option.objectID) else {
                        issues.append(.init(sourceObjectID: option.objectID, field: "objectID",
                                            reason: "option-identity-cannot-be-a-native-option-key")); continue
                    }
                    do {
                        let evidence = try AnyDestinationDefinitionEvidence(snapshot: option.snapshot)
                        let descriptor = try AnyDestinationDefinitionChecks.optionDescriptor(evidence, relationObjectID: relation.objectID)
                        options[option.objectID] = descriptor
                        definitionCoverage.append(.init(sourceObjectID: option.objectID,
                            disposition: .embeddedOption(propertySourceKey: key("property", relation.objectID),
                                evidence: evidence, descriptorSHA256: try AnyDestinationDefinitionChecks.digest(descriptor))))
                    } catch {
                        issues.append(.init(sourceObjectID: option.objectID, field: "option",
                            reason: "native-option-evidence-or-descriptor-not-representable"))
                    }
                }
                format["options"] = .object(options)
            }
            if shape.format == "relation" {
                var handles: [AnyJSON] = []
                for id in relation.targetTypeIDs {
                    guard let type = typesByID[Data(id.utf8)] else {
                        issues.append(.init(sourceObjectID: relation.objectID, field: "relationFormatObjectTypes",
                                            reason: "target-type-not-captured:" + id)); continue
                    }
                    // Native Any relation targets are type xKey handles, not
                    // newly allocated object IDs and not source type IDs.
                    handles.append(.string(type.xKey))
                }
                if !handles.isEmpty { format["relation"] = .object(["targetTypes": .array(handles)]) }
            }
            format["pinkhaHeart"] = .object(source)
            let binding = PropertyBinding(relation: relation, sourceKey: key("property", relation.objectID),
                kind: shape.kind, format: shape.format,
                xKey: "heart_property_" + Self.identity(catalog.sourceSpaceID, relation.objectID, "property-handle"),
                owner: .mapped(sourceKey: ownerKey, slot: .objectID, encoding: .rawID),
                record: .mapped(sourceKey: key("property", relation.objectID), slot: .record(index: 0), encoding: .rawID),
                canonicalBinding: nil)
            properties.append(binding)
            items.append(.init(sourceKey: binding.sourceKey, sourceObjectID: relation.objectID,
                operation: .propertyDefinition(owner: binding.owner,
                    kind: binding.kind, name: relation.name, xKey: binding.xKey, description: relation.description,
                    scope: "synced", xFormat: .literal(.object(format)), index: nil)))
        }
        let propertiesByID = Dictionary(uniqueKeysWithValues: properties.map { (Data($0.relation.objectID.utf8), $0) })
        for type in types {
            let definition = type.definition
            let isBookmark = definition.recommendedLayout == 11
            var recommendations: [AnyDestinationField] = []
            if let ownerKey {
                recommendations.append(.init(key: .native("propertyOwnerId"),
                    value: .reference(.mapped(sourceKey: ownerKey, slot: .objectID, encoding: .rawID))))
            }
            recommendations.append(.init(key: .native("contract"),
                value: .literal(.string(isBookmark
                    ? AnyNativeImportedTypePresentation.bookmarkContract
                    : AnyNativeImportedTypePresentation.contract))))
            recommendations.append(.init(key: .native("sourceRecommendedLayout"),
                value: .literal(definition.recommendedLayout.map(AnyJSON.integer) ?? .null)))
            // Source relation visibility is independent of a type's ordered
            // recommendedHiddenRelations. Preserve both concepts explicitly.
            recommendations.append(.init(key: .native("definitionHidden"),
                value: .array(properties.filter { $0.sourceHidden == true }.map(\.address))))
            for (field, ids) in [("recommended", definition.recommendedRelations),
                ("featured", definition.featuredRelations), ("hidden", definition.hiddenRelations),
                ("files", definition.fileRelations)] {
                let references: [AnyDestinationValue] = ids.compactMap {
                    propertiesByID[Data($0.utf8)].map(\.address)
                }
                if references.count != ids.count {
                    issues.append(.init(sourceObjectID: definition.objectID, field: field,
                                        reason: "recommended-property-not-mapped"))
                }
                recommendations.append(.init(key: .native(field), value: .array(references)))
            }
            if isBookmark {
                // This is the captured Bookmark's ordinary URL relation, not
                // the immutable sourceObject provenance relation. Both sides
                // of the native address come from the same definition plan.
                let candidates = properties.filter {
                    Data($0.relation.relationKey.utf8) == Data("source".utf8) &&
                    Data($0.relation.snapshot.uniqueKey.utf8) == Data("rel-source".utf8)
                }
                let visible = Set((definition.recommendedRelations + definition.featuredRelations).map { Data($0.utf8) })
                if let ownerKey, candidates.count == 1, let source = candidates.first,
                   source.relation.format == .url, source.kind == "string", source.format == "url",
                   source.canonicalBinding == nil, source.relation.maximumCount == 1,
                   source.relation.readonlyValue != true,
                   source.owner == .mapped(sourceKey: ownerKey, slot: .objectID, encoding: .rawID),
                   visible.contains(Data(source.relation.objectID.utf8)) {
                    recommendations.append(.init(key: .native("sourceURL"), value: source.address))
                } else {
                    issues.append(.init(sourceObjectID: definition.objectID, field: "sourceURL",
                        reason: "bookmark-requires-exact-mapped-visible-source-url-definition"))
                }
            }
            let layout = AnyDestinationValue.object([
                .init(key: .native("type"), value: .literal(.string(isBookmark ? "bookmark" : "page"))),
                .init(key: .native("config"), value: .object([
                    .init(key: .native("pinkhaHeart"), value: .object(recommendations)),
                ])),
            ])
            // Preserve the exact ordered identities in an explicit descriptor.
            // A page layout alone does not implement every Heart layout or
            // recommendation's application behavior.
            // Basic0 and Bookmark11 use their distinct closed presentation
            // contracts. Other native layouts retain their existing gaps.
            if definition.recommendedLayout != 0 && !isBookmark {
                issues.append(.init(sourceObjectID: definition.objectID, field: "recommendedLayout/recommendations",
                    reason: "native-layout-not-qualified:\(definition.recommendedLayout.map(String.init) ?? "absent")"))
            }
            var metadata: [String: AnyJSON] = [
                "heartSourceObjectID": .string(definition.objectID),
                "heartUniqueKey": .string(definition.snapshot.uniqueKey),
                "heartTypeKey": .string(definition.typeKey),
                "heartSnapshotSHA256": .string(definition.snapshot.snapshotSHA256),
                "heartJSONViewSHA256": .string(definition.snapshot.viewSHA256),
                "heartDefinitionJSON": .string(try Self.jsonString(.object(definition.snapshot.details))),
                AnyNativeImportedTypeOrder.contractKey: .string(AnyNativeImportedTypeOrder.contract),
                AnyNativeImportedTypeOrder.scopeKey: .string(catalog.contentSHA256),
            ]
            if let orderID = definition.orderID {
                metadata[AnyNativeImportedTypeOrder.valueKey] = .string(orderID)
            }
            if let original = definition.sourceProvenance.originalAddedDate {
                metadata["heartSourceAddedDateSeconds"] = original
                metadata["heartSourceAddedDateContract"] = .string("pinkha-heart-source-added-date-seconds-v1")
            }
            if contentSelection != nil {
                // Native definition metadata is a scalar map. The actual
                // immutable Records declaration remains in the owned part.
                metadata["heartSourceFactsContract"] = .string(AnyHeartNativeSourceFacts.contract)
                metadata["heartSourceFactsDataset"] = .string(AnyHeartNativeSourceFacts.datasetKey)
            }
            items.append(.init(sourceKey: type.sourceKey, sourceObjectID: definition.objectID,
                operation: .typeDefinition(.init(xKey: type.xKey, name: definition.name,
                    description: definition.description, layout: layout,
                    hidden: definition.snapshot.details["isHidden"]?.bool ?? false, meta: .literal(.object(metadata))))))
            // The ordinary native editor module supplies its schema. This
            // minimal part has the part and one dataset head in one batch.
            items.append(.init(sourceKey: key("editor-part", definition.objectID), sourceObjectID: definition.objectID,
                expectedRecordCount: 2, operation: .partDefinition(owner: type.object, draft: .literal(.object([
                    "key": .string("content"), "name": .string("Content"), "pos": .string("m"),
                    "ui": .object(["type": .string("document")]),
                    "datasets": .array([.object(["module": .string("editor"), "key": .string("editor_blocks")])]),
                ])))))
            if contentSelection != nil { items.append(AnyHeartNativeSourceFacts.definitionItem(type: type)) }
        }
        self.catalogSourceKey = ownerKey; self.types = types; self.properties = properties
        self.schemaItems = items; self.definitionCoverage = definitionCoverage; self.issues = issues
    }

    /// Full execution must consume this guard, together with the enclosing
    /// source census and remaining object/block/file/history coverage.
    public func admittedSchemaItems() throws -> [AnyDestinationMigrationItem] {
        guard let issue = issues.first else { return schemaItems }
        throw AnyHeartNativeDefinitionPlanError.unsupported(issue.sourceObjectID, issue.field + ":" + issue.reason)
    }

    public func type(sourceURL: String) -> TypeBinding? {
        guard let definition = catalog.type(url: sourceURL) else { return nil }
        return types.first { Data($0.definition.objectID.utf8) == Data(definition.objectID.utf8) }
    }
    public func property(sourceKey: String) -> PropertyBinding? {
        guard let relation = catalog.relation(key: sourceKey) else { return nil }
        return properties.first { Data($0.relation.objectID.utf8) == Data(relation.objectID.utf8) }
    }

    /// Maps exactly the requested present details. The caller retains a census
    /// of every unrequested field; selection does not grant whole-object
    /// coverage. Unknown/ambiguous keys and nulls never become guessed values.
    public func values(snapshot: AnyHeartNativeSnapshotView, relationKeys: [String],
                       objects: [ObjectBinding], files: [AnyHeartNativeFileBinding] = []) throws -> Values {
        try contentSelection?.require(snapshot)
        guard Data(snapshot.sourceSpaceID.utf8) == Data(catalog.sourceSpaceID.utf8),
              Set(relationKeys.map { Data($0.utf8) }).count == relationKeys.count else {
            throw AnyHeartNativeDefinitionPlanError.wrongSource
        }
        var targets: [Data: String] = [:]
        for object in objects {
            let key = Data(object.sourceObjectID.utf8)
            guard !key.isEmpty, targets[key] == nil,
                  AnyPreparedMigrationPlanBinding.validOpaque(object.destinationSourceKey, maximum: 4096) else {
                throw AnyHeartNativeDefinitionPlanError.wrongSource
            }
            targets[key] = object.destinationSourceKey
        }
        var fileTargets: [Data: AnyHeartNativeFileBinding] = [:], fileNames = Set<String>()
        for file in files {
            guard Data(file.sourceAccountID.utf8) == Data(catalog.sourceAccountID.utf8),
                  Data(file.sourceSpaceID.utf8) == Data(catalog.sourceSpaceID.utf8),
                  file.captureManifestSHA256 == catalog.captureManifestSHA256,
                  file.sourceWitnessSHA256 == catalog.sourceWitnessSHA256,
                  fileTargets.updateValue(file, forKey: Data(file.fileID.utf8)) == nil,
                  fileNames.insert(file.fileID).inserted else {
                throw AnyHeartNativeDefinitionPlanError.wrongSource
            }
        }
        var initial: [(AnyDestinationReference, [AnyDestinationField], [String])] = []
        var deferred: [(AnyDestinationReference, [AnyDestinationField], [String])] = []
        var initialKeys: [String] = [], deferredKeys: [String] = [], nativeIdentityKeys: [String] = []
        var nativeDerivedSourceValues: [DerivedSourceValue] = []
        func append(_ field: AnyDestinationField, owner: AnyDestinationReference, key: String,
                    to groups: inout [(AnyDestinationReference, [AnyDestinationField], [String])]) throws {
            let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
            let identity = try encoder.encode(owner)
            if let index = try groups.firstIndex(where: { try encoder.encode($0.0) == identity }) {
                groups[index].1.append(field); groups[index].2.append(key)
            } else { groups.append((owner, [field], [key])) }
        }
        for key in relationKeys {
            guard let binding = property(sourceKey: key), let value = snapshot.details[key] else {
                throw AnyHeartNativeDefinitionPlanError.missingDefinition(key)
            }
            if let role = binding.canonicalBinding?.identityRole {
                try validateNativeIdentity(value, role: role, snapshot: snapshot, targets: targets)
                nativeIdentityKeys.append(key)
                continue
            }
            if let role = binding.canonicalBinding?.derivedRole {
                // Any's author is the destination signing account, whereas a
                // Heart creator may name a captured Participant object. The
                // identities and clocks are not interchangeable. Retain the
                // exact source value and require a separate immutable fact.
                if role.isTimestamp {
                    guard value.integer != nil else {
                        throw AnyHeartNativeDefinitionPlanError.invalidValue(key, "historical integer epoch seconds required")
                    }
                } else {
                    let identities = value.string.map { [$0] } ?? value.array?.compactMap(\.string)
                    guard let identities, identities.count <= 1,
                          value.array == nil || identities.count == value.array?.count,
                          identities.allSatisfy({ AnyDestinationPlanChecks.identity($0) }) else {
                        throw AnyHeartNativeDefinitionPlanError.invalidValue(key, "historical singular participant identity required")
                    }
                }
                nativeDerivedSourceValues.append(.init(sourceObjectID: snapshot.sourceObjectID,
                    sourceRelationKey: key, destinationPropertyID: role.rawValue, originalValue: value,
                    snapshotSHA256: snapshot.snapshotSHA256, jsonViewSHA256: snapshot.viewSHA256))
                continue
            }
            let mapped = try map(value, property: binding, targets: targets, files: fileTargets)
            let field = AnyDestinationField(key: binding.record, value: mapped)
            if binding.relation.format == .object || binding.relation.format == .file {
                try append(field, owner: binding.owner, key: key, to: &deferred); deferredKeys.append(key)
            } else { try append(field, owner: binding.owner, key: key, to: &initial); initialKeys.append(key) }
        }
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return .init(initialGroups: initial.map { .init(owner: $0.0, fields: .object($0.1), sourceRelationKeys: $0.2) },
            deferredGroups: deferred.map { .init(owner: $0.0, fields: .object($0.1), sourceRelationKeys: $0.2) }, initialRelationKeys: initialKeys,
            deferredRelationKeys: deferredKeys, nativeIdentityRelationKeys: nativeIdentityKeys,
            nativeDerivedSourceValues: nativeDerivedSourceValues,
            originalDetailsSHA256: AnyContentDigest.sha256(try encoder.encode(AnyJSON.object(snapshot.details))))
    }

    static func isNativeCanonicalIdentity(_ relation: AnyHeartNativeDefinitionCatalog.Relation) -> Bool {
        relation.snapshot.nativeType == 521 && ["name", "description", "id", "spaceId", "type",
            "creator", "createdDate", "lastModifiedDate", "lastModifiedBy"].contains(relation.relationKey) &&
        Data(relation.snapshot.uniqueKey.utf8) == Data(("rel-" + relation.relationKey).utf8)
    }

    /// Heart's system relation is a link to the current object, source space
    /// or its actual captured Type. The destination verifier already compares
    /// root id + spaceId and any.type for every migrated object; source IDs
    /// must never be written into those native target fields.
    private func validateNativeIdentity(_ value: AnyJSON,
                                        role: AnyDestinationCanonicalPropertyBinding.IdentityRole,
                                        snapshot: AnyHeartNativeSnapshotView,
                                        targets: [Data: String]) throws {
        func invalid(_ reason: String) -> AnyHeartNativeDefinitionPlanError {
            .invalidValue(role.rawValue, reason)
        }
        guard targets[Data(snapshot.sourceObjectID.utf8)] != nil else {
            throw invalid("native identity requires the current object mapping")
        }
        let sourceIdentity: String
        if let scalar = value.string { sourceIdentity = scalar }
        else if let rows = value.array, rows.count == 1, let scalar = rows[0].string { sourceIdentity = scalar }
        else { throw invalid("one exact native identity required") }
        let expected: [String]
        switch role {
        case .id: expected = [snapshot.sourceObjectID]
        case .spaceId: expected = [snapshot.sourceSpaceID]
        case .type:
            guard snapshot.objectTypes.count == 1,
                  let sourceType = catalog.type(url: snapshot.objectTypes[0]) else {
                throw invalid("one captured native Type required")
            }
            expected = [sourceType.objectID, sourceType.typeURL]
        }
        guard expected.contains(where: { Data($0.utf8) == Data(sourceIdentity.utf8) }) else {
            throw invalid("source native identity differs from the captured object context")
        }
    }

    private func map(_ value: AnyJSON, property: PropertyBinding, targets: [Data: String],
                     files: [Data: AnyHeartNativeFileBinding]) throws -> AnyDestinationValue {
        let relation = property.relation
        func invalid(_ reason: String) -> AnyHeartNativeDefinitionPlanError { .invalidValue(relation.relationKey, reason) }
        guard value != .null else { throw invalid("explicit-null-has-no-qualified-target-value") }
        switch relation.format {
        case .longText, .shortText, .emoji, .url, .email, .phone:
            guard value.string != nil else { throw invalid("string required") }
            return .literal(value)
        case .number:
            switch value {
            case .integer: return .literal(value)
            case .number(let number) where number.isFinite: return .literal(value)
            default: throw invalid("finite number required")
            }
        case .checkbox:
            guard value.bool != nil else { throw invalid("boolean required") }
            return .literal(value)
        case .date:
            // Native Heart dates are epoch seconds; Any native datetime is
            // epoch milliseconds. Refuse precision/calendar transformations.
            guard let seconds = value.integer, seconds >= -9_007_199_254_740,
                  seconds <= 9_007_199_254_740 else { throw invalid("exact bounded integer epoch seconds required") }
            if relation.includeTime != true && seconds % 86_400 != 0 {
                throw invalid("date-without-time-is-not-midnight-UTC")
            }
            return .literal(.object(["$date": .integer(seconds * 1000)]))
        case .file:
            guard let rows = value.array, rows.count <= 20_000 else { throw invalid("bounded file array required") }
            let maximum = relation.maximumCount ?? 0
            guard maximum <= 0 || rows.count <= maximum else { throw invalid("source file cardinality exceeded") }
            return .array(try rows.map { row in
                guard let id = row.string, let file = files[Data(id.utf8)] else {
                    throw invalid("unmapped native file identity")
                }
                return .reference(file.reference)
            })
        case .status, .tag, .object:
            guard let rows = value.array, rows.count <= 20_000 else { throw invalid("bounded array required") }
            let max = relation.maximumCount ?? (relation.format == .status ? 1 : 0)
            guard max <= 0 || rows.count <= max else { throw invalid("source cardinality exceeded") }
            return .array(try rows.map { row in
                guard let id = row.string, !id.isEmpty else { throw invalid("reference/option ID required") }
                if relation.format == .object {
                    guard let target = targets[Data(id.utf8)] else { throw invalid("unmapped object reference:" + id) }
                    return .reference(.mapped(sourceKey: target, slot: .objectID, encoding: .anyURI))
                }
                guard let option = catalog.option(objectID: id),
                      Data(option.relationKey.utf8) == Data(relation.relationKey.utf8) else {
                    throw invalid("unknown or foreign option:" + id)
                }
                return .literal(.string(option.objectID))
            })
        default: throw invalid("unsupported format")
        }
    }

    private static func shape(_ relation: AnyHeartNativeDefinitionCatalog.Relation) -> (kind: String, format: String)? {
        switch relation.format {
        case .longText: ("string", "longtext")
        case .shortText, .emoji: ("string", "text")
        case .number: ("number", "number")
        case .checkbox: ("boolean", "checkbox")
        case .url: ("string", "url")
        case .email: ("string", "email")
        case .phone: ("string", "phone")
        case .date: ("datetime", relation.includeTime == true ? "datetime" : "date")
        case .file: ("array", AnyNativeFilePropertyFormat.slug)
        case .status, .tag: ("array", "choice")
        case .object: ("array", "relation")
        default: nil
        }
    }
    private static func identity(_ space: String, _ id: String, _ kind: String) -> String {
        AnyContentDigest.sha256(AnyPreparedMigrationPlanBinding.material([
            "pinkha-heart-native-definition/v1", space, id, kind,
        ]))
    }
    private static func jsonString(_ value: AnyJSON) throws -> String {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return String(decoding: try encoder.encode(value), as: UTF8.self)
    }
    private static func descriptorKey(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 256 && !value.contains(".") && !value.hasPrefix("$")
    }
}
