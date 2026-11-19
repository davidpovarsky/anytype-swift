import SwiftUI
import Foundation
import PinkhaAnyNative

/// Separate executable: this target links AnyLib and never links the retained
/// Heart framework, AppDelegate, middleware, or account coordinator.
@main
@MainActor
struct AnyNativeApp: App {
    private let application: AnyNativeApplication?

    init() {
        do {
            let directory: URL
            let service: String
            #if DEBUG
            if ProcessInfo.processInfo.arguments.contains("--native-ui-tests") {
                let args = ProcessInfo.processInfo.arguments
                let position = args.firstIndex(of: "--native-ui-test-scope")
                let candidate = position.flatMap { $0 + 1 < args.count ? UUID(uuidString: args[$0 + 1]) : nil }
                let scope = (candidate ?? UUID()).uuidString
                directory = FileManager.default.temporaryDirectory.appendingPathComponent("native-ui-" + scope)
                service = "io.pinkha.anynative.uitests." + scope
            } else {
                directory = try AnyNativeApplication.defaultDataDirectory()
                service = "io.pinkha.anynative.accounts.v1"
            }
            #else
            directory = try AnyNativeApplication.defaultDataDirectory()
            service = "io.pinkha.anynative.accounts.v1"
            #endif
            application = try AnyNativeApplication(dataDirectory: directory, credentialService: service)
        } catch {
            application = nil
        }
    }

    var body: some Scene {
        WindowGroup {
            if let application {
                AnyNativeRootView(application: application)
            } else {
                ContentUnavailableView("לא ניתן לפתוח את האפליקציה",
                    systemImage: "exclamationmark.triangle",
                    description: Text("אחסון האפליקציה אינו זמין. נסה לפתוח אותה מחדש."))
            }
        }
    }
}
