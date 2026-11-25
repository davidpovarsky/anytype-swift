import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

typealias AnyDestinationAuthorization = @Sendable () async throws -> Void

enum AnyDestinationNativeIntent: Sendable {
    case definition(AnyPreparedDefinitionIntent)
    case object(AnyPreparedMigrationIntent)
    case inlineFile(AnyPreparedInlineFileIntent)
    case file(AnyPreparedFileIntent)
    case properties(AnyPreparedPropertyUpdateIntent)

    var identity: (id: String, spec: Data, sha: String) {
        switch self {
        case .definition(let i): (i.intentID, i.specBytes, i.specSHA256)
        case .object(let i): (i.intentID, i.specBytes, i.specSHA256)
        case .inlineFile(let i): (i.intentID, i.specBytes, i.specSHA256)
        case .file(let i): (i.intentID, i.specBytes, i.specSHA256)
        case .properties(let i): (i.intentID, i.specBytes, i.specSHA256)
        }
    }

    func validateReceipt(_ value: AnyJSON) throws {
        switch self {
        case .definition(let i): _ = try AnyPreparedDefinitionReceipt(value, intent: i)
        case .object(let i): _ = try AnyPreparedMigrationReceipt(value, intent: i)
        case .inlineFile(let i): _ = try AnyPreparedInlineFileReceipt(value, intent: i)
        case .file(let i): _ = try AnyPreparedFileReceipt(value, intent: i)
        case .properties(let i): _ = try AnyPreparedPropertyUpdateReceipt(value, intent: i)
        }
    }

    static func make(_ operation: AnyDestinationMigrationOperation, binding: AnyPreparedMigrationPlanBinding,
                     sourceKey: String, sequence: Int64?, inlineContent: Data?) throws -> Self {
        func id(_ reference: AnyDestinationReference) throws -> String {
            guard case .native(let value) = reference else { throw AnyDestinationMigrationError.journalCorrupt }
            return value
        }
        func json(_ value: AnyDestinationValue) throws -> AnyJSON {
            guard case .literal(let value) = value else { throw AnyDestinationMigrationError.journalCorrupt }
            return value
        }
        guard (operation.kind == "propertyUpdate") == (sequence != nil),
              (operation.kind == "inlineFile") == (inlineContent != nil) else {
            throw AnyDestinationMigrationError.journalCorrupt
        }
        switch operation {
        case .typeDefinition(let seed):
            return .definition(try .type(binding: binding, sourceKey: sourceKey, xKey: seed.xKey, name: seed.name,
                description: seed.description, iconCID: seed.iconCID, layout: seed.layout.map(json),
                hidden: seed.hidden, meta: json(seed.meta)))
        case .collectionDefinition(let seed):
            return .definition(try .collection(binding: binding, sourceKey: sourceKey, xKey: seed.xKey, name: seed.name,
                description: seed.description, iconCID: seed.iconCID, hidden: seed.hidden, meta: json(seed.meta)))
        case .propertyDefinition(let owner, let kind, let name, let xKey, let description, let scope, let format, let index):
            guard let kind = AnyPreparedDefinitionIntent.PropertyKind(rawValue: kind),
                  let scope = AnyPreparedDefinitionIntent.PropertyScope(rawValue: scope) else {
                throw AnyDestinationMigrationError.invalidPlan("property vocabulary")
            }
            return .definition(try .property(binding: binding, sourceKey: sourceKey, ownerID: id(owner),
                kind: kind, name: name, xKey: xKey, description: description, scope: scope,
                xFormat: format.map(json), index: index))
        case .partDefinition(let owner, let draft):
            return .definition(try .part(binding: binding, sourceKey: sourceKey, ownerID: id(owner), draft: json(draft)))
        case .object(let type, let collections, let properties):
            return .object(try .object(binding: binding, sourceKey: sourceKey, typeID: id(type),
                collections: collections.map(id), initialProperties: json(properties)))
        case .editorBlock(let owner, let dataset, let type, let text, let style, let parent, let position):
            return .object(try .block(binding: binding, sourceKey: sourceKey, objectID: id(owner), dataset: dataset,
                type: type, text: text, style: json(style), parentID: parent.map(id) ?? "", position: position))
        case .file(let owner, let name, let mime, let size, let digest):
            if size < 4096 {
                guard let data = inlineContent, Int64(data.count) == size,
                      AnyContentDigest.sha256(data) == digest else { throw AnyDestinationMigrationError.payloadMismatch(sourceKey) }
                return .inlineFile(try .init(binding: binding, sourceKey: sourceKey, ownerObjectID: id(owner),
                                             name: name, mime: mime, content: data))
            }
            return .file(try .init(binding: binding, sourceKey: sourceKey, ownerObjectID: id(owner),
                name: name, mime: mime, size: size, contentSHA256: digest))
        case .propertyUpdate(let object, let owner, let patch):
            guard let values = try json(patch).object, let sequence else {
                throw AnyDestinationMigrationError.journalCorrupt
            }
            return .properties(try .init(binding: binding, sourceKey: sourceKey, objectID: id(object),
                ownerID: id(owner), patch: values, expectedApplySequence: sequence))
        }
    }
}

protocol AnyDestinationNativeDriving: Sendable {
    func status(_ intent: AnyDestinationNativeIntent, authorize: @escaping AnyDestinationAuthorization) async throws -> AnyJSON
    func prepare(_ intent: AnyDestinationNativeIntent, payload: URL?, authorize: @escaping AnyDestinationAuthorization) async throws -> AnyJSON
    func commit(_ intent: AnyDestinationNativeIntent, receipt: AnyJSON, authorize: @escaping AnyDestinationAuthorization) async throws -> AnyJSON
    func applySequence(objectID: String, authorize: @escaping AnyDestinationAuthorization) async throws -> Int64
}

/// Production adaptation uses the existing typed native clients. It does not
/// implement an alternative auto-ID, generic HTTP mutation or retry path.
struct AnyDestinationNativeClients: AnyDestinationNativeDriving {
    let client: AnyHTTPClient
    let workspace: AnyTorahWorkspace
    let definitions: AnyNativePreparedDefinitionMigration?
    let objects: AnyNativePreparedMigration?
    let inlineFiles: AnyNativePreparedInlineFileMigration?
    let files: AnyNativePreparedFileMigration?
    let properties: AnyNativePreparedPropertyUpdate?

    static func open(client: AnyHTTPClient, plan: AnyDestinationMigrationPlan,
                     authorize: @escaping AnyDestinationAuthorization) async throws -> Self {
        let binding = plan.binding, workspace = binding.workspace
        guard Data(client.expectedAccountID.utf8) == Data(workspace.accountID.utf8) else { throw AnyHostError.wrongWorkspace }
        let kinds = Set(plan.items.map { $0.operation.kind })
        var definitions: AnyNativePreparedDefinitionMigration?
        var objects: AnyNativePreparedMigration?
        var inlineFiles: AnyNativePreparedInlineFileMigration?
        var files: AnyNativePreparedFileMigration?
        var properties: AnyNativePreparedPropertyUpdate?
        func store(_ value: String) throws {
            guard Data(value.utf8) == Data(binding.storeID.utf8) else { throw AnyPreparedMigrationError.changedStore }
        }
        if !kinds.isDisjoint(with: ["typeDefinition", "collectionDefinition", "propertyDefinition", "partDefinition"]) {
            let value = try await AnyNativePreparedDefinitionMigration.open(client: client, workspace: workspace, authorize: authorize)
            try store(value.capabilities.storeID)
            guard !kinds.contains("partDefinition") || value.capabilities.supportsParts else {
                throw AnyDestinationMigrationError.unsupportedCapability("partDefinition")
            }
            definitions = value
        }
        if !kinds.isDisjoint(with: ["object", "editorBlock"]) {
            let value = try await AnyNativePreparedMigration.open(client: client, workspace: workspace, authorize: authorize)
            try store(value.capabilities.storeID); objects = value
        }
        if kinds.contains("inlineFile") {
            let value = try await AnyNativePreparedInlineFileMigration.open(client: client, workspace: workspace, authorize: authorize)
            try store(value.capabilities.storeID); inlineFiles = value
        }
        if kinds.contains("file") {
            let value = try await AnyNativePreparedFileMigration.open(client: client, workspace: workspace, authorize: authorize)
            try store(value.capabilities.storeID); files = value
        }
        if kinds.contains("propertyUpdate") {
            let value = try await AnyNativePreparedPropertyUpdate.open(client: client, workspace: workspace, authorize: authorize)
            try store(value.capabilities.storeID); properties = value
        }
        try await AnyDestinationDefinitionChecks.admitCanonicalProperties(plan.coverage, client: client,
            workspace: workspace, authorize: authorize)
        return .init(client: client, workspace: workspace, definitions: definitions, objects: objects,
                     inlineFiles: inlineFiles, files: files, properties: properties)
    }

    private func require<T>(_ value: T?) throws -> T {
        guard let value else { throw AnyPreparedMigrationError.unsupportedContract }; return value
    }

    func status(_ intent: AnyDestinationNativeIntent, authorize: @escaping AnyDestinationAuthorization) async throws -> AnyJSON {
        switch intent {
        case .definition(let i): return Self.wire(try await require(definitions).status(i, authorize: authorize))
        case .object(let i): return Self.wire(try await require(objects).status(i, authorize: authorize))
        case .inlineFile(let i): return Self.wire(try await require(inlineFiles).status(i, authorize: authorize))
        case .file(let i): return Self.wire(try await require(files).status(i, authorize: authorize))
        case .properties(let i): return Self.wire(try await require(properties).status(i, authorize: authorize))
        }
    }
    func prepare(_ intent: AnyDestinationNativeIntent, payload: URL?, authorize: @escaping AnyDestinationAuthorization) async throws -> AnyJSON {
        switch intent {
        case .definition(let i): return Self.wire(try await require(definitions).prepare(i, authorize: authorize))
        case .object(let i): return Self.wire(try await require(objects).prepare(i, authorize: authorize))
        case .inlineFile(let i): return Self.wire(try await require(inlineFiles).prepare(i, authorize: authorize))
        case .file(let i):
            guard let payload else { throw AnyDestinationMigrationError.payloadMismatch(i.sourceKey) }
            return Self.wire(try await require(files).prepare(i, fileURL: payload, authorize: authorize))
        case .properties(let i): return Self.wire(try await require(properties).prepare(i, authorize: authorize))
        }
    }
    func commit(_ intent: AnyDestinationNativeIntent, receipt: AnyJSON,
                authorize: @escaping AnyDestinationAuthorization) async throws -> AnyJSON {
        switch intent {
        case .definition(let i): return Self.wire(try await require(definitions).commit(.init(receipt, intent: i), authorize: authorize))
        case .object(let i): return Self.wire(try await require(objects).commit(.init(receipt, intent: i), authorize: authorize))
        case .inlineFile(let i): return Self.wire(try await require(inlineFiles).commit(.init(receipt, intent: i), authorize: authorize))
        case .file(let i): return Self.wire(try await require(files).commit(.init(receipt, intent: i), authorize: authorize))
        case .properties(let i): return Self.wire(try await require(properties).commit(.init(receipt, intent: i), authorize: authorize))
        }
    }
    func applySequence(objectID: String, authorize: @escaping AnyDestinationAuthorization) async throws -> Int64 {
        let value = try await client.requestJSON(method: "GET", path: ["v1", "spaces", workspace.spaceID, "objects", objectID],
                                                maximumResponseBytes: 8 << 20, authorize: authorize)
        guard let actual = value["objectId"]?.string, Data(actual.utf8) == Data(objectID.utf8),
              let record = value["record"], let id = record["id"]?.string,
              Data(id.utf8) == Data(objectID.utf8), let space = record["spaceId"]?.string,
              Data(space.utf8) == Data(workspace.spaceID.utf8),
              let sequence = record["_applySeq"]?.integer, sequence > 0 else {
            throw AnyDestinationMigrationError.changedIdentity(objectID)
        }
        try await authorize(); try Task.checkCancellation(); return sequence
    }

    private static func base(contract: String, binding: AnyPreparedMigrationPlanBinding,
                             sourceKey: String, kind: String, intentID: String, specSHA256: String,
                             fingerprint: String, stage: String, outcome: String,
                             objectID: String?, changeID: String?, recordIDs: [String]) -> [String: AnyJSON] {
        var value: [String: AnyJSON] = ["contract": .string(contract), "intentId": .string(intentID),
            "storeId": .string(binding.storeID), "accountId": .string(binding.workspace.accountID),
            "spaceId": .string(binding.workspace.spaceID), "planId": .string(binding.planID),
            "planSHA256": .string(binding.planSHA256), "sourceKey": .string(sourceKey),
            "kind": .string(kind), "specSHA256": .string(specSHA256), "fingerprint": .string(fingerprint),
            "stage": .string(stage), "outcome": .string(outcome), "recordIds": .array(recordIDs.map(AnyJSON.string))]
        if let objectID { value["objectId"] = .string(objectID) }
        if let changeID { value["changeId"] = .string(changeID) }
        return value
    }
    static func wire(_ r: AnyPreparedDefinitionReceipt) -> AnyJSON {
        let i = r.intent
        return .object(base(contract: AnyNativePreparedDefinitionMigration.contract, binding: i.binding,
            sourceKey: i.sourceKey, kind: i.kind.rawValue, intentID: i.intentID, specSHA256: i.specSHA256,
            fingerprint: r.fingerprint, stage: r.stage.rawValue, outcome: r.outcome.rawValue,
            objectID: r.objectID, changeID: r.changeID, recordIDs: r.recordIDs))
    }
    static func wire(_ r: AnyPreparedMigrationReceipt) -> AnyJSON {
        let i = r.intent
        return .object(base(contract: AnyNativePreparedMigration.contract, binding: i.binding,
            sourceKey: i.sourceKey, kind: i.kind.rawValue, intentID: i.intentID, specSHA256: i.specSHA256,
            fingerprint: r.fingerprint, stage: r.stage.rawValue, outcome: r.outcome.rawValue,
            objectID: r.objectID, changeID: r.changeID, recordIDs: r.recordIDs))
    }
    static func wire(_ r: AnyPreparedPropertyUpdateReceipt) -> AnyJSON {
        let i = r.intent
        return .object(base(contract: AnyNativePreparedPropertyUpdate.contract, binding: i.binding,
            sourceKey: i.sourceKey, kind: "propertyUpdate", intentID: i.intentID, specSHA256: i.specSHA256,
            fingerprint: r.fingerprint, stage: r.stage.rawValue, outcome: r.outcome.rawValue,
            objectID: r.objectID, changeID: r.changeID, recordIDs: r.recordIDs))
    }
    static func wire(_ r: AnyPreparedInlineFileReceipt) -> AnyJSON {
        let i = r.intent
        var v = base(contract: AnyNativePreparedInlineFileMigration.contract, binding: i.binding,
            sourceKey: i.sourceKey, kind: "inlineFile", intentID: i.intentID, specSHA256: i.specSHA256,
            fingerprint: r.fingerprint, stage: r.stage.rawValue, outcome: r.outcome.rawValue,
            objectID: r.objectID, changeID: r.changeID, recordIDs: r.recordIDs)
        v["ownerObjectId"] = .string(i.ownerObjectID); v["fileId"] = .string(r.fileID)
        v["contentSHA256"] = .string(i.contentSHA256); v["size"] = .integer(Int64(i.size))
        return .object(v)
    }
    static func wire(_ r: AnyPreparedFileReceipt) -> AnyJSON {
        let i = r.intent
        var v = base(contract: AnyNativePreparedFileMigration.contract, binding: i.binding,
            sourceKey: i.sourceKey, kind: "file", intentID: i.intentID, specSHA256: i.specSHA256,
            fingerprint: r.fingerprint, stage: r.stage.rawValue, outcome: r.outcome.rawValue,
            objectID: r.objectID, changeID: r.changeID, recordIDs: r.recordIDs)
        v["ownerObjectId"] = .string(i.ownerObjectID); v["fileId"] = .string(r.fileID)
        v["contentSHA256"] = .string(i.contentSHA256); v["size"] = .integer(i.size)
        v["rootCid"] = .string(r.rootCID); v["localFileComplete"] = .bool(r.localFileComplete)
        v["networkVerified"] = .bool(r.networkVerified)
        return .object(v)
    }
}

extension AnyDestinationMigrationOperation {
    func resolved(_ resolve: (AnyDestinationReference) throws -> String) throws -> Self {
        func id(_ r: AnyDestinationReference) throws -> AnyDestinationReference { .native(try resolve(r)) }
        func json(_ v: AnyDestinationValue) throws -> AnyDestinationValue { .literal(try v.resolved(resolve)) }
        func seed(_ v: AnyDestinationRootDefinition) throws -> AnyDestinationRootDefinition {
            .init(xKey: v.xKey, name: v.name, description: v.description, iconCID: v.iconCID,
                  layout: try v.layout.map(json), hidden: v.hidden, meta: try json(v.meta))
        }
        switch self {
        case .typeDefinition(let v): return .typeDefinition(try seed(v))
        case .collectionDefinition(let v): return .collectionDefinition(try seed(v))
        case .propertyDefinition(let owner, let kind, let name, let key, let description, let scope, let format, let index):
            return .propertyDefinition(owner: try id(owner), kind: kind, name: name, xKey: key,
                description: description, scope: scope, xFormat: try format.map(json), index: index)
        case .partDefinition(let owner, let draft): return .partDefinition(owner: try id(owner), draft: try json(draft))
        case .object(let type, let collections, let props):
            return .object(type: try id(type), collections: try collections.map(id), initialProperties: try json(props))
        case .editorBlock(let owner, let dataset, let type, let text, let style, let parent, let position):
            return .editorBlock(owner: try id(owner), dataset: dataset, type: type, text: text,
                                style: try json(style), parent: try parent.map(id), position: position)
        case .file(let owner, let name, let mime, let size, let digest):
            return .file(owner: try id(owner), name: name, mime: mime, size: size, contentSHA256: digest)
        case .propertyUpdate(let object, let owner, let patch):
            return .propertyUpdate(object: try id(object), owner: try id(owner), patch: try json(patch))
        }
    }
}
