import Foundation
import OSLog

/// Opt-in observations for disposable simulator acceptance; no authentication behavior.
@MainActor
enum PinkhaUI27StartupDiagnostics {
    static var isEnabled: Bool {
        ProcessInfo.processInfo.environment["PINKHA_UI27_STARTUP_OBSERVATION"] == "1"
    }

    private static let logger = Logger(subsystem: "com.anytype.pinkha", category: "UI27Startup")

    static func record(
        _ phase: String, consumed: ApplicationState?, model: ApplicationState,
        service: ApplicationState, errorType: String?, taskCancelled: Bool
    ) {
        guard isEnabled else { return }
        // Only closed state labels, error metatypes, timestamps and cancellation state.
        // Never pass credentials, account/Space/object IDs, payloads or error descriptions.
        let line = "phase=\(phase) consumed=\(name(consumed)) model=\(name(model)) service=\(name(service)) errorType=\(errorType ?? "none") taskCancelled=\(taskCancelled) utc=\(Date().timeIntervalSince1970) monotonic=\(ProcessInfo.processInfo.systemUptime)"
        logger.info("\(line, privacy: .public)")
    }

    private static func name(_ state: ApplicationState?) -> String {
        switch state {
        case .initial: "initial"
        case .launch: "launch"
        case .home: "home"
        case .auth: "auth"
        case .delete: "delete"
        case nil: "none"
        }
    }
}
