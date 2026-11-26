#if os(macOS) || os(Linux)
import Foundation
import XCTest
@testable import PinkhaAnyEngine

/// Real loopback HTTP exercises the consumer's lifetime fence; this is not native ACL acceptance.
final class AnyHTTPAuthorizationFenceTests: XCTestCase, @unchecked Sendable {
    func testReadRevokedDuringHTTPDoesNotDeliverPayloadFromSameAccount() async throws {
        let fixture = try AuthorizationFenceFixture()
        defer { fixture.stop() }
        let client = try fixture.client()
        do {
            _ = try await client.requestJSON(method: "GET",
                path: ["v1", "spaces", "space", "objects", "object"],
                authorize: { try fixture.requireBeforeResponse() })
            XCTFail("A payload escaped after its original consumer scope was revoked")
        } catch { XCTAssertEqual(error as? AuthorizationFenceFailure, .revoked) }
        XCTAssertEqual(try fixture.dispatched(), ["GET /v1/spaces/space/objects/object"])
    }

    func testRevokedAfterCommittedWriteReportsUncertainWithoutRetry() async throws {
        let fixture = try AuthorizationFenceFixture()
        defer { fixture.stop() }
        let client = try fixture.client()
        do {
            _ = try await client.requestJSONResponse(method: "POST",
                path: ["v1", "spaces", "join"], body: .object([:]),
                validateResponse: { try fixture.requireBeforeResponse() },
                authorize: { try fixture.requireBeforeResponse() })
            XCTFail("A completed mutation escaped through a revoked consumer scope")
        } catch { XCTAssertEqual(error as? AnyEngineError, .writeUncertain) }
        XCTAssertEqual(try fixture.dispatched(), ["POST /v1/spaces/join"])
    }

    func testRevokedCreateRetainsOnlyOriginalScopeRecoveryIdentity() async throws {
        let fixture = try AuthorizationFenceFixture()
        defer { fixture.stop() }
        let client = try fixture.client()
        do {
            _ = try await client.requestJSON(method: "POST",
                path: ["v1", "spaces", "original-space", "pinkha", "objects"], body: .object([:]),
                validateResponse: { try fixture.requireBeforeResponse() },
                authorize: { try fixture.requireBeforeResponse() })
            XCTFail("A confirmed create escaped after consumer revocation")
        } catch let recovery as AnyObjectCreationUncertain {
            XCTAssertEqual(recovery.spaceID, "original-space")
            XCTAssertEqual(recovery.objectID, "created-object")
            XCTAssertEqual(recovery.stage, .bootstrapStored)
            XCTAssertEqual(String(reflecting: recovery), "AnyObjectCreationUncertain(recovery metadata redacted)")
        }
        XCTAssertEqual(try fixture.dispatched(), ["POST /v1/spaces/original-space/pinkha/objects"])
    }

    func testRevokedBeforeDispatchSendsNoMutation() async throws {
        let fixture = try AuthorizationFenceFixture()
        defer { fixture.stop() }
        let client = try fixture.client()
        do {
            _ = try await client.requestJSON(method: "POST", path: ["v1", "spaces", "join"],
                body: .object([:]), authorize: { throw AuthorizationFenceFailure.revoked })
            XCTFail("A revoked request was dispatched")
        } catch { XCTAssertEqual(error as? AuthorizationFenceFailure, .revoked) }
        XCTAssertEqual(try fixture.dispatched(), [])
    }

    func testAuthorizedStatusAndLegacyBodyBothRetainTheirSemantics() async throws {
        let fixture = try AuthorizationFenceFixture()
        defer { fixture.stop() }
        let client = try fixture.client()
        let authority = AuthorizationCheckCount()
        let response = try await client.requestJSONResponse(method: "POST",
            path: ["v1", "spaces", "join"], body: .object([:]),
            validateResponse: { await authority.check() },
            authorize: { await authority.check() })
        let body = try await client.requestJSON(method: "POST",
            path: ["v1", "spaces", "join"], body: .object([:]),
            validateResponse: { await authority.check() },
            authorize: { await authority.check() })
        XCTAssertEqual(response.statusCode, 202)
        XCTAssertEqual(response.body, body)
        XCTAssertEqual(body["status"]?.string, "joining")
        let checks = await authority.value
        XCTAssertEqual(checks, 4)
        XCTAssertEqual(try fixture.dispatched(), ["POST /v1/spaces/join", "POST /v1/spaces/join"])
    }
    func testOneShotWriteDispatchApprovalIsNotConsumedAgain() async throws {
        let fixture = try AuthorizationFenceFixture()
        defer { fixture.stop() }
        let client = try fixture.client()
        let authority = AuthorizationCheckCount()
        let response = try await client.requestJSONResponse(method: "POST",
            path: ["v1", "spaces", "join"], body: .object([:]),
            authorize: { try await authority.consumeOnce() })
        XCTAssertEqual(response.statusCode, 202)
        XCTAssertEqual(response.body["status"]?.string, "joining")
        let checks = await authority.value
        XCTAssertEqual(checks, 1)
        XCTAssertEqual(try fixture.dispatched(), ["POST /v1/spaces/join"])
    }

    func testSeparateReadResponseFencePreservesOneShotDispatchApproval() async throws {
        let fixture = try AuthorizationFenceFixture()
        defer { fixture.stop() }
        let client = try fixture.client()
        let authority = AuthorizationCheckCount()
        do {
            _ = try await client.requestJSON(method: "GET",
                path: ["v1", "spaces", "space", "objects", "object"],
                validateResponse: { try fixture.requireBeforeResponse() },
                authorize: { try await authority.consumeOnce() })
            XCTFail("A payload escaped the separate response fence")
        } catch { XCTAssertEqual(error as? AuthorizationFenceFailure, .revoked) }
        let checks = await authority.value
        XCTAssertEqual(checks, 1)
        XCTAssertEqual(try fixture.dispatched(), ["GET /v1/spaces/space/objects/object"])
    }

}

private enum AuthorizationFenceFailure: Error { case revoked, consumed }

private actor AuthorizationCheckCount {
    private(set) var value = 0
    func check() { value += 1 }
    func consumeOnce() throws {
        value += 1
        guard value == 1 else { throw AuthorizationFenceFailure.consumed }
    }
}

private final class AuthorizationFenceFixture: @unchecked Sendable {
    private let process = Process()
    private let output = Pipe()
    private let directory: URL
    private let marker: URL
    private let journal: URL
    private var port = 0

    init() throws {
        directory = FileManager.default.temporaryDirectory
            .appendingPathComponent("pinkha-auth-fence-" + UUID().uuidString, isDirectory: true)
        marker = directory.appendingPathComponent("response-began")
        journal = directory.appendingPathComponent("dispatch.json")
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false,
                                                attributes: [.posixPermissions: 0o700])
        let fixture = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
            .deletingLastPathComponent().appendingPathComponent("Fixtures/authorization_fence_server.py")
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = ["python3", "-B", fixture.path, directory.path]
        process.standardOutput = output
        process.standardError = FileHandle.nullDevice
        do {
            try process.run()
            let line = String(data: output.fileHandleForReading.availableData, encoding: .utf8) ?? ""
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

    func client() throws -> AnyHTTPClient {
        try AnyHTTPClient(baseURL: URL(string: "http://127.0.0.1:\(port)")!, expectedAccountID: "account")
    }
    func requireBeforeResponse() throws {
        if FileManager.default.fileExists(atPath: marker.path) { throw AuthorizationFenceFailure.revoked }
    }
    func dispatched() throws -> [String] {
        guard FileManager.default.fileExists(atPath: journal.path) else { return [] }
        return try JSONDecoder().decode([String].self, from: Data(contentsOf: journal))
    }
    func stop() {
        if process.isRunning { process.terminate() }
        process.waitUntilExit()
        try? FileManager.default.removeItem(at: directory)
    }
}
#endif
