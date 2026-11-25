import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

/// A captured Heart long-text default is definition metadata. The qualified
/// Heart ordinary/from-state creation and Any creation paths do not synthesize
/// a missing value from it. Templates are separate operations and not admitted
/// by this contract. Reading this metadata never grants source/write authority.
public struct AnyNativeImportedDefaultMetadata: Equatable, Sendable {
    public static let contract = "pinkha-heart-longtext-default-metadata-v1"
    public let sourceObjectID: String
    public let sourceUniqueKey: String
    public let sourceRelationKey: String
    public let sourceSnapshotSHA256: String
    public let sourceJSONViewSHA256: String
    public let definitionJSON: String
    public let defaultValueJSON: String
    public let value: AnyJSON

    static func qualifies(_ relation: AnyHeartNativeDefinitionCatalog.Relation) -> Bool {
        qualifies(details: relation.snapshot.details) &&
            relation.snapshot.nativeType == 521 &&
            Data(relation.snapshot.uniqueKey.utf8) == Data(("rel-" + relation.relationKey).utf8) &&
            relation.snapshot.issues.isEmpty
    }

    private static func qualifies(details: [String: AnyJSON]) -> Bool {
        details["relationFormat"] == .integer(0) &&
            details["relationMaxCount"] == .integer(1) &&
            (details["relationReadonlyValue"] == nil || details["relationReadonlyValue"] == .bool(false)) &&
            details["relationDefaultValue"]?.string != nil &&
            (details["isArchived"] == nil || details["isArchived"] == .bool(false)) &&
            (details["isReadonly"] == nil || details["isReadonly"] == .bool(false))
    }

    /// Returns nil for an unrelated property or metadata without an admitted
    /// behavior contract. A present but malformed/unknown contract is rejected.
    public init?(property: AnyJSON) throws {
        guard let source = property["xFormat"]?["pinkhaHeart"],
              let behavior = source["defaultBehaviorContract"] else { return nil }
        guard behavior == .string(Self.contract),
              property["kind"] == .string("string"),
              property["scope"] == nil || property["scope"] == .string("synced"),
              property["xFormat"]?["type"] == .string("longtext"),
              let sourceObjectID = source["sourceObjectID"]?.string,
              let sourceUniqueKey = source["sourceUniqueKey"]?.string,
              let sourceRelationKey = source["relationKey"]?.string,
              AnyDestinationPlanChecks.identity(sourceObjectID),
              !sourceRelationKey.isEmpty, sourceRelationKey.utf8.count <= 4096,
              !sourceRelationKey.utf8.contains(0),
              Data(sourceUniqueKey.utf8) == Data(("rel-" + sourceRelationKey).utf8),
              let snapshot = source["snapshotSHA256"]?.string, AnyDestinationPlanChecks.digest(snapshot),
              let view = source["jsonViewSHA256"]?.string, AnyDestinationPlanChecks.digest(view),
              let definitionJSON = source["definitionJSON"]?.string,
              let defaultValueJSON = source["defaultValueJSON"]?.string else {
            throw AnyNativePropertyError.invalidProperty
        }
        let definition = try Self.decodeExact(definitionJSON)
        let value = try Self.decodeExact(defaultValueJSON)
        guard let details = definition.object, Self.qualifies(details: details),
              details["relationKey"]?.string.map({ Data($0.utf8) }) == Data(sourceRelationKey.utf8),
              try AnyDestinationDefinitionChecks.bytes(value) ==
                AnyDestinationDefinitionChecks.bytes(details["relationDefaultValue"] ?? .null) else {
            throw AnyNativePropertyError.invalidProperty
        }
        self.sourceObjectID = sourceObjectID; self.sourceUniqueKey = sourceUniqueKey
        self.sourceRelationKey = sourceRelationKey; sourceSnapshotSHA256 = snapshot
        sourceJSONViewSHA256 = view; self.definitionJSON = definitionJSON
        self.defaultValueJSON = defaultValueJSON; self.value = value
    }

    private static func decodeExact(_ text: String) throws -> AnyJSON {
        let data = Data(text.utf8)
        guard !data.isEmpty, data.count <= 131_072 else { throw AnyNativePropertyError.invalidProperty }
        let value = try JSONDecoder().decode(AnyJSON.self, from: data)
        try AnyTorahSourceJSONGuard.validateRoundTrip(original: data,
            encoded: AnyDestinationDefinitionChecks.bytes(value))
        return value
    }
}
