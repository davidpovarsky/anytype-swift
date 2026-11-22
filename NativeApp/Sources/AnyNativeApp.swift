import SwiftUI
import Foundation
import PinkhaAnyNative

/// Separate executable: this target links AnyLib and never links the retained
/// Heart framework, AppDelegate, middleware, or account coordinator.
@main
@MainActor
struct AnyNativeApp: App {
    private let application: AnyNativeApplication?
    #if DEBUG
    private let customTypeFixture: NativeCustomTypeFixture?
    #endif

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
            let prepared = try AnyNativeApplication(dataDirectory: directory, credentialService: service)
            #if DEBUG
            let fixture = try NativeCustomTypeFixture.configured(arguments: ProcessInfo.processInfo.arguments,
                dataDirectory: directory, credentialService: service)
            customTypeFixture = fixture
            #endif
            application = prepared
        } catch {
            application = nil
            #if DEBUG
            customTypeFixture = nil
            #endif
        }
    }

    var body: some Scene {
        WindowGroup {
            if let application {
                #if DEBUG
                AnyNativeRootView(application: application)
                    .overlay(alignment: .bottom) {
                        if let customTypeFixture {
                            Text("Native custom Type fixture").font(.caption2)
                                .accessibilityIdentifier("any-native-ui-custom-type-fixture")
                                .accessibilityValue(customTypeFixture.accessibilityValue)
                                .allowsHitTesting(false)
                        }
                    }
                    .task { await customTypeFixture?.run(application: application) }
                #else
                AnyNativeRootView(application: application)
                #endif
            } else {
                ContentUnavailableView("לא ניתן לפתוח את האפליקציה",
                    systemImage: "exclamationmark.triangle",
                    description: Text("אחסון האפליקציה אינו זמין. נסה לפתוח אותה מחדש."))
            }
        }
    }
}
