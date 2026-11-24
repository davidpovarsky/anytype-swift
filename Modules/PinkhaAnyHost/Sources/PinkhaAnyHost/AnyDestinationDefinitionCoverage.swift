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
              Data(objectID.utf8) == Data(sourceObjectID.utf8) else {
            throw AnyDestinationMigrationError.invalidPlan("foreign definition evidence")
        }
    }
}

/// This closed contract currently binds only Heart's unmodified native name
/// relation to Any's existing synced string name. It never creates or patches
/// the native schema. Other builtin-looking keys are ordinary source data.
public struct AnyDestinationCanonicalPropertyBinding: Codable, Equatable, Sendable {
    public static let contract = "pinkha-native-any-name-v1"
    public let evidence: AnyDestinationDefinitionEvidence
    public let ownerID: String
    public let propertyID: String
    public let nativeContract: String
    public let nativeDescriptorSHA256: String

    // SDK e195f6/internal/types/any/any.go, admitted again through native HTTP
    // before the first executor mutation. No label-only inference is used.
    public static let nativeDescriptor: AnyJSON = .object([
        "id": .string("name"), "name": .string("Name"), "description": .string("Display name."),
        "kind": .string("string"), "scope": .string("synced"),
        "xFormat": .object(["type": .string("text")]),
    ])

    public init(evidence: AnyDestinationDefinitionEvidence) throws {
        self.evidence = evidence; ownerID = "any"; propertyID = "name"; nativeContract = Self.contract
        nativeDescriptorSHA256 = try AnyDestinationDefinitionChecks.digest(Self.nativeDescriptor)
        try validate()
    }
    func validate() throws {
        let row = evidence.snapshot, d = row.details
        guard ownerID == "any", propertyID == "name", nativeContract == Self.contract,
              nativeDescriptorSHA256 == (try AnyDestinationDefinitionChecks.digest(Self.nativeDescriptor)),
              row.nativeType == 521, Data(row.uniqueKey.utf8) == Data("rel-name".utf8),
              d["relationKey"] == .string("name"), d["relationFormat"] == .integer(1),
              d["relationMaxCount"] == .integer(1), d["relationReadonlyValue"] == .bool(false),
              d["relationDefaultValue"] == .null, d["relationFormatIncludeTime"] == .bool(false),
              d["relationFormatObjectTypes"] == .array([]),
              d["name"] == .string("Name"), d["description"] == .string("Name of the object"),
              d["isArchived"] == nil || d["isArchived"] == .bool(false),
              d["isHidden"] == nil || d["isHidden"] == .bool(false),
              d["isReadonly"] == nil || d["isReadonly"] == .bool(false), row.issues.isEmpty else {
            throw AnyDestinationMigrationError.invalidPlan("canonical native name contract")
        }
        guard Set(d.keys).isSubset(of: AnyDestinationDefinitionChecks.nameDetailFields) else {
            throw AnyDestinationMigrationError.invalidPlan("unknown canonical native name semantics")
        }
    }
    private enum CodingKeys: String, CodingKey {
        case evidence, ownerID, propertyID, nativeContract, nativeDescriptorSHA256
    }
    public init(from decoder: any Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        evidence = try c.decode(AnyDestinationDefinitionEvidence.self, forKey: .evidence)
        ownerID = try c.decode(String.self, forKey: .ownerID)
        propertyID = try c.decode(String.self, forKey: .propertyID)
        nativeContract = try c.decode(String.self, forKey: .nativeContract)
        nativeDescriptorSHA256 = try c.decode(String.self, forKey: .nativeDescriptorSHA256)
        try validate()
    }
}

enum AnyDestinationDefinitionChecks {
    static let nameDetailFields: Set<String> = [
        "name", "description", "isHidden", "layout", "origin", "revision", "sourceObject", "apiObjectKey",
        "internalFlags", "iconEmoji", "iconImage", "createdDate", "creator", "lastModifiedDate", "lastModifiedBy",
        "isArchived", "isReadonly", "uniqueKey", "type", "id", "spaceId", "relationKey", "relationFormat",
        "relationFormatIncludeTime", "relationFormatObjectTypes", "relationMaxCount", "relationReadonlyValue",
        "relationDefaultValue",
    ]
    static func bytes(_ value: AnyJSON) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(value)
    }
    static func digest(_ value: AnyJSON) throws -> String { AnyContentDigest.sha256(try bytes(value)) }
    static func optionDescriptor(_ evidence: AnyDestinationDefinitionEvidence,
                                 relationObjectID: String) throws -> AnyJSON {
        let row = evidence.snapshot, d = row.details
        let unique = row.uniqueKey.split(separator: "-", omittingEmptySubsequences: false)
        guard row.nativeType == 529, row.issues.isEmpty,
              unique.count == 2, unique[0] == "opt", !unique[1].isEmpty,
              !row.sourceObjectID.isEmpty, row.sourceObjectID.utf8.count <= 256,
              !row.sourceObjectID.contains("."), !row.sourceObjectID.hasPrefix("$"),
              let key = d["relationKey"]?.string, !key.isEmpty,
              let name = d["name"]?.string, let color = d["relationOptionColor"]?.string,
              let order = d["orderId"]?.string, !order.isEmpty,
              Data(relationObjectID.utf8) != Data(row.sourceObjectID.utf8) else {
            throw AnyDestinationMigrationError.invalidPlan("native option evidence")
        }
        return .object([
            "name": .string(name), "color": .string(color), "pos": .string(order),
            "meta": .object([
                "heartSourceObjectID": .string(row.sourceObjectID), "heartUniqueKey": .string(row.uniqueKey),
                "heartSnapshotSHA256": .string(row.snapshotSHA256), "heartJSONViewSHA256": .string(row.viewSHA256),
                "heartRelationKey": .string(key), "heartRelationObjectID": .string(relationObjectID),
                "heartDefinitionJSON": .string(String(decoding: try bytes(.object(d)), as: UTF8.self)),
            ]),
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
            if case .canonicalProperty(let binding) = item.disposition { return binding }; return nil
        }
        guard !bindings.isEmpty else { return }
        for binding in bindings { try binding.validate() }
        try await authorize()
        let value = try await client.requestJSON(method: "GET",
            path: ["v1", "spaces", workspace.spaceID, "types", "any", "properties"],
            maximumResponseBytes: 1_048_576, authorize: authorize)
        try verifyNativeNameProperties(value)
        try await authorize(); try Task.checkCancellation()
    }
    static func verifyNativeNameProperties(_ value: AnyJSON) throws {
        guard let properties = value["properties"]?.array, properties.count <= 512 else {
            throw AnyDestinationMigrationError.unsupportedCapability("canonical any.name descriptor")
        }
        let names = properties.filter { $0["id"]?.string.map { Data($0.utf8) } == Data("name".utf8) }
        guard names.count == 1, try bytes(names[0]) == bytes(AnyDestinationCanonicalPropertyBinding.nativeDescriptor) else {
            throw AnyDestinationMigrationError.unsupportedCapability("canonical any.name descriptor")
        }
    }
}
