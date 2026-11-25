import Foundation
import PinkhaAnyEngine

/// A typed view of the original compiled Relation resolver descriptor. A registry
/// entry has no native object or tree identity. In particular, its _br identifier
/// must never enter an object mapping or replace a captured relation override.
public struct AnyHeartNativeCompiledRelation: Sendable {
    public let source: AnyHeartNativeBundledDefinition
    public let relationKey: String
    public let name: String
    public let description: String
    public let rawFormat: Int64
    public let dataSource: Int64
    public let scope: Int64
    public let hidden: Bool
    public let readonlyValue: Bool
    public let readonlyDefinition: Bool
    public let multiple: Bool
    public let maximumCount: Int64
    public let includeTime: Bool
    public let targetTypeIDs: [String]
    public let selectDictionary: [AnyJSON]
    public let creator: String
    public let revision: Int64
    /// Unlike proto3 scalar defaults, an absent protobuf Value stays absent.
    /// Explicit null, false, zero and empty values remain distinct.
    public let defaultValue: AnyJSON?
    public let unknownFields: [String]
    public var format: AnyHeartNativeDefinitionCatalog.Format? {
        AnyHeartNativeDefinitionCatalog.Format(rawValue: rawFormat)
    }
    public var sourceIdentity: String { source.identity }

    public init(source: AnyHeartNativeBundledDefinition) throws {
        guard source.kind == .property, let fields = source.definition.object else {
            throw AnyHeartNativeDefinitionCatalogError.invalidDefinition(source.identity, "compiled-relation")
        }
        let d = source.definition
        func invalid(_ field: String) -> AnyHeartNativeDefinitionCatalogError {
            .invalidDefinition(source.identity, "compiled." + field)
        }
        func string(_ field: String) throws -> String {
            guard let value = d[field] else { return "" }
            guard let text = value.string, text.utf8.count <= 65_536 else { throw invalid(field) }
            return text
        }
        func int32(_ field: String) throws -> Int64 {
            guard let value = d[field] else { return 0 }
            guard let number = value.integer, (Int64(Int32.min)...Int64(Int32.max)).contains(number) else { throw invalid(field) }
            return number
        }
        func bool(_ field: String) throws -> Bool {
            guard let value = d[field] else { return false }
            guard let flag = value.bool else { throw invalid(field) }
            return flag
        }
        func identifiers(_ field: String) throws -> [String] {
            guard let value = d[field] else { return [] }
            guard let values = value.array, values.count <= 20_000 else { throw invalid(field) }
            return try values.map {
                guard let id = $0.string, !id.isEmpty, id.utf8.count <= 4096,
                      !id.utf8.contains(0) else { throw invalid(field) }
                return id
            }
        }
        // The native generated JSON uses the proto3 zero defaults for omitted
        // scalar fields and decimal strings for int64 revision. It does not
        // supply the same defaults for the optional google.protobuf.Value.
        let revision: Int64
        if let value = d["revision"] {
            guard let text = value.string, let number = Int64(text),
                  String(number) == text else { throw invalid("revision") }
            revision = number
        } else { revision = 0 }
        let options: [AnyJSON]
        if let value = d["selectDict"] {
            guard let list = value.array, list.count <= 20_000,
                  list.allSatisfy({ $0.object != nil }) else { throw invalid("selectDict") }
            options = list
        } else { options = [] }
        self.source = source
        relationKey = source.key
        name = try string("name")
        description = try string("description")
        rawFormat = try int32("format")
        dataSource = try int32("dataSource")
        scope = try int32("scope")
        hidden = try bool("hidden")
        readonlyValue = try bool("readOnly")
        readonlyDefinition = try bool("readOnlyRelation")
        multiple = try bool("multi")
        maximumCount = try int32("maxCount")
        includeTime = try bool("includeTime")
        targetTypeIDs = try identifiers("objectTypes")
        selectDictionary = options
        creator = try string("creator")
        self.revision = revision
        defaultValue = d["defaultValue"]
        unknownFields = fields.keys.filter { !Self.knownFields.contains($0) }
            .sorted { Data($0.utf8).lexicographicallyPrecedes(Data($1.utf8)) }
    }

    private static let knownFields: Set<String> = [
        "id", "key", "format", "name", "defaultValue", "dataSource", "hidden",
        "readOnly", "readOnlyRelation", "multi", "objectTypes", "selectDict",
        "maxCount", "description", "scope", "creator", "revision", "includeTime",
    ]
}
