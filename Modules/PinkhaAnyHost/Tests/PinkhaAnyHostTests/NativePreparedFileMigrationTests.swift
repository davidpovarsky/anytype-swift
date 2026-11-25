import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

final class NativePreparedFileMigrationTests: XCTestCase, @unchecked Sendable {
    private func intent(size: Int64 = 2 << 20, digest: String = String(repeating: "d", count: 64)) throws -> AnyPreparedFileIntent {
        let workspace = try AnyTorahWorkspace(accountID: "account", spaceID: "space")
        let binding = try AnyPreparedMigrationPlanBinding(workspace: workspace, storeID: "native-store",
            planID: String(repeating: "a", count: 64), planSHA256: String(repeating: "b", count: 64))
        return try .init(binding: binding, sourceKey: "source-file", ownerObjectID: "document",
            name: "שלום.bin", mime: "application/octet-stream", size: size, contentSHA256: digest)
    }

    func testFullFileIntentPreservesStableIdentityAndStreamsPayloadSeparately() throws {
        let original = try intent(), changed = try intent(digest: String(repeating: "e", count: 64))
        XCTAssertEqual(original.intentID, changed.intentID)
        XCTAssertNotEqual(original.specSHA256, changed.specSHA256)
        let spec = try JSONDecoder().decode(AnyJSON.self, from: original.specBytes)
        XCTAssertEqual(spec["size"]?.integer, 2 << 20)
        XCTAssertNil(spec["content"])
        XCTAssertLessThan(original.specBytes.count, 1024)
        XCTAssertNoThrow(try intent(size: 4096))
        XCTAssertNoThrow(try intent(size: 512 << 20))
        XCTAssertThrowsError(try intent(size: 4095))
        XCTAssertThrowsError(try intent(size: (512 << 20) + 1))
        XCTAssertThrowsError(try intent(digest: "invalid"))
    }

    func testFullFileReceiptSeparatesNativeRowFromLocalFileCompletion() throws {
        let input = try intent()
        let row = try AnyPreparedFileReceipt(FullFileWire.receipt(input, stage: "file-row-committed"), intent: input)
        XCTAssertFalse(row.isCompleteAndCurrent)
        let done = try AnyPreparedFileReceipt(FullFileWire.receipt(input, stage: "complete"), intent: input)
        XCTAssertTrue(done.localFileComplete)
        XCTAssertFalse(done.networkVerified)
        var bad = FullFileWire.receipt(input, stage: "complete").object!
        bad["localFileComplete"] = .bool(false)
        XCTAssertThrowsError(try AnyPreparedFileReceipt(.object(bad), intent: input))
        for key in ["contentSHA256", "ownerObjectId", "specSHA256", "kind", "intentId"] {
            var changed = FullFileWire.receipt(input, stage: "complete").object!
            changed[key] = .string("foreign")
            XCTAssertThrowsError(try AnyPreparedFileReceipt(.object(changed), intent: input), key)
        }
    }

    func testFullFileKnownPreparationSkipsUploadAndAdvancesExactNativeStages() async throws {
        let input = try intent(), wire = FullFileWire(try intent())
        let service = try client(input, wire)
        let prepared = try await service.prepare(input, fileURL: URL(fileURLWithPath: "/unused-fixture"), authorize: {})
        let recovered = try await service.prepare(input, fileURL: URL(fileURLWithPath: "/missing-after-restart"), authorize: {})
        XCTAssertEqual(prepared, recovered)
        let done = try await service.commit(prepared, authorize: {})
        XCTAssertTrue(done.isCompleteAndCurrent)
        XCTAssertEqual(done.rootCID, prepared.rootCID)
        let stats = await wire.counts()
        XCTAssertEqual(stats.uploads, 1)
        XCTAssertEqual(stats.posts, 3)
    }

    func testFullFileLostCommitAcknowledgementReconcilesWithoutAnotherWrite() async throws {
        let input = try intent(), wire = FullFileWire(try intent(), loseFinal: true)
        let service = try client(input, wire)
        let prepared = try await service.prepare(input, fileURL: URL(fileURLWithPath: "/fixture"), authorize: {})
        do { _ = try await service.commit(prepared, authorize: {}); XCTFail("expected uncertain write") }
        catch { XCTAssertEqual(error as? AnyEngineError, .writeUncertain) }
        let before = await wire.counts()
        let recovered = try await service.commit(prepared, authorize: {})
        XCTAssertTrue(recovered.isCompleteAndCurrent)
        let after = await wire.counts()
        XCTAssertEqual(before.posts, after.posts)
        XCTAssertEqual(after.uploads, 1)
    }

    private func client(_ intent: AnyPreparedFileIntent, _ wire: FullFileWire) throws -> AnyNativePreparedFileMigration {
        let caps = try AnyPreparedFileCapabilities(FullFileWire.capabilities(intent), workspace: intent.binding.workspace)
        return AnyNativePreparedFileMigration(capabilities: caps, request: { method, path, body, authorize in
            try await authorize()
            return try await wire.request(method: method, path: path, body: body)
        }, fileRequest: { path, metadata, _, size, digest, authorize in
            try await authorize()
            return try await wire.upload(path: path, metadata: metadata, size: size, digest: digest)
        })
    }
}

private actor FullFileWire {
    let intent: AnyPreparedFileIntent
    let loseFinal: Bool
    var present = false
    var stage = "file-prepared"
    var uploads = 0
    var posts = 0
    init(_ intent: AnyPreparedFileIntent, loseFinal: Bool = false) { self.intent = intent; self.loseFinal = loseFinal }
    func counts() -> (uploads: Int, posts: Int) { (uploads, posts) }
    static func capabilities(_ i: AnyPreparedFileIntent) -> AnyJSON { .object([
        "contract": .string(AnyNativePreparedFileMigration.contract), "storeId": .string(i.binding.storeID),
        "accountId": .string(i.binding.workspace.accountID), "spaceId": .string(i.binding.workspace.spaceID),
        "preparedFile": .integer(1), "maximumBytes": .integer(512 << 20), "file": .integer(0), "networkVerified": .bool(false)
    ]) }
    static func receipt(_ i: AnyPreparedFileIntent, stage: String) -> AnyJSON {
        .object([
            "contract": .string(AnyNativePreparedFileMigration.contract), "storeId": .string(i.binding.storeID),
            "accountId": .string(i.binding.workspace.accountID), "spaceId": .string(i.binding.workspace.spaceID),
            "planId": .string(i.binding.planID), "planSHA256": .string(i.binding.planSHA256),
            "sourceKey": .string(i.sourceKey), "intentId": .string(i.intentID), "kind": .string("file"),
            "specSHA256": .string(i.specSHA256), "ownerObjectId": .string(i.ownerObjectID),
            "contentSHA256": .string(i.contentSHA256), "size": .integer(i.size),
            "fingerprint": .string(String(repeating: "f", count: 64)), "objectId": .string("native-carrier"),
            "changeId": .string("native-change"), "fileId": .string("native-file"), "recordIds": .array([.string("native-file")]),
            "rootCid": .string("native-content-root"), "stage": .string(stage),
            "outcome": .string(stage == "file-prepared" || stage == "file-root-committed" ? "prepared" : "committed"),
            "localFileComplete": .bool(stage == "complete"), "networkVerified": .bool(false)
        ])
    }
    func upload(path: [String], metadata: AnyJSON, size: Int64, digest: String) throws -> AnyJSON {
        guard Array(path.suffix(2)) == ["file", "prepare"], metadata == intent.prepareBody, size == intent.size, digest == intent.contentSHA256 else { throw AnyPreparedMigrationError.changedIntent }
        uploads += 1; present = true
        return Self.receipt(intent, stage: stage)
    }
    func request(method: String, path: [String], body: AnyJSON?) throws -> AnyJSON {
        if path.last == "capabilities" { return Self.capabilities(intent) }
        guard present else { throw AnyEngineError.http(status: 404, code: "pinkha.migration_not_found") }
        if method == "POST" {
            posts += 1
            stage = posts == 1 ? "file-root-committed" : posts == 2 ? "file-row-committed" : "complete"
            if stage == "complete" && loseFinal { throw AnyEngineError.writeUncertain }
        }
        return Self.receipt(intent, stage: stage)
    }
}
