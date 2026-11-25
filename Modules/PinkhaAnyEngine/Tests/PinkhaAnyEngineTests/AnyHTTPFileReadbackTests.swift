#if os(macOS) || os(Linux)
import Foundation
import XCTest
@testable import PinkhaAnyEngine

final class AnyHTTPFileReadbackTests: XCTestCase, @unchecked Sendable {
    func testRangeReadAndPrivateDownloadPreserveExactBytes() async throws {
        let fixture = try FileReadbackFixture()
        defer { fixture.stop() }
        let client = try fixture.client()
        let count: Int = 2 * 1024 * 1024 + 17
        var bytes = Data(count: count)
        for index in 0..<count { bytes[index] = UInt8((index * 31 + 17) % 251) }
        let digest = AnyContentDigest.sha256(bytes)
        let read = try await client.readFileContentDigest(spaceID: "space", fileID: "normal",
            size: Int64(bytes.count), mime: "application/x-pinkha-test", authorize: {})
        XCTAssertEqual(read.byteCount, Int64(bytes.count)); XCTAssertEqual(read.sha256, digest)
        let directory = try privateDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let output = directory.appendingPathComponent("content")
        let actual = try await client.downloadFileContent(spaceID: "space", fileID: "normal",
            size: Int64(bytes.count), mime: "application/x-pinkha-test", to: output,
            expectedSHA256: digest, authorize: {})
        XCTAssertEqual(actual, digest); XCTAssertEqual(try Data(contentsOf: output), bytes)
        let permissions = try FileManager.default.attributesOfItem(atPath: output.path)[.posixPermissions] as? NSNumber
        XCTAssertEqual(permissions?.intValue, 0o600)
    }

    func testWrongRangeMimeLengthAndRedirectAreRefused() async throws {
        for fault in ["wrong-range", "wrong-mime", "short", "oversize", "ignored-range", "redirect"] {
            let fixture = try FileReadbackFixture()
            defer { fixture.stop() }
            let client = try fixture.client()
            do {
                _ = try await client.readFileContentDigest(spaceID: "space", fileID: fault,
                    size: 8192, mime: "application/x-pinkha-test", authorize: {})
                XCTFail("Accepted invalid native content response: \(fault)")
            } catch {}
        }
    }

    func testDeclaredAndChunkedResponseOverflowStopsAtByteCeiling() async throws {
        for fault in ["large-header", "chunked-overflow"] {
            let fixture = try FileReadbackFixture()
            defer { fixture.stop() }
            let client = try fixture.client()
            do {
                _ = try await client.readFileContentDigest(spaceID: "space", fileID: fault,
                    size: 8192, mime: "application/x-pinkha-test", authorize: {})
                XCTFail("An oversized native response exceeded the streaming ceiling")
            } catch { XCTAssertEqual(error as? AnyEngineError, .readLimit) }
        }
    }

    func testAccountChangeCannotPublishNewOutput() async throws {
        let fixture = try FileReadbackFixture()
        defer { fixture.stop() }
        let client = try fixture.client()
        let directory = try privateDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let output = directory.appendingPathComponent("content")
        do {
            _ = try await client.downloadFileContent(spaceID: "space", fileID: "account-switch",
                size: 8192, mime: "application/x-pinkha-test", to: output, authorize: {})
            XCTFail("Published bytes after account switch")
        } catch { XCTAssertEqual(error as? AnyEngineError, .accountChanged) }
        XCTAssertFalse(FileManager.default.fileExists(atPath: output.path))
    }

    func testDigestMismatchAndAuthorizationWithdrawalCleanOnlyNewOutput() async throws {
        let fixture = try FileReadbackFixture()
        defer { fixture.stop() }
        let client = try fixture.client()
        let directory = try privateDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let sentinel = directory.appendingPathComponent("existing")
        try Data("retained".utf8).write(to: sentinel)
        let mismatch = directory.appendingPathComponent("mismatch")
        do {
            _ = try await client.downloadFileContent(spaceID: "space", fileID: "normal",
                size: 8192, mime: "application/x-pinkha-test", to: mismatch,
                expectedSHA256: String(repeating: "0", count: 64), authorize: {})
            XCTFail("Published a digest mismatch")
        } catch {}
        XCTAssertFalse(FileManager.default.fileExists(atPath: mismatch.path))
        let revoked = directory.appendingPathComponent("revoked")
        let authority = ReadbackAuthority()
        do {
            _ = try await client.downloadFileContent(spaceID: "space", fileID: "normal",
                size: 2 * 1024 * 1024 + 17, mime: "application/x-pinkha-test", to: revoked,
                authorize: { try await authority.check() })
            XCTFail("Published content after authority withdrawal")
        } catch { XCTAssertEqual(error as? ReadbackFailure, .revoked) }
        XCTAssertFalse(FileManager.default.fileExists(atPath: revoked.path))
        XCTAssertEqual(try Data(contentsOf: sentinel), Data("retained".utf8))
    }

    func testExistingFileSymlinkAndPublicParentAreNeverOverwritten() async throws {
        let fixture = try FileReadbackFixture()
        defer { fixture.stop() }
        let client = try fixture.client()
        let directory = try privateDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let existing = directory.appendingPathComponent("existing")
        try Data("original".utf8).write(to: existing)
        let fileAlias = directory.appendingPathComponent("alias")
        try FileManager.default.createSymbolicLink(at: fileAlias, withDestinationURL: existing)
        let directoryAlias = directory.appendingPathComponent("directory-alias")
        try FileManager.default.createSymbolicLink(at: directoryAlias, withDestinationURL: directory)
        let publicDirectory = directory.appendingPathComponent("public")
        try FileManager.default.createDirectory(at: publicDirectory, withIntermediateDirectories: false,
                                                attributes: [.posixPermissions: 0o755])
        for output in [existing, fileAlias, directoryAlias.appendingPathComponent("new"),
                       publicDirectory.appendingPathComponent("new")] {
            do {
                _ = try await client.downloadFileContent(spaceID: "space", fileID: "normal",
                    size: 8192, mime: "application/x-pinkha-test", to: output, authorize: {})
                XCTFail("Accepted unsafe existing/public/symlink destination")
            } catch {}
        }
        XCTAssertEqual(try Data(contentsOf: existing), Data("original".utf8))
        XCTAssertFalse(FileManager.default.fileExists(atPath: directory.appendingPathComponent("new").path))
    }

    func testEmptyNativeFileIsReadWithoutInventedRange() async throws {
        let fixture = try FileReadbackFixture()
        defer { fixture.stop() }
        let client = try fixture.client()
        let directory = try privateDirectory()
        defer { try? FileManager.default.removeItem(at: directory) }
        let output = directory.appendingPathComponent("empty")
        let digest = try await client.downloadFileContent(spaceID: "space", fileID: "empty",
            size: 0, mime: "application/x-pinkha-test", to: output, authorize: {})
        XCTAssertEqual(digest, AnyContentDigest.sha256(Data()))
        XCTAssertEqual(try Data(contentsOf: output), Data())
    }

    private func privateDirectory() throws -> URL {
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent("pinkha-file-readback-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false,
                                                attributes: [.posixPermissions: 0o700])
        return directory
    }
}

private enum ReadbackFailure: Error { case revoked }

private actor ReadbackAuthority {
    private var checks = 0
    func check() throws {
        checks += 1
        if checks >= 4 { throw ReadbackFailure.revoked }
    }
}

private final class FileReadbackFixture {
    private let process = Process()
    private let output = Pipe()
    private let port: Int

    init() throws {
        let fixture = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
            .deletingLastPathComponent().appendingPathComponent("Fixtures/file_readback_server.py")
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = ["python3", "-B", fixture.path]
        process.standardOutput = output
        process.standardError = FileHandle.nullDevice
        try process.run()
        let text = String(data: output.fileHandleForReading.availableData, encoding: .utf8) ?? ""
        guard let port = Int(text.trimmingCharacters(in: .whitespacesAndNewlines)), (1...65535).contains(port) else {
            if process.isRunning { process.terminate() }; process.waitUntilExit()
            throw AnyEngineError.invalidEndpoint
        }
        self.port = port
    }
    func client() throws -> AnyHTTPClient {
        try AnyHTTPClient(baseURL: URL(string: "http://127.0.0.1:\(port)")!, expectedAccountID: "account",
                          authorization: .init(token: String(repeating: "b", count: 64)))
    }
    func stop() {
        if process.isRunning { process.terminate() }
        process.waitUntilExit()
    }
}
#endif
