import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

public enum AnyDestinationContentVerificationError: Error, Equatable, Sendable {
    case invalidProgress
    case mismatch(sourceKey: String, field: String)
    case changedDuringRead(String)
}

public struct AnyDestinationContentObservation: Codable, Sendable, Equatable {
    public let sourceKey: String
    public let kind: String
    public let objectID: String
    public let semanticSHA256: String
}

public struct AnyDestinationFileAvailability: Codable, Sendable, Equatable {
    public let fileID: String
    public let byteCount: Int64
    public let plaintextSHA256: String
    public let cached: Bool
    public let durable: Bool
}

/// Current content of the admitted operations, read through ordinary native
/// APIs. This is not an atomic Space snapshot and does not certify unsupported
/// source semantics, history, account/ACL migration or network file custody.
public struct AnyDestinationContentVerification: Codable, Sendable {
    public let planSHA256: String
    public let sourceManifestSHA256: String
    public let destinationAccountID: String
    public let destinationSpaceID: String
    public let destinationStoreID: String
    public let observations: [AnyDestinationContentObservation]
    public let files: [AnyDestinationFileAvailability]
    public let retainedSourceSystemObjectIDs: [String]
    public var comparedOperationCount: Int { observations.count }
}

public struct AnyDestinationMigrationVerifier: Sendable {
    private let client: AnyHTTPClient
    public init(client: AnyHTTPClient) { self.client = client }

    /// The caller must retain the original capture authority. A reconciled
    /// journal is necessary but insufficient: definitions, properties, bodies,
    /// hierarchy, reference cycles and plaintext files are compared here.
    public func verify(
        plan: AnyDestinationMigrationPlan,
        progress: AnyDestinationMigrationProgress,
        verifySource: @escaping @Sendable (AnyDestinationSourceBinding) async throws -> Void,
        authorize: @escaping @Sendable () async throws -> Void
    ) async throws -> AnyDestinationContentVerification {
        try plan.requireExecutable()
        guard progress.allItemsReconciled, progress.totalItems == plan.items.count,
              progress.mappings.count == plan.items.count, progress.verificationIntents.count == plan.items.count,
              progress.binding == plan.binding,
              try Self.bytes(progress.source) == Self.bytes(plan.source),
              Data(client.expectedAccountID.utf8) == Data(plan.binding.workspace.accountID.utf8) else {
            throw AnyDestinationContentVerificationError.invalidProgress
        }
        let admit: AnyDestinationAuthorization = {
            try Task.checkCancellation(); try await verifySource(plan.source)
            try await authorize(); try Task.checkCancellation()
        }
        try await admit()
        // Reopen the exact advertised contracts/store, including canonical
        // property admission. A new process cannot silently substitute a store.
        let driver = try await AnyDestinationNativeClients.open(client: client, plan: plan, authorize: admit)
        let prefix = ["v1", "spaces", plan.binding.workspace.spaceID]
        @Sendable func read(_ suffix: [String], body: AnyJSON? = nil,
                            query: [String: String] = [:]) async throws -> AnyJSON {
            try await admit()
            let value = try await client.requestJSON(method: body == nil ? "GET" : "POST",
                path: prefix + suffix, body: body, query: query, maximumResponseBytes: 8 << 20, authorize: admit)
            try await admit()
            return value
        }
        @Sendable func verifyReceipts() async throws {
            for (intent, mapping) in zip(progress.verificationIntents, progress.mappings) {
                guard intent.identity.id == mapping.intentID else {
                    throw AnyDestinationContentVerificationError.invalidProgress
                }
                let current = try await driver.status(intent, authorize: admit)
                guard current["stage"]?.string == "complete", current["outcome"]?.string == "committed",
                      AnyContentDigest.sha256(try Self.bytes(current)) == mapping.currentReceiptSHA256 else {
                    throw Self.failure(mapping.sourceKey, "current native receipt")
                }
            }
        }
        try await verifyReceipts()
        var mappings: [Data: AnyDestinationMigrationMapping] = [:]
        for (item, mapping) in zip(plan.items, progress.mappings) {
            guard Data(item.sourceKey.utf8) == Data(mapping.sourceKey.utf8),
                  Data(item.sourceObjectID.utf8) == Data(mapping.sourceObjectID.utf8),
                  item.operation.kind == mapping.kind, mapping.recordIDs.count == item.expectedRecordCount,
                  AnyEditorBlock.validID(mapping.objectID),
                  mapping.recordIDs.allSatisfy(AnyEditorBlock.validID),
                  Set(mapping.recordIDs.map { Data($0.utf8) }).count == mapping.recordIDs.count,
                  mappings.updateValue(mapping, forKey: Data(item.sourceKey.utf8)) == nil else {
                throw AnyDestinationContentVerificationError.invalidProgress
            }
        }
        let immutableMappings = mappings
        let resolved = try plan.items.map { item in
            try item.operation.resolved(destinationSpaceID: plan.binding.workspace.spaceID) { reference in
                try Self.resolve(reference, in: immutableMappings, destinationSpaceID: plan.binding.workspace.spaceID)
            }
        }
        var roots: [Data: String] = [:]
        var objectIndexes: [Data: Int] = [:]
        for (index, operation) in resolved.enumerated() {
            let mapping = progress.mappings[index]
            switch operation {
            case .typeDefinition: roots[Data(mapping.objectID.utf8)] = "types"
            case .collectionDefinition: roots[Data(mapping.objectID.utf8)] = "collections"
            case .object: objectIndexes[Data(mapping.objectID.utf8)] = index
            default: break
            }
        }
        var definitionsBefore: [String: AnyJSON] = [:]
        var objectsBefore: [Data: AnyJSON] = [:]
        var propertyKinds: [Data: [Data: String]] = [:]
        var observations: [AnyDestinationContentObservation] = []
        var fileAvailability: [AnyDestinationFileAvailability] = []
        var observed: [Data: AnyJSON] = [:]

        // Compare whole owned definition lists, not only a found first match.
        // Extra properties/parts on a newly created definition are a mismatch.
        for (index, operation) in resolved.enumerated() {
            let mapping = progress.mappings[index], item = plan.items[index]
            let route: String
            let seed: AnyDestinationRootDefinition
            switch operation {
            case .typeDefinition(let value): route = "types"; seed = value
            case .collectionDefinition(let value): route = "collections"; seed = value
            default: continue
            }
            let path = [route, mapping.objectID]
            let actual = try await read(path)
            let expected = try AnyDestinationContentProjection.root(seed, id: mapping.objectID, type: route == "types")
            try Self.equal(AnyDestinationContentProjection.root(actual, type: route == "types"), expected,
                           item.sourceKey, "definition")
            definitionsBefore[path.joined(separator: "/")] = actual
            observed[Data(item.sourceKey.utf8)] = expected
            let propertiesPath = path + ["properties"]
            let propertyResponse = try await read(propertiesPath)
            let propertyValues = try Self.array(propertyResponse["properties"], item.sourceKey, "properties")
            let propertyIndexes = resolved.indices.filter {
                if case .propertyDefinition(let owner, _, _, _, _, _, _, _) = resolved[$0] {
                    return (try? Self.native(owner)) == mapping.objectID
                }
                return false
            }
            guard propertyValues.count == propertyIndexes.count else { throw Self.failure(item.sourceKey, "property count") }
            var kinds: [Data: String] = [:]
            for propertyIndex in propertyIndexes {
                let propertyItem = plan.items[propertyIndex], propertyMapping = progress.mappings[propertyIndex]
                guard case .propertyDefinition(_, let kind, let name, let xKey, let description, let scope,
                                              let format, let searchIndex) = resolved[propertyIndex] else {
                    throw AnyDestinationContentVerificationError.invalidProgress
                }
                let id = propertyMapping.recordIDs[0]
                let value = try Self.unique(propertyValues, id: id, key: "id", sourceKey: propertyItem.sourceKey)
                let expected = try AnyDestinationContentProjection.property(id: id, kind: kind, name: name,
                    xKey: xKey, description: description, scope: scope, format: format, index: searchIndex)
                try Self.equal(AnyDestinationContentProjection.property(value), expected, propertyItem.sourceKey, "property definition")
                observed[Data(propertyItem.sourceKey.utf8)] = expected
                kinds[Data(id.utf8)] = kind
            }
            propertyKinds[Data(mapping.objectID.utf8)] = kinds
            definitionsBefore[propertiesPath.joined(separator: "/")] = propertyResponse
            if route == "types" {
                let partsPath = path + ["parts"]
                let partResponse = try await read(partsPath)
                let values = try Self.array(partResponse["parts"], item.sourceKey, "parts")
                let indexes = resolved.indices.filter {
                    if case .partDefinition(let owner, _) = resolved[$0] { return (try? Self.native(owner)) == mapping.objectID }
                    return false
                }
                guard values.count == indexes.count else { throw Self.failure(item.sourceKey, "part count") }
                for partIndex in indexes {
                    let partItem = plan.items[partIndex], partMapping = progress.mappings[partIndex]
                    guard case .partDefinition(_, let draft) = resolved[partIndex] else {
                        throw AnyDestinationContentVerificationError.invalidProgress
                    }
                    let value = try Self.unique(values, id: partMapping.recordIDs[0], key: "id", sourceKey: partItem.sourceKey)
                    let expected = try AnyDestinationContentProjection.part(draft: Self.literal(draft),
                        owner: mapping.objectID, recordIDs: partMapping.recordIDs)
                    try Self.equal(AnyDestinationContentProjection.part(value), expected, partItem.sourceKey, "compiled part")
                    observed[Data(partItem.sourceKey.utf8)] = expected
                }
                definitionsBefore[partsPath.joined(separator: "/")] = partResponse
            }
        }

        for (index, operation) in resolved.enumerated() {
            guard case .object(let type, let collections, let initial) = operation else { continue }
            let item = plan.items[index], mapping = progress.mappings[index]
            let object = try await read(["objects", mapping.objectID])
            let record = try Self.objectRecord(object, id: mapping.objectID, spaceID: plan.binding.workspace.spaceID)
            objectsBefore[Data(mapping.objectID.utf8)] = object
            let typeID = try Self.native(type)
            try Self.equal(record["any"]?["type"], .string(typeID), item.sourceKey, "object type")
            let collectionIDs = try collections.map { try Self.native($0) }
            let actualCollections = try Self.array(record["any"]?["collections"] ?? .array([]), item.sourceKey, "collections")
            guard actualCollections.count == collectionIDs.count,
                  Set(actualCollections.compactMap { $0.string.map { Data($0.utf8) } }) == Set(collectionIDs.map { Data($0.utf8) }) else {
                throw Self.failure(item.sourceKey, "object collections")
            }
            guard var properties = try Self.literal(initial).object else { throw AnyDestinationContentVerificationError.invalidProgress }
            for updateIndex in resolved.indices {
                if case .propertyUpdate(let target, let owner, let patch) = resolved[updateIndex],
                   try Self.native(target) == mapping.objectID {
                    let ownerID = try Self.native(owner)
                    var fields = properties[ownerID]?.object ?? [:]
                    guard let values = try Self.literal(patch).object else { throw AnyDestinationContentVerificationError.invalidProgress }
                    for (key, value) in values { fields[key] = value }
                    properties[ownerID] = .object(fields)
                }
            }
            // A native JSON null is an unset in this specific properties API.
            // Empty strings and empty arrays remain present and distinct.
            for owner in [typeID] + collectionIDs {
                if properties[owner] == nil { properties[owner] = .object([:]) }
            }
            var projection: [String: AnyJSON] = ["id": .string(mapping.objectID), "type": .string(typeID),
                "collections": .array(collectionIDs.sorted().map(AnyJSON.string))]
            for (owner, value) in properties {
                guard let expectedFields = value.object else { throw AnyDestinationContentVerificationError.invalidProgress }
                let actualFields = record[owner]?.object ?? [:]
                var expected: [String: AnyJSON] = [:]
                for (key, value) in expectedFields {
                    if value == .null {
                        guard actualFields[key] == nil else { throw Self.failure(item.sourceKey, "unset property") }
                    } else {
                        let kind = propertyKinds[Data(owner.utf8)]?[Data(key.utf8)]
                        let canonical = try AnyDestinationContentProjection.propertyValue(value, kind: kind)
                        let actual = try actualFields[key].map { try AnyDestinationContentProjection.propertyValue($0, kind: kind) }
                        try Self.equal(actual, canonical, item.sourceKey, "property value")
                        expected[key] = canonical
                    }
                }
                if owner != "any", roots[Data(owner.utf8)] != nil,
                   Set(actualFields.keys.map { Data($0.utf8) }) != Set(expected.keys.map { Data($0.utf8) }) {
                    throw Self.failure(item.sourceKey, "extra or missing property value")
                }
                projection[owner] = .object(expected)
            }
            observed[Data(item.sourceKey.utf8)] = .object(projection)
        }

        struct BlockGroup: Hashable { let owner: String; let dataset: String }
        var groups: [BlockGroup: [Int]] = [:]
        for (index, operation) in resolved.enumerated() {
            if case .editorBlock(let owner, let dataset, _, _, _, _, _) = operation {
                groups[.init(owner: try Self.native(owner), dataset: dataset), default: []].append(index)
            }
        }
        // Also inspect empty datasets declared by this plan. Otherwise a new
        // unexpected body on an object with zero planned blocks could escape.
        for index in resolved.indices {
            guard case .object(let type, _, _) = resolved[index] else { continue }
            let typeID = try Self.native(type), objectID = progress.mappings[index].objectID
            for partIndex in resolved.indices {
                guard case .partDefinition(let owner, _) = resolved[partIndex],
                      try Self.native(owner) == typeID,
                      let datasets = observed[Data(plan.items[partIndex].sourceKey.utf8)]?["datasets"]?.array else { continue }
                for dataset in datasets {
                    guard let collection = dataset["collection"]?.string else {
                        throw AnyDestinationContentVerificationError.invalidProgress
                    }
                    let group = BlockGroup(owner: objectID, dataset: collection)
                    if groups[group] == nil { groups[group] = [] }
                }
            }
        }
        for (group, indexes) in groups {
            var rows: [AnyJSON] = [], offset = 0
            repeat {
                let response = try await read(["query"], body: .object([
                    "objectId": .string(group.owner), "dataset": .string(group.dataset),
                    "sort": .array([.string("id")]), "limit": .integer(256),
                    "offset": .integer(Int64(offset)), "includeTotal": .bool(true)
                ]))
                let page = try Self.array(response["records"], group.owner, "block records")
                guard response["total"]?.integer == Int64(indexes.count), (indexes.isEmpty || !page.isEmpty),
                      page.count <= 256, page.count <= indexes.count - offset,
                      response["hasNext"]?.bool == (offset + page.count < indexes.count) else {
                    throw Self.failure(group.owner, "complete block census")
                }
                rows.append(contentsOf: page); offset += page.count
            } while offset < indexes.count
            guard Set(rows.compactMap { $0["id"]?.string.map { Data($0.utf8) } }).count == indexes.count else {
                throw Self.failure(group.owner, "duplicate block identity")
            }
            for index in indexes {
                let item = plan.items[index], mapping = progress.mappings[index]
                guard case .editorBlock(_, _, let type, let text, let style, let parent, let position) = resolved[index] else {
                    throw AnyDestinationContentVerificationError.invalidProgress
                }
                let row = try Self.unique(rows, id: mapping.recordIDs[0], key: "id", sourceKey: item.sourceKey)
                let expected = AnyJSON.object(["id": .string(mapping.recordIDs[0]), "type": .string(type), "text": .string(text),
                    "style": try Self.literal(style), "parentId": .string(try parent.map(Self.native) ?? ""), "position": .string(position)])
                let actual = AnyJSON.object(["id": row["id"] ?? .null, "type": row["type"] ?? .null,
                    "text": row["text"] ?? .string(""), "style": row["style"] ?? .object([:]),
                    "parentId": row["nav"]?["parentId"] ?? .string(""), "position": row["nav"]?["pos"] ?? .null])
                try Self.equal(actual, expected, item.sourceKey, "block text/style/hierarchy")
                observed[Data(item.sourceKey.utf8)] = expected
            }
        }
        for (index, operation) in resolved.enumerated() {
            guard case .file(let owner, let name, let mime, let size, let digest) = operation else { continue }
            let item = plan.items[index], mapping = progress.mappings[index]
            guard let fileID = mapping.fileID else { throw AnyDestinationContentVerificationError.invalidProgress }
            let ownerID = try Self.native(owner), path = ["files", fileID]
            let before = try await read(path)
            let expected = AnyJSON.object(["fileId": .string(fileID), "objectId": .string(ownerID),
                "name": .string(name), "mime": .string(mime), "size": .integer(size), "inline": .bool(size < 4096),
                "variant": .string(""), "variantOf": .string("")])
            try Self.equal(AnyDestinationContentProjection.file(before), expected, item.sourceKey, "file metadata")
            let content = try await client.readFileContentDigest(spaceID: plan.binding.workspace.spaceID,
                fileID: fileID, size: size, mime: mime, authorize: admit)
            guard content.byteCount == size, content.sha256 == digest else { throw Self.failure(item.sourceKey, "plaintext file bytes") }
            let after = try await read(path)
            try Self.equal(AnyDestinationContentProjection.file(after), expected, item.sourceKey, "file metadata after read")
            guard after["cached"]?.bool == true, let durable = after["durable"]?.bool,
                  try Self.bytes(before["rootCid"]) == Self.bytes(after["rootCid"]) else {
                throw Self.failure(item.sourceKey, "file cache/content identity")
            }
            if size < 4096 {
                guard durable, after["rootCid"] == nil || after["rootCid"]?.string == "" else {
                    throw Self.failure(item.sourceKey, "inline file tier")
                }
            } else if after["rootCid"]?.string?.isEmpty != false { throw Self.failure(item.sourceKey, "encrypted file content address") }
            observed[Data(item.sourceKey.utf8)] = .object(["metadata": expected, "plaintextSHA256": .string(digest)])
            fileAvailability.append(.init(fileID: fileID, byteCount: size, plaintextSHA256: digest, cached: true, durable: durable))
        }
        // The native file list is bounded to one extra row to detect duplicates
        // without loading unrelated objects or an unbounded workspace listing.
        for (owner, index) in objectIndexes {
            let id = progress.mappings[index].objectID
            let files = resolved.indices.compactMap { fileIndex -> String? in
                if case .file(let ref, _, _, _, _) = resolved[fileIndex],
                   (try? Self.native(ref)).map({ Data($0.utf8) }) == owner { return progress.mappings[fileIndex].fileID }
                return nil
            }
            let listing = try await read(["files"], query: ["objectId": id, "limit": String(files.count + 1)])
            let actual = try Self.array(listing["files"], id, "file census")
            guard actual.count == files.count,
                  Set(actual.compactMap { $0["fileId"]?.string.map { Data($0.utf8) } }) == Set(files.map { Data($0.utf8) }) else {
                throw Self.failure(id, "complete file census")
            }
        }
        for (index, operation) in resolved.enumerated() {
            guard case .propertyUpdate(let object, let owner, let patch) = operation else { continue }
            let id = try Self.native(object), ownerID = try Self.native(owner), item = plan.items[index]
            // The complete final property state (including cycles) was compared
            // on the real object above; retain this operation's exact patch too.
            guard objectsBefore[Data(id.utf8)] != nil else { throw AnyDestinationContentVerificationError.invalidProgress }
            observed[Data(item.sourceKey.utf8)] = .object(["objectId": .string(id), "ownerId": .string(ownerID),
                                                        "patch": try Self.literal(patch)])
        }

        // Detect changes while the comparison was running. This is explicitly
        // still a series of native reads, not a global transactional snapshot.
        for (path, before) in definitionsBefore {
            let after = try await read(path.split(separator: "/").map(String.init))
            guard try Self.bytes(after) == Self.bytes(before) else {
                throw AnyDestinationContentVerificationError.changedDuringRead(path)
            }
        }
        for (id, before) in objectsBefore {
            guard let value = String(data: id, encoding: .utf8) else { throw AnyDestinationContentVerificationError.invalidProgress }
            let after = try await read(["objects", value])
            guard try Self.bytes(after) == Self.bytes(before) else {
                throw AnyDestinationContentVerificationError.changedDuringRead(value)
            }
        }
        for (item, mapping) in zip(plan.items, progress.mappings) {
            guard let value = observed[Data(item.sourceKey.utf8)] else { throw AnyDestinationContentVerificationError.invalidProgress }
            observations.append(.init(sourceKey: item.sourceKey, kind: item.operation.kind, objectID: mapping.objectID,
                                      semanticSHA256: AnyContentDigest.sha256(try Self.bytes(value))))
        }
        try await verifyReceipts()
        try await admit()
        return .init(planSHA256: plan.binding.planSHA256, sourceManifestSHA256: plan.source.captureManifestSHA256,
            destinationAccountID: plan.binding.workspace.accountID, destinationSpaceID: plan.binding.workspace.spaceID,
            destinationStoreID: plan.binding.storeID, observations: observations, files: fileAvailability,
            retainedSourceSystemObjectIDs: plan.coverage.compactMap {
                if case .retainedSystem = $0.disposition { return $0.sourceObjectID }; return nil
            })
    }

    static func bytes<T: Encodable>(_ value: T) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(value)
    }
    static func equal(_ actual: AnyJSON?, _ expected: AnyJSON?, _ sourceKey: String, _ field: String) throws {
        guard try bytes(actual) == bytes(expected) else { throw failure(sourceKey, field) }
    }
    static func failure(_ sourceKey: String, _ field: String) -> AnyDestinationContentVerificationError {
        .mismatch(sourceKey: sourceKey, field: field)
    }
    static func native(_ ref: AnyDestinationReference) throws -> String {
        guard case .native(let value) = ref else { throw AnyDestinationContentVerificationError.invalidProgress }; return value
    }
    static func literal(_ value: AnyDestinationValue) throws -> AnyJSON {
        guard case .literal(let value) = value else { throw AnyDestinationContentVerificationError.invalidProgress }; return value
    }
    static func array(_ value: AnyJSON?, _ sourceKey: String, _ field: String) throws -> [AnyJSON] {
        guard let values = value?.array else { throw failure(sourceKey, field) }; return values
    }
    static func unique(_ values: [AnyJSON], id: String, key: String, sourceKey: String) throws -> AnyJSON {
        let matches = values.filter { $0[key]?.string.map({ Data($0.utf8) }) == Data(id.utf8) }
        guard matches.count == 1 else { throw failure(sourceKey, key) }; return matches[0]
    }
    static func objectRecord(_ value: AnyJSON, id: String, spaceID: String) throws -> AnyJSON {
        guard value["objectId"]?.string.map({ Data($0.utf8) }) == Data(id.utf8),
              let record = value["record"], record.object != nil,
              record["id"]?.string.map({ Data($0.utf8) }) == Data(id.utf8),
              record["spaceId"]?.string.map({ Data($0.utf8) }) == Data(spaceID.utf8),
              let sequence = record["_applySeq"]?.integer, sequence > 0 else { throw failure(id, "object identity/sequence") }
        return record
    }
    static func resolve(_ reference: AnyDestinationReference,
                        in mappings: [Data: AnyDestinationMigrationMapping], destinationSpaceID: String) throws -> String {
        guard case .mapped(let key, let slot, let encoding) = reference else { return try native(reference) }
        guard let mapping = mappings[Data(key.utf8)] else { throw AnyDestinationContentVerificationError.invalidProgress }
        let result: String
        switch slot {
        case .objectID: result = mapping.objectID
        case .record(let index):
            guard mapping.recordIDs.indices.contains(index) else { throw AnyDestinationContentVerificationError.invalidProgress }
            result = mapping.recordIDs[index]
        case .fileID:
            guard let id = mapping.fileID else { throw AnyDestinationContentVerificationError.invalidProgress }; result = id
        }
        switch encoding {
        case .rawID: return result
        case .anyURI: return "any://" + result
        case .fileURI: return try AnyNativeFileReference(spaceID: destinationSpaceID, fileID: result).uri
        }
    }
}
