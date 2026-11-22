import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration
import PinkhaKit

public enum AnyNativeHistoryError: Error, Equatable, Sendable {
    case unavailable
    case authorityUnavailable
    case versionNotFound
    case truncated
    case viewTooLarge
    case malformedResponse
    case paginationLimit
    case paginationChanged
}

/// A continuation belongs to one object and one account/Space/native run.
/// Its opaque server value is never decoded or synthesized by the UI.
public struct AnyNativeHistoryCursor: Sendable, Equatable {
    public let workspace: AnyTorahWorkspace
    public let objectID: String
    public let generation: UUID
    public let engineStartedAt: String
    let value: String
}

public struct AnyNativeHistoryChange: Sendable, Equatable, Identifiable {
    public var id: String { version }
    public let version: String
    public let author: String
    /// Author clock for display only. Native DAG/cursor order is retained.
    public let timestamp: Int64
    public let dataset: String
    public let groupSize: Int
    public let truncated: Bool
    /// Retain opaque fields rather than round-tripping a reduced history DTO.
    public let native: AnyJSON

    public init(native: AnyJSON) throws {
        guard native.object != nil,
              let version = native["version"]?.string, AnyEditorBlock.validID(version),
              let author = native["author"]?.string, AnyEditorBlock.validID(author),
              let timestamp = native["timestamp"]?.integer,
              let dataset = native["dataset"]?.string, dataset.utf8.count <= 1024,
              let count = native["groupSize"]?.integer, count == 1,
              native["truncated"] == nil || native["truncated"]?.bool != nil else {
            throw AnyNativeHistoryError.malformedResponse
        }
        _ = try AnyHostCanonical.bytes(native, maximumBytes: 131_072)
        self.version = version; self.author = author; self.timestamp = timestamp
        self.dataset = dataset; self.groupSize = Int(count)
        self.truncated = native["truncated"]?.bool ?? false; self.native = native
    }
}

public struct AnyNativeHistoryPage: Sendable, Equatable {
    public let changes: [AnyNativeHistoryChange]
    public let next: AnyNativeHistoryCursor?
    public let native: AnyJSON

    init(response: AnyJSON, workspace: AnyTorahWorkspace, objectID: String,
         lease: AnyHostLease, previous: AnyNativeHistoryCursor?) throws {
        guard response.object != nil, let rows = response["changes"]?.array, rows.count <= 50,
              response["cursor"] == nil || response["cursor"]?.string != nil else {
            throw AnyNativeHistoryError.malformedResponse
        }
        let changes = try rows.map(AnyNativeHistoryChange.init(native:))
        guard Set(changes.map(\.version)).count == changes.count else {
            throw AnyNativeHistoryError.paginationChanged
        }
        let cursor = response["cursor"]?.string ?? ""
        guard cursor.utf8.count <= 8192, !cursor.utf8.contains(0),
              cursor.isEmpty || (!rows.isEmpty && cursor != previous?.value) else {
            throw AnyNativeHistoryError.paginationChanged
        }
        _ = try AnyHostCanonical.bytes(response, maximumBytes: 2 * 1024 * 1024)
        self.changes = changes; self.native = response
        self.next = cursor.isEmpty ? nil : .init(workspace: workspace, objectID: objectID,
            generation: lease.generation, engineStartedAt: lease.engineStartedAt, value: cursor)
    }
}

public struct AnyNativeHistoryDataset: Sendable, Equatable, Identifiable {
    public var id: String { name }
    public let name: String
    public let records: [AnyJSON]
    public let native: AnyJSON
}

/// A synced causal cut, not a current document or a wall-clock snapshot.
/// Unknown datasets/fields/blocks stay intact and are never submitted as edits.
public struct AnyNativeHistoryVersion: Sendable, Equatable {
    public let version: String
    public let datasets: [AnyNativeHistoryDataset]
    public let editor: AnyEditorSnapshot?
    public let native: AnyJSON

    public init(response: AnyJSON, requestedVersion: String, workspace: AnyTorahWorkspace,
                objectID: String) throws {
        guard response.object != nil, response["version"]?.string == requestedVersion,
              let rows = response["datasets"]?.array else {
            throw AnyNativeHistoryError.malformedResponse
        }
        guard rows.count <= 32 else { throw AnyNativeHistoryError.viewTooLarge }
        var names = Set<String>(), recordCount = 0
        var datasets: [AnyNativeHistoryDataset] = []
        var editor: AnyEditorSnapshot?
        for row in rows {
            guard row.object != nil, let name = row["dataset"]?.string,
                  AnyEditorBlock.validID(name), names.insert(name).inserted,
                  let records = row["records"]?.array, records.allSatisfy({ $0.object != nil }) else {
                throw AnyNativeHistoryError.malformedResponse
            }
            guard records.count <= 10_000 - recordCount else { throw AnyNativeHistoryError.viewTooLarge }
            recordCount += records.count
            datasets.append(.init(name: name, records: records, native: row))
            if name == "editor_blocks" {
                editor = try .init(spaceID: workspace.spaceID, objectID: objectID, title: "",
                    response: .object(["records": .array(records), "total": .integer(Int64(records.count)), "hasNext": .bool(false)]))
            }
        }
        // Bound nested/opaque data as well as the known record counts. The
        // original complete AnyJSON is retained; this is not an export format.
        _ = try AnyHostCanonical.bytes(response, maximumBytes: 8 * 1024 * 1024)
        self.version = requestedVersion; self.datasets = datasets; self.editor = editor; self.native = response
    }
}

public protocol AnyNativeHistoryReading: Sendable {
    var workspace: AnyTorahWorkspace { get }
    var objectID: String { get }
    func page(after: AnyNativeHistoryCursor?, lease: AnyHostLease,
              authorize: @escaping @Sendable () async throws -> Void) async throws -> AnyNativeHistoryPage
    func version(_ id: String, lease: AnyHostLease,
                 authorize: @escaping @Sendable () async throws -> Void) async throws -> AnyNativeHistoryVersion
}

/// Uses the existing current-reader native document policy and account/run
/// lease around every history read. There is no restore or write path.
public struct AnyNativeHistoryReader: AnyNativeHistoryReading, Sendable {
    public let workspace: AnyTorahWorkspace
    public let objectID: String
    private let request: @Sendable ([String], [String: String], Int) async throws -> AnyJSON
    private let authority: @Sendable () async throws -> AnyNativeDocumentTargetProof

    public init(client: AnyHTTPClient, workspace: AnyTorahWorkspace,
                objectID: String, allowedTypeIDs: Set<String>) throws {
        guard client.expectedAccountID == workspace.accountID, AnyEditorBlock.validID(objectID) else {
            throw AnyHostError.wrongWorkspace
        }
        let access = try AnyHTTPTorahTargetAccess(client: client, workspace: workspace,
            allowedTypeIDs: allowedTypeIDs, documentTypePolicy: .nativeCanonicalEditorV1)
        self.workspace = workspace; self.objectID = objectID
        self.request = { path, query, limit in
            try await client.requestJSON(method: "GET", path: path, query: query, maximumResponseBytes: limit)
        }
        self.authority = {
            let member = try await client.requestJSON(method: "GET",
                path: ["v1", "spaces", workspace.spaceID, "members", "me"])
            try AnyHTTPTorahTargetAccess.validateMember(member, workspace: workspace, intent: .read)
            return try await access.currentNativeProof(objectID: objectID, intent: .read)
        }
    }

    /// Scoped transport/authority injection for focused boundary tests.
    init(workspace: AnyTorahWorkspace, objectID: String,
         request: @escaping @Sendable ([String], [String: String], Int) async throws -> AnyJSON,
         authority: @escaping @Sendable () async throws -> AnyNativeDocumentTargetProof) {
        self.workspace = workspace; self.objectID = objectID; self.request = request; self.authority = authority
    }

    public func page(after cursor: AnyNativeHistoryCursor? = nil, lease: AnyHostLease,
                     authorize: @escaping @Sendable () async throws -> Void = {}) async throws -> AnyNativeHistoryPage {
        try await validate(lease)
        if let cursor {
            guard cursor.workspace == workspace, cursor.objectID == objectID,
                  cursor.generation == lease.generation, cursor.engineStartedAt == lease.engineStartedAt else {
                throw AnyHostError.wrongWorkspace
            }
        }
        var query = ["limit": "50", "coalesce": "false"]
        if let cursor { query["cursor"] = cursor.value }
        let response = try await read(path: path, query: query, limit: 1_048_576, lease: lease, authorize: authorize)
        let page = try AnyNativeHistoryPage(response: response, workspace: workspace, objectID: objectID,
                                            lease: lease, previous: cursor)
        try await validate(lease); try await authorize()
        return page
    }

    public func version(_ id: String, lease: AnyHostLease,
                        authorize: @escaping @Sendable () async throws -> Void = {}) async throws -> AnyNativeHistoryVersion {
        guard AnyEditorBlock.validID(id), id != "diff", id != ".", id != ".." else {
            throw AnyNativeHistoryError.malformedResponse
        }
        let response = try await read(path: path + [id], query: [:], limit: 4 * 1024 * 1024,
                                      lease: lease, authorize: authorize)
        let result = try AnyNativeHistoryVersion(response: response, requestedVersion: id,
                                                workspace: workspace, objectID: objectID)
        try await validate(lease); try await authorize()
        return result
    }

    private var path: [String] { ["v1", "spaces", workspace.spaceID, "objects", objectID, "history"] }

    private func validate(_ lease: AnyHostLease) async throws {
        guard lease.workspace == workspace else { throw AnyHostError.wrongWorkspace }
        try await lease.validate()
    }

    private func read(path: [String], query: [String: String], limit: Int, lease: AnyHostLease,
                      authorize: @escaping @Sendable () async throws -> Void) async throws -> AnyJSON {
        try await validate(lease); try await authorize()
        let before = try await currentAuthority()
        guard before.objectID == objectID, before.spaceID == workspace.spaceID else { throw AnyHostError.wrongWorkspace }
        try await validate(lease); try await authorize()
        let result: AnyJSON
        do { result = try await request(path, query, limit) }
        catch AnyEngineError.http(let status, let code) {
            switch code {
            case "history.version_not_found": throw AnyNativeHistoryError.versionNotFound
            case "history.truncated": throw AnyNativeHistoryError.truncated
            case "history.view_too_large": throw AnyNativeHistoryError.viewTooLarge
            case "route.not_found", "not_found", "unknown":
                guard status == 404 else { throw AnyEngineError.http(status: status, code: code) }
                throw AnyNativeHistoryError.unavailable
            default: throw AnyEngineError.http(status: status, code: code)
            }
        } catch AnyEngineError.readLimit { throw AnyNativeHistoryError.viewTooLarge }
        let after = try await currentAuthority()
        guard before == after else { throw AnyNativeDocumentPolicyError.dependenciesChanged }
        try await validate(lease); try await authorize()
        return result
    }

    private func currentAuthority() async throws -> AnyNativeDocumentTargetProof {
        do { return try await authority() }
        catch is CancellationError { throw CancellationError() }
        catch { throw AnyNativeHistoryError.authorityUnavailable }
    }
}
