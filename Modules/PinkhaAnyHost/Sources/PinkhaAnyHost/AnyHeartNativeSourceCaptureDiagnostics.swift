import Foundation

/// Opt-in diagnostic output only. It records closed phase/error categories and
/// authority booleans, never identity, tokens, native payloads or error text.
/// This observer has no engine callback and grants no source/destination rights.
public final class AnyHeartNativeSourceCaptureDiagnostics: @unchecked Sendable {
    public enum Phase: String, Codable, Sendable {
        case runtimeCheck, seedRead, sessionCreate, sessionGrant, nativeCapture
        case sourceReview, nativeValidate, sessionClose
    }
    public enum Outcome: String, Codable, Sendable { case started, succeeded, failed, observed }
    public struct Authority: Codable, Equatable, Sendable {
        public let accountMatches: Bool
        public let full: Bool
        public let appAssociated: Bool
        public let tokenPresent: Bool

        public init(accountMatches: Bool, full: Bool, appAssociated: Bool, tokenPresent: Bool) {
            self.accountMatches = accountMatches; self.full = full
            self.appAssociated = appAssociated; self.tokenPresent = tokenPresent
        }
    }
    public struct Failure: Codable, Equatable, Sendable {
        public let category: String
        public let numericCode: Int
        public let nativeReasons: [String]
    }
    public struct Event: Codable, Sendable {
        public let sequence: Int
        public let phase: Phase
        public let outcome: Outcome
        public let failure: Failure?
        public let authority: Authority?
    }
    public struct Trace: Codable, Sendable {
        public let contract: String
        public let acceptance: Bool
        public let truncated: Bool
        public let events: [Event]
    }
    public enum StorageError: Error { case invalidPrivateDirectory }

    public let fileURL: URL
    private let lock = NSLock()
    private var events: [Event] = []
    private var truncated = false
    private static let maximumEvents = 128

    public init(privateDirectory: URL) throws {
        let fm = FileManager.default
        let values = try privateDirectory.resourceValues(forKeys: [.isDirectoryKey, .isSymbolicLinkKey])
        let attributes = try fm.attributesOfItem(atPath: privateDirectory.path)
        guard privateDirectory.isFileURL, privateDirectory.path.hasPrefix("/"),
              values.isDirectory == true, values.isSymbolicLink != true,
              privateDirectory.standardizedFileURL == privateDirectory.resolvingSymlinksInPath().standardizedFileURL,
              (attributes[.posixPermissions] as? NSNumber)?.intValue == 0o700 else {
            throw StorageError.invalidPrivateDirectory
        }
        fileURL = privateDirectory.appendingPathComponent("source-observation-" + UUID().uuidString + ".json")
        let empty = try Self.encode(events: [], truncated: false)
        try empty.write(to: fileURL, options: .withoutOverwriting)
        try fm.setAttributes([.posixPermissions: 0o600], ofItemAtPath: fileURL.path)
    }

    /// A diagnostic I/O failure is returned to the observer's caller. It never
    /// changes the product operation's result or suppresses its original error.
    @discardableResult
    public func record(_ phase: Phase, _ outcome: Outcome,
                       error: (any Error)? = nil, authority: Authority? = nil) -> Bool {
        lock.lock()
        defer { lock.unlock() }
        if events.count == Self.maximumEvents {
            if truncated { return true }
            truncated = true
        } else {
            events.append(.init(sequence: events.count + 1, phase: phase, outcome: outcome,
                                failure: error.map(Self.classify), authority: authority))
        }
        do {
            try Self.encode(events: events, truncated: truncated).write(to: fileURL, options: .atomic)
            try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: fileURL.path)
            return true
        } catch {
            return false
        }
    }

    private static func encode(events: [Event], truncated: Bool) throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(Trace(contract: "pinkha-heart-source-diagnostic-v1",
                                        acceptance: false, truncated: truncated, events: events))
    }

    private static func classify(_ error: any Error) -> Failure {
        let native = error as NSError
        let category: String
        switch error {
        case is CancellationError: category = "cancelled"
        case AnyHeartNativeSourceAccountError.invalidAuthority: category = "invalid-authority"
        case AnyHeartNativeSourceAccountError.invalidLifecycle: category = "invalid-account-lifecycle"
        case AnyHeartNativeSourceAccountError.inactiveCapture: category = "inactive-account-capture"
        case AnyHeartNativeSourceAccountError.sessionCloseFailed: category = "session-close-failed"
        case is AnyHeartNativeSourceCaptureCoordinatorError: category = "source-coordinator"
        case is AnyHeartNativeCaptureError: category = "native-descriptor-or-bundle"
        default:
            switch native.domain {
            case NSCocoaErrorDomain: category = "cocoa"
            case NSOSStatusErrorDomain: category = "os-status"
            case "go", "go.error": category = "native-go"
            default: category = "other"
            }
        }
        // Read only to classify fixed native error literals; never serialize
        // localizedDescription, userInfo, a dynamic domain or a Swift value.
        let message = String(native.localizedDescription.prefix(8192))
        let known: [(String, String)] = [
            ("current application or session transition is busy", "native-session-transition-busy"),
            ("current owned account identity required", "native-account-identity"),
            ("current native full non-app-associated session required", "native-full-session"),
            ("authorized unchanged whole native source capture required", "native-whole-source"),
            ("native source checkpoint changed during capture", "native-checkpoint-changed"),
            ("native source capture descriptor unavailable", "native-descriptor"),
            ("native tree inventory required", "native-tree-inventory"),
            ("native loaded source capture unavailable", "native-capture-unavailable")
        ]
        return .init(category: category, numericCode: native.code,
                     nativeReasons: known.compactMap { message.contains($0.0) ? $0.1 : nil })
    }
}
