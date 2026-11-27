import Foundation
import XCTest
@testable import PinkhaAnyEngine

final class AnyNativeFileDurabilityTests: XCTestCase, @unchecked Sendable {
    func testNativeStatesDoNotConflateLocalAvailabilityWithCustody() throws {
        let scope = try reference()
        for state in ["limited", "inflight", "durable"] {
            for cached in [false, true] {
                let value = try AnyNativeFileDurability.decode(body(state: state, cached: cached), reference: scope)
                XCTAssertEqual(value.state.rawValue, state)
                XCTAssertEqual(value.cached, cached)
                XCTAssertEqual(value.failedAttempts, 0)
                XCTAssertNil(value.lastError)
            }
        }
        var data = body().object!
        data["attempts"] = .integer(3)
        data["lastErr"] = .string("private storage refusal for original-file")
        let result = try AnyNativeFileDurability.decode(.object(data), reference: scope)
        XCTAssertEqual(result.failedAttempts, 3)
        XCTAssertEqual(result.lastError, "private storage refusal for original-file")
        XCTAssertFalse(String(describing: result).contains("original-file"))
        XCTAssertFalse(String(reflecting: result).contains("private storage refusal"))
    }

    func testMalformedAndUnknownStatusCannotBecomeAnOptimisticSuccess() throws {
        let scope = try reference()
        var cases = [AnyJSON.null, .object([:])]
        for (key, values) in [
            "state": [AnyJSON.string("ready"), .null, .bool(true)],
            "cached": [.null, .string("true")],
            "attempts": [.integer(-1), .number(0.5), .bool(false), .null],
            "lastErr": [.bool(false), .null, .string(String(repeating: "x", count: 65_537))]
        ] {
            for value in values {
                var row = body().object!
                row[key] = value
                cases.append(.object(row))
            }
        }
        for value in cases {
            XCTAssertThrowsError(try AnyNativeFileDurability.decode(value, reference: scope))
        }
    }

    func testFileAndObjectIdentityRequireExactBytes() throws {
        for key in ["fileId", "objectId"] {
            var row = body().object!
            row[key] = .string("other")
            XCTAssertThrowsError(try AnyNativeFileDurability.decode(.object(row), reference: reference()))
        }
        let composed = "object-\u{00E9}", decomposed = "object-e\u{0301}"
        XCTAssertEqual(composed, decomposed)
        var row = body().object!
        row["objectId"] = .string(decomposed)
        XCTAssertThrowsError(try AnyNativeFileDurability.decode(.object(row),
            reference: reference(object: composed)))
    }

    func testInvalidNativeScopeIsRefusedAtConstruction() throws {
        for invalid in ["", ".", "..", "a/b", "a%2Fb", "a?b", "a#b", "a b", "a\n", String(repeating: "x", count: 4097)] {
            XCTAssertThrowsError(try AnyNativeFileReference(accountID: "account", spaceID: "space",
                                                          objectID: "object", fileID: invalid))
        }
    }

    private func reference(object: String = "object") throws -> AnyNativeFileReference {
        try .init(accountID: "account", spaceID: "space", objectID: object, fileID: "file")
    }

    private func body(state: String = "limited", cached: Bool = true) -> AnyJSON {
        .object(["fileId": .string("file"), "objectId": .string("object"),
                 "state": .string(state), "cached": .bool(cached)])
    }
}

#if os(Linux) || os(macOS)
final class AnyNativeFileDurabilityHTTPTests: XCTestCase, @unchecked Sendable {
    func testNativeLimitedStateIsReadWithoutAutomaticRetry() async throws {
        let fixture = try FileDurabilityFixture()
        defer { fixture.stop() }
        let checks = FileDurabilityCounter()
        let result = try await AnyNativeFileDurability(client: fixture.client()).status(
            fixture.reference(), authorize: { await checks.check() })
        XCTAssertEqual(result.state, .limited)
        XCTAssertTrue(result.cached)
        XCTAssertEqual(result.failedAttempts, 2)
        XCTAssertEqual(result.lastError, "filestatus: storage limit exceeded: file")
        let count = await checks.value
        XCTAssertEqual(count, 3)
        XCTAssertEqual(try fixture.dispatched(), ["GET /v1/spaces/space/files/file/status"])
    }

    func testRetryAcknowledgesOneDispatchAndDoesNotClaimDurability() async throws {
        let fixture = try FileDurabilityFixture()
        defer { fixture.stop() }
        let reads = FileDurabilityCounter(), approvals = FileDurabilityCounter()
        let ack = try await AnyNativeFileDurability(client: fixture.client()).retry(
            fixture.reference(), authorizeRead: { await reads.check() },
            authorizeRetry: { try await approvals.consumeOnce() })
        XCTAssertEqual(ack.reference.fileID, "file")
        let readCount = await reads.value, approvalCount = await approvals.value
        XCTAssertEqual(readCount, 5)
        XCTAssertEqual(approvalCount, 1)
        XCTAssertEqual(try fixture.dispatched(), [
            "GET /v1/spaces/space/files/file/status", "POST /v1/spaces/space/files/file/retry"
        ])
    }

    func testWrongObjectIsRejectedBeforeRetryApprovalOrPost() async throws {
        let fixture = try FileDurabilityFixture(object: "other-object")
        defer { fixture.stop() }
        let approvals = FileDurabilityCounter()
        do {
            _ = try await AnyNativeFileDurability(client: fixture.client()).retry(
                fixture.reference(), authorizeRead: {}, authorizeRetry: { try await approvals.consumeOnce() })
            XCTFail("Cross-object file status admitted a retry")
        } catch { XCTAssertEqual(error as? AnyEngineError, .malformedResponse("file status scope or fields")) }
        let count = await approvals.value
        XCTAssertEqual(count, 0)
        XCTAssertEqual(try fixture.dispatched(), ["GET /v1/spaces/space/files/file/status"])
    }

    func testForeignAccountScopeIsRejectedWithoutDispatch() async throws {
        let fixture = try FileDurabilityFixture()
        defer { fixture.stop() }
        let foreign = try AnyNativeFileReference(accountID: "different", spaceID: "space", objectID: "object", fileID: "file")
        do {
            _ = try await AnyNativeFileDurability(client: fixture.client()).status(foreign, authorize: {})
            XCTFail("A different account was accepted")
        } catch { XCTAssertEqual(error as? AnyEngineError, .accountChanged) }
        XCTAssertEqual(try fixture.dispatched(), [])
    }

    func testPostDispatchRevocationReturnsUncertainWithoutConsumingApprovalAgain() async throws {
        let fixture = try FileDurabilityFixture()
        defer { fixture.stop() }
        let approvals = FileDurabilityCounter()
        do {
            _ = try await AnyNativeFileDurability(client: fixture.client()).retry(
                fixture.reference(), authorizeRead: { try fixture.requireBefore("retry") },
                authorizeRetry: { try await approvals.consumeOnce() })
            XCTFail("A retry acknowledgment escaped its revoked lifetime")
        } catch { XCTAssertEqual(error as? AnyEngineError, .writeUncertain) }
        let count = await approvals.value
        XCTAssertEqual(count, 1)
        XCTAssertEqual(try fixture.dispatched().filter { $0.hasPrefix("POST ") }.count, 1)
    }

    func testAccountSwitchAfterRetryReturnsUncertainWithoutAnotherWrite() async throws {
        let fixture = try FileDurabilityFixture(switchAfter: "retry")
        defer { fixture.stop() }
        do {
            _ = try await AnyNativeFileDurability(client: fixture.client()).retry(
                fixture.reference(), authorizeRead: {}, authorizeRetry: {})
            XCTFail("The old account's acknowledgment was delivered to a new account")
        } catch { XCTAssertEqual(error as? AnyEngineError, .writeUncertain) }
        XCTAssertEqual(try fixture.dispatched().filter { $0.hasPrefix("POST ") }.count, 1)
    }

    func testTypedAuthorityRefusalAndUnexpectedSuccessKeepNativeOutcomeDistinct() async throws {
        for code in [403, 200] {
            let fixture = try FileDurabilityFixture(retryStatus: code)
            defer { fixture.stop() }
            do {
                _ = try await AnyNativeFileDurability(client: fixture.client()).retry(
                    fixture.reference(), authorizeRead: {}, authorizeRetry: {})
                XCTFail("A refused or unqualified native retry became an acknowledgment")
            } catch {
                XCTAssertEqual(error as? AnyEngineError,
                    code == 403 ? .http(status: 403, code: "acl.forbidden") : .writeUncertain)
            }
            XCTAssertEqual(try fixture.dispatched().filter { $0.hasPrefix("POST ") }.count, 1)
        }
    }

    func testCanonicallyEquivalentDifferentAccountBytesAreDeniedBeforeStatusRead() async throws {
        let fixture = try FileDurabilityFixture(clientAccount: "account-\u{00E9}",
                                               authorizedAccount: "account-e\u{0301}")
        defer { fixture.stop() }
        do {
            _ = try await AnyNativeFileDurability(client: fixture.client()).status(fixture.reference(), authorize: {})
            XCTFail("Different native account bytes were accepted as the current account")
        } catch { XCTAssertEqual(error as? AnyEngineError, .accountChanged) }
        XCTAssertEqual(try fixture.dispatched(), [])
    }

    func testMalformedSuccessfulRetryReceiptIsUncertainAfterOneDispatch() async throws {
        let fixture = try FileDurabilityFixture(retryStatus: 200, rawRetryMode: "invalid-json")
        defer { fixture.stop() }
        do {
            _ = try await AnyNativeFileDurability(client: fixture.client()).retry(
                fixture.reference(), authorizeRead: {}, authorizeRetry: {})
            XCTFail("Malformed successful native receipt was accepted")
        } catch { XCTAssertEqual(error as? AnyEngineError, .writeUncertain) }
        XCTAssertEqual(try fixture.dispatched().filter { $0.hasPrefix("POST ") }.count, 1)
    }

    func testOversizedSuccessfulRetryReceiptIsUncertainAfterOneDispatch() async throws {
        let fixture = try FileDurabilityFixture(retryStatus: 200, rawRetryMode: "oversized-json")
        defer { fixture.stop() }
        do {
            _ = try await AnyNativeFileDurability(client: fixture.client()).retry(
                fixture.reference(), authorizeRead: {}, authorizeRetry: {})
            XCTFail("Oversized successful native receipt was accepted")
        } catch { XCTAssertEqual(error as? AnyEngineError, .writeUncertain) }
        XCTAssertEqual(try fixture.dispatched().filter { $0.hasPrefix("POST ") }.count, 1)
    }

    func testRevokedReadCannotPublishQuotaOrAvailability() async throws {
        let fixture = try FileDurabilityFixture()
        defer { fixture.stop() }
        do {
            _ = try await AnyNativeFileDurability(client: fixture.client()).status(
                fixture.reference(), authorize: { try fixture.requireBefore("status") })
            XCTFail("File status escaped its revoked lifetime")
        } catch { XCTAssertEqual(error as? FileDurabilityFailure, .revoked) }
        XCTAssertEqual(try fixture.dispatched().count, 1)
    }
}

private enum FileDurabilityFailure: Error { case revoked, duplicateApproval }
private actor FileDurabilityCounter {
    private(set) var value = 0
    func check() { value += 1 }
    func consumeOnce() throws {
        value += 1
        if value != 1 { throw FileDurabilityFailure.duplicateApproval }
    }
}

private final class FileDurabilityFixture: @unchecked Sendable {
    private let process = Process()
    private let pipe = Pipe()
    private let directory: URL
    private var port = 0
    private let expectedAccount: String

    init(object: String = "object", retryStatus: Int = 204, switchAfter: String = "",
         clientAccount: String = "account", authorizedAccount: String = "account", rawRetryMode: String = "") throws {
        expectedAccount = clientAccount
        directory = FileManager.default.temporaryDirectory.appendingPathComponent("pinkha-file-durability-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false,
                                                attributes: [.posixPermissions: 0o700])
        let body: AnyJSON = .object(["fileId": .string("file"), "objectId": .string(object),
            "state": .string("limited"), "cached": .bool(true), "attempts": .integer(2),
            "lastErr": .string("filestatus: storage limit exceeded: file")])
        let config: AnyJSON = .object(["statusBody": body, "retryStatus": .integer(Int64(retryStatus)),
            "retryBody": .object(["error": .object(["code": .string("acl.forbidden")])]),
            "switchAfter": .string(switchAfter), "authorizedAccount": .string(authorizedAccount),
            "rawRetryMode": .string(rawRetryMode)])
        try JSONEncoder().encode(config).write(to: directory.appendingPathComponent("config.json"))
        let script = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("Fixtures/file_durability_server.py")
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = ["python3", "-B", script.path, directory.path]
        process.standardOutput = pipe
        process.standardError = FileHandle.nullDevice
        do {
            try process.run()
            let line = String(data: pipe.fileHandleForReading.availableData, encoding: .utf8) ?? ""
            guard let port = Int(line.trimmingCharacters(in: .whitespacesAndNewlines)), (1...65_535).contains(port) else {
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

    func reference() throws -> AnyNativeFileReference {
        try .init(accountID: expectedAccount, spaceID: "space", objectID: "object", fileID: "file")
    }

    func client() throws -> AnyHTTPClient {
        try .init(baseURL: URL(string: "http://127.0.0.1:\(port)")!, expectedAccountID: expectedAccount)
    }

    func requireBefore(_ action: String) throws {
        if FileManager.default.fileExists(atPath: directory.appendingPathComponent(action + "-responded").path) {
            throw FileDurabilityFailure.revoked
        }
    }

    func dispatched() throws -> [String] {
        let path = directory.appendingPathComponent("dispatch.json")
        guard FileManager.default.fileExists(atPath: path.path) else { return [] }
        return try JSONDecoder().decode([String].self, from: Data(contentsOf: path))
    }

    func stop() {
        if process.isRunning { process.terminate() }
        if process.processIdentifier > 0 { process.waitUntilExit() }
        try? FileManager.default.removeItem(at: directory)
    }
}
#endif
