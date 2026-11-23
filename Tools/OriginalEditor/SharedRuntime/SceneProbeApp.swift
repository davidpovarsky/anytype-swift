import UIKit
import ObjectiveC
import MachO

@main
final class SharedRuntimeSceneProbeApp: UIResponder, UIApplicationDelegate {
    func application(_ application: UIApplication,
                     configurationForConnecting session: UISceneSession,
                     options: UIScene.ConnectionOptions) -> UISceneConfiguration {
        let configuration = UISceneConfiguration(name: "Shared provider", sessionRole: session.role)
        configuration.sceneClass = UIWindowScene.self
        configuration.delegateClass = SharedRuntimeProbeScene.self
        return configuration
    }
}

final class SharedRuntimeProbeScene: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?

    func scene(_ scene: UIScene, willConnectTo session: UISceneSession,
               options connectionOptions: UIScene.ConnectionOptions) {
        guard let windowScene = scene as? UIWindowScene else { return }
        let required = ["FIRApp", "FIRInstallations", "FIRMessaging", "FBLPromise", "GDTCORTransport"]
        let main = Bundle.main.bundlePath
        var providers: [String: [String]] = Dictionary(uniqueKeysWithValues: required.map { ($0, []) })
        for index in 0..<_dyld_image_count() {
            guard let cPath = _dyld_get_image_name(index) else { continue }
            let path = String(cString: cPath)
            guard path.hasPrefix(main + "/") else { continue }
            var count: UInt32 = 0
            guard let names = objc_copyClassNamesForImage(cPath, &count) else { continue }
            defer { free(names) }
            for offset in 0..<Int(count) {
                let name = String(cString: names[offset])
                if providers[name] != nil { providers[name, default: []].append(path) }
            }
        }
        let suffix = "/Frameworks/OriginalEditorSharedFirebase.framework/OriginalEditorSharedFirebase"
        let unique = required.allSatisfy {
            providers[$0]?.count == 1 && providers[$0]![0].hasSuffix(suffix)
        }
        let anchors = required.compactMap { NSClassFromString($0) }.map { NSStringFromClass($0) }
        let view = UIViewController()
        view.view.backgroundColor = .systemBackground
        let label = UILabel(frame: CGRect(x: 24, y: 80, width: 620, height: 100))
        label.text = unique ? "Shared Firebase provider verified" : "Shared Firebase provider failed"
        view.view.addSubview(label)
        window = UIWindow(windowScene: windowScene)
        window?.rootViewController = view
        window?.makeKeyAndVisible()
        let nonce = ProcessInfo.processInfo.environment["SHARED_RUNTIME_PROBE_NONCE"] ?? ""
        let result: [String: Any] = [
            "schema": 1, "status": unique && anchors == required && !nonce.isEmpty
                ? "PASS_SINGLE_LOADED_PROVIDER" : "FAIL",
            "nonce": nonce, "process_id": ProcessInfo.processInfo.processIdentifier,
            "main_bundle": main, "providers": providers, "actual_firebase_class_names": anchors,
            "scene_delegate": NSStringFromClass(type(of: self)),
            "scene_session_id": session.persistentIdentifier,
            "original_editor_stageb_qualified": false
        ]
        do {
            let root = try FileManager.default.url(for: .documentDirectory, in: .userDomainMask,
                                                  appropriateFor: nil, create: true)
            try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys, .prettyPrinted])
                .write(to: root.appendingPathComponent("shared-runtime-result.json"), options: .atomic)
        } catch { NSLog("Shared runtime result write failed: %@", String(describing: error)) }
    }
}
