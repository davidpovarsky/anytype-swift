#if os(macOS) || os(Linux)
import Foundation
import XCTest
@testable import PinkhaAnyEngine

final class AnyHTTPResponseTests: XCTestCase, @unchecked Sendable {
    func testPendingAndCreatedStatusesSurviveActualHTTPAndLegacyBodyAPI() async throws {
        let server = try HTTPStatusFixture()
        defer { server.stop() }
        let client = try server.client()
        let pending = try await client.requestJSONResponse(method: "POST", path: ["v1", "spaces", "join"],
            body: .object(["inviteToken": .string("pending")]))
        XCTAssertEqual(pending.statusCode, 202)
        XCTAssertEqual(pending.body["status"]?.string, "active")
        let active = try await client.requestJSONResponse(method: "POST", path: ["v1", "spaces", "join"],
            body: .object(["inviteToken": .string("active")]))
        XCTAssertEqual(active.statusCode, 201)
        let legacy = try await client.requestJSON(method: "POST", path: ["v1", "spaces", "join"],
            body: .object(["inviteToken": .string("pending")]))
        XCTAssertEqual(legacy, pending.body)
    }

    func testAccountSwitchAfterActualJoinResponseRemainsWriteUncertain() async throws {
        let server = try HTTPStatusFixture()
        defer { server.stop() }
        let client = try server.client()
        do {
            _ = try await client.requestJSONResponse(method: "POST", path: ["v1", "spaces", "join"],
                body: .object(["inviteToken": .string("switch")]))
            XCTFail("A response escaped after the native account changed")
        } catch { XCTAssertEqual(error as? AnyEngineError, .writeUncertain) }
    }

    func testAcceptedHTTPStatusCannotHideNativePartialRejection() async throws {
        let server = try HTTPStatusFixture()
        defer { server.stop() }
        let client = try server.client()
        do {
            _ = try await client.requestJSONResponse(method: "POST", path: ["v1", "spaces", "join"],
                body: .object(["inviteToken": .string("partial")]))
            XCTFail("A 202 partial rejection became a successful join")
        } catch { XCTAssertEqual(error as? AnyEngineError, .writeRejected(["acl.forbidden"])) }
    }
}

private final class HTTPStatusFixture {
    private let process = Process()
    private let output = Pipe()
    private var port = 0

    init() throws {
        let fixture = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
            .deletingLastPathComponent().appendingPathComponent("Fixtures/status_transition_server.py")
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = ["python3", "-B", fixture.path]
        process.standardOutput = output
        process.standardError = FileHandle.nullDevice
        try process.run()
        let value = String(data: output.fileHandleForReading.availableData, encoding: .utf8) ?? ""
        guard let port = Int(value.trimmingCharacters(in: .whitespacesAndNewlines)), (1...65_535).contains(port) else {
            if process.isRunning { process.terminate() }
            process.waitUntilExit()
            throw AnyEngineError.invalidEndpoint
        }
        self.port = port
    }

    func client() throws -> AnyHTTPClient {
        try AnyHTTPClient(baseURL: URL(string: "http://127.0.0.1:\(port)")!, expectedAccountID: "account")
    }

    func stop() {
        if process.isRunning { process.terminate() }
        process.waitUntilExit()
    }
}
#endif
