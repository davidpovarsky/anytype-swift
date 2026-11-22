import Foundation

private struct Vector: Decodable {
    let name: String
    let bytes: Data
    let failure: String?
}

private enum ControlFailure: Error { case failed(String) }

@main
private struct NativeBodyMapEntryControls {
    static func main() throws {
        let vectors = try JSONDecoder().decode([Vector].self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
        var results: [[String: String]] = []
        for vector in vectors {
            var actual: String?
            do { try OriginalAnnotationNativeMapKeyGuard.validate(vector.bytes) }
            catch { actual = String(describing: error) }
            guard actual == vector.failure else {
                throw ControlFailure.failed("\(vector.name): expected \(String(describing: vector.failure)), actual \(String(describing: actual))")
            }
            results.append(["name": vector.name, "status": "PASS"])
        }
        let report: [String: Any] = ["status": "PASS_NEW_MAP_ENTRY_LOSS_CONTROLS", "tests_run": results.count,
                                    "tests": results, "native_executions": 0,
                                    "scope": "Only new map-entry fields/wire/value loss cases; no replay of prior 40 controls"]
        print(String(decoding: try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys]), as: UTF8.self))
    }
}
