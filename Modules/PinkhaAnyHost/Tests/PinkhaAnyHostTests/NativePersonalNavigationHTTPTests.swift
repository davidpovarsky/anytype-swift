import Foundation
import XCTest
import PinkhaAnyIntegration
@testable import PinkhaAnyEngine
@testable import PinkhaAnyHost
#if canImport(Darwin)
import Darwin
#elseif canImport(Glibc)
import Glibc
#endif

#if os(macOS) || os(Linux)
/// Real loopback/client execution, with synthetic HTTP authority only. Native
/// signed READ, engine lifetime, offline and storage proofs are separate.
final class NativePersonalNavigationHTTPTests: XCTestCase, @unchecked Sendable {
    func testCurrentHomeKeepsAbsenceEmptySelectionAndUnsetDistinct() async throws {
        let fixture = try PersonalNavigationHTTPFixture()
        defer { fixture.stop() }
        let store = try await makeStore(fixture)
        let lease = try makeLease()
        let box = PersonalNavigationAckBox()
        let first = try await store.readHome(lease: lease)
        if case .absent = first.value {} else { XCTFail("missing preference manufactured a default") }
        let selections: [AnyNativeHomeSelection?] = [.empty, .object("object"), nil]
        for selection in selections {
            let prepared = try await store.prepareHome(selection, lease: lease)
            let result = try await store.commitHome(prepared, lease: lease, onAcknowledged: box.record)
            if case .verifiedCurrent = result.readback {} else { XCTFail("exact accepted readback missing") }
            let value = try XCTUnwrap(result.snapshot)
            if let selection {
                if case .selection(let actual) = value.value { XCTAssertEqual(actual, selection) }
                else { XCTFail("explicit selection disappeared") }
            } else {
                if case .absent = value.value {} else { XCTFail("unset became explicit empty") }
            }
        }
        XCTAssertEqual(box.count, 3)
        let writes = try fixture.writes()
        XCTAssertEqual(writes.count, 3)
        XCTAssertTrue(writes.allSatisfy { $0["path"]?.string == "/v1/pinkha/bound/spaces/space/settings" })
        XCTAssertEqual(writes[0]["body"], .object(["set": .object(["pinkhaHomeV1": .string("")])]))
        XCTAssertEqual(writes[2]["body"], .object(["unset": .array([.string("pinkhaHomeV1")])]))
        XCTAssertFalse(try fixture.rows().contains { $0["method"] == .string("GET") && $0["path"]?.string?.hasSuffix("/settings") == true })
        try requireBoundHeaders(writes)
    }

    func testActualOpenWritesOneNativeLocalDatetimeForReaderWithoutSharedHistory() async throws {
        let fixture = try PersonalNavigationHTTPFixture()
        defer { fixture.stop() }
        let store = try await makeStore(fixture)
        let lease = try makeLease()
        let box = PersonalNavigationAckBox()
        let intent = try await store.prepareActualOpen(objectID: "object",
            observedAt: Date(timeIntervalSince1970: 1_760_000_123.875), lease: lease)
        let result = try await store.commitActualOpen(intent, lease: lease, onAcknowledged: box.record)
        XCTAssertEqual(intent.observedUnixSecond, 1_760_000_123)
        XCTAssertEqual(result.snapshot?.unixMilliseconds, 1_760_000_123_000)
        if case .verifiedCurrent = result.readback {} else { XCTFail("native local result was not read back") }
        let writes = try fixture.writes()
        XCTAssertEqual(writes.count, 1)
        XCTAssertEqual(writes[0]["path"], .string("/v1/pinkha/bound/spaces/space/properties/object/set/any"))
        XCTAssertEqual(writes[0]["body"], .object(["patch": .object([
            "pinkhaLastOpenedV1": .object(["$date": .integer(1_760_000_123_000)])
        ])]))
        XCTAssertEqual(box.count, 1)
        XCTAssertEqual(box.last?.operationID, intent.operationID)
        try requireBoundHeaders(writes)
    }

    func testAcknowledgmentSurvivesAnEnclosingSessionRetirementWithoutPrivateReadback() async throws {
        let fixture = try PersonalNavigationHTTPFixture(mode: "retire-after-write")
        defer { fixture.stop() }
        let store = try await makeStore(fixture)
        let workspace = try AnyTorahWorkspace(accountID: "account", spaceID: "space")
        let session = AnyApplicationSession(workspace: workspace, engineStartedAt: "fixture-run") {
            if fixture.hasRetiredOwner() { throw AnyHostError.engineRestarted }
            return "fixture-run"
        }
        let intent = try await session.perform { lease in
            try await store.prepareActualOpen(objectID: "object",
                observedAt: Date(timeIntervalSince1970: 1_760_000_123), lease: lease)
        }
        let box = PersonalNavigationAckBox()
        do {
            _ = try await session.perform { lease in
                let result = try await store.commitActualOpen(intent, lease: lease, onAcknowledged: box.record)
                XCTAssertNil(result.snapshot)
                if case .nativeAcknowledgedCurrentStateUnverified = result.readback {} else {
                    XCTFail("revoked current data was delivered")
                }
                return result
            }
            XCTFail("the enclosing retired session delivered a receipt")
        } catch is CancellationError {
            // Run invalidation revokes this session and cancels its registered
            // task before the outer perform fence checks cancellation again.
            let active = await session.isActive
            XCTAssertFalse(active, "the retired owner remained active")
            XCTAssertTrue(fixture.hasRetiredOwner(), "cancellation preceded native retirement")
        }
        let retained = await store.acknowledgment(for: intent.operationID)
        XCTAssertEqual(retained?.operationID, intent.operationID)
        XCTAssertEqual(box.last?.operationID, intent.operationID)
        XCTAssertEqual(box.count, 1)
        XCTAssertEqual(try fixture.writes().count, 1)
        await session.revokeAndDrain()
    }

    func testSameAccountNewRunAndRevokedReaderCannotDispatchPreparedOpen() async throws {
        for mode in ["run", "removed"] {
            let fixture = try PersonalNavigationHTTPFixture()
            defer { fixture.stop() }
            let store = try await makeStore(fixture)
            let lease = try makeLease()
            let intent = try await store.prepareActualOpen(objectID: "object", lease: lease)
            if mode == "run" { try fixture.changeRun() } else { try fixture.revoke() }
            do {
                _ = try await store.commitActualOpen(intent, lease: lease, onAcknowledged: { _ in XCTFail("no effect was admitted") })
                XCTFail("stale authority dispatched")
            } catch let error as AnyEngineError {
                if mode == "run" { XCTAssertEqual(error, .accountChanged) }
                else { XCTAssertEqual(error, .http(status: 403, code: "acl.forbidden")) }
            }
            XCTAssertTrue(try fixture.writes().isEmpty)
        }
    }

    func testMissingOrForeignNativeAcknowledgmentStaysUncertainWithoutResend() async throws {
        for mode in ["missing-ack", "foreign-ack", "shared-ack"] {
            let fixture = try PersonalNavigationHTTPFixture(mode: mode)
            defer { fixture.stop() }
            let store = try await makeStore(fixture)
            let lease = try makeLease()
            let intent = try await store.prepareActualOpen(objectID: "object", lease: lease)
            let box = PersonalNavigationAckBox()
            do {
                _ = try await store.commitActualOpen(intent, lease: lease, onAcknowledged: box.record)
                XCTFail("malformed success became a known native local ACK")
            } catch let error as AnyEngineError { XCTAssertEqual(error, .writeUncertain) }
            do {
                _ = try await store.commitActualOpen(intent, lease: lease, onAcknowledged: box.record)
                XCTFail("an uncertain mutation was resent")
            } catch let error as AnyNativePersonalNavigationError { XCTAssertEqual(error, .intentAlreadyDispatched) }
            let retained = await store.acknowledgment(for: intent.operationID)
            XCTAssertNil(retained)
            XCTAssertEqual(box.count, 0)
            XCTAssertEqual(try fixture.writes().count, 1)
        }
    }

    func testDuplicateIntentForeignWorkspaceAndCancellationCannotCreateSecondEffect() async throws {
        let fixture = try PersonalNavigationHTTPFixture()
        defer { fixture.stop() }
        let store = try await makeStore(fixture)
        let lease = try makeLease()
        let before = try fixture.rows().count
        let foreign = try makeLease(workspace: AnyTorahWorkspace(accountID: "account", spaceID: "foreign"))
        do {
            _ = try await store.prepareActualOpen(objectID: "object", lease: foreign)
            XCTFail("foreign lease reached HTTP")
        } catch let error as AnyHostError { XCTAssertEqual(error, .wrongWorkspace) }
        let cancelled = Task<Void, Error> {
            withUnsafeCurrentTask { $0?.cancel() }
            _ = try await store.prepareActualOpen(objectID: "object", lease: lease)
        }
        do { try await cancelled.value; XCTFail("cancelled prepare dispatched") } catch is CancellationError {}
        XCTAssertEqual(try fixture.rows().count, before)
        let intent = try await store.prepareActualOpen(objectID: "object", lease: lease)
        let box = PersonalNavigationAckBox()
        let values = await withTaskGroup(of: String.self) { group in
            for _ in 0..<2 {
                group.addTask {
                    do {
                        _ = try await store.commitActualOpen(intent, lease: lease, onAcknowledged: box.record)
                        return "accepted"
                    } catch AnyNativePersonalNavigationError.intentAlreadyDispatched { return "duplicate" }
                    catch { return "unexpected:\(error)" }
                }
            }
            var values: [String] = []
            for await value in group { values.append(value) }
            return values.sorted()
        }
        XCTAssertEqual(values, ["accepted", "duplicate"])
        XCTAssertEqual(box.count, 1)
        XCTAssertEqual(try fixture.writes().count, 1)
    }

    func testNonlocalDefinitionAndForeignOrUnmaterializedObjectRefuseBeforeWrite() async throws {
        for mode in ["nonlocal", "foreign-target", "unmaterialized", "guest-member"] {
            let fixture = try PersonalNavigationHTTPFixture(mode: mode)
            defer { fixture.stop() }
            let store = try await makeStore(fixture)
            do {
                _ = try await store.prepareActualOpen(objectID: "object", lease: makeLease())
                XCTFail("invalid native prerequisites became an open intent")
            } catch let error as AnyHostError {
                // Synthetic foreign guest identity: this is a client refusal
                // control, not native guest/account membership acceptance.
                XCTAssertEqual(mode, "guest-member")
                XCTAssertEqual(error, .wrongWorkspace)
            } catch let error as AnyNativePersonalNavigationError {
                XCTAssertNotEqual(mode, "guest-member")
                XCTAssertEqual(error, mode == "nonlocal" ? .unavailableContract : .invalidObject)
            }
            XCTAssertTrue(try fixture.writes().isEmpty)
        }
    }

    private func makeStore(_ fixture: PersonalNavigationHTTPFixture) async throws -> AnyNativePersonalNavigationStore {
        let client = try fixture.client()
        let binding = try await client.nativeAccountRunBinding(expectedNetworkID: "network")
        return try .init(client: client, workspace: AnyTorahWorkspace(accountID: "account", spaceID: "space"),
                         binding: binding)
    }
    private func makeLease(workspace: AnyTorahWorkspace? = nil) throws -> AnyHostLease {
        let workspace = try workspace ?? AnyTorahWorkspace(accountID: "account", spaceID: "space")
        return .init(workspace: workspace, generation: UUID(), engineStartedAt: "fixture-run", check: {})
    }
    private func requireBoundHeaders(_ rows: [AnyJSON]) throws {
        XCTAssertTrue(rows.allSatisfy {
            $0["expectedAccount"] == .string("account") &&
            $0["expectedRun"] == .string(String(repeating: "a", count: 64))
        })
    }
}

private final class PersonalNavigationAckBox: @unchecked Sendable {
    private let lock = NSLock()
    private var values: [AnyNativeNavigationAcknowledgment] = []
    func record(_ value: AnyNativeNavigationAcknowledgment) { lock.lock(); defer { lock.unlock() }; values.append(value) }
    var count: Int { lock.lock(); defer { lock.unlock() }; return values.count }
    var last: AnyNativeNavigationAcknowledgment? { lock.lock(); defer { lock.unlock() }; return values.last }
}
private enum PersonalNavigationHTTPFixtureError: Error { case fixture }

private final class PersonalNavigationHTTPFixture: @unchecked Sendable {
    private let directory: URL
    private let process = Process()
    private let control = Pipe()
    private var stderr: FileHandle?
    private var port = 0
    private var started = false
    private var stopped = false
    private let token = String(repeating: "a", count: 64)

    init(mode: String = "normal") throws {
        let parent: URL
        if let path = ProcessInfo.processInfo.environment["PINKHA_RUNTIME_STATE_FIXTURE_ROOT"] {
            parent = URL(fileURLWithPath: path, isDirectory: true)
            let attributes = try FileManager.default.attributesOfItem(atPath: path)
            guard parent.resolvingSymlinksInPath().path == parent.path,
                  attributes[.type] as? FileAttributeType == .typeDirectory,
                  (attributes[.posixPermissions] as? NSNumber)?.intValue == 0o700,
                  (attributes[.ownerAccountID] as? NSNumber)?.uint32Value == geteuid() else {
                throw PersonalNavigationHTTPFixtureError.fixture
            }
        } else {
            parent = FileManager.default.temporaryDirectory.appendingPathComponent("pinkha-runtime-state-" + UUID().uuidString)
            try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false, attributes: [.posixPermissions: 0o700])
        }
        directory = parent.appendingPathComponent("case-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false, attributes: [.posixPermissions: 0o700])
        try JSONEncoder().encode(AnyJSON.object(["mode": .string(mode),
            "controlToken": .string(token)])).write(to: directory.appendingPathComponent("config.json"))
        try Data(String(repeating: "a", count: 64).utf8).write(to: directory.appendingPathComponent("run.txt"))
        let script = directory.appendingPathComponent("server.py")
        try Data(Self.server.utf8).write(to: script)
        try Data("account".utf8).write(to: directory.appendingPathComponent("account.txt"))
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = ["python3", "-B", script.path, directory.path]
        process.standardInput = control
        guard fcntl(control.fileHandleForWriting.fileDescriptor, F_SETFD, FD_CLOEXEC) == 0 else { throw PersonalNavigationHTTPFixtureError.fixture }
        let log = directory.appendingPathComponent("stderr.log")
        guard FileManager.default.createFile(atPath: log.path, contents: nil, attributes: [.posixPermissions: 0o600]) else {
            throw PersonalNavigationHTTPFixtureError.fixture
        }
        stderr = try FileHandle(forWritingTo: log)
        process.standardOutput = FileHandle.nullDevice
        process.standardError = stderr
        do {
            try process.run()
            started = true
            try control.fileHandleForReading.close()
            let path = directory.appendingPathComponent("port.json")
            let deadline = Date().addingTimeInterval(5)
            while !FileManager.default.fileExists(atPath: path.path) {
                guard process.isRunning, Date() < deadline else { throw PersonalNavigationHTTPFixtureError.fixture }
                Thread.sleep(forTimeInterval: 0.01)
            }
            port = try JSONDecoder().decode(Int.self, from: Data(contentsOf: path))
            guard (1...65_535).contains(port) else { throw PersonalNavigationHTTPFixtureError.fixture }
        } catch { stop(); throw error }
    }

    deinit { try? control.fileHandleForWriting.close() }

    func client() throws -> AnyHTTPClient {
        let url = try XCTUnwrap(URL(string: "http://127.0.0.1:\(port)"))
        return try .init(baseURL: url, expectedAccountID: "account", authorization: AnyHTTPAuthorization(token: token))
    }
    func changeAccount(_ account: String) throws {
        try Data(account.utf8).write(to: directory.appendingPathComponent("account.txt"), options: .atomic)
    }
    func changeRun() throws {
        try Data(String(repeating: "b", count: 64).utf8).write(to: directory.appendingPathComponent("run.txt"), options: .atomic)
    }
    func revoke() throws {
        try Data("removed".utf8).write(to: directory.appendingPathComponent("removed.txt"), options: .atomic)
    }
    func writes() throws -> [AnyJSON] { try rows().filter { ["PATCH", "POST"].contains($0["method"]?.string ?? "") } }
    func hasRetiredOwner() -> Bool { FileManager.default.fileExists(atPath: directory.appendingPathComponent("owner-retired.json").path) }
    func rows() throws -> [AnyJSON] {
        let path = directory.appendingPathComponent("requests.json")
        if !FileManager.default.fileExists(atPath: path.path) { return [] }
        return try JSONDecoder().decode([AnyJSON].self, from: Data(contentsOf: path))
    }
    func posts() throws -> [AnyJSON] { try rows().filter { $0["method"]?.string == "POST" } }

    func stop() {
        guard !stopped else { return }
        stopped = true
        var errors: [String] = []
        do { try control.fileHandleForWriting.close() }
        catch { errors.append("owned stdin close failed") }
        let deadline = Date().addingTimeInterval(3)
        while started && process.isRunning && Date() < deadline { Thread.sleep(forTimeInterval: 0.01) }
        let exited = started && !process.isRunning
        var status: Int64?
        if exited {
            process.waitUntilExit()
            status = Int64(process.terminationStatus)
            if process.terminationReason != .exit || status != 0 { errors.append("fixture did not exit normally") }
        } else if started { errors.append("fixture remained live after stdin EOF") }
        do { try stderr?.synchronize(); try stderr?.close() }
        catch { errors.append("stderr retention failed") }
        let initial = try? JSONDecoder().decode(AnyJSON.self, from: Data(contentsOf: directory.appendingPathComponent("start.json")))
        let ended = try? JSONDecoder().decode(AnyJSON.self, from: Data(contentsOf: directory.appendingPathComponent("exit.json")))
        if started && (initial?["pid"]?.integer != Int64(process.processIdentifier) ||
                       ended?["pid"]?.integer != Int64(process.processIdentifier) || ended?["reason"]?.string != "stdin-eof") {
            errors.append("fixture exit ownership mismatch")
        }
        for key in ["pgid", "sessionID", "parentPID", "startTimeTicks", "bootID", "controllerOwnedGroup",
                    "ownerRecord", "ownerRecordSHA256", "ownerPID", "ownerAncestors"] {
            if initial?[key] != ended?[key] { errors.append("fixture ownership changed: " + key) }
        }
        if ProcessInfo.processInfo.environment["PINKHA_RUNTIME_STATE_OWNER_RECORD"] != nil &&
            (initial?["controllerOwnedGroup"]?.bool != true || initial?["pgid"] != initial?["ownerPID"] ||
             initial?["sessionID"] != initial?["ownerPID"]) {
            errors.append("fixture original owner group was not qualified")
        }
        let proof: AnyJSON = .object(["started": .bool(started), "pid": .integer(Int64(process.processIdentifier)),
            "leaderObservedExited": .bool(exited), "exitCode": status.map(AnyJSON.integer) ?? .null,
            "ownership": initial ?? .null,
            "errors": .array(errors.map(AnyJSON.string))])
        do { try JSONEncoder().encode(proof).write(to: directory.appendingPathComponent("parent-stop.json"), options: .atomic) }
        catch { errors.append("stop evidence retention failed") }
        XCTAssertTrue(errors.isEmpty, errors.joined(separator: "; "))
        // An abnormal live descendant is left to the outer owned test-group
        // supervisor. Retained synthetic request/source/lifecycle files remain.
    }

    private static let server = #"""
import datetime, hashlib, http.server, json, os, selectors, signal, socket, stat, sys, time
from pathlib import Path

root = Path(sys.argv[1])
config = json.loads((root / 'config.json').read_text())
rows = []
serial = 0
reason = 'deadline'
home = None
opened = None
applied = 0

def owned_group():
    path = os.environ.get('PINKHA_RUNTIME_STATE_OWNER_RECORD')
    if not path:
        return {'controllerOwnedGroup': False}
    record = Path(path)
    if not record.is_absolute() or record.resolve() != record:
        raise RuntimeError('fixture owner record is not physical')
    fd = os.open(record, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        attributes = os.fstat(stream.fileno())
        raw = stream.read(65537)
    if not stat.S_ISREG(attributes.st_mode) or attributes.st_uid != os.geteuid() or stat.S_IMODE(attributes.st_mode) != 0o600 or len(raw) > 65536:
        raise RuntimeError('fixture owner record custody')
    owner = json.loads(raw)
    pid = owner.get('pid')
    if type(pid) is not int or pid <= 1 or owner.get('cwd') != os.environ.get('PINKHA_RUNTIME_STATE_OWNER_CWD'):
        raise RuntimeError('fixture owner record identity')
    if os.getsid(pid) != pid or os.getpgid(pid) != pid or os.getsid(0) != pid:
        raise RuntimeError('fixture is outside the qualified owner session')
    ancestor = os.getppid()
    lineage = []
    for _ in range(64):
        raw_stat = Path(f'/proc/{ancestor}/stat').read_bytes()
        if len(raw_stat) > 8192:
            raise RuntimeError('fixture owner ancestor bound')
        fields = raw_stat.rsplit(b')', 1)[1].split()
        if len(fields) < 20 or int(fields[3]) != pid:
            raise RuntimeError('fixture owner ancestor session')
        lineage.append({'pid': ancestor, 'startTimeTicks': int(fields[19])})
        if ancestor == pid: break
        ancestor = int(fields[1])
        if ancestor <= 1: raise RuntimeError('fixture qualified leader is not an ancestor')
    else: raise RuntimeError('fixture owner ancestry exceeded bound')
    os.setpgid(0, pid)
    if os.getpgrp() != pid or os.getsid(0) != pid:
        raise RuntimeError('fixture did not join its original owned group')
    return {'controllerOwnedGroup': True, 'ownerRecord': str(record),
            'ownerRecordSHA256': hashlib.sha256(raw).hexdigest(), 'ownerPID': pid, 'ownerAncestors': lineage}

def save(name, value):
    global serial
    serial += 1
    raw = json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()
    if len(raw) > 1048576: raise RuntimeError('fixture evidence bound')
    temporary = root / (name + '.' + str(serial) + '.new')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, root / name)

class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def setup(self):
        self.request.settimeout(1.0)
        super().setup()
    def log_message(self, *args): pass
    def reply(self, status, body, binding=None):
        raw = b'' if status == 204 else json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Connection', 'close')
        if binding:
            if config['mode'] != 'missing-ack':
                self.send_header('X-Any-Binding-Contract', 'pinkha-any-http-engine-binding-v1')
            self.send_header('X-Any-Bound-Account-Id', binding[0])
            self.send_header('X-Any-Bound-Run-Id', binding[1])
        self.end_headers()
        self.close_connection = True
        try: self.wfile.write(raw); self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, socket.timeout): pass
    def handle_one(self):
        global home, opened, applied
        if self.headers.get('X-Any-Control-Token') != config['controlToken']:
            self.reply(403, {'error': {'code': 'fixture.control'}}); return
        body = None
        if self.command in ('POST', 'PATCH'):
            length = int(self.headers.get('Content-Length', '-1'))
            if not 0 <= length <= 32768: raise RuntimeError('fixture request bound')
            raw = self.rfile.read(length)
            if len(raw) != length: raise RuntimeError('fixture short request')
            body = json.loads(raw)
        if len(rows) >= 512: raise RuntimeError('fixture request count')
        rows.append({'method': self.command, 'path': self.path, 'body': body,
            'expectedAccount': self.headers.get('X-Any-Expected-Account-Id'),
            'expectedRun': self.headers.get('X-Any-Expected-Run-Id')})
        save('requests.json', rows)
        account = (root / 'account.txt').read_text()
        run = (root / 'run.txt').read_text()
        if self.command == 'GET':
            if self.path == '/v1/auth':
                self.reply(200, {'authorized': True, 'accountId': account})
            elif self.path == '/v1/auth/engine-binding':
                self.reply(200, {'contract': 'pinkha-any-http-engine-binding-v1',
                    'accountId': account, 'networkId': 'network', 'runId': run})
            elif self.path == '/v1/spaces/space/members/me':
                if (root/'removed.txt').exists():
                    self.reply(403, {'error': {'code': 'acl.forbidden'}})
                else: self.reply(200, {'identity': 'synthetic-guest-key' if config['mode'] == 'guest-member' else 'account', 'permission': 'reader', 'status': 'active'})
            elif self.path == '/v1/spaces/space':
                answer = {'id': 'space', 'status': 'active', 'ownRole': 'owner', 'createdAt': 1}
                if home is not None: answer['settings'] = {'pinkhaHomeV1': home}
                self.reply(200, answer)
            elif self.path == '/v1/spaces/space/types/any/properties':
                scope = 'synced' if config['mode'] == 'nonlocal' else 'local'
                prop = {'id': 'pinkhaLastOpenedV1', 'kind': 'datetime', 'scope': scope,
                    'xFormat': {'type': 'datetime', 'contract': 'pinkha-last-opened-local-v1', 'precision': 'seconds'}}
                self.reply(200, {'properties': [prop]})
            elif self.path == '/v1/spaces/space/objects/object':
                record = {'id': 'object', 'spaceId': 'space', 'any': {'type': 'page'}}
                if opened is not None: record['any']['pinkhaLastOpenedV1'] = opened
                if config['mode'] == 'foreign-target': record['id'] = 'other'
                if config['mode'] == 'unmaterialized': record = {'id': 'object'}
                self.reply(200, {'objectId': 'object', 'record': record})
            else: self.reply(404, {'error': {'code': 'fixture.unknown_read'}})
            return
        if self.headers.get('X-Any-Expected-Account-Id') != account or self.headers.get('X-Any-Expected-Run-Id') != run:
            self.reply(409, {'error': {'code': 'auth.binding_mismatch'}}); return
        if (root/'removed.txt').exists():
            self.reply(403, {'error': {'code': 'acl.forbidden'}}); return
        binding = (account, run)
        if self.command == 'PATCH' and self.path == '/v1/pinkha/bound/spaces/space/settings':
            if body == {'unset': ['pinkhaHomeV1']}:
                home = None
            elif isinstance(body, dict) and set(body) == {'set'} and set(body['set']) == {'pinkhaHomeV1'} and isinstance(body['set']['pinkhaHomeV1'], str):
                home = body['set']['pinkhaHomeV1']
            else:
                self.reply(400, {'error': {'code': 'fixture.settings_shape'}}); return
            status, answer = 204, None
        elif self.command == 'POST' and self.path == '/v1/pinkha/bound/spaces/space/properties/object/set/any':
            if not isinstance(body, dict) or set(body) != {'patch'} or set(body['patch']) != {'pinkhaLastOpenedV1'}:
                self.reply(400, {'error': {'code': 'fixture.patch_shape'}}); return
            value = body['patch']['pinkhaLastOpenedV1']
            if not isinstance(value, dict) or set(value) != {'$date'} or type(value['$date']) is not int or value['$date'] % 1000:
                self.reply(400, {'error': {'code': 'fixture.datetime_shape'}}); return
            opened = {'$date': datetime.datetime.fromtimestamp(value['$date'] // 1000,
                datetime.timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')}
            answer = {'versionId': 'local:1', 'changeId': '', 'recordIds': ['object']}
            if config['mode'] == 'foreign-ack': answer['recordIds'] = ['foreign']
            if config['mode'] == 'shared-ack': answer['changeId'] = 'shared-dag'
            status = 200
        else:
            self.reply(404, {'error': {'code': 'fixture.unbound_or_unknown_write'}}); return
        applied += 1
        save('applied.json', {'count': applied, 'home': home, 'opened': opened})
        if config['mode'] == 'retire-after-write': save('owner-retired.json', True)
        self.reply(status, answer, binding)

    do_GET = handle_one
    do_POST = handle_one
    do_PATCH = handle_one

if hasattr(signal, 'pthread_sigmask'):
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM, signal.SIGINT})
owner = owned_group()
server = http.server.HTTPServer(('127.0.0.1', 0), Handler)
selector = selectors.DefaultSelector()
selector.register(0, selectors.EVENT_READ, 'owner')
selector.register(server.socket, selectors.EVENT_READ, 'http')
started = {'pid': os.getpid(), 'pgid': os.getpgrp(), 'sessionID': os.getsid(0), 'parentPID': os.getppid(), **owner}
if Path('/proc/self/stat').is_file():
    started['startTimeTicks'] = int(Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19])
    started['bootID'] = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
save('start.json', started)
save('port.json', server.server_address[1])
deadline = time.monotonic() + 45
try:
    done = False
    while not done and time.monotonic() < deadline:
        for key, _ in selector.select(0.05):
            if key.data == 'owner':
                if os.read(0, 4096) != b'': raise RuntimeError('unexpected owner bytes')
                reason = 'stdin-eof'; done = True; break
            server._handle_request_noblock()
finally:
    selector.close(); server.server_close()
    save('exit.json', {**started, 'reason': reason, 'requestCount': len(rows)})
if reason != 'stdin-eof': raise RuntimeError('fixture owner deadline')
"""#
}
#endif
