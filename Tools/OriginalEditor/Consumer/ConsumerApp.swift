import Foundation
import UIKit
import AnytypeOriginalEditor

/// A separate acceptance host. This is not an editor or a replacement renderer.
@main
@MainActor
final class OriginalEditorConsumerApp: UIResponder, UIApplicationDelegate {
    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        let arguments = ProcessInfo.processInfo.arguments
        guard let position = arguments.firstIndex(of: "--original-editor-nonce"),
              arguments.indices.contains(position + 1),
              let nonce = UUID(uuidString: arguments[position + 1]),
              arguments[position + 1] == nonce.uuidString else { return true }
        let destination = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("original-editor-" + nonce.uuidString + ".json")
        do {
            let inspection = try AnytypeOriginalEditorModule.inspectResources()
            let encoder = JSONEncoder()
            encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
            let report = ConsumerReport(nonce: nonce.uuidString,
                                        mainBundleIdentifier: Bundle.main.bundleIdentifier ?? "",
                                        mainBundleURL: Bundle.main.bundleURL.standardizedFileURL.path,
                                        preferredLanguages: Locale.preferredLanguages,
                                        inspection: inspection)
            try encoder.encode(report).write(to: destination, options: .atomic)
        } catch {
            let payload: [String: String] = ["status": "RESOURCE_INSPECTION_FAILED", "nonce": nonce.uuidString,
                                             "errorType": String(reflecting: type(of: error))]
            if let data = try? JSONSerialization.data(withJSONObject: payload, options: [.sortedKeys]) {
                try? data.write(to: destination, options: .atomic)
            }
        }
        return true
    }
}

@MainActor
final class OriginalEditorConsumerScene: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?

    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options: UIScene.ConnectionOptions) {
        guard let scene = scene as? UIWindowScene else { return }
        let controller = UIViewController()
        controller.view.backgroundColor = .systemBackground
        let window = UIWindow(windowScene: scene)
        window.rootViewController = controller
        self.window = window
        window.makeKeyAndVisible()
    }
}

private struct ConsumerReport: Encodable {
    let schema = 1
    let status = "ACTUAL_EXTERNAL_CONSUMER_RESOURCE_OBSERVATION"
    let nonce: String
    let mainBundleIdentifier: String
    let mainBundleURL: String
    let preferredLanguages: [String]
    let inspection: AnytypeOriginalEditorModule.Inspection
}
