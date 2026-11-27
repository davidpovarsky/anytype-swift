import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration
import PinkhaKit

public struct AnyEditorRead: Sendable {
    public let snapshot: AnyEditorSnapshot
    public let markdown: String
    public let nativeVersion: String
    public let engineStartedAt: String
    public let generation: UUID
}

public struct AnyPreparedBlockEdit: Sendable {
    public let objectID: String
    public let blockID: String
    public let dataset: String
    public let expectedVersion: String
    public let engineStartedAt: String
    public let generation: UUID
    let workspace: AnyTorahWorkspace
    let set: [String: AnyJSON]
    let unset: [String]
    let inverseSet: [String: AnyJSON]
    let inverseUnset: [String]
}

public struct AnyBlockEditReceipt: Sendable {
    public enum Readback: String, Sendable {
        case verifiedCurrent
        case nativeAcceptedButCurrentStateUnverified
    }
    public let objectID: String
    public let blockID: String
    public let nativeVersionID: String
    public let readback: Readback
    /// Nil when another writer moved the document, readback failed, or the
    /// server could not bind a version to precisely this native write.
    public let undo: AnyPreparedBlockEdit?
}

/// Native document I/O. Interactive writes use the compiled Pinkha conditional
/// block API. Stock Any rejects these extra fields before writing; no fallback
/// to unconditional patch or whole-document Markdown replacement is allowed.
public struct AnyEditorDocumentStore: Sendable {
    public let workspace: AnyTorahWorkspace
    private let client: AnyHTTPClient
    private let access: AnyHTTPTorahTargetAccess
    private let blockLimit: Int
    public let dataset: String

    public init(client: AnyHTTPClient, workspace: AnyTorahWorkspace,
                allowedTypeIDs: Set<String>, dataset: String = "editor_blocks",
                blockLimit: Int = 10_000,
                documentTypePolicy: AnyTorahDocumentPolicy = .explicitTypeAllowlist) throws {
        guard client.expectedAccountID == workspace.accountID,
              AnyEditorBlock.validID(dataset), (1...10_000).contains(blockLimit) else {
            throw AnyHostError.wrongWorkspace
        }
        self.client = client; self.workspace = workspace; self.dataset = dataset
        self.blockLimit = blockLimit
        self.access = try .init(client: client, workspace: workspace, allowedTypeIDs: allowedTypeIDs,
                                blockLimit: blockLimit, editorDataset: dataset, documentTypePolicy: documentTypePolicy)
    }

    public func read(objectID: String, lease: AnyHostLease) async throws -> AnyEditorRead {
        try await validate(lease)
        guard AnyEditorBlock.validID(objectID) else { throw AnyHostError.invalidDocument("object ID") }
        try await access.validate(.object(objectId: objectID), intent: .read)
        // Bracket both metadata (including its native version tree) and the
        // editor dataset. A concurrent rename must not produce a mixed title/body.
        for _ in 0..<3 {
            let object = try await objectRecord(objectID: objectID, lease: lease)
            let first = try await markdown(objectID: objectID, lease: lease)
            let response = try await client.requestJSON(method: "POST", path: spacePath + ["query"],
                body: .object(["objectId": .string(objectID), "dataset": .string(dataset),
                    "limit": .integer(Int64(blockLimit + 1)), "includeTotal": .bool(true),
                    "sort": .array([.string("nav.pos"), .string("id")])]),
                authorize: { try await lease.validate() })
            let second = try await markdown(objectID: objectID, lease: lease)
            let objectAfter = try await objectRecord(objectID: objectID, lease: lease)
            guard first.version == second.version, object == objectAfter else { continue }
            let title = object["any"]?["name"]?.string ?? ""
            let snapshot = try AnyEditorSnapshot(spaceID: workspace.spaceID, objectID: objectID,
                                                 title: title, response: response, limit: blockLimit, dataset: dataset)
            try await access.validate(.object(objectId: objectID), intent: .read)
            try await validate(lease)
            return .init(snapshot: snapshot, markdown: second.content, nativeVersion: second.version,
                         engineStartedAt: lease.engineStartedAt, generation: lease.generation)
        }
        throw AnyHostError.changedDocument
    }

    public func prepareTextEdit(_ read: AnyEditorRead, blockID: String, inlineMarkdown: String) throws -> AnyPreparedBlockEdit {
        guard inlineMarkdown.utf8.count <= 65_536 else { throw AnyEngineError.invalidOperation("block text exceeds native limit") }
        return try prepare(read, blockID: blockID, set: ["text": .string(inlineMarkdown)])
    }

    public func prepareWritingStyle(_ read: AnyEditorRead, blockID: String,
                                    direction: AnyWritingDirection, alignment: AnyTextAlignment) throws -> AnyPreparedBlockEdit {
        try prepare(read, blockID: blockID, set: [
            "style.pinkhaWritingDirection": .string(direction.rawValue),
            "style.pinkhaTextAlignment": .string(alignment.rawValue),
            "style.pinkhaAlignmentWasExplicit": .bool(true)
        ])
    }

    public func apply(_ edit: AnyPreparedBlockEdit, lease: AnyHostLease,
                      authorize: @escaping @Sendable () async throws -> Void = {}) async throws -> AnyBlockEditReceipt {
        try await authorize()
        try await validate(lease)
        guard edit.workspace == workspace, edit.dataset == dataset, edit.generation == lease.generation,
              edit.engineStartedAt == lease.engineStartedAt else { throw AnyHostError.wrongWorkspace }
        let target = TorahAssociationTarget.block(objectId: edit.objectID, blockId: edit.blockID)
        try await access.validate(target, intent: .write)
        let result: AnyJSON
        do {
            result = try await client.requestJSON(method: "PATCH",
                path: editorPath(edit.objectID) + ["blocks", edit.blockID],
                body: .object([
                    "set": .object(edit.set), "unset": .array(edit.unset.map(AnyJSON.string)),
                    "ifVersion": .string(edit.expectedVersion),
                    "ifStartedAt": .string(edit.engineStartedAt)
                ]), authorize: {
                    try await lease.validate()
                    try await authorize()
                })
        } catch AnyEngineError.http(let status, let code) where status == 409 &&
            ["blocks.conflict", "blocks.engine_restarted"].contains(code) {
            throw AnyHostError.changedDocument
        } catch AnyEngineError.writeUncertain {
            throw AnyHostError.writeUncertain
        }
        guard result["recordIds"] == .array([.string(edit.blockID)]),
              let version = result["versionId"]?.string, !version.isEmpty,
              result["engineStartedAt"]?.string == lease.engineStartedAt else {
            throw AnyHostError.writeUncertain
        }
        let nextVersion = result["editorVersion"]?.string
        var undo: AnyPreparedBlockEdit?
        var state = AnyBlockEditReceipt.Readback.nativeAcceptedButCurrentStateUnverified
        if let nextVersion, !nextVersion.isEmpty,
           let current = try? await read(objectID: edit.objectID, lease: lease),
           current.nativeVersion == nextVersion,
           let block = current.snapshot.blocks.first(where: { $0.id == edit.blockID }),
           Self.matches(block.native, set: edit.set, unset: edit.unset) {
            state = .verifiedCurrent
            undo = .init(objectID: edit.objectID, blockID: edit.blockID, dataset: dataset, expectedVersion: nextVersion,
                engineStartedAt: edit.engineStartedAt, generation: edit.generation, workspace: workspace,
                set: edit.inverseSet, unset: edit.inverseUnset,
                inverseSet: edit.set, inverseUnset: edit.unset)
        }
        try await validate(lease)
        return .init(objectID: edit.objectID, blockID: edit.blockID, nativeVersionID: version,
                     readback: state, undo: undo)
    }

    private func prepare(_ read: AnyEditorRead, blockID: String, set: [String: AnyJSON]) throws -> AnyPreparedBlockEdit {
        guard read.snapshot.spaceID == workspace.spaceID, read.snapshot.dataset == dataset,
              let block = read.snapshot.blocks.first(where: { $0.id == blockID }),
              read.snapshot.depthFirstIDs.contains(blockID), !read.nativeVersion.isEmpty else {
            throw AnyHostError.invalidSelection
        }
        var inverseSet: [String: AnyJSON] = [:]
        var inverseUnset: [String] = []
        for path in set.keys.sorted() {
            if let value = Self.field(block.native, path: path) {
                inverseSet[path] = value
            } else { inverseUnset.append(path) }
        }
        return .init(objectID: read.snapshot.objectID, blockID: blockID, dataset: dataset, expectedVersion: read.nativeVersion,
            engineStartedAt: read.engineStartedAt, generation: read.generation, workspace: workspace,
            set: set, unset: [], inverseSet: inverseSet, inverseUnset: inverseUnset)
    }

    private func objectRecord(objectID: String, lease: AnyHostLease) async throws -> AnyJSON {
        let object = try await client.requestJSON(method: "GET",
            path: spacePath + ["objects", objectID], authorize: { try await lease.validate() })
        guard object["objectId"]?.string == objectID,
              let record = object["record"],
              record["id"]?.string == objectID,
              record["spaceId"]?.string == workspace.spaceID,
              record["any"]?["name"] == nil || record["any"]?["name"]?.string != nil else {
            throw AnyHostError.invalidDocument("native object identity")
        }
        return record
    }

    private func markdown(objectID: String, lease: AnyHostLease) async throws -> (content: String, version: String) {
        let value = try await client.requestJSON(method: "GET", path: editorPath(objectID) + ["markdown"],
                                                authorize: { try await lease.validate() })
        let content = try value.requireString("content")
        let version = try value.requireString("version")
        guard !version.isEmpty, version.utf8.count <= 1024,
              content.utf8.count <= 16_777_216 else { throw AnyEngineError.readLimit }
        return (content, version)
    }

    private func validate(_ lease: AnyHostLease) async throws {
        guard lease.workspace == workspace else { throw AnyHostError.wrongWorkspace }
        try await lease.validate()
    }

    private var spacePath: [String] { ["v1", "spaces", workspace.spaceID] }
    private func editorPath(_ objectID: String) -> [String] {
        spacePath + ["objects", objectID, "editor", dataset]
    }
    static func field(_ value: AnyJSON, path: String) -> AnyJSON? {
        path.split(separator: ".").reduce(Optional(value)) { $0?[$1.description] }
    }
    static func matches(_ native: AnyJSON, set: [String: AnyJSON], unset: [String]) -> Bool {
        set.allSatisfy { entry in
            let actual = field(native, path: entry.key)
            if entry.key == "text", let expected = entry.value.string {
                guard let value = actual?.string else { return false }
                return value.utf8.elementsEqual(expected.utf8)
            }
            return actual == entry.value
        } && unset.allSatisfy { field(native, path: $0) == nil }
    }
}
