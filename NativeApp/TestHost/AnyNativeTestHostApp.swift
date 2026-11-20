import SwiftUI

/// Supplies an application identity for the unchanged native integration tests.
/// Each test owns its real Any runtime; this host never starts a second one.
@main
struct AnyNativeTestHostApp: App {
    var body: some Scene {
        WindowGroup {
            Color.clear
        }
    }
}
