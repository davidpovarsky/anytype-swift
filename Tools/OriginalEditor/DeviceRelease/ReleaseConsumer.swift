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

/// Compiled against the exported production module, never invoked. The actual
/// resource launch above does not create an account, import, editor or save.
@MainActor
public func compileOriginalProductionAPI(
    binding: AnytypeOriginalEditorBinding,
    sourceLifetime: AnytypeOriginalEditorSourceLifetime,
    host: AnytypeOriginalEditorHost,
    snapshot: AnytypeOriginalEditorSnapshot,
    session: AnytypeOriginalEditorAccountSession,
    source: AnytypeOriginalAnnotationImportSource,
    history: AnytypeOriginalAnnotationImportHistory,
    attempt: AnytypeOriginalAnnotationImportAttempt
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
    try session.validateCurrent()
    _ = session.identity.accountID
    _ = session.identity.spaceID
    let presentation = try AnytypeOriginalEditorAccountSession.makePresentation(
        appGroup: "org.otzaria.acceptance.original-editor", onReady: { _ in }, onFailure: { _ in }
    )
    _ = presentation.viewController
    try await presentation.close()
    try await presentation.retryClose()
    let exactSource = try AnytypeOriginalAnnotationImportSource(
        namespace: source.namespace, annotationUUID: source.annotationUUID,
        preparedSessionID: source.preparedSessionID, attemptID: source.attemptID,
        savedRevision: source.savedRevision, sourceDigest: source.sourceDigest,
        payloadDigest: source.payloadDigest, bodyDigest: source.bodyDigest,
        accountID: source.accountID, spaceID: source.spaceID
    )
    let importLifetime = AnytypeOriginalAnnotationImportSourceLifetime(source: exactSource)
    _ = importLifetime.source
    _ = importLifetime.isCurrent
    let prepared = try session.prepareAnnotationImport(
        snapshot: snapshot, sourceLifetime: importLifetime,
        sourceIsCurrent: { $0 == exactSource }, onDrained: { _ in }
    )
    _ = prepared.source
    _ = attempt.drainedHistory
    _ = history.nativeResponseBytes
    _ = history.nativeResponseCopyError
    _ = history.cancellationResponseBytes
    _ = history.cancellationResponseCopyError
    _ = history.cancellationWasScheduled
    _ = history.cancellationAwaitFailed
    _ = prepared.requestCancellation()
    try await prepared.invoke()
    prepared.retire()
    importLifetime.retire()
    opened.retire()
    lifetime.retire()
    try await session.close()
    try await session.retryClose()
}
