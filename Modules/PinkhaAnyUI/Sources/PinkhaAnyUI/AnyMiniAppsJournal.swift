#if canImport(UIKit) && canImport(HanlinMiniAppsBridge)
import Foundation
import Darwin
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration
import PinkhaHanlinUI
import HanlinMiniAppsBridge

struct AnyMiniAppsFileReceipt: Codable, Sendable {
    let fileID: String
    let bytes: Int64
    let sha256: String
    let name: String
    let mime: String
}

struct AnyMiniAppsJournalRecord: Codable, Sendable {
    let requestDigest: String
    let resultDigest: String
    var plan: PinkhaMiniAppsEditPlan
    var blockIntents: [String: AnyNativeBlockCreationIntent] = [:]
    var files: [String: AnyMiniAppsFileReceipt] = [:]
    var nativeVersions: [String: String] = [:]
    // Nil identifies a legacy partial receipt that cannot prove a safe retry.
    var dispatchVersions: [String: String]? = [:]
    var nativeStoreID: String?
}

/// The private plan is synchronized before dispatch and before the bridge ACK.
/// Its identity includes engine, account, Space, document and original request.
struct AnyMiniAppsJournal: Sendable {
    let url: URL
    let requestDigest: String
    let resultDigest: String

    init(request: MiniAppInvocation, result: MiniAppResult,
         workspace: AnyTorahWorkspace, objectID: String) throws {
        requestDigest = try AnyMiniAppsCodec.digest(request)
        resultDigest = try AnyMiniAppsCodec.digest(result)
        let support = try FileManager.default.url(for: .applicationSupportDirectory, in: .userDomainMask,
                                                   appropriateFor: nil, create: true)
        let scope = AnyContentDigest.sha256(try AnyMiniAppsCodec.encode([
            "any", workspace.accountID, workspace.spaceID, objectID
        ]))
        let root = support.appendingPathComponent("MiniAppsReceipts", isDirectory: true)
            .appendingPathComponent("any", isDirectory: true).appendingPathComponent(scope, isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true,
                                               attributes: [.posixPermissions: 0o700])
        let values = try root.resourceValues(forKeys: [.isDirectoryKey, .isSymbolicLinkKey])
        guard values.isDirectory == true, values.isSymbolicLink != true,
              root.standardizedFileURL == root.resolvingSymlinksInPath().standardizedFileURL else {
            throw AnyHostError.invalidDocument("private MiniApps receipt directory")
        }
        url = root.appendingPathComponent(request.id.uuidString.lowercased() + ".json")
    }

    func load() throws -> AnyMiniAppsJournalRecord? {
        guard FileManager.default.fileExists(atPath: url.path) else { return nil }
        let values = try url.resourceValues(forKeys: [.isRegularFileKey, .isSymbolicLinkKey, .fileSizeKey])
        guard values.isRegularFile == true, values.isSymbolicLink != true,
              let bytes = values.fileSize, bytes <= 32 << 20 else { throw AnyHostError.invalidDocument("MiniApps receipt") }
        let record = try JSONDecoder().decode(AnyMiniAppsJournalRecord.self, from: Data(contentsOf: url))
        guard record.requestDigest == requestDigest, record.resultDigest == resultDigest else {
            throw MiniAppBridgeError.conflictingResult
        }
        return record
    }

    func save(_ record: AnyMiniAppsJournalRecord) throws {
        guard record.requestDigest == requestDigest, record.resultDigest == resultDigest else {
            throw MiniAppBridgeError.conflictingResult
        }
        let bytes = try AnyMiniAppsCodec.encode(record)
        guard bytes.count <= 32 << 20 else { throw AnyHostError.invalidDocument("MiniApps receipt size") }
        try bytes.write(to: url, options: [.atomic, .completeFileProtectionUntilFirstUserAuthentication])
        try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: url.path)
        let output = try FileHandle(forWritingTo: url); defer { try? output.close() }
        try output.synchronize()
        let fd = open(url.deletingLastPathComponent().path, O_RDONLY | O_DIRECTORY | O_NOFOLLOW)
        guard fd >= 0 else { throw AnyHostError.writeUncertain }
        defer { close(fd) }
        guard fsync(fd) == 0 else { throw AnyHostError.writeUncertain }
    }
}
#endif
