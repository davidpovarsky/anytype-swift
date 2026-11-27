import Foundation
import XCTest
@testable import PinkhaAnyEngine

#if os(Linux) || os(macOS)
/// Selected only by the owned native controller, after it starts a real retained
/// account copy under OS network denial. Missing fixture is a failure, not skip.
final class AnyNativeMarkdownBodyNativeTests: XCTestCase, @unchecked Sendable {
    func testNativeConditionalBodyCommitAndStaleVersionRefusal() async throws {
        let f = try NativeMarkdownFixture()
        let api = AnyNativeMarkdownBody(client: f.client)
        let before = try await api.read(f.reference, authorize: {})
        XCTAssertEqual(before.content, "")
        let content = try String(contentsOf: f.bodyURL, encoding: .utf8)
        XCTAssertEqual(content.utf8.count, 262144)
        let intent = try AnyNativeMarkdownWriteIntent(reference: f.reference,
            requestID: "0123456789abcdef0123456789abcdef", expectedVersion: before.version, content: content)
        let receipt = try await api.replace(intent, authorizeRead: {}, authorizeWrite: {})
        XCTAssertEqual(receipt.saved.reference, f.reference)
        XCTAssertTrue(receipt.exactRequestedBytesPreserved)
        XCTAssertEqual(receipt.saved.contentSHA256, AnyNativeMarkdownBody.digest(content))
        XCTAssertEqual(receipt.acknowledgement.insertedBlockIDs.count, 256)
        XCTAssertTrue(receipt.acknowledgement.updatedBlockIDs.isEmpty)
        XCTAssertTrue(receipt.acknowledgement.deletedBlockIDs.isEmpty)
        XCTAssertNotEqual(receipt.saved.version, before.version)

        let stale = try AnyNativeMarkdownWriteIntent(reference: f.reference,
            requestID: "1123456789abcdef0123456789abcdef", expectedVersion: before.version,
            content: "A stale body must never replace the committed message.")
        do {
            _ = try await api.replace(stale, authorizeRead: {}, authorizeWrite: {})
            XCTFail("Actual native stale CAS was accepted")
        } catch {
            XCTAssertEqual(error as? AnyEngineError, .http(status: 409, code: "markdown.conflict"))
        }
        let after = try await api.read(f.reference, authorize: {})
        XCTAssertEqual(after.contentSHA256, receipt.saved.contentSHA256)
        XCTAssertEqual(after.version, receipt.saved.version)
        try f.writeProof(name: "write-proof.json", body: .object([
            "accountID": .string(f.reference.accountID), "spaceID": .string(f.reference.spaceID),
            "objectID": .string(f.reference.objectID), "contentBytes": .integer(Int64(after.contentBytes)),
            "contentSHA256": .string(after.contentSHA256), "nativeVersion": .string(after.version),
            "insertedBlockIDs": .array(receipt.acknowledgement.insertedBlockIDs.map(AnyJSON.string)),
            "staleCASRefused": .bool(true), "newNativeWrites": .integer(1)
        ]))
    }

    func testNativeColdReopenReadsOriginalBodyAfterProcessCrash() async throws {
        let f = try NativeMarkdownFixture()
        let original = try JSONDecoder().decode(AnyJSON.self, from: Data(contentsOf: f.proofDirectory.appendingPathComponent("write-proof.json")))
        let saved = try await AnyNativeMarkdownBody(client: f.client).read(f.reference, authorize: {})
        XCTAssertEqual(saved.reference.accountID, original["accountID"]?.string)
        XCTAssertEqual(saved.reference.spaceID, original["spaceID"]?.string)
        XCTAssertEqual(saved.reference.objectID, original["objectID"]?.string)
        XCTAssertEqual(Int64(saved.contentBytes), original["contentBytes"]?.integer)
        XCTAssertEqual(saved.contentSHA256, original["contentSHA256"]?.string)
        let content = try String(contentsOf: f.bodyURL, encoding: .utf8)
        XCTAssertTrue(saved.content.utf8.elementsEqual(content.utf8))
        try f.writeProof(name: "cold-proof.json", body: .object([
            "accountID": .string(f.reference.accountID), "spaceID": .string(f.reference.spaceID),
            "objectID": .string(f.reference.objectID), "contentBytes": .integer(Int64(saved.contentBytes)),
            "contentSHA256": .string(saved.contentSHA256), "nativeVersion": .string(saved.version),
            "nativeVersionChangedAcrossProcess": .bool(saved.version != original["nativeVersion"]?.string),
            "writes": .integer(0)
        ]))
    }
}

private struct NativeMarkdownFixture {
    let client: AnyHTTPClient
    let reference: AnyNativeMarkdownReference
    let bodyURL: URL
    let proofDirectory: URL
    init() throws {
        guard let path = ProcessInfo.processInfo.environment["PINKHA_MARKDOWN_NATIVE_FIXTURE"], !path.isEmpty else {
            throw AnyEngineError.invalidOperation("missing owned native body fixture")
        }
        let fixture = try JSONDecoder().decode(AnyJSON.self, from: Data(contentsOf: URL(fileURLWithPath: path)))
        reference = try .init(accountID: fixture.requireString("accountID"),
                              spaceID: fixture.requireString("spaceID"), objectID: fixture.requireString("objectID"))
        guard let url = URL(string: try fixture.requireString("baseURL")) else { throw AnyEngineError.invalidEndpoint }
        client = try .init(baseURL: url, expectedAccountID: reference.accountID)
        bodyURL = URL(fileURLWithPath: try fixture.requireString("bodyPath"))
        proofDirectory = URL(fileURLWithPath: try fixture.requireString("proofDirectory"), isDirectory: true)
    }
    func writeProof(name: String, body: AnyJSON) throws {
        let path = proofDirectory.appendingPathComponent(name)
        guard !FileManager.default.fileExists(atPath: path.path) else {
            throw AnyEngineError.invalidOperation("native proof path already exists")
        }
        let encoder = JSONEncoder(); encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        try encoder.encode(body).write(to: path, options: [.withoutOverwriting])
    }
}
#endif
