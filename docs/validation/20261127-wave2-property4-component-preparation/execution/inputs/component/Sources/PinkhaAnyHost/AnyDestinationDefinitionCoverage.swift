import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

/// Exact, bounded source material for definitions represented by an existing
/// native property or an embedded option rather than a newly created object.
/// The outer source binding still owns account, authorization and checkpoint.
public struct AnyDestinationDefinitionEvidence: Codable, Equatable, Sendable {
    public let sourceSpaceID: String
    public let sourceObjectID: String
    public let protobufBytes: Data
    public let jsonViewBytes: Data
    let snapshot: AnyHeartNativeSnapshotView
    public var snapshotSHA256: String { snapshot.snapshotSHA256 }
    public var viewSHA256: String { snapshot.viewSHA256 }

    public init(snapshot: AnyHeartNativeSnapshotView) throws {
        try self.init(sourceSpaceID: snapshot.sourceSpaceID, sourceObjectID: snapshot.sourceObjectID,
                      protobufBytes: snapshot.protobufBytes, jsonViewBytes: snapshot.jsonViewBytes)
    }
    public init(sourceSpaceID: String, sourceObjectID: String, protobufBytes: Data, jsonViewBytes: Data) throws {
        guard !protobufBytes.isEmpty, protobufBytes.count <= 1_048_576,
              !jsonViewBytes.isEmpty, jsonViewBytes.count <= 1_048_576 else {
            throw AnyDestinationMigrationError.invalidPlan("definition evidence bounds")
        }
        snapshot = try .init(jsonView: jsonViewBytes, snapshotBytes: protobufBytes,
                             sourceSpaceID: sourceSpaceID, sourceObjectID: sourceObjectID)
        self.sourceSpaceID = sourceSpaceID; self.sourceObjectID = sourceObjectID
        self.protobufBytes = protobufBytes; self.jsonViewBytes = jsonViewBytes
    }
    private enum CodingKeys: String, CodingKey { case sourceSpaceID, sourceObjectID, protobufBytes, jsonViewBytes }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        try self.init(sourceSpaceID: c.decode(String.self, forKey: .sourceSpaceID),
                      sourceObjectID: c.decode(String.self, forKey: .sourceObjectID),
                      protobufBytes: c.decode(Data.self, forKey: .protobufBytes),
                      jsonViewBytes: c.decode(Data.self, forKey: .jsonViewBytes))
    }
    public static func == (a: Self, b: Self) -> Bool {
        Data(a.sourceSpaceID.utf8) == Data(b.sourceSpaceID.utf8) &&
        Data(a.sourceObjectID.utf8) == Data(b.sourceObjectID.utf8) &&
        a.protobufBytes == b.protobufBytes && a.jsonViewBytes == b.jsonViewBytes
    }
    func requireSource(_ source: AnyDestinationSourceBinding, objectID: String) throws {
        guard Data(source.spaceID.utf8) == Data(sourceSpaceID.utf8),
              Data(objectID.utf8) == Data(sourceObjectID.utf8),
              let member = source.definitionMembers[Data(objectID.utf8)],
              member.nativeType == snapshot.nativeType,
              Data(member.uniqueKey.utf8) == Data(snapshot.uniqueKey.utf8),
              member.snapshotSHA256 == snapshotSHA256, member.snapshotBytes == protobufBytes.count,
              member.viewSHA256 == viewSHA256, member.viewBytes == jsonViewBytes.count else {
            throw AnyDestinationMigrationError.invalidPlan("foreign definition evidence")
        }
    }
}

/// Exact correspondence with an existing native property. Source definitions
/// remain bound to their original bytes; no native schema is created or patched.
public struct AnyDestinationCanonicalPropertyBinding: Codable, Equatable, Sendable {
    public static let contract = "pinkha-native-any-name-v1"
    public static let descriptionContract = "pinkha-native-any-description-v1"
    public enum IdentityRole: String, Codable, Sendable { case id, spaceId, type }
    /// A destination's native clocks/signers remain native. Captured historical
    /// values belong to the immutable source facts, never to these fields.
    public enum DerivedRole: String, Codable, Sendable {
        case author, createdAt, modifiedAt, modifiedBy
        public var sourceKey: String {
            switch self {
            case .author: "creator"
            case .createdAt: "createdDate"
            case .modifiedAt: "lastModifiedDate"
            case .modifiedBy: "lastModifiedBy"
            }
        }
        public var isTimestamp: Bool { self == .createdAt || self == .modifiedAt }
    }
    public let evidence: AnyDestinationDefinitionEvidence
    /// The captured target Type of a system relation, in the same source
    /// checkpoint. Registry labels cannot substitute for this native object.
    public let targetTypeEvidence: AnyDestinationDefinitionEvidence?
    public let ownerID: String
    public let propertyID: String
    public let nativeContract: String
    public let nativeDescriptorSHA256: String
    public var sourceHidden: Bool? { evidence.snapshot.details["isHidden"]?.bool }
    public var identityRole: IdentityRole? { IdentityRole(rawValue: propertyID) }
    public var derivedRole: DerivedRole? { DerivedRole(rawValue: propertyID) }
    public var sourceRelationKey: String { derivedRole?.sourceKey ?? propertyID }

    // SDK e195f6/internal/types/any/any.go. The executor admits the complete
    // actual native HTTP descriptor again before its first mutation.
    public static let nativeDescriptor: AnyJSON = .object([
        "id": .string("name"), "name": .string("Name"), "description": .string("Display name."),
        "kind": .string("string"), "scope": .string("synced"),
        "xFormat": .object(["type": .string("text")]),
    ])
    public static let nativeDescriptionDescriptor: AnyJSON = .object([
        "id": .string("description"), "name": .string("Description"), "description": .string("Display description."),
        "kind": .string("string"), "scope": .string("synced"),
        "xFormat": .object(["type": .string("longtext")]),
    ])
    public static func nativeIdentityDescriptor(_ role: IdentityRole) -> AnyJSON {
        switch role {
        case .id: .object([
            "id": .string("id"), "name": .string("Id"),
            "description": .string("Object id; derived, never written."),
            "kind": .string("string"), "scope": .string("derived"),
        ])
        case .spaceId: .object([
            "id": .string("spaceId"), "name": .string("Space"),
            "description": .string("Id of the space the object lives in; derived."),
            "kind": .string("string"), "scope": .string("derived"),
        ])
        case .type: .object([
            "id": .string("type"), "name": .string("Type"),
            "description": .string("Id of the object's type; a definition object carries its marker here."),
            "kind": .string("string"), "scope": .string("synced"),
        ])
        }
    }

    public static func nativeDerivedDescriptor(_ role: DerivedRole) -> AnyJSON {
        let name: String, description: String
        switch role {
        case .author:
            name = "Author"; description = "Account identity that created the object; derived."
        case .createdAt:
            name = "Created at"; description = "Instant of the creating change (author's clock); derived."
        case .modifiedAt:
            name = "Modified at"; description = "Instant of the latest valid synced change (author's clock); derived."
        case .modifiedBy:
            name = "Modified by"; description = "Account identity that signed the change modifiedAt names; derived."
        }
        var fields: [String: AnyJSON] = ["id": .string(role.rawValue), "name": .string(name),
            "description": .string(description), "kind": .string(role.isTimestamp ? "datetime" : "string"),
            "scope": .string("derived")]
        if role.isTimestamp { fields["xFormat"] = .object(["type": .string("datetime")]) }
        return .object(fields)
    }

    public init(evidence: AnyDestinationDefinitionEvidence,
                targetTypeEvidence: AnyDestinationDefinitionEvidence? = nil) throws {
        self.evidence = evidence; self.targetTypeEvidence = targetTypeEvidence; ownerID = "any"
        switch Data(evidence.snapshot.uniqueKey.utf8) {
        case Data("rel-name".utf8): propertyID = "name"
        case Data("rel-description".utf8): propertyID = "description"
        case Data("rel-id".utf8): propertyID = "id"
        case Data("rel-spaceId".utf8): propertyID = "spaceId"
        case Data("rel-type".utf8): propertyID = "type"
        case Data("rel-creator".utf8): propertyID = "author"
        case Data("rel-createdDate".utf8): propertyID = "createdAt"
        case Data("rel-lastModifiedDate".utf8): propertyID = "modifiedAt"
        case Data("rel-lastModifiedBy".utf8): propertyID = "modifiedBy"
        default: throw AnyDestinationMigrationError.invalidPlan("unknown canonical property identity")
        }
        let required = try Self.specification(propertyID)
        nativeContract = required.contract
        nativeDescriptorSHA256 = try AnyDestinationDefinitionChecks.digest(required.descriptor)
        try validate()
    }
    var expectedNativeDescriptor: AnyJSON { get throws { try Self.specification(propertyID).descriptor } }

    private struct Specification {
        let contract: String
        let descriptor: AnyJSON
        let sourceFormat: Int64
        let sourceName: String
        let sourceDescription: String
        let sourceReadonly: Bool
        let targetTypeUniqueKey: String?
        var sourceIncludeTime: Bool { sourceFormat == 4 }
    }
    private static func specification(_ propertyID: String) throws -> Specification {
        switch propertyID {
        case "name": return .init(contract: contract, descriptor: nativeDescriptor, sourceFormat: 1,
            sourceName: "Name", sourceDescription: "Name of the object", sourceReadonly: false, targetTypeUniqueKey: nil)
        case "description": return .init(contract: descriptionContract, descriptor: nativeDescriptionDescriptor, sourceFormat: 0,
            sourceName: "Description", sourceDescription: "", sourceReadonly: false, targetTypeUniqueKey: nil)
        case "id": return .init(contract: "pinkha-native-any-self-identity-v1", descriptor: nativeIdentityDescriptor(.id),
            sourceFormat: 100, sourceName: "Anytype ID", sourceDescription: "Link to itself. Used in databases",
            sourceReadonly: false, targetTypeUniqueKey: nil)
        case "spaceId": return .init(contract: "pinkha-native-any-space-identity-v1", descriptor: nativeIdentityDescriptor(.spaceId),
            sourceFormat: 100, sourceName: "Space ID", sourceDescription: "Space belongs to",
            sourceReadonly: true, targetTypeUniqueKey: "ot-space")
        case "type": return .init(contract: "pinkha-native-any-type-membership-v1", descriptor: nativeIdentityDescriptor(.type),
            sourceFormat: 100, sourceName: "Object type", sourceDescription: "Relation that stores the object's type",
            sourceReadonly: true, targetTypeUniqueKey: "ot-objectType")
        case "author": return .init(contract: "pinkha-native-any-derived-author-v1", descriptor: nativeDerivedDescriptor(.author),
            sourceFormat: 100, sourceName: "Created by", sourceDescription: "Human which created this object",
            sourceReadonly: true, targetTypeUniqueKey: "ot-participant")
        case "createdAt": return .init(contract: "pinkha-native-any-derived-created-at-v1", descriptor: nativeDerivedDescriptor(.createdAt),
            sourceFormat: 4, sourceName: "Creation date", sourceDescription: "Date when the object was initially created",
            sourceReadonly: true, targetTypeUniqueKey: nil)
        case "modifiedAt": return .init(contract: "pinkha-native-any-derived-modified-at-v1", descriptor: nativeDerivedDescriptor(.modifiedAt),
            sourceFormat: 4, sourceName: "Last modified date", sourceDescription: "Date when the object was modified last time",
            sourceReadonly: true, targetTypeUniqueKey: nil)
        case "modifiedBy": return .init(contract: "pinkha-native-any-derived-modified-by-v1", descriptor: nativeDerivedDescriptor(.modifiedBy),
            sourceFormat: 100, sourceName: "Last modified by", sourceDescription: "Human who updated the object last time",
            sourceReadonly: true, targetTypeUniqueKey: "ot-participant")
        default: throw AnyDestinationMigrationError.invalidPlan("unknown canonical property identity")
        }
    }
    func validate() throws {
        let row = evidence.snapshot, d = row.details, required = try Self.specification(propertyID)
        guard ownerID == "any", nativeContract == required.contract,
              nativeDescriptorSHA256 == (try AnyDestinationDefinitionChecks.digest(required.descriptor)),
              row.nativeType == 521, Data(row.uniqueKey.utf8) == Data(("rel-" + sourceRelationKey).utf8),
              d["relationKey"] == .string(sourceRelationKey), d["relationFormat"] == .integer(required.sourceFormat),
              d["relationMaxCount"] == .integer(1), d["relationReadonlyValue"] == .bool(required.sourceReadonly),
              d["relationDefaultValue"] == .null, d["relationFormatIncludeTime"] == .bool(required.sourceIncludeTime),
              d["name"] == .string(required.sourceName), d["description"] == .string(required.sourceDescription),
              d["isArchived"] == nil || d["isArchived"] == .bool(false),
              d["isHidden"] == nil || d["isHidden"]?.bool != nil,
              d["isReadonly"] == nil || d["isReadonly"] == .bool(false), row.issues.isEmpty else {
            throw AnyDestinationMigrationError.invalidPlan("canonical native property contract")
        }
        guard Set(d.keys).isSubset(of: AnyDestinationDefinitionChecks.nameDetailFields) else {
            throw AnyDestinationMigrationError.invalidPlan("unknown canonical native property semantics")
        }
        if let expected = required.targetTypeUniqueKey {
            guard let target = targetTypeEvidence,
                  Data(target.sourceSpaceID.utf8) == Data(evidence.sourceSpaceID.utf8),
                  target.snapshot.nativeType == 528,
                  Data(target.snapshot.uniqueKey.utf8) == Data(expected.utf8), target.snapshot.issues.isEmpty,
                  let values = d["relationFormatObjectTypes"]?.array, values.count == 1,
                  values[0].string.map({ Data($0.utf8) }) == Data(target.sourceObjectID.utf8) else {
                throw AnyDestinationMigrationError.invalidPlan("canonical system relation target Type")
            }
        } else {
            guard targetTypeEvidence == nil, d["relationFormatObjectTypes"] == .array([]) else {
                throw AnyDestinationMigrationError.invalidPlan("unexpected canonical relation target Type")
            }
        }
    }
    func requireSource(_ source: AnyDestinationSourceBinding, objectID: String) throws {
        try evidence.requireSource(source, objectID: objectID)
        if let targetTypeEvidence {
            try targetTypeEvidence.requireSource(source, objectID: targetTypeEvidence.sourceObjectID)
        }
    }
    private enum CodingKeys: String, CodingKey {
        case evidence, targetTypeEvidence, ownerID, propertyID, nativeContract, nativeDescriptorSHA256
    }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        evidence = try c.decode(AnyDestinationDefinitionEvidence.self, forKey: .evidence)
        targetTypeEvidence = try c.decodeIfPresent(AnyDestinationDefinitionEvidence.self, forKey: .targetTypeEvidence)
        ownerID = try c.decode(String.self, forKey: .ownerID)
        propertyID = try c.decode(String.self, forKey: .propertyID)
        nativeContract = try c.decode(String.self, forKey: .nativeContract)
        nativeDescriptorSHA256 = try c.decode(String.self, forKey: .nativeDescriptorSHA256)
        try validate()
    }
}

struct AnyDestinationDefinitionMember: Equatable, Sendable {
    let nativeType: Int64
    let uniqueKey: String
    let snapshotSHA256: String
    let snapshotBytes: Int
    let viewSHA256: String
    let viewBytes: Int
}

enum AnyDestinationDefinitionChecks {
    static let nameDetailFields: Set<String> = [
        "name", "description", "isHidden", "layout", "origin", "revision", "sourceObject", "apiObjectKey",
        "internalFlags", "iconEmoji", "iconImage", "createdDate", "creator", "lastModifiedDate", "lastModifiedBy",
        "isArchived", "isReadonly", "uniqueKey", "type", "id", "spaceId", "relationKey", "relationFormat",
        "relationFormatIncludeTime", "relationFormatObjectTypes", "relationMaxCount", "relationReadonlyValue",
        "relationDefaultValue",
    ]
    static let optionDetailFields: Set<String> = [
        "name", "description", "isHidden", "layout", "origin", "revision", "sourceObject", "apiObjectKey",
        "internalFlags", "iconEmoji", "iconImage", "createdDate", "creator", "lastModifiedDate", "lastModifiedBy",
        "isArchived", "isReadonly", "uniqueKey", "type", "id", "spaceId", "relationKey", "relationOptionColor", "orderId", "addedDate",
    ]
    /// This is the declaration-to-evidence digest join. Full bundle byte
    /// verification and current account/checkpoint authorization remain the
    /// source reader/authorizer's responsibility. A replaced self-consistent
    /// pair cannot pass this join under the original manifest SHA.
    static func members(manifest: Data, accountID: String, spaceID: String,
                        witnessSHA256: String, manifestSHA256: String) throws -> [Data: AnyDestinationDefinitionMember] {
        guard !manifest.isEmpty, manifest.count <= 16 * 1024 * 1024,
              AnyContentDigest.sha256(manifest) == manifestSHA256 else {
            throw AnyDestinationMigrationError.invalidPlan("definition manifest digest/bounds")
        }
        let root = try JSONDecoder().decode(AnyJSON.self, from: manifest)
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: manifest, encoded: bytes(root))
        let receipt = root["Receipt"], inventory = receipt?["Inventory"], account = receipt?["Source"]
        let accountHash = AnyContentDigest.sha256(Data(accountID.utf8))
        let spaceHash = AnyContentDigest.sha256(Data(spaceID.utf8))
        guard root["Contract"] == .string("pinkha-native-whole-source-bundle-v1"),
              receipt?["Version"] == .string("loaded-account-native-space-source-v1"),
              receipt?["AccountSessionAuthorizedAtFinalCapture"] == .bool(true),
              receipt?["AllNativeHeadRowsAccounted"] == .bool(true),
              receipt?["CapturedSnapshotsBoundToUnchangedCheckpoint"] == .bool(true),
              inventory?["SourceWitnessSHA256"] == .string(witnessSHA256),
              inventory?["SpaceSHA256"] == .string(spaceHash),
              account?["accountSHA256"] == .string(accountHash),
              account?["source"]?["accountSHA256"] == .string(accountHash),
              account?["source"]?["spaceSHA256"] == .string(spaceHash),
              account?["source"]?["native"]?["WitnessSHA256"] == .string(witnessSHA256),
              let rows = root["Objects"]?.array, rows.count <= AnyDestinationMigrationPlan.maximumItems else {
            throw AnyDestinationMigrationError.invalidPlan("definition manifest source binding")
        }
        var result: [Data: AnyDestinationDefinitionMember] = [:], strings = Set<String>()
        for row in rows {
            guard let fields = row.object,
                  Set(fields.keys) == ["ObjectID", "UniqueKey", "NativeType", "Snapshot", "NativeJSONView"],
                  let id = row["ObjectID"]?.string, AnyDestinationPlanChecks.identity(id),
                  result[Data(id.utf8)] == nil, strings.insert(id).inserted,
                  let kind = row["NativeType"]?.integer, kind >= 0, kind <= Int64(Int32.max),
                  let key = row["UniqueKey"]?.string, key.utf8.count <= 4096, !key.utf8.contains(0) else {
                throw AnyDestinationMigrationError.invalidPlan("definition manifest object identity")
            }
            let hash = AnyContentDigest.sha256(Data(id.utf8))
            func member(_ field: String, suffix: String, maximum: Int64) throws -> (String, Int) {
                guard let value = row[field], let fields = value.object, Set(fields.keys) == ["Path", "SHA256", "Bytes"],
                      value["Path"] == .string("snapshot-" + hash + suffix),
                      let sha = value["SHA256"]?.string, AnyDestinationPlanChecks.digest(sha),
                      let count = value["Bytes"]?.integer, count > 0, count <= maximum else {
                    throw AnyDestinationMigrationError.invalidPlan("definition manifest member")
                }
                return (sha, Int(count))
            }
            let pb = try member("Snapshot", suffix: ".pb", maximum: 8 * 1024 * 1024)
            let json = try member("NativeJSONView", suffix: ".json", maximum: 32 * 1024 * 1024)
            result[Data(id.utf8)] = .init(nativeType: kind, uniqueKey: key, snapshotSHA256: pb.0,
                                         snapshotBytes: pb.1, viewSHA256: json.0, viewBytes: json.1)
        }
        return result
    }
    static func bytes(_ value: AnyJSON) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(value)
    }
    static func digest(_ value: AnyJSON) throws -> String { AnyContentDigest.sha256(try bytes(value)) }
    static func optionDescriptor(_ evidence: AnyDestinationDefinitionEvidence,
                                 relationObjectID: String) throws -> AnyJSON {
        let row = evidence.snapshot, d = row.details
        let provenance = try AnyHeartNativeDefinitionCatalog.SourceProvenance(snapshot: row)
        let unique = row.uniqueKey.split(separator: "-", omittingEmptySubsequences: false)
        guard row.nativeType == 529, row.issues.isEmpty,
              Set(d.keys).isSubset(of: optionDetailFields),
              d["isArchived"] == nil || d["isArchived"] == .bool(false),
              d["isHidden"] == nil || d["isHidden"] == .bool(false),
              d["isReadonly"] == nil || d["isReadonly"] == .bool(false),
              d["iconEmoji"] == nil || d["iconEmoji"] == .string(""),
              d["iconImage"] == nil || d["iconImage"] == .string(""),
              unique.count == 2, unique[0] == "opt", !unique[1].isEmpty,
              !row.sourceObjectID.isEmpty, row.sourceObjectID.utf8.count <= 256,
              !row.sourceObjectID.contains("."), !row.sourceObjectID.hasPrefix("$"),
              let key = d["relationKey"]?.string, !key.isEmpty,
              let name = d["name"]?.string, let color = d["relationOptionColor"]?.string,
              let order = d["orderId"]?.string, !order.isEmpty,
              Data(relationObjectID.utf8) != Data(row.sourceObjectID.utf8) else {
            throw AnyDestinationMigrationError.invalidPlan("native option evidence")
        }
        var metadata: [String: AnyJSON] = [
                "heartSourceObjectID": .string(row.sourceObjectID), "heartUniqueKey": .string(row.uniqueKey),
                "heartSnapshotSHA256": .string(row.snapshotSHA256), "heartJSONViewSHA256": .string(row.viewSHA256),
                "heartRelationKey": .string(key), "heartRelationObjectID": .string(relationObjectID),
                "heartDefinitionJSON": .string(String(decoding: try bytes(.object(d)), as: UTF8.self)),
        ]
        if let original = provenance.originalAddedDate {
            // Native choice-option metadata has string leaves only. Preserve
            // the typed source number as canonical JSON, not a native stamp.
            // Property/type vendor metadata has a different scalar contract.
            metadata["heartSourceAddedDateJSON"] = .string(String(decoding: try bytes(original), as: UTF8.self))
            metadata["heartSourceAddedDateContract"] = .string("pinkha-heart-source-added-date-json-v1")
        }
        return .object([
            "name": .string(name), "color": .string(color), "pos": .string(order),
            "meta": .object(metadata),
        ])
    }
    static func embeddedOption(_ evidence: AnyDestinationDefinitionEvidence, descriptorSHA256: String,
                               property: AnyDestinationMigrationItem) throws {
        guard AnyDestinationPlanChecks.digest(descriptorSHA256),
              case .propertyDefinition(_, let kind, _, _, _, _, .literal(let format)?, _) = property.operation,
              kind == "array", format["type"] == .string("choice"),
              let relation = format["pinkhaHeart"],
              relation["sourceObjectID"]?.string.map({ Data($0.utf8) }) == Data(property.sourceObjectID.utf8),
              let key = evidence.snapshot.details["relationKey"]?.string,
              relation["relationKey"]?.string.map({ Data($0.utf8) }) == Data(key.utf8),
              relation["sourceUniqueKey"]?.string.map({ Data($0.utf8) }) == Data(("rel-" + key).utf8),
              let options = format["options"]?.object,
              let exact = options.first(where: { Data($0.key.utf8) == Data(evidence.sourceObjectID.utf8) }) else {
            throw AnyDestinationMigrationError.invalidPlan("embedded option property/path")
        }
        let expected = try optionDescriptor(evidence, relationObjectID: property.sourceObjectID)
        guard try bytes(exact.value) == bytes(expected), try digest(expected) == descriptorSHA256 else {
            throw AnyDestinationMigrationError.invalidPlan("embedded option descriptor/provenance")
        }
    }

    static func admitCanonicalProperties(_ coverage: [AnyDestinationCoverage], client: AnyHTTPClient,
                                         workspace: AnyTorahWorkspace,
                                         authorize: @escaping AnyDestinationAuthorization) async throws {
        let bindings = coverage.compactMap { item -> AnyDestinationCanonicalPropertyBinding? in
            switch item.disposition {
            case .canonicalProperty(let binding), .preservedCanonicalProperty(let binding, _): return binding
            default: return nil
            }
        }
        guard !bindings.isEmpty else { return }
        for binding in bindings { try binding.validate() }
        try await authorize()
        let value = try await client.requestJSON(method: "GET",
            path: ["v1", "spaces", workspace.spaceID, "types", "any", "properties"],
            maximumResponseBytes: 1_048_576, authorize: authorize)
        try verifyNativeCanonicalProperties(value, bindings: bindings)
        try await authorize(); try Task.checkCancellation()
    }
    static func verifyNativeCanonicalProperties(_ value: AnyJSON,
                                                bindings: [AnyDestinationCanonicalPropertyBinding]) throws {
        for binding in bindings {
            try binding.validate()
            try verifyNativeProperty(value, propertyID: binding.propertyID, expected: binding.expectedNativeDescriptor)
        }
    }
    static func verifyNativeNameProperties(_ value: AnyJSON) throws {
        try verifyNativeProperty(value, propertyID: "name", expected: AnyDestinationCanonicalPropertyBinding.nativeDescriptor)
    }
    private static func verifyNativeProperty(_ value: AnyJSON, propertyID: String, expected: AnyJSON) throws {
        guard let properties = value["properties"]?.array, properties.count <= 512 else {
            throw AnyDestinationMigrationError.unsupportedCapability("canonical any." + propertyID + " descriptor")
        }
        let matches = properties.filter { $0["id"]?.string.map { Data($0.utf8) } == Data(propertyID.utf8) }
        guard matches.count == 1, try bytes(matches[0]) == bytes(expected) else {
            throw AnyDestinationMigrationError.unsupportedCapability("canonical any." + propertyID + " descriptor")
        }
    }
}
