import Foundation
import Glibc

@main
private struct OriginalArchiveLimitControls {
    static func main() {
        var passed: [String] = []
        do {
            guard CommandLine.arguments.count == 2 else { throw NSError(domain: "arguments", code: 1) }
            let packet = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
            for kind in ["text", "format", "nested", "attachment"] {
                let data = try Data(contentsOf: packet.appendingPathComponent("fixtures/" + kind + ".zip"))
                guard data.count > OriginalAnnotationNativeArchiveLayout.maximumArchiveBytes else {
                    throw NSError(domain: "fixture-does-not-exceed-original-cap", code: 2)
                }
                do {
                    _ = try OriginalAnnotationNativeArchiveLayout(data)
                    throw NSError(domain: "original-cap-did-not-reject", code: 3)
                } catch OriginalAnnotationNativeArchiveLayout.Failure.sizeLimit {
                    passed.append(kind)
                    print("{\"case\":\"original-limit-rejects-" + kind + "\",\"status\":\"PASS\"}")
                }
            }
            let result: [String: Any] = ["status": "PASS", "passed": passed, "assertions": 8,
                "scope": "NEW_CONTROLS_OF_UNCHANGED_ORIGINAL_LAYOUT_ON_ACTUAL_EXPORT_BYTES",
                "native_body_or_restore_qualified": false]
            let data = try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
            FileHandle.standardOutput.write(data + Data([10]))
        } catch {
            let data = try! JSONSerialization.data(withJSONObject: ["status": "FAIL", "passed": passed, "error": String(describing: error)], options: [.sortedKeys])
            FileHandle.standardOutput.write(data + Data([10]))
            exit(1)
        }
    }
}
