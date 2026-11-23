import UIKit
import ObjectiveC
import MachO
import FirebaseCore
import FirebaseMessaging
import OriginalEditorSharedFirebase

@main
final class SharedRuntimeProbeApp: UIResponder, UIApplicationDelegate {
    var window: UIWindow?

    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
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
        let expectedSuffix = "/Frameworks/OriginalEditorSharedFirebase.framework/OriginalEditorSharedFirebase"
        let unique = required.allSatisfy {
            providers[$0]?.count == 1 && providers[$0]![0].hasSuffix(expectedSuffix)
        }
        let anchors = OriginalEditorSharedFirebase.firebaseClassNames
        let nonce = ProcessInfo.processInfo.environment["SHARED_RUNTIME_PROBE_NONCE"] ?? ""
        let result: [String: Any] = [
            "schema": 1, "status": unique && !nonce.isEmpty ? "PASS_SINGLE_LOADED_PROVIDER" : "FAIL",
            "nonce": nonce, "process_id": ProcessInfo.processInfo.processIdentifier,
            "main_bundle": main, "providers": providers,
            "actual_firebase_class_names": anchors,
            "original_editor_stageb_qualified": false
        ]
        do {
            let root = try FileManager.default.url(for: .documentDirectory, in: .userDomainMask,
                                                  appropriateFor: nil, create: true)
            try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys, .prettyPrinted])
                .write(to: root.appendingPathComponent("shared-runtime-result.json"), options: .atomic)
        } catch { NSLog("Shared runtime result write failed: %@", String(describing: error)) }
        let view = UIViewController()
        view.view.backgroundColor = .systemBackground
        let label = UILabel(frame: CGRect(x: 24, y: 80, width: 620, height: 100))
        label.text = unique ? "Shared Firebase provider verified" : "Shared Firebase provider failed"
        view.view.addSubview(label)
        window = UIWindow(frame: UIScreen.main.bounds)
        window?.rootViewController = view
        window?.makeKeyAndVisible()
        return true
    }
}
