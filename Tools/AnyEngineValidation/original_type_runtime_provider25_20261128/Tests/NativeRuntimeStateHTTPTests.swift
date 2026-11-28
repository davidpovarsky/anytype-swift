import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost
#if canImport(Darwin)
import Darwin
#elseif canImport(Glibc)
import Glibc
#endif

#if os(macOS) || os(Linux)
/// Real loopback HTTP and the existing AnyHTTPClient. This fixture grants no
/// native authority and does not claim current native or coordinator evidence.
final class NativeRuntimeStateHTTPTests: XCTestCase, @unchecked Sendable {
    func testBothScopedReadRoutesUseTheExistingClientAndRetainTheDeliveryLease() async throws {
        let fixture = try RuntimeStateHTTPFixture()
        defer { fixture.stop() }
        let store = try makeStore(fixture)
        let lease = try NativeRuntimeWireFixture.lease()
        let space = try await store.space(lease: lease)
        let object = try await store.object("object", lease: lease)
        XCTAssertEqual(space.generation, lease.generation)
        XCTAssertEqual(object.generation, lease.generation)
        XCTAssertEqual(space.engineStartedAt, lease.engineStartedAt)
        XCTAssertEqual(object.scope, space.scope)
        XCTAssertEqual(object.objectID, "object")
        XCTAssertFalse(space.permitsDestinationWrites)
        XCTAssertFalse(object.provesObjectExistence)
        let rows = try fixture.rows()
        XCTAssertEqual(rows.count, 6)
        XCTAssertTrue(rows.allSatisfy { $0["method"]?.string == "GET" })
        XCTAssertEqual(rows.compactMap { $0["path"]?.string }.filter { $0 != "/v1/auth" },
            ["/v1/spaces/space/runtime-state", "/v1/spaces/space/objects/object/runtime-state"])
    }

    func testAccountSwitchWithholdsEachAlreadyReceivedRuntimeResponse() async throws {
        for object in [false, true] {
            let fixture = try RuntimeStateHTTPFixture(mode: "switch-after-get")
            defer { fixture.stop() }
            do {
                try await read(makeStore(fixture), object: object, lease: NativeRuntimeWireFixture.lease())
                XCTFail("a response from the retired account escaped")
            } catch let error as AnyEngineError { XCTAssertEqual(error, .accountChanged) }
            XCTAssertEqual(try runtimeRows(fixture).count, 1)
            XCTAssertEqual(try fixture.rows().count, 3)
        }
    }

    func testEngineRestartAndSessionRetirementWithholdBothReceivedResponseTypes() async throws {
        for expected in [AnyHostError.engineRestarted, .sessionClosed] {
            for object in [false, true] {
                let fixture = try RuntimeStateHTTPFixture(mode: "retire-after-get")
                defer { fixture.stop() }
                let lease = try NativeRuntimeWireFixture.lease {
                    if fixture.hasRetiredOwner() { throw expected }
                }
                do {
                    try await read(makeStore(fixture), object: object, lease: lease)
                    XCTFail("received data escaped its retired host lifetime")
                } catch let error as AnyHostError { XCTAssertEqual(error, expected) }
                XCTAssertTrue(fixture.hasRetiredOwner())
                XCTAssertEqual(try runtimeRows(fixture).count, 1)
            }
        }
    }

    func testForeignLeaseAndCurrentTaskCancellationRefuseBeforeAnyHTTPDispatch() async throws {
        let fixture = try RuntimeStateHTTPFixture()
        defer { fixture.stop() }
        let store = try makeStore(fixture)
        let foreign = try AnyTorahWorkspace(accountID: "other-account", spaceID: "space")
        do {
            _ = try await store.space(lease: NativeRuntimeWireFixture.lease(workspace: foreign))
            XCTFail("foreign account lease dispatched")
        } catch let error as AnyHostError { XCTAssertEqual(error, .wrongWorkspace) }
        let lease = try NativeRuntimeWireFixture.lease()
        let cancelled = Task<Void, Error> {
            withUnsafeCurrentTask { $0?.cancel() }
            _ = try await store.object("object", lease: lease)
        }
        do { try await cancelled.value; XCTFail("a cancelled reader dispatched") }
        catch is CancellationError {}
        XCTAssertTrue(try fixture.rows().isEmpty)
    }

    func testUnsupportedOversizedAndForeignNetworkAnswersFailWithoutRetry() async throws {
        for mode in ["unsupported", "oversize", "foreign-network"] {
            for object in [false, true] {
                let fixture = try RuntimeStateHTTPFixture(mode: mode)
                defer { fixture.stop() }
                do {
                    try await read(makeStore(fixture), object: object, lease: NativeRuntimeWireFixture.lease())
                    XCTFail("invalid runtime answer escaped: " + mode)
                } catch let error as AnyEngineError {
                    switch mode {
                    case "unsupported": XCTAssertEqual(error, .http(status: 501, code: "runtime_state.unsupported"))
                    case "oversize": XCTAssertEqual(error, .readLimit)
                    default: XCTAssertEqual(error, .malformedResponse("native runtime identity or contract differs"))
                    }
                }
                XCTAssertEqual(try runtimeRows(fixture).count, 1)
                XCTAssertTrue(try fixture.rows().allSatisfy { $0["method"]?.string == "GET" })
            }
        }
    }

    private func makeStore(_ fixture: RuntimeStateHTTPFixture) throws -> AnyNativeRuntimeStateStore {
        try .init(client: fixture.client(), workspace: NativeRuntimeWireFixture.workspace(), expectedNetworkID: "network")
    }
    private func read(_ store: AnyNativeRuntimeStateStore, object: Bool, lease: AnyHostLease) async throws {
        if object { _ = try await store.object("object", lease: lease) }
        else { _ = try await store.space(lease: lease) }
    }
    private func runtimeRows(_ fixture: RuntimeStateHTTPFixture) throws -> [AnyJSON] {
        try fixture.rows().filter { $0["path"]?.string != "/v1/auth" }
    }
}

private enum RuntimeStateHTTPFixtureError: Error { case fixture }

private final class RuntimeStateHTTPFixture: @unchecked Sendable {
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
                throw RuntimeStateHTTPFixtureError.fixture
            }
        } else {
            parent = FileManager.default.temporaryDirectory.appendingPathComponent("pinkha-runtime-state-" + UUID().uuidString)
            try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false, attributes: [.posixPermissions: 0o700])
        }
        directory = parent.appendingPathComponent("case-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false, attributes: [.posixPermissions: 0o700])
        try JSONEncoder().encode(AnyJSON.object(["spaceBody": NativeRuntimeWireFixture.space(),
            "objectBody": NativeRuntimeWireFixture.object(), "mode": .string(mode),
            "controlToken": .string(token)])).write(to: directory.appendingPathComponent("config.json"))
        let script = directory.appendingPathComponent("server.py")
        try Data(Self.server.utf8).write(to: script)
        try Data("account".utf8).write(to: directory.appendingPathComponent("account.txt"))
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = ["python3", "-B", script.path, directory.path]
        process.standardInput = control
        guard fcntl(control.fileHandleForWriting.fileDescriptor, F_SETFD, FD_CLOEXEC) == 0 else { throw RuntimeStateHTTPFixtureError.fixture }
        let log = directory.appendingPathComponent("stderr.log")
        guard FileManager.default.createFile(atPath: log.path, contents: nil, attributes: [.posixPermissions: 0o600]) else {
            throw RuntimeStateHTTPFixtureError.fixture
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
                guard process.isRunning, Date() < deadline else { throw RuntimeStateHTTPFixtureError.fixture }
                Thread.sleep(forTimeInterval: 0.01)
            }
            port = try JSONDecoder().decode(Int.self, from: Data(contentsOf: path))
            guard (1...65_535).contains(port) else { throw RuntimeStateHTTPFixtureError.fixture }
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
import hashlib, http.server, json, os, selectors, signal, socket, stat, sys, time
from pathlib import Path

root = Path(sys.argv[1])
config = json.loads((root / 'config.json').read_text())
rows = []
serial = 0
reason = 'deadline'
auth_count = 0

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
    def reply(self, status, body, oversized=False):
        raw = json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode()
        if oversized:
            if len(raw) > 32769: raise RuntimeError('fixture response base bound')
            raw += b' ' * (32769 - len(raw))
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Connection', 'close')
        self.end_headers()
        self.close_connection = True
        try: self.wfile.write(raw); self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, socket.timeout): pass
    def handle_one(self):
        global auth_count
        if self.headers.get('X-Any-Control-Token') != config['controlToken']:
            self.reply(403, {'error': {'code': 'fixture.control'}}); return
        body = None
        if self.command == 'POST':
            length = int(self.headers.get('Content-Length', '-1'))
            if not 0 <= length <= 262144: raise RuntimeError('fixture request bound')
            raw = self.rfile.read(length)
            if len(raw) != length: raise RuntimeError('fixture short request')
            body = json.loads(raw)
        if len(rows) >= 64: raise RuntimeError('fixture request count')
        rows.append({'method': self.command, 'path': self.path, 'body': body})
        save('requests.json', rows)
        if self.command == 'GET' and self.path == '/v1/auth':
            self.reply(200, {'authorized': True, 'accountId': (root / 'account.txt').read_text()})
        elif self.command == 'GET' and self.path in ('/v1/spaces/space/runtime-state', '/v1/spaces/space/objects/object/runtime-state'):
            if config['mode'] == 'unsupported':
                self.reply(501, {'error': {'code': 'runtime_state.unsupported'}}); return
            answer = config['objectBody'] if '/objects/' in self.path else config['spaceBody']
            if config['mode'] == 'switch-after-get': (root / 'account.txt').write_text('other-account')
            if config['mode'] == 'retire-after-get': save('owner-retired.json', True)
            if config['mode'] == 'foreign-network': answer['scope']['networkId'] = 'foreign-network'
            self.reply(200, answer, config['mode'] == 'oversize')
        else: self.reply(404, {'error': {'code': 'fixture.unknown'}})
    do_GET = handle_one
    do_POST = handle_one

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
