#if PINKHA_PREPARED_INLINE_HTTP_ACCEPTANCE
import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// Selected only by the owned native HTTP handoff. An absent server is a failure.
final class NativePreparedInlineFileHTTPTests: XCTestCase, @unchecked Sendable {
    func testRealNativeInlineFilesRoundTripThroughThePublicSwiftClient() async throws {
        let environment = ProcessInfo.processInfo.environment
        let inputPath = try XCTUnwrap(environment["PINKHA_INLINE_FILE_HANDSHAKE"])
        let resultPath = try XCTUnwrap(environment["PINKHA_INLINE_FILE_RESULT"])
        try require(inputPath.hasPrefix("/") && resultPath.hasPrefix("/"), "Absolute handoff paths required.")
        try require(!FileManager.default.fileExists(atPath: resultPath), "A prior result must not be overwritten.")
        let input = try Data(contentsOf: URL(fileURLWithPath: inputPath))
        try require(input.count <= 8192, "Handoff exceeded its size bound.")
        let handshake = try JSONDecoder().decode(Handshake.self, from: input)
        try require(handshake.protocolName == "pinkha-native-inline-file-http-v1", "Unexpected handoff protocol.")
        try require(AnyNativeCreationIdentity.isHex(handshake.nonce, count: 32), "Invalid owned nonce.")
        let url = try XCTUnwrap(URL(string: handshake.baseURL))
        try require(url.scheme == "http" && url.host == "127.0.0.1" && url.port != nil &&
                    url.user == nil && url.password == nil && url.query == nil && url.fragment == nil &&
                    (url.path.isEmpty || url.path == "/"), "The owned loopback endpoint is required.")
        let output = URL(fileURLWithPath: resultPath)
        do {
            let workspace = try AnyTorahWorkspace(accountID: handshake.accountID, spaceID: handshake.spaceID)
            let http = try AnyHTTPClient(baseURL: url, expectedAccountID: workspace.accountID)
            let migration = try await AnyNativePreparedInlineFileMigration.open(
                client: http, workspace: workspace, authorize: {})
            try require(migration.capabilities.maximumInlineBytes == 4095 &&
                        !migration.capabilities.networkVerified, "Unexpected inline capability.")
            let binding = try AnyPreparedMigrationPlanBinding(
                workspace: workspace, storeID: migration.capabilities.storeID,
                planID: AnyContentDigest.sha256(Data(("swift-inline-http-plan|" + handshake.nonce).utf8)),
                planSHA256: AnyContentDigest.sha256(Data("inline-file-cases:empty+4095/v1".utf8)))
            var observations: [AnyJSON] = []
            var firstCompleted: AnyPreparedInlineFileReceipt?
            for (label, content, name, mime) in [
                ("empty", Data(), "", ""),
                ("maximum", Data((0..<4095).map { UInt8($0 % 256) }), "קובץ 🧪.bin", "application/octet-stream")
            ] {
                let intent = try AnyPreparedInlineFileIntent(binding: binding,
                    sourceKey: "swift-inline-" + label + "-" + handshake.nonce,
                    ownerObjectID: handshake.ownerObjectID, name: name, mime: mime, content: content)
                let prepared = try await migration.prepare(intent, authorize: {})
                try require(prepared.outcome == .prepared, "Fresh inline intent was already committed.")
                if let first = firstCompleted {
                    try require(prepared.stage == .fileRootCommitted && prepared.objectID == first.objectID,
                                "Second file must reuse the already committed owner payload root.")
                    try require(prepared.fileID != first.fileID && prepared.changeID != first.changeID &&
                                prepared.fingerprint != first.fingerprint,
                                "Different source files must keep distinct reserved row identities.")
                } else {
                    try require(prepared.stage == .filePrepared, "First owner payload root must be prepared.")
                }
                let complete = try await migration.commit(prepared, authorize: {})
                try require(complete.isCompleteAndCurrent, "Native file did not complete.")
                try require(complete.fileID == prepared.fileID && complete.objectID == prepared.objectID &&
                            complete.changeID == prepared.changeID && complete.fingerprint == prepared.fingerprint,
                            "Native signed file identity changed across stages.")
                let status = try await migration.status(intent, authorize: {})
                let retry = try await migration.commit(prepared, authorize: {})
                try require(status == complete && retry == complete, "Completed retry changed the native file.")
                if firstCompleted == nil { firstCompleted = complete }
                observations.append(.object([
                    "label": .string(label), "intentId": .string(intent.intentID),
                    "storeId": .string(binding.storeID), "planId": .string(binding.planID),
                    "planSHA256": .string(binding.planSHA256), "sourceKey": .string(intent.sourceKey),
                    "specBase64": .string(intent.specBytes.base64EncodedString()),
                    "specSHA256": .string(intent.specSHA256), "ownerObjectId": .string(intent.ownerObjectID),
                    "objectId": .string(complete.objectID), "changeId": .string(complete.changeID),
                    "fileId": .string(complete.fileID), "fingerprint": .string(complete.fingerprint),
                    "recordIds": .array(complete.recordIDs.map(AnyJSON.string)),
                    "contentSHA256": .string(intent.contentSHA256), "size": .integer(Int64(intent.size)),
                    "stage": .string(complete.stage.rawValue), "outcome": .string(complete.outcome.rawValue)
                ]))
            }
            try write(.object([
                "protocol": .string(handshake.protocolName), "nonce": .string(handshake.nonce),
                "completed": .bool(true), "handshakeSHA256": .string(AnyContentDigest.sha256(input)),
                "observations": .array(observations),
                "scope": .string("Swift client through actual native HTTP; original XCTest and native readback also required")
            ]), to: output)
        } catch {
            try? write(.object([
                "protocol": .string(handshake.protocolName), "nonce": .string(handshake.nonce),
                "completed": .bool(false), "errorType": .string(String(reflecting: type(of: error)))
            ]), to: output)
            throw error
        }
    }

    private struct Handshake: Decodable {
        let protocolName: String
        let nonce: String
        let baseURL: String
        let accountID: String
        let spaceID: String
        let ownerObjectID: String

        enum CodingKeys: String, CodingKey {
            case protocolName = "protocol", nonce, baseURL
            case accountID = "accountId", spaceID = "spaceId", ownerObjectID = "ownerObjectId"
        }
    }

    private struct HandoffFailure: Error { let message: String }

    private func require(_ condition: Bool, _ message: String) throws {
        guard condition else { throw HandoffFailure(message: message) }
    }

    private func write(_ result: AnyJSON, to url: URL) throws {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        let data = try encoder.encode(result)
        try require(data.count <= 32_768, "Handoff result exceeded its size bound.")
        try data.write(to: url, options: .atomic)
    }
}
#endif
