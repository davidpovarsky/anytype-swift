import Foundation
import XCTest
@testable import PinkhaAnyEngine
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif
#if canImport(Darwin)
import Darwin
#elseif canImport(Glibc)
import Glibc
#endif

#if os(Linux) || os(macOS)
final class AnyNativeFileUploadHTTPTests: XCTestCase, @unchecked Sendable {
    func testEmptyAndStreamedAttachmentsHaveOneApprovalAndRetainNativeMetadataBeforePostflight() async throws {
        for count in [0, 3 * 1_048_576 + 17] {
            let fixture = try UploadHTTPFixture(body: uploadBody(size: Int64(count), name: "native-name.png",
                mime: "image/png", inline: count == 0))
            defer { fixture.stop() }
            let source = try fixture.files.write(byteCount: count)
            let specification = try uploadSpecification(name: "native-name", mime: "image/png",
                size: Int64(count), digest: source.sha256)
            let events = UploadEvents()
            let uploader = AnyNativeFileUploader(client: try fixture.client())
            let result = try await uploader.attach(specification: specification, fileURL: source.url,
                validateScope: {
                    if fixture.has("post-responded") { try await events.requireKnownReceipt() }
                }, authorizeDispatch: { try await events.approveOnce() },
                retainReceipt: { value in await events.retain(value) })
            XCTAssertEqual(result.name, "native-name.png")
            XCTAssertEqual(result.mime, "image/png")
            let info = try await uploader.info(specification: specification, fileID: result.reference.fileID, authorize: {})
            XCTAssertEqual(info.name, result.name)
            XCTAssertEqual(info.byteCount, Int64(count))
            let state = await events.snapshot()
            XCTAssertEqual(state.approvals, 1); XCTAssertEqual(state.fileIDs, ["file"])
            let rows = try fixture.rows()
            XCTAssertEqual(rows.count, 2)
            XCTAssertEqual(rows[0]["method"]?.string, "POST")
            XCTAssertEqual(rows[0]["name"]?.array, [.string("native-name")])
            XCTAssertEqual(rows[0]["contentType"]?.string, "image/png")
            XCTAssertEqual(rows[0]["byteCount"]?.integer, Int64(count))
            XCTAssertEqual(rows[0]["sha256"]?.string, source.sha256)
            XCTAssertEqual(rows[1]["method"]?.string, "GET")
            XCTAssertEqual(try fixture.files.digest(source.url), source.sha256)
        }
    }

    func testForeignAccountWrongDigestAndChangedSourceAreRefusedBeforeApprovalOrPost() async throws {
        for scenario in ["foreign-account", "wrong-digest", "changed-source"] {
            let fixture = try UploadHTTPFixture(body: uploadBody(size: 8_193, inline: false))
            defer { fixture.stop() }
            let source = try fixture.files.write(byteCount: 8_193)
            let specification = try uploadSpecification(size: 8_193,
                digest: scenario == "wrong-digest" ? String(repeating: "0", count: 64) : source.sha256,
                account: scenario == "foreign-account" ? "foreign" : "account")
            let events = UploadEvents()
            do {
                _ = try await AnyNativeFileUploader(client: fixture.client()).attach(
                    specification: specification, fileURL: source.url,
                    validateScope: {
                        let count = await events.check()
                        if scenario == "changed-source", count == 2 { try Data([0x44]).write(to: source.url, options: .atomic) }
                    }, authorizeDispatch: { try await events.approveOnce() },
                    retainReceipt: { value in await events.retain(value) })
                XCTFail("Predispatch failure was admitted: \(scenario)")
            } catch {
                XCTAssertFalse(error is AnyNativeFileUploadUncertain)
                if scenario == "foreign-account" { XCTAssertEqual(error as? AnyEngineError, .accountChanged) }
                if scenario == "wrong-digest" { XCTAssertEqual(error as? AnyNativeFileUploadError, .contentMismatch) }
                if scenario == "changed-source" { XCTAssertEqual(error as? AnyNativeFileUploadError, .sourceChanged) }
            }
            let state = await events.snapshot()
            XCTAssertEqual(state.approvals, 0); XCTAssertEqual(state.fileIDs, [])
            XCTAssertEqual(try fixture.rows().count, 0)
        }
    }

    func testFailedOneShotCallbackPreservesUncertaintyWithoutSendingTheBody() async throws {
        let fixture = try UploadHTTPFixture(body: uploadBody(size: 12))
        defer { fixture.stop() }
        let source = try fixture.files.write(byteCount: 12)
        let specification = try uploadSpecification(size: 12, digest: source.sha256)
        let events = UploadEvents()
        do {
            _ = try await AnyNativeFileUploader(client: fixture.client()).attach(
                specification: specification, fileURL: source.url, validateScope: {},
                authorizeDispatch: { try await events.approveOnce(); throw UploadTestFailure.revoked },
                retainReceipt: { value in await events.retain(value) })
            XCTFail("A denied callback dispatched content")
        } catch let uncertain as AnyNativeFileUploadUncertain {
            XCTAssertNil(uncertain.knownReceipt)
            XCTAssertEqual(uncertain.underlying as? UploadTestFailure, .revoked)
        }
        let state = await events.snapshot()
        XCTAssertEqual(state.approvals, 1); XCTAssertEqual(state.fileIDs, [])
        XCTAssertEqual(try fixture.rows().count, 0)
    }

    func testKnownReceiptPrecedesRevokedScopeAndAccountPostflight() async throws {
        for switchAccount in [false, true] {
            let fixture = try UploadHTTPFixture(body: uploadBody(size: 12,
                name: "private-native-name.png", mime: "image/png"), switchAfterPost: switchAccount)
            defer { fixture.stop() }
            let source = try fixture.files.write(byteCount: 12)
            let specification = try uploadSpecification(size: 12, digest: source.sha256)
            let events = UploadEvents()
            do {
                _ = try await AnyNativeFileUploader(client: fixture.client()).attach(
                    specification: specification, fileURL: source.url,
                    validateScope: { if fixture.has("post-responded") { throw UploadTestFailure.revoked } },
                    authorizeDispatch: { try await events.approveOnce() },
                    retainReceipt: { value in await events.retain(value) })
                XCTFail("A revoked consumer received an attachment")
            } catch let uncertain as AnyNativeFileUploadUncertain {
                XCTAssertEqual(uncertain.knownReceipt?.reference.fileID, "file")
                XCTAssertEqual(uncertain.knownReceipt?.reference.accountID, "account")
                let acknowledgement = try XCTUnwrap(uncertain.knownReceipt)
                // This error crosses a failed authority fence. Its closed
                // recovery model must not carry full native private metadata.
                XCTAssertEqual(Set(Mirror(reflecting: acknowledgement).children.compactMap(\.label)), ["reference", "byteCount"])
                XCTAssertFalse(String(reflecting: uncertain).contains("private-native-name"))
                XCTAssertFalse(String(reflecting: acknowledgement).contains("image/png"))
                if switchAccount { XCTAssertEqual(uncertain.underlying as? AnyEngineError, .accountChanged) }
                else { XCTAssertEqual(uncertain.underlying as? UploadTestFailure, .revoked) }
            }
            let state = await events.snapshot()
            XCTAssertEqual(state.approvals, 1); XCTAssertEqual(state.fileIDs, ["file"])
            XCTAssertEqual(try fixture.posts().count, 1)
        }
    }

    func testFailedReceiptJournalAndCancellationAfterAcknowledgementKeepKnownIdentity() async throws {
        for cancel in [false, true] {
            let fixture = try UploadHTTPFixture(body: uploadBody(size: 12))
            defer { fixture.stop() }
            let source = try fixture.files.write(byteCount: 12)
            let specification = try uploadSpecification(size: 12, digest: source.sha256)
            let events = UploadEvents()
            let uploader = AnyNativeFileUploader(client: try fixture.client())
            let operation = Task {
                try await uploader.attach(specification: specification, fileURL: source.url, validateScope: {},
                    authorizeDispatch: { try await events.approveOnce() },
                    retainReceipt: { value in
                        await events.retain(value)
                        if cancel { withUnsafeCurrentTask { $0?.cancel() } }
                        else { throw UploadTestFailure.journalUnavailable }
                    })
            }
            do { _ = try await operation.value; XCTFail("A failed post-ACK operation was reported as verified") }
            catch let uncertain as AnyNativeFileUploadUncertain {
                XCTAssertEqual(uncertain.knownReceipt?.reference.fileID, "file")
                if !cancel { XCTAssertEqual(uncertain.underlying as? UploadTestFailure, .journalUnavailable) }
            }
            let state = await events.snapshot()
            XCTAssertEqual(state.approvals, 1); XCTAssertEqual(state.fileIDs, ["file"])
            XCTAssertEqual(try fixture.posts().count, 1)
        }
    }

    func testMalformedAcknowledgementsAndNativeErrorsNeverBecomeReceiptsOrAutomaticRetries() async throws {
        let base = uploadBody(size: 12)
        var wrongObject = base.object!; wrongObject["objectId"] = .string("other-object")
        var wrongSize = base.object!; wrongSize["size"] = .integer(13)
        let cases: [(String, Int, AnyJSON)] = [
            ("invalid-json", 201, base), ("normal", 200, base),
            ("normal", 201, .object(wrongObject)), ("normal", 201, .object(wrongSize)),
            ("normal", 201, .object(["rejections": .array([.object(["code": .string("partial")])])])),
            ("normal", 403, .object(["error": .object(["code": .string("acl.forbidden")])])),
            ("normal", 500, .object(["error": .object(["code": .string("server.internal")])]))
        ]
        for (mode, status, body) in cases {
            let fixture = try UploadHTTPFixture(body: body, mode: mode, status: status)
            defer { fixture.stop() }
            let source = try fixture.files.write(byteCount: 12)
            let specification = try uploadSpecification(size: 12, digest: source.sha256)
            let events = UploadEvents()
            do {
                _ = try await AnyNativeFileUploader(client: fixture.client()).attach(specification: specification,
                    fileURL: source.url, validateScope: {}, authorizeDispatch: { try await events.approveOnce() },
                    retainReceipt: { value in await events.retain(value) })
                XCTFail("Unqualified response accepted: \(mode) / \(status)")
            } catch let uncertain as AnyNativeFileUploadUncertain {
                XCTAssertNil(uncertain.knownReceipt)
                if status == 403 { XCTAssertEqual(uncertain.underlying as? AnyEngineError, .http(status: 403, code: "acl.forbidden")) }
                if status == 500 { XCTAssertEqual(uncertain.underlying as? AnyEngineError, .http(status: 500, code: "server.internal")) }
            }
            let state = await events.snapshot()
            XCTAssertEqual(state.approvals, 1); XCTAssertEqual(state.fileIDs, [])
            XCTAssertEqual(try fixture.posts().count, 1)
        }
    }

    func testResponseCeilingIncludesExactChunkedBoundaryAndRefusesBothOversizeForms() async throws {
        for mode in ["exact-cap", "chunked-over-cap", "advertised-over-cap"] {
            let fixture = try UploadHTTPFixture(body: uploadBody(size: 12), mode: mode)
            defer { fixture.stop() }
            let source = try fixture.files.write(byteCount: 12)
            let specification = try uploadSpecification(size: 12, digest: source.sha256)
            let events = UploadEvents()
            do {
                let result = try await AnyNativeFileUploader(client: fixture.client()).attach(
                    specification: specification, fileURL: source.url, validateScope: {},
                    authorizeDispatch: { try await events.approveOnce() },
                    retainReceipt: { value in await events.retain(value) })
                XCTAssertEqual(mode, "exact-cap")
                XCTAssertEqual(result.reference.fileID, "file")
            } catch let uncertain as AnyNativeFileUploadUncertain {
                XCTAssertNotEqual(mode, "exact-cap")
                XCTAssertNil(uncertain.knownReceipt)
                XCTAssertEqual(uncertain.underlying as? AnyEngineError, .readLimit)
            }
            let state = await events.snapshot()
            XCTAssertEqual(state.approvals, 1)
            XCTAssertEqual(state.fileIDs, mode == "exact-cap" ? ["file"] : [])
            XCTAssertEqual(try fixture.posts().count, 1)
        }
    }

    func testRedirectCannotForwardThePrivateBodyOrConsumeAnotherDispatch() async throws {
        let fixture = try UploadHTTPFixture(body: uploadBody(size: 12), mode: "redirect")
        defer { fixture.stop() }
        let source = try fixture.files.write(byteCount: 12)
        let specification = try uploadSpecification(size: 12, digest: source.sha256)
        let events = UploadEvents()
        do {
            _ = try await AnyNativeFileUploader(client: fixture.client()).attach(specification: specification,
                fileURL: source.url, validateScope: {}, authorizeDispatch: { try await events.approveOnce() },
                retainReceipt: { value in await events.retain(value) })
            XCTFail("Redirected upload was accepted")
        } catch let uncertain as AnyNativeFileUploadUncertain {
            XCTAssertNil(uncertain.knownReceipt)
            XCTAssertEqual(uncertain.underlying as? AnyNativeFileUploadError, .redirectRefused)
        }
        XCTAssertEqual(try fixture.posts().map { $0["path"]?.string }, ["/v1/spaces/space/objects/object/files"])
        let state = await events.snapshot()
        XCTAssertEqual(state.approvals, 1); XCTAssertEqual(state.fileIDs, [])
    }

    func testCancellationAfterBodyDispatchKeepsUnknownOutcomeAndDoesNotResend() async throws {
        let fixture = try UploadHTTPFixture(body: uploadBody(size: 8_193, inline: false), mode: "hold-ack")
        defer { fixture.stop() }
        let source = try fixture.files.write(byteCount: 8_193)
        let specification = try uploadSpecification(size: 8_193, digest: source.sha256)
        let events = UploadEvents()
        let uploader = AnyNativeFileUploader(client: try fixture.client())
        let operation = Task {
            try await uploader.attach(specification: specification, fileURL: source.url, validateScope: {},
                authorizeDispatch: { try await events.approveOnce() },
                retainReceipt: { value in await events.retain(value) })
        }
        try await fixture.waitFor("body-accepted")
        operation.cancel()
        do { _ = try await operation.value; XCTFail("Cancelled upload claimed an unreceived acknowledgement") }
        catch let uncertain as AnyNativeFileUploadUncertain { XCTAssertNil(uncertain.knownReceipt) }
        let state = await events.snapshot()
        XCTAssertEqual(state.approvals, 1); XCTAssertEqual(state.fileIDs, [])
        let posts = try fixture.posts()
        XCTAssertEqual(posts.count, 1)
        XCTAssertEqual(posts[0]["byteCount"]?.integer, 8_193)
        XCTAssertEqual(posts[0]["sha256"]?.string, source.sha256)
    }

    func testCancelledTransportCannotFinishBeforeItsSerialDelegateDrains() async throws {
        let fixture = try UploadHTTPFixture(body: uploadBody(size: 8_193, inline: false), mode: "hold-ack")
        defer { fixture.stop() }
        let source = try fixture.files.write(byteCount: 8_193)
        let request = try fixture.rawUploadRequest(byteCount: 8_193)
        let queue = OperationQueue()
        queue.maxConcurrentOperationCount = 1
        defer { queue.isSuspended = false }
        let response = AnyNativeFileUploadResponse(delegateQueue: queue)
        let state = UploadDrainState()
        let operation = Task {
            let outcome: Result<Void, any Error>
            do {
                _ = try await response.perform(request, fileURL: source.url)
                outcome = .success(())
            } catch { outcome = .failure(error) }
            await state.complete()
            try outcome.get()
        }
        defer { operation.cancel() }
        // The real server has received all bytes, but withholds its ACK.
        // The deliberately suspended serial delegate cannot deliver either
        // completion callback. Merely asking URLSession to cancel is not drain.
        try await fixture.waitFor("body-accepted")
        queue.isSuspended = true
        operation.cancel()
        try await Task.sleep(for: .milliseconds(200))
        let finishedWhileCallbacksBlocked = await state.isComplete()
        XCTAssertFalse(finishedWhileCallbacksBlocked, "Task.value must retain ownership while its delegate is blocked")
        XCTAssertFalse(fixture.has("post-responded"))
        XCTAssertEqual(try fixture.files.digest(source.url), source.sha256)
        queue.isSuspended = false
        do { try await operation.value; XCTFail("Cancellation became a success") }
        catch { XCTAssertTrue(error is CancellationError) }
        let completedAfterRelease = await state.isComplete()
        XCTAssertTrue(completedAfterRelease)
        let posts = try fixture.posts()
        XCTAssertEqual(posts.count, 1)
        XCTAssertEqual(posts[0]["byteCount"]?.integer, 8_193)
        XCTAssertEqual(posts[0]["sha256"]?.string, source.sha256)
    }

    func testLostAcknowledgementAfterCompleteBodyDoesNotReplayTheUpload() async throws {
        let fixture = try UploadHTTPFixture(body: uploadBody(size: 8_193, inline: false), mode: "drop-ack")
        defer { fixture.stop() }
        let source = try fixture.files.write(byteCount: 8_193)
        let specification = try uploadSpecification(size: 8_193, digest: source.sha256)
        let events = UploadEvents()
        do {
            _ = try await AnyNativeFileUploader(client: fixture.client()).attach(specification: specification,
                fileURL: source.url, validateScope: {}, authorizeDispatch: { try await events.approveOnce() },
                retainReceipt: { value in await events.retain(value) })
            XCTFail("A lost acknowledgement became a file receipt")
        } catch let uncertain as AnyNativeFileUploadUncertain { XCTAssertNil(uncertain.knownReceipt) }
        let state = await events.snapshot()
        XCTAssertEqual(state.approvals, 1); XCTAssertEqual(state.fileIDs, [])
        let posts = try fixture.posts()
        XCTAssertEqual(posts.count, 1)
        XCTAssertEqual(posts[0]["byteCount"]?.integer, 8_193)
        XCTAssertEqual(posts[0]["sha256"]?.string, source.sha256)
    }

    func testKnownFileInfoRequiresCurrentScopeAndExactObjectWithoutWriting() async throws {
        for wrongObject in [false, true] {
            var body = uploadBody(size: 8_193, inline: false).object!
            if wrongObject { body["objectId"] = .string("other-object") }
            let fixture = try UploadHTTPFixture(body: .object(body))
            defer { fixture.stop() }
            let specification = try uploadSpecification(size: 8_193)
            do {
                _ = try await AnyNativeFileUploader(client: fixture.client()).info(specification: specification,
                    fileID: "file", authorize: { if fixture.has("info-responded") { throw UploadTestFailure.revoked } })
                XCTFail("An invalid info read escaped its scope")
            } catch {
                if wrongObject { XCTAssertEqual(error as? AnyEngineError, .malformedResponse("file attachment scope or fields")) }
                else { XCTAssertEqual(error as? UploadTestFailure, .revoked) }
            }
            XCTAssertEqual(try fixture.posts().count, 0)
            XCTAssertEqual(try fixture.rows().count, 1)
        }
    }
}

private enum UploadTestFailure: Error, Equatable { case revoked, journalUnavailable, duplicateApproval, receiptMissing, fixtureFailed }

private actor UploadEvents {
    private var checks = 0
    private var approvals = 0
    private var fileIDs: [String] = []
    func check() -> Int { checks += 1; return checks }
    func approveOnce() throws {
        approvals += 1
        guard approvals == 1 else { throw UploadTestFailure.duplicateApproval }
    }
    func retain(_ receipt: AnyNativeAttachedFile) { fileIDs.append(receipt.reference.fileID) }
    func requireKnownReceipt() throws {
        guard fileIDs == ["file"] else { throw UploadTestFailure.receiptMissing }
    }
    func snapshot() -> (approvals: Int, fileIDs: [String]) { (approvals, fileIDs) }
}

private actor UploadDrainState {
    private var completed = false
    func complete() { completed = true }
    func isComplete() -> Bool { completed }
}

private final class UploadHTTPFixture: @unchecked Sendable {
    let files: UploadTestFiles
    private let directory: URL
    private let process = Process()
    private let control = Pipe()
    private var stderr: FileHandle?
    private var port = 0
    private var stopped = false
    private let token = String(repeating: "a", count: 64)

    init(body: AnyJSON, mode: String = "normal", status: Int = 201, switchAfterPost: Bool = false) throws {
        let parent: URL
        if let path = ProcessInfo.processInfo.environment["PINKHA_FILE_UPLOAD_FIXTURE_ROOT"] {
            parent = URL(fileURLWithPath: path, isDirectory: true)
            let attributes = try FileManager.default.attributesOfItem(atPath: path)
            guard parent.resolvingSymlinksInPath().path == parent.path,
                  attributes[.type] as? FileAttributeType == .typeDirectory,
                  (attributes[.posixPermissions] as? NSNumber)?.intValue == 0o700,
                  (attributes[.ownerAccountID] as? NSNumber)?.uint32Value == geteuid() else {
                throw UploadTestFailure.fixtureFailed
            }
        } else {
            parent = FileManager.default.temporaryDirectory.appendingPathComponent("pinkha-upload-evidence-" + UUID().uuidString)
            try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false,
                attributes: [.posixPermissions: 0o700])
        }
        directory = parent.appendingPathComponent("case-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false,
            attributes: [.posixPermissions: 0o700])
        files = try UploadTestFiles(parent: directory)
        let config: AnyJSON = .object(["body": body, "mode": .string(mode), "status": .integer(Int64(status)),
            "switchAfterPost": .bool(switchAfterPost), "controlToken": .string(token)])
        try JSONEncoder().encode(config).write(to: directory.appendingPathComponent("config.json"))
        let script = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("Fixtures/file_upload_server.py")
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = ["python3", "-B", script.path, directory.path]
        process.standardInput = control
        // The child inherits only fd0. If the XCTest owner dies, no duplicate
        // write descriptor can hide EOF and keep this fixture alive.
        guard fcntl(control.fileHandleForWriting.fileDescriptor, F_SETFD, FD_CLOEXEC) == 0 else {
            throw UploadTestFailure.fixtureFailed
        }
        let stderrURL = directory.appendingPathComponent("stderr.log")
        guard FileManager.default.createFile(atPath: stderrURL.path, contents: nil,
            attributes: [.posixPermissions: 0o600]) else { throw UploadTestFailure.fixtureFailed }
        stderr = try FileHandle(forWritingTo: stderrURL)
        process.standardOutput = FileHandle.nullDevice
        process.standardError = stderr
        do {
            try process.run()
            try control.fileHandleForReading.close()
            let deadline = Date().addingTimeInterval(5)
            let path = directory.appendingPathComponent("port.json")
            while !FileManager.default.fileExists(atPath: path.path) {
                guard process.isRunning, Date() < deadline else { throw UploadTestFailure.fixtureFailed }
                Thread.sleep(forTimeInterval: 0.01)
            }
            port = try JSONDecoder().decode(Int.self, from: Data(contentsOf: path))
            guard (1...65_535).contains(port) else { throw UploadTestFailure.fixtureFailed }
        } catch { stop(); throw error }
    }

    deinit { try? control.fileHandleForWriting.close() }

    func client() throws -> AnyHTTPClient {
        guard let url = URL(string: "http://127.0.0.1:\(port)") else { throw UploadTestFailure.fixtureFailed }
        return try .init(baseURL: url, expectedAccountID: "account", authorization: AnyHTTPAuthorization(token: token))
    }

    func rawUploadRequest(byteCount: Int) throws -> URLRequest {
        guard let url = URL(string: "http://127.0.0.1:\(port)/v1/spaces/space/objects/object/files") else {
            throw UploadTestFailure.fixtureFailed
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 5
        request.setValue(token, forHTTPHeaderField: "X-Any-Control-Token")
        request.setValue(String(byteCount), forHTTPHeaderField: "Content-Length")
        request.setValue("application/octet-stream", forHTTPHeaderField: "Content-Type")
        return request
    }

    func has(_ name: String) -> Bool { FileManager.default.fileExists(atPath: directory.appendingPathComponent(name + ".json").path) }
    func rows() throws -> [AnyJSON] {
        let path = directory.appendingPathComponent("dispatch.json")
        if !FileManager.default.fileExists(atPath: path.path) { return [] }
        return try JSONDecoder().decode([AnyJSON].self, from: Data(contentsOf: path))
    }
    func posts() throws -> [AnyJSON] { try rows().filter { $0["method"]?.string == "POST" } }
    func waitFor(_ name: String) async throws {
        let deadline = Date().addingTimeInterval(5)
        while !has(name) {
            guard process.isRunning, Date() < deadline else { throw UploadTestFailure.fixtureFailed }
            try await Task.sleep(for: .milliseconds(10))
        }
    }
    func stop() {
        guard !stopped else { return }
        stopped = true
        var errors: [String] = []
        var stdinEOFSignalled = false
        do { try control.fileHandleForWriting.close(); stdinEOFSignalled = true }
        catch { errors.append("stdin ownership close failed") }
        let deadline = Date().addingTimeInterval(3)
        while process.isRunning && Date() < deadline { Thread.sleep(forTimeInterval: 0.01) }
        let exited = process.processIdentifier > 0 && !process.isRunning
        var exitCode: Int64?
        if exited {
            process.waitUntilExit()
            exitCode = Int64(process.terminationStatus)
            if process.terminationReason != .exit || process.terminationStatus != 0 {
                errors.append("fixture did not exit normally")
            }
        } else { errors.append("fixture remained active after owned stdin EOF") }
        do { try stderr?.synchronize(); try stderr?.close() }
        catch { errors.append("fixture stderr could not be retained") }
        let started = try? JSONDecoder().decode(AnyJSON.self,
            from: Data(contentsOf: directory.appendingPathComponent("fixture-start.json")))
        let ended = try? JSONDecoder().decode(AnyJSON.self,
            from: Data(contentsOf: directory.appendingPathComponent("fixture-exit.json")))
        if started?["pid"]?.integer != Int64(process.processIdentifier) ||
           ended?["pid"]?.integer != Int64(process.processIdentifier) || ended?["stopReason"]?.string != "stdin-eof" {
            errors.append("fixture ownership receipt mismatch")
        }
        var payloadsRemoved = false
        // Retain raw request, error and lifecycle ledgers in the controller's
        // evidence directory. Only synthetic source bytes are cleaned, and
        // only after this exact Process has positively reported exit.
        if exited {
            do { try files.removeChecked(); payloadsRemoved = true }
            catch { errors.append("synthetic source cleanup failed") }
        }
        let proof: AnyJSON = .object(["pid": .integer(Int64(process.processIdentifier)),
            "processGroup": started?["pgid"] ?? .null, "leaderObservedExited": .bool(exited),
            "exitCode": exitCode.map(AnyJSON.integer) ?? .null, "stdinEOFSignalled": .bool(stdinEOFSignalled),
            "payloadsRemoved": .bool(payloadsRemoved), "errors": .array(errors.map(AnyJSON.string))])
        do { try JSONEncoder().encode(proof).write(to: directory.appendingPathComponent("parent-stop.json"), options: .atomic) }
        catch { errors.append("fixture stop receipt could not be retained") }
        XCTAssertTrue(errors.isEmpty, errors.joined(separator: "; "))
        // No numeric PID signal is sent here. The outer qualified Swift owner
        // handles abnormal lifetime, and inherited-pipe EOF also works when
        // the XCTest process exits before this method can be called.
    }
}
#endif
