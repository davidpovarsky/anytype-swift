import Foundation
import Security
import Darwin
import AnyLib
import PinkhaAnyEngine

public enum AnyEmbeddedRuntimeError: Error, Equatable, Sendable {
    case invalidConfiguration
    case alreadyRunning
    case allocationFailed
    case randomGenerationFailed(Int32)
    case startFailed(code: Int32, message: String)
    case invalidBoundAddress
    case unexpectedVersion
    case notRunning
    case controlBusy
    case controlHTTPStatus(Int)
    case sessionChanged
}

/// Selects the native code contract, independently of which network is used.
/// A native application must explicitly request pinkhaNativeV1.
public enum AnyEmbeddedBuild: String, Sendable, Codable {
    case upstreamV050
    case pinkhaNativeV1
    case pinkhaPreparedMigrationCandidateV1
    case pinkhaPreparedInlineMigrationCandidateV1
    case pinkhaPreparedFileMigrationCandidateV1
    case pinkhaPreparedComponentsCandidateV1
    case pinkhaPreparedComponentsCandidateV2

    public static var linked: Self {
        #if PINKHA_PREPARED_COMPONENTS_V2_RUNTIME
        return .pinkhaPreparedComponentsCandidateV2
        #elseif PINKHA_PREPARED_COMPONENTS_RUNTIME
        return .pinkhaPreparedComponentsCandidateV1
        #elseif PINKHA_PREPARED_FILE_MIGRATION_RUNTIME
        return .pinkhaPreparedFileMigrationCandidateV1
        #elseif PINKHA_PREPARED_INLINE_MIGRATION_RUNTIME
        return .pinkhaPreparedInlineMigrationCandidateV1
        #elseif PINKHA_PREPARED_MIGRATION_RUNTIME
        return .pinkhaPreparedMigrationCandidateV1
        #elseif PINKHA_NATIVE_RUNTIME
        return .pinkhaNativeV1
        #else
        return .upstreamV050
        #endif
    }

    public var versionPrefix: String {
        switch self {
        case .upstreamV050: return "any v0.5.0 "
        case .pinkhaNativeV1: return "any v0.5.0-pinkha.1 "
        case .pinkhaPreparedMigrationCandidateV1: return "any v0.5.0-pinkha.prepared.1 "
        case .pinkhaPreparedInlineMigrationCandidateV1: return "any v0.5.0-pinkha.prepared.inline.1 "
        case .pinkhaPreparedFileMigrationCandidateV1: return "any v0.5.0-pinkha.prepared.file.1 "
        case .pinkhaPreparedComponentsCandidateV1: return "any v0.5.0-pinkha.prepared.components.1 "
        case .pinkhaPreparedComponentsCandidateV2: return "any v0.5.0-pinkha.prepared.components.2 "
        }
    }
}

/// Selecting the official network must be an explicit host decision.
public enum AnyEmbeddedNetwork: Sendable {
    case official
    case custom(nodeconfYAML: String, pushPeerID: String = "", pushAddresses: String = "")

    fileprivate var arguments: (String, String, String) {
        get throws {
            switch self {
            case .official:
                return ("", "", "")
            case .custom(let nodeconf, let peer, let addresses):
                guard !nodeconf.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
                      peer.isEmpty == addresses.isEmpty else {
                    throw AnyEmbeddedRuntimeError.invalidConfiguration
                }
                return (nodeconf, peer, addresses)
            }
        }
    }
}

/// A synchronous, generation-bound last-resort hook for iOS background-task
/// expiry. Normal shutdown must still drain the host and reconcile actor state.
public struct AnyEmbeddedEmergencyStop: Sendable {
    fileprivate let generation: UUID
    public func requestStop() { AnyRuntimeEmergencyRegistry.shared.signal(generation) }
}

private final class AnyRuntimeEmergencyRegistry: @unchecked Sendable {
    static let shared = AnyRuntimeEmergencyRegistry()
    private let lock = NSLock()
    private var generation: UUID?
    func install(_ value: UUID) {
        lock.lock(); defer { lock.unlock() }
        generation = value
    }
    func clear(_ value: UUID) {
        lock.lock(); defer { lock.unlock() }
        if generation == value { generation = nil }
    }
    func signal(_ value: UUID) {
        lock.lock(); defer { lock.unlock() }
        guard generation == value else { return }
        // Native StopNow is the upstream synchronous, non-draining signal.
        // Holding this lock prevents an old signal crossing a later boot.
        AnyLibStopNow()
    }
}

/// Holds a loopback address and the control capability for this one engine boot.
/// The patched mobile runtime requires the token on every route. It remains
/// independent of document membership and of Hanlin read/write consent.
public struct AnyEmbeddedSession: Sendable, CustomStringConvertible, CustomDebugStringConvertible {
    public let baseURL: URL
    public let generation: UUID
    public let engineVersion: String
    private let controlToken: String

    public enum ControlOperation: Sendable {
        case authenticate
        case signOut
        case shutdown
    }

    fileprivate init(baseURL: URL, engineVersion: String, controlToken: String) {
        self.baseURL = baseURL
        self.engineVersion = engineVersion
        self.controlToken = controlToken
        self.generation = UUID()
    }

    public var emergencyStop: AnyEmbeddedEmergencyStop { .init(generation: generation) }
    /// Creates the scoped transport without revealing the managed token.
    public func dataClient(expectedAccountID: String) throws -> AnyHTTPClient {
        try .init(baseURL: baseURL, expectedAccountID: expectedAccountID,
                  authorization: AnyHTTPAuthorization(token: controlToken))
    }

    func authenticatedRead(path: String) -> URLRequest {
        var request = URLRequest(url: baseURL.appendingPathComponent("v1").appendingPathComponent(path))
        request.setValue(controlToken, forHTTPHeaderField: "X-Any-Control-Token")
        return request
    }


    public var description: String { "AnyEmbeddedSession(\(generation), control capability redacted)" }
    public var debugDescription: String { description }

    /// Wallet creation/restoration and Keychain ownership belong to the host.
    /// Callers must fence and drain document operations before changing account.
    func controlRequest(_ operation: ControlOperation, jsonBody: Data? = nil) -> URLRequest {
        let path: String
        let method: String
        switch operation {
        case .authenticate: path = "auth"; method = "POST"
        case .signOut: path = "auth"; method = "DELETE"
        case .shutdown: path = "shutdown"; method = "POST"
        }
        var request = URLRequest(url: baseURL.appendingPathComponent("v1").appendingPathComponent(path))
        request.httpMethod = method
        request.httpBody = jsonBody
        request.timeoutInterval = 30
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(controlToken, forHTTPHeaderField: "X-Any-Control-Token")
        return request
    }
}

/// Owns the process-global AnyLib instance. No lifecycle call runs on MainActor.
/// This is a real iOS embedded runtime binding, not the application's backend switch.
public actor AnyEmbeddedRuntime {
    public static let shared = AnyEmbeddedRuntime()
    private var active: AnyEmbeddedSession?
    private var controlGeneration: UUID?
    private init() {}

    public func currentSession() -> AnyEmbeddedSession? { active }

    public func start(dataDirectory: URL, network: AnyEmbeddedNetwork, build: AnyEmbeddedBuild = .upstreamV050) throws -> AnyEmbeddedSession {
        guard active == nil else { throw AnyEmbeddedRuntimeError.alreadyRunning }
        guard dataDirectory.isFileURL, dataDirectory.path.hasPrefix("/"),
              dataDirectory.path != "/" else {
            throw AnyEmbeddedRuntimeError.invalidConfiguration
        }
        let (nodeconf, pushPeer, pushAddresses) = try network.arguments
        guard let versionPointer = AnyLibVersion() else { throw AnyEmbeddedRuntimeError.unexpectedVersion }
        let version = String(cString: versionPointer)
        guard build == .linked, version.hasPrefix(build.versionPrefix) else { throw AnyEmbeddedRuntimeError.unexpectedVersion }
        var random = [UInt8](repeating: 0, count: 32)
        let status = SecRandomCopyBytes(kSecRandomDefault, random.count, &random)
        guard status == errSecSuccess else {
            throw AnyEmbeddedRuntimeError.randomGenerationFailed(status)
        }
        let token = random.map { String(format: "%02x", $0) }.joined()
        let strings = [dataDirectory.path, "127.0.0.1:0", nodeconf, pushPeer, pushAddresses, "managed", token]
        guard strings.allSatisfy({ !$0.utf8.contains(0) }) else {
            throw AnyEmbeddedRuntimeError.invalidConfiguration
        }
        let pointers = strings.map { strdup($0) }
        defer { pointers.forEach { free($0) } }
        guard pointers.allSatisfy({ $0 != nil }) else {
            throw AnyEmbeddedRuntimeError.allocationFailed
        }
        var result = AnyLibStartWithMode(
            pointers[0], pointers[1], pointers[2], pointers[3],
            pointers[4], pointers[5], pointers[6]
        )
        guard result.code == 0 else {
            throw AnyEmbeddedRuntimeError.startFailed(code: result.code, message: Self.read(&result.message))
        }
        let address = Self.read(&result.address)
        guard let url = URL(string: "http://" + address),
              url.host == "127.0.0.1", let port = url.port, port > 0,
              url.path.isEmpty else {
            AnyLibStop()
            throw AnyEmbeddedRuntimeError.invalidBoundAddress
        }
        let session = AnyEmbeddedSession(baseURL: url, engineVersion: version, controlToken: token)
        active = session
        AnyRuntimeEmergencyRegistry.shared.install(session.generation)
        return session
    }

    /// Sends owner controls over a fresh redirect-denying loopback session.
    /// Auth responses may contain a recovery phrase; hand them directly to the
    /// host's secure onboarding flow, never to diagnostics or analytics.
    public func executeControl(
        _ operation: AnyEmbeddedSession.ControlOperation, jsonBody: Data? = nil,
        expectedGeneration: UUID? = nil
    ) async throws -> Data {
        guard let active else { throw AnyEmbeddedRuntimeError.notRunning }
        if let expectedGeneration, expectedGeneration != active.generation { throw AnyEmbeddedRuntimeError.sessionChanged }
        guard controlGeneration == nil else { throw AnyEmbeddedRuntimeError.controlBusy }
        let requestGeneration = UUID()
        controlGeneration = requestGeneration
        defer {
            if controlGeneration == requestGeneration { controlGeneration = nil }
        }
        let configuration = URLSessionConfiguration.ephemeral
        configuration.urlCache = nil
        configuration.httpCookieStorage = nil
        configuration.httpShouldSetCookies = false
        let session = URLSession(configuration: configuration, delegate: AnyControlRedirectRefusal(), delegateQueue: nil)
        defer { session.invalidateAndCancel() }
        let (data, response) = try await session.data(for: active.controlRequest(operation, jsonBody: jsonBody))
        guard self.active?.generation == active.generation else {
            throw AnyEmbeddedRuntimeError.sessionChanged
        }
        guard let response = response as? HTTPURLResponse, (200..<300).contains(response.statusCode) else {
            throw AnyEmbeddedRuntimeError.controlHTTPStatus((response as? HTTPURLResponse)?.statusCode ?? 0)
        }
        return data
    }

    /// The owner must first cancel/drain its HTTP subscriptions and operations.
    /// This does not erase data and never deletes a corrupt store automatically.
    public func stop(expectedGeneration: UUID? = nil) {
        guard let active else { return }
        if let expectedGeneration, active.generation != expectedGeneration { return }
        AnyRuntimeEmergencyRegistry.shared.clear(active.generation)
        AnyLibStop()
        self.active = nil
    }

    /// Await this while time remains in a background task. The main app's
    /// synchronous expiration callback still needs its own native lifecycle hook.
    public func stopNow(expectedGeneration: UUID? = nil) {
        guard let active else { return }
        if let expectedGeneration, active.generation != expectedGeneration { return }
        AnyRuntimeEmergencyRegistry.shared.clear(active.generation)
        AnyLibStopNow()
        self.active = nil
    }

    private static func read<T>(_ value: inout T) -> String {
        withUnsafePointer(to: &value) { pointer in
            pointer.withMemoryRebound(to: CChar.self, capacity: MemoryLayout<T>.size) {
                String(cString: $0)
            }
        }
    }
}


private final class AnyControlRedirectRefusal: NSObject, URLSessionTaskDelegate, Sendable {
    func urlSession(
        _ session: URLSession, task: URLSessionTask,
        willPerformHTTPRedirection response: HTTPURLResponse,
        newRequest request: URLRequest,
        completionHandler: @escaping @Sendable (URLRequest?) -> Void
    ) {
        completionHandler(nil)
    }
}
