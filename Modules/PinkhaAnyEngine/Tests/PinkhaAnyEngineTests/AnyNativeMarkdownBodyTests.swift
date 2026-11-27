import Foundation
import XCTest
@testable import PinkhaAnyEngine

final class AnyNativeMarkdownBodyTests: XCTestCase, @unchecked Sendable {
    func testScopeUsesExactIdentityBytesAndRejectsPathAmbiguity() throws {
        let composed = try scope("account-\u{00E9}")
        let decomposed = try scope("account-e\u{0301}")
        XCTAssertNotEqual(composed, decomposed)
        for invalid in ["", ".", "..", "a/b", "a%2Fb", "a b", "a?b", "a#b"] {
            XCTAssertThrowsError(try AnyNativeMarkdownReference(accountID: "account", spaceID: "space", objectID: invalid))
        }
    }

    func testIntentRequiresCASCorrelationAndUTF8Bounds() throws {
        let reference = try scope()
        for version in ["", "v 1", "v\n1", String(repeating: "v", count: 1025)] {
            XCTAssertThrowsError(try AnyNativeMarkdownWriteIntent(reference: reference, requestID: String(repeating: "a", count: 32), expectedVersion: version, content: "x"))
        }
        for request in ["", String(repeating: "A", count: 32), String(repeating: "a", count: 31)] {
            XCTAssertThrowsError(try AnyNativeMarkdownWriteIntent(reference: reference, requestID: request, expectedVersion: "v1", content: "x"))
        }
        let limit = String(repeating: "א", count: 131072)
        let accepted = try intent(content: limit)
        XCTAssertEqual(accepted.context.requestedContentBytes, 262144)
        XCTAssertThrowsError(try intent(content: limit + "x"))
        XCTAssertFalse(String(reflecting: accepted).contains(limit))
    }

    func testReadbackDigestIsOfExactUTF8AndRequiresNativeVersion() throws {
        let reference = try scope()
        let a = try AnyNativeMarkdownBody.decodeSnapshot(.object(["content": .string("é"), "version": .string("v1")]), reference: reference)
        let b = try AnyNativeMarkdownBody.decodeSnapshot(.object(["content": .string("e\u{0301}"), "version": .string("v1")]), reference: reference)
        XCTAssertNotEqual(a.contentSHA256, b.contentSHA256)
        XCTAssertEqual(a.contentBytes, 2); XCTAssertEqual(b.contentBytes, 3)
        XCTAssertThrowsError(try AnyNativeMarkdownBody.decodeSnapshot(.object(["content": .string("private body")]), reference: reference))
        XCTAssertFalse(String(reflecting: a).contains("é"))
    }

    func testMalformedOrOverlappingBlockReceiptsCannotBecomeSuccess() throws {
        let context = try intent().context
        let valid: AnyJSON = .object(["version": .string("v2"), "inserted": .array([.string("b")]),
                                     "updated": .array([]), "deleted": .array([]), "unchanged": .integer(0)])
        XCTAssertEqual(try AnyNativeMarkdownBody.decodeAcknowledgement(valid, context: context).insertedBlockIDs, ["b"])
        for (key, value) in [("version", AnyJSON.string("")), ("unchanged", .integer(-1)),
                             ("inserted", .array([.string("b"), .string("b")])),
                             ("updated", .array([.string("b")])), ("deleted", .null)] {
            var row = valid.object!; row[key] = value
            XCTAssertThrowsError(try AnyNativeMarkdownBody.decodeAcknowledgement(.object(row), context: context))
        }
    }

    private func scope(_ account: String = "account") throws -> AnyNativeMarkdownReference {
        try .init(accountID: account, spaceID: "space", objectID: "object")
    }
    private func intent(content: String = "private body") throws -> AnyNativeMarkdownWriteIntent {
        try .init(reference: scope(), requestID: String(repeating: "a", count: 32), expectedVersion: "v1", content: content)
    }
}

#if os(Linux) || os(macOS)
final class AnyNativeMarkdownBodyHTTPTests: XCTestCase, @unchecked Sendable {
    func testCurrentReadRequiresLiveScopeAndDoesNotWrite() async throws {
        let f = try MarkdownFixture(); defer { f.stop() }
        let value = try await AnyNativeMarkdownBody(client: f.client()).read(f.reference(), authorize: {})
        XCTAssertEqual(value.version, "v1"); XCTAssertEqual(value.content, "")
        XCTAssertEqual(try f.methods(), ["GET"])
    }

    func testOneConditionalWriteRetainsOriginalIDAndSameVersionReadback() async throws {
        let f = try MarkdownFixture(); defer { f.stop() }
        let approvals = MarkdownApproval()
        let receipt = try await AnyNativeMarkdownBody(client: f.client()).replace(f.intent(),
            authorizeRead: {}, authorizeWrite: { try await approvals.consume() })
        XCTAssertEqual(receipt.saved.reference, try f.reference())
        XCTAssertEqual(receipt.acknowledgement.context.requestID, String(repeating: "a", count: 32))
        XCTAssertEqual(receipt.saved.version, "v2")
        XCTAssertEqual(receipt.saved.content, "private body")
        XCTAssertTrue(receipt.exactRequestedBytesPreserved)
        let count = await approvals.count; XCTAssertEqual(count, 1)
        XCTAssertEqual(try f.methods(), ["PUT", "GET"])
        XCTAssertEqual(try f.events().first?["body"]?["ifVersion"]?.string, "v1")
    }

    func testCanonicalizedNativeBodyIsExplicitAndBoundToSavedVersion() async throws {
        let f = try MarkdownFixture(normalized: "# Header"); defer { f.stop() }
        let receipt = try await AnyNativeMarkdownBody(client: f.client()).replace(
            f.intent(content: "Header\n======"), authorizeRead: {}, authorizeWrite: {})
        XCTAssertEqual(receipt.saved.content, "# Header")
        XCTAssertFalse(receipt.exactRequestedBytesPreserved)
        XCTAssertEqual(receipt.saved.version, receipt.acknowledgement.nativeVersion)
    }

    func testNativeConflictPreservesTypedRefusalAndDoesNotRetry() async throws {
        let f = try MarkdownFixture(mode: "conflict"); defer { f.stop() }
        do {
            _ = try await AnyNativeMarkdownBody(client: f.client()).replace(f.intent(), authorizeRead: {}, authorizeWrite: {})
            XCTFail("Stale native body was accepted")
        } catch { XCTAssertEqual(error as? AnyEngineError, .http(status: 409, code: "markdown.conflict")) }
        XCTAssertEqual(try f.methods(), ["PUT"])
    }

    func testMalformedSuccessRetainsOriginalPageAsUncertain() async throws {
        for mode in ["malformed-json", "missing-ack-version"] {
            let f = try MarkdownFixture(mode: mode); defer { f.stop() }
            do {
                _ = try await AnyNativeMarkdownBody(client: f.client()).replace(f.intent(), authorizeRead: {}, authorizeWrite: {})
                XCTFail("Ambiguous native acknowledgement became success")
            } catch AnyNativeMarkdownWriteFailure.uncertain(let context) {
                XCTAssertEqual(context.reference, try f.reference())
                XCTAssertEqual(context.requestID, String(repeating: "a", count: 32))
            }
            XCTAssertEqual(try f.methods(), ["PUT"])
        }
    }

    func testLateRevocationWithholdsReceiptWithoutSecondApproval() async throws {
        let f = try MarkdownFixture(); defer { f.stop() }
        let approvals = MarkdownApproval()
        do {
            _ = try await AnyNativeMarkdownBody(client: f.client()).replace(f.intent(),
                authorizeRead: { try f.requireBefore("write") }, authorizeWrite: { try await approvals.consume() })
            XCTFail("A late revoked acknowledgement was delivered")
        } catch AnyNativeMarkdownWriteFailure.uncertain(let context) {
            XCTAssertEqual(context.reference, try f.reference())
        }
        let count = await approvals.count; XCTAssertEqual(count, 1)
        XCTAssertEqual(try f.methods(), ["PUT"])
    }

    func testReadbackRevocationRetainsNativeAcknowledgementWithoutPrivateBody() async throws {
        let f = try MarkdownFixture(); defer { f.stop() }
        do {
            _ = try await AnyNativeMarkdownBody(client: f.client()).replace(f.intent(),
                authorizeRead: { try f.requireBefore("readback") }, authorizeWrite: {})
            XCTFail("Revoked private readback escaped")
        } catch AnyNativeMarkdownWriteFailure.acknowledgedReadbackUnavailable(let ack) {
            XCTAssertEqual(ack.nativeVersion, "v2")
            XCTAssertEqual(ack.context.reference, try f.reference())
        }
        XCTAssertEqual(try f.methods(), ["PUT", "GET"])
    }

    func testChangedReadbackCannotCertifyEarlierAcknowledgement() async throws {
        let f = try MarkdownFixture(mode: "readback-changed"); defer { f.stop() }
        do {
            _ = try await AnyNativeMarkdownBody(client: f.client()).replace(f.intent(), authorizeRead: {}, authorizeWrite: {})
            XCTFail("Concurrent body replaced the saved receipt")
        } catch AnyNativeMarkdownWriteFailure.acknowledgedReadbackChanged(let ack) {
            XCTAssertEqual(ack.nativeVersion, "v2")
            XCTAssertEqual(ack.context.reference, try f.reference())
        }
        XCTAssertEqual(try f.methods(), ["PUT", "GET"])
    }

    func testReadbackAuthorityErrorKeepsKnownOriginalAcknowledgement() async throws {
        let f = try MarkdownFixture(mode: "readback-forbidden"); defer { f.stop() }
        do {
            _ = try await AnyNativeMarkdownBody(client: f.client()).replace(f.intent(), authorizeRead: {}, authorizeWrite: {})
            XCTFail("Unreadable body was certified")
        } catch AnyNativeMarkdownWriteFailure.acknowledgedReadbackUnavailable(let ack) {
            XCTAssertEqual(ack.insertedBlockIDs, ["block-1"])
            XCTAssertEqual(ack.nativeVersion, "v2")
        }
        XCTAssertEqual(try f.methods(), ["PUT", "GET"])
    }

    func testAccountSwitchAfterDispatchRetainsUncertainOriginalScope() async throws {
        let f = try MarkdownFixture(mode: "account-switch"); defer { f.stop() }
        do {
            _ = try await AnyNativeMarkdownBody(client: f.client()).replace(f.intent(), authorizeRead: {}, authorizeWrite: {})
            XCTFail("A different account received the old receipt")
        } catch AnyNativeMarkdownWriteFailure.uncertain(let context) {
            XCTAssertEqual(context.reference.accountID, "account")
            XCTAssertEqual(context.reference.objectID, "object")
        }
        XCTAssertEqual(try f.methods(), ["PUT"])
    }

    func testForeignAccountIntentIsRefusedBeforeTargetRequest() async throws {
        let f = try MarkdownFixture(); defer { f.stop() }
        let foreign = try AnyNativeMarkdownReference(accountID: "other", spaceID: "space", objectID: "object")
        let intent = try AnyNativeMarkdownWriteIntent(reference: foreign, requestID: String(repeating: "a", count: 32),
                                                     expectedVersion: "v1", content: "private body")
        do {
            _ = try await AnyNativeMarkdownBody(client: f.client()).replace(intent, authorizeRead: {}, authorizeWrite: {})
            XCTFail("Foreign account dispatched")
        } catch { XCTAssertEqual(error as? AnyEngineError, .accountChanged) }
        XCTAssertEqual(try f.methods(), [])
    }

    func testNativePartialRejectionRemainsRefusalWithoutReadback() async throws {
        let f = try MarkdownFixture(mode: "partial-rejection"); defer { f.stop() }
        do {
            _ = try await AnyNativeMarkdownBody(client: f.client()).replace(f.intent(), authorizeRead: {}, authorizeWrite: {})
            XCTFail("Native partial rejection became body success")
        } catch AnyNativeMarkdownWriteFailure.uncertain(let context) {
            XCTAssertEqual(context.reference, try f.reference())
        }
        XCTAssertEqual(try f.methods(), ["PUT"])
    }

    func testPostDispatchServerAndUndocumentedFailuresRetainUncertainScope() async throws {
        for mode in ["server-error", "unknown-error"] {
            let f = try MarkdownFixture(mode: mode); defer { f.stop() }
            do {
                _ = try await AnyNativeMarkdownBody(client: f.client()).replace(f.intent(), authorizeRead: {}, authorizeWrite: {})
                XCTFail("Potentially applied native error was treated as no write")
            } catch AnyNativeMarkdownWriteFailure.uncertain(let context) {
                XCTAssertEqual(context.reference, try f.reference())
                XCTAssertEqual(context.requestID, String(repeating: "a", count: 32))
            }
            XCTAssertEqual(try f.methods(), ["PUT"])
        }
    }

    func testDocumentedPrewriteBodyLimitRefusalRemainsTyped() async throws {
        let f = try MarkdownFixture(mode: "block-too-large"); defer { f.stop() }
        do {
            _ = try await AnyNativeMarkdownBody(client: f.client()).replace(f.intent(), authorizeRead: {}, authorizeWrite: {})
            XCTFail("Native body limit refusal was lost")
        } catch { XCTAssertEqual(error as? AnyEngineError, .http(status: 400, code: "markdown.block_too_large")) }
        XCTAssertEqual(try f.methods(), ["PUT"])
    }
}

private enum MarkdownFixtureFailure: Error { case revoked, duplicateApproval }
private actor MarkdownApproval {
    private(set) var count = 0
    func consume() throws {
        count += 1
        if count != 1 { throw MarkdownFixtureFailure.duplicateApproval }
    }
}
private final class MarkdownFixture: @unchecked Sendable {
    private let process = Process()
    private let pipe = Pipe()
    private let directory: URL
    private var port = 0

    init(mode: String = "", normalized: String? = nil) throws {
        directory = FileManager.default.temporaryDirectory.appendingPathComponent("pinkha-markdown-body-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false,
                                                attributes: [.posixPermissions: 0o700])
        var config: [String: AnyJSON] = ["mode": .string(mode)]
        if let normalized { config["normalized"] = .string(normalized) }
        try JSONEncoder().encode(AnyJSON.object(config)).write(to: directory.appendingPathComponent("config.json"))
        let script = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("Fixtures/markdown_body_server.py")
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = ["python3", "-B", script.path, directory.path]
        process.standardOutput = pipe; process.standardError = FileHandle.nullDevice
        do {
            try process.run()
            let line = String(data: pipe.fileHandleForReading.availableData, encoding: .utf8) ?? ""
            guard let port = Int(line.trimmingCharacters(in: .whitespacesAndNewlines)), (1...65535).contains(port) else {
                throw AnyEngineError.invalidEndpoint
            }
            self.port = port
        } catch {
            if process.isRunning { process.terminate() }
            if process.processIdentifier > 0 { process.waitUntilExit() }
            try? FileManager.default.removeItem(at: directory)
            throw error
        }
    }
    func reference() throws -> AnyNativeMarkdownReference {
        try .init(accountID: "account", spaceID: "space", objectID: "object")
    }
    func client() throws -> AnyHTTPClient {
        try .init(baseURL: URL(string: "http://127.0.0.1:\(port)")!, expectedAccountID: "account")
    }
    func intent(content: String = "private body") throws -> AnyNativeMarkdownWriteIntent {
        try .init(reference: reference(), requestID: String(repeating: "a", count: 32), expectedVersion: "v1", content: content)
    }
    func requireBefore(_ action: String) throws {
        if FileManager.default.fileExists(atPath: directory.appendingPathComponent(action + "-responded").path) {
            throw MarkdownFixtureFailure.revoked
        }
    }
    func events() throws -> [AnyJSON] {
        let path = directory.appendingPathComponent("events.json")
        guard FileManager.default.fileExists(atPath: path.path) else { return [] }
        return try JSONDecoder().decode([AnyJSON].self, from: Data(contentsOf: path))
    }
    func methods() throws -> [String] { try events().map { try $0.requireString("method") } }
    func stop() {
        if process.isRunning { process.terminate() }
        if process.processIdentifier > 0 { process.waitUntilExit() }
        try? FileManager.default.removeItem(at: directory)
    }
}
#endif
