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
    private let bookmarkFixture: NativeBookmarkFixture?
    #endif

    init() {
        do {
            let configuration = try AnyNativeLaunchConfiguration.current()
            let directory = configuration.dataDirectory
            let service = configuration.credentialService
            let prepared = try AnyNativeApplication(dataDirectory: directory, credentialService: service)
            #if DEBUG
            let fixture = try NativeCustomTypeFixture.configured(arguments: ProcessInfo.processInfo.arguments,
                dataDirectory: directory, credentialService: service)
            customTypeFixture = fixture
            bookmarkFixture = try NativeBookmarkFixture.configured(arguments: ProcessInfo.processInfo.arguments,
                dataDirectory: directory, credentialService: service)
            #endif
            application = prepared
        } catch {
            application = nil
            #if DEBUG
            customTypeFixture = nil
            bookmarkFixture = nil
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
                    .overlay(alignment: .bottomTrailing) {
                        if let bookmarkFixture {
                            VStack(alignment: .trailing, spacing: 4) {
                                Text("Native Bookmark fixture").font(.caption2)
                                    .accessibilityIdentifier("any-native-ui-bookmark-fixture")
                                    .accessibilityValue(bookmarkFixture.accessibilityValue)
                                    .allowsHitTesting(false)
                                if bookmarkFixture.canReadNext {
                                    Button("Read Bookmark checkpoint") {
                                        Task { await bookmarkFixture.readNext(application: application) }
                                    }
                                    .font(.caption2)
                                    .accessibilityIdentifier("any-native-ui-bookmark-read-checkpoint")
                                }
                            }.padding(8)
                        }
                    }
                    .task { await bookmarkFixture?.run(application: application) }
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
