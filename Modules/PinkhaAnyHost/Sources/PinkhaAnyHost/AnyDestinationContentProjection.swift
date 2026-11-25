import Foundation
import PinkhaAnyEngine

/// Wire projections follow the original Any API's documented omission/default
/// rules. Unknown fields are refused; arbitrary source JSON is never normalized.
enum AnyDestinationContentProjection {
    private static func object(_ value: AnyJSON, allowed: Set<String>) throws -> [String: AnyJSON] {
        guard let values = value.object, Set(values.keys).isSubset(of: allowed) else {
            throw AnyDestinationContentVerificationError.mismatch(sourceKey: "schema", field: "unqualified wire fields")
        }
        return values
    }
    private static func defaults(_ value: AnyJSON, _ fallback: [String: AnyJSON],
                                 allowed: Set<String>) throws -> [String: AnyJSON] {
        var result = fallback
        for (key, value) in try object(value, allowed: allowed) { result[key] = value }
        return result
    }
    private static func nonempty(_ value: AnyJSON?, _ fallback: String) -> String {
        guard let string = value?.string, !string.isEmpty else { return fallback }; return string
    }
    private static func literal(_ value: AnyDestinationValue) throws -> AnyJSON {
        try AnyDestinationMigrationVerifier.literal(value)
    }
    private static func absentObject(_ value: AnyJSON?) -> AnyJSON { value ?? .object([:]) }

    static func root(_ seed: AnyDestinationRootDefinition, id: String, type: Bool) throws -> AnyJSON {
        var value: [String: AnyJSON] = ["id": .string(id), "xKey": .string(seed.xKey),
            "name": .string(seed.name), "description": .string(seed.description), "iconCid": .string(seed.iconCID),
            "builtIn": .bool(false), "hidden": .bool(seed.hidden), "meta": try literal(seed.meta)]
        if type { value["layout"] = try seed.layout.map(literal) ?? .object([:]) }
        return .object(value)
    }
    static func root(_ value: AnyJSON, type: Bool) throws -> AnyJSON {
        var fallback: [String: AnyJSON] = ["name": .string(""), "description": .string(""), "iconCid": .string(""),
            "builtIn": .bool(false), "hidden": .bool(false), "meta": .object([:])]
        var allowed: Set<String> = ["id", "xKey", "name", "description", "iconCid", "builtIn", "hidden", "meta"]
        if type { fallback["layout"] = .object([:]); allowed.insert("layout") }
        return .object(try defaults(value, fallback, allowed: allowed))
    }

    static func property(id: String, kind: String, name: String, xKey: String, description: String,
                         scope: String, format: AnyDestinationValue?, index: String?) throws -> AnyJSON {
        .object(["id": .string(id), "kind": .string(kind), "name": .string(name), "xKey": .string(xKey),
            "description": .string(description), "scope": .string(scope),
            "xFormat": try format.map(literal) ?? .object([:]),
            "meta": index.map { .object(["index": .string($0)]) } ?? .object([:]),
            "properties": .array([]), "required": .array([])])
    }
    static func property(_ value: AnyJSON) throws -> AnyJSON {
        .object(try defaults(value, ["name": .string(""), "description": .string(""), "xKey": .string(""),
            "scope": .string("synced"), "xFormat": .object([:]), "meta": .object([:]),
            "properties": .array([]), "required": .array([])],
            allowed: ["id", "kind", "name", "description", "xKey", "scope", "xFormat", "meta", "items", "properties", "required"]))
    }

    static func part(draft: AnyJSON, owner: String, recordIDs: [String]) throws -> AnyJSON {
        var value = try object(draft, allowed: ["key", "name", "icon", "pos", "hidden", "ui", "uses", "datasets"])
        guard let partID = recordIDs.first else { throw AnyDestinationContentVerificationError.invalidProgress }
        value["id"] = .string(partID)
        var cursor = 1
        func next() throws -> String {
            guard recordIDs.indices.contains(cursor) else { throw AnyDestinationContentVerificationError.invalidProgress }
            defer { cursor += 1 }; return recordIDs[cursor]
        }
        var compiled: [AnyJSON] = []
        guard let datasets = (value["datasets"] ?? .array([])).array else {
            throw AnyDestinationContentVerificationError.invalidProgress
        }
        for declaration in datasets {
            var dataset = try object(declaration, allowed: datasetDraftKeys)
            let id = try next()
            let module = nonempty(dataset["module"], "records")
            let defaultKey = module == "editor" ? "editor_blocks" : module == "chat" ? "chat_messages" : ""
            let key = nonempty(dataset["key"], defaultKey)
            guard !key.isEmpty else { throw AnyDestinationContentVerificationError.invalidProgress }
            let collection = (key == "editor_blocks" && module == "editor") ||
                (key == "chat_messages" && module == "chat") ? key : owner + "_" + key
            dataset["id"] = .string(id); dataset["partId"] = .string(partID)
            dataset["module"] = .string(module); dataset["key"] = .string(key)
            dataset["collection"] = .string(collection)
            dataset["idRule"] = .string(nonempty(dataset["idRule"], "auto"))
            dataset["deleteBy"] = .string(nonempty(dataset["deleteBy"], "anyone"))
            var fields: [AnyJSON] = []
            guard let declaredFields = (dataset["fields"] ?? .array([])).array else {
                throw AnyDestinationContentVerificationError.invalidProgress
            }
            for declaration in declaredFields {
                var field = try object(declaration, allowed: fieldDraftKeys)
                field["id"] = .string(try next())
                let stamp = nonempty(field["stamp"], "")
                let kind = nonempty(field["kind"], nonempty(field["shape"]?["kind"],
                    stamp == "creator" ? "string" : (stamp == "createTime" || stamp == "modifyTime") ? "datetime" : ""))
                guard !kind.isEmpty else { throw AnyDestinationContentVerificationError.invalidProgress }
                field["kind"] = .string(kind)
                field["scope"] = .string(nonempty(field["scope"], stamp.isEmpty ? "synced" : "derived"))
                field["mutableBy"] = .string(nonempty(field["mutableBy"], "never"))
                // The original API omits a bare kind-only shape.
                if let shape = field["shape"]?.object, shape["items"] == nil, shape["properties"]?.object?.isEmpty != false {
                    field.removeValue(forKey: "shape")
                }
                fields.append(.object(field))
            }
            // Native SDK compile.go orders fields declared in this one
            // signed batch by key after preserving their allocated record IDs.
            fields.sort { byteKey($0).lexicographicallyPrecedes(byteKey($1)) }
            dataset["fields"] = .array(fields)
            var indexes: [AnyJSON] = []
            guard let declaredIndexes = (dataset["indexes"] ?? .array([])).array else {
                throw AnyDestinationContentVerificationError.invalidProgress
            }
            for declaration in declaredIndexes {
                var index = try object(declaration, allowed: ["key", "fields", "sparse"])
                index["id"] = .string(try next()); indexes.append(.object(index))
            }
            indexes.sort { byteKey($0).lexicographicallyPrecedes(byteKey($1)) }
            dataset["indexes"] = .array(indexes)
            compiled.append(.object(dataset))
        }
        guard cursor == recordIDs.count else { throw AnyDestinationContentVerificationError.invalidProgress }
        compiled.sort { byteKey($0).lexicographicallyPrecedes(byteKey($1)) }
        value["datasets"] = .array(compiled)
        if let uses = value["uses"]?.array {
            guard uses.allSatisfy({ $0.string != nil }),
                  Set(uses.compactMap { $0.string.map { Data($0.utf8) } }).count == uses.count else {
                throw AnyDestinationContentVerificationError.invalidProgress
            }
            value["uses"] = .array(uses.sorted {
                Data(($0.string ?? "").utf8).lexicographicallyPrecedes(Data(($1.string ?? "").utf8))
            })
        }
        return try part(.object(value))
    }
    private static func byteKey(_ value: AnyJSON) -> Data { Data((value["key"]?.string ?? "").utf8) }

    static func part(_ value: AnyJSON) throws -> AnyJSON {
        var part = try defaults(value, ["name": .string(""), "icon": .string(""), "pos": .string(""),
            "hidden": .bool(false), "ui": .object([:]), "uses": .array([]), "datasets": .array([])],
            allowed: ["id", "key", "name", "icon", "pos", "hidden", "ui", "uses", "datasets"])
        guard let datasets = part["datasets"]?.array else { throw AnyDestinationContentVerificationError.invalidProgress }
        part["datasets"] = .array(try datasets.map { value in
            var dataset = try defaults(value, ["displayName": .string(""), "description": .string(""),
                "dynamic": .bool(false), "idPattern": .string(""), "idMaxLen": .integer(0),
                "skipHistory": .bool(false), "shared": .bool(false), "fields": .array([]), "indexes": .array([]),
                "invalid": .bool(false), "invalidReason": .string("")],
                allowed: datasetDraftKeys.union(["id", "partId", "collection", "invalid", "invalidReason"]))
            if let search = dataset["search"] {
                var normalized = try defaults(search, ["title": .string(""), "scope": .string("")],
                                               allowed: ["title", "text", "scope"])
                if let keys = normalized["text"]?.array, keys.count == 1 { normalized["text"] = keys[0] }
                dataset["search"] = .object(normalized)
            }
            guard let fields = dataset["fields"]?.array, let indexes = dataset["indexes"]?.array else {
                throw AnyDestinationContentVerificationError.invalidProgress
            }
            dataset["fields"] = .array(try fields.map {
                .object(try defaults($0, ["name": .string(""), "description": .string(""),
                    "required": .bool(false), "stamp": .string(""), "xFormat": .object([:])],
                    allowed: fieldDraftKeys.union(["id"])))
            })
            dataset["indexes"] = .array(try indexes.map {
                .object(try defaults($0, ["sparse": .bool(false), "invalid": .bool(false), "invalidReason": .string("")],
                    allowed: ["id", "key", "fields", "sparse", "invalid", "invalidReason"]))
            })
            return .object(dataset)
        })
        return .object(part)
    }
    private static let datasetDraftKeys: Set<String> = [
        "key", "module", "displayName", "description", "dynamic", "idRule", "idPattern", "idMaxLen",
        "deleteBy", "skipHistory", "shared", "search", "fields", "indexes"
    ]
    private static let fieldDraftKeys: Set<String> = [
        "key", "name", "description", "kind", "shape", "scope", "required", "mutableBy", "stamp", "xFormat"
    ]

    static func propertyValue(_ value: AnyJSON, kind: String?) throws -> AnyJSON {
        guard kind == "datetime" else { return value }
        guard let fields = value.object, fields.count == 1, let date = fields["$date"] else {
            throw AnyDestinationContentVerificationError.mismatch(sourceKey: "datetime", field: "native date value")
        }
        if let milliseconds = date.integer { return .integer(milliseconds) }
        guard let string = date.string,
              string.range(of: #"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})$"#,
                           options: .regularExpression) != nil else {
            throw AnyDestinationContentVerificationError.mismatch(sourceKey: "datetime", field: "millisecond RFC3339")
        }
        let parser = ISO8601DateFormatter()
        parser.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        var parsed = parser.date(from: string)
        if parsed == nil { parser.formatOptions = [.withInternetDateTime]; parsed = parser.date(from: string) }
        guard let parsed else {
            throw AnyDestinationContentVerificationError.mismatch(sourceKey: "datetime", field: "native date syntax")
        }
        let milliseconds = parsed.timeIntervalSince1970 * 1000
        guard milliseconds.isFinite, milliseconds > Double(Int64.min), milliseconds < Double(Int64.max) else {
            throw AnyDestinationContentVerificationError.mismatch(sourceKey: "datetime", field: "native date bounds")
        }
        return .integer(Int64(milliseconds.rounded()))
    }

    static func file(_ value: AnyJSON) throws -> AnyJSON {
        let fields = try object(value, allowed: ["fileId", "objectId", "rootCid", "size", "inline",
            "durable", "cached", "name", "mime", "variant", "variantOf"])
        return .object(["fileId": fields["fileId"] ?? .null, "objectId": fields["objectId"] ?? .null,
            "name": fields["name"] ?? .string(""), "mime": fields["mime"] ?? .string(""),
            "size": fields["size"] ?? .null, "inline": fields["inline"] ?? .null,
            "variant": fields["variant"] ?? .string(""), "variantOf": fields["variantOf"] ?? .string("")])
    }
}
