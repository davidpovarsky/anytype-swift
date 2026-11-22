import Foundation
import UIKit
@_spi(OriginalEditorQualification) import AnytypeOriginalEditor

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

/// This body is typechecked and linked against only the exported binary. It is
/// deliberately never invoked by the resource probe: no account, Space, editor
/// object, native edit, or persistence acceptance is inferred from compilation.
@MainActor
private func compileOriginalHostAPI(
    binding: AnytypeOriginalEditorBinding,
    sourceLifetime: AnytypeOriginalEditorSourceLifetime,
    host: AnytypeOriginalEditorHost,
    snapshot: AnytypeOriginalEditorSnapshot,
    source: AnytypeOriginalEditorQualificationSource,
    qualification: AnytypeOriginalEditorQualificationSession
) async throws {
    let exactBinding = try AnytypeOriginalEditorBinding(
        accountID: binding.accountID, spaceID: binding.spaceID, objectID: binding.objectID,
        hostProfileID: binding.hostProfileID, annotationUUID: binding.annotationUUID,
        expectedRevision: binding.expectedRevision, sourceWitnessSHA256: binding.sourceWitnessSHA256
    )
    let lifetime = AnytypeOriginalEditorSourceLifetime(binding: exactBinding)
    let opened = try await AnytypeOriginalEditorModule.openExistingEditor(
        binding: exactBinding, sourceLifetime: sourceLifetime, sourceIsCurrent: { $0 == exactBinding }
    )
    _ = try opened.makeViewController()
    let capture = try await host.captureNativeSnapshot(maximumBodyBytes: 65_536)
    _ = try AnytypeOriginalEditorSnapshot(bodyBytes: capture.snapshot.bodyBytes, maximumBodyBytes: 65_536)
    _ = snapshot.provenance.matchesCaptureBinding(exactBinding)
    let qualificationSource = try AnytypeOriginalEditorQualificationSource(
        hostProfileID: source.hostProfileID, annotationUUID: source.annotationUUID,
        expectedRevision: source.expectedRevision, sourceWitnessSHA256: source.sourceWitnessSHA256
    )
    _ = try await AnytypeOriginalEditorModule.beginEditableAcceptance(
        source: qualificationSource, sourceIsCurrent: { $0 == qualificationSource }
    )
    _ = try await AnytypeOriginalEditorModule.beginFidelityAcceptance(
        source: qualificationSource, sourceIsCurrent: { $0 == qualificationSource }
    )
    _ = try await qualification.prepareReopen(
        snapshot: snapshot, currentSource: qualificationSource,
        sourceIsCurrent: { $0 == qualificationSource }
    )
    _ = try await qualification.verifyFidelityAfterReopen(host: opened)
    opened.retire()
    lifetime.retire()
}
