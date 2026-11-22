import Foundation

private struct Vector: Decodable {
    let name: String
    let kind: String
    let bytes: Data
    let failure: String?
}

private enum ControlFailure: Error {
    case failed(String)
}

@main
private struct NativeBodyBoundaryControls {
    static func main() throws {
        let vectors = try JSONDecoder().decode([Vector].self, from: Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1])))
        var results: [[String: String]] = []
        for vector in vectors {
            var actual: String?
            do {
                switch vector.kind {
                case "zip": _ = try OriginalAnnotationNativeArchiveLayout(vector.bytes)
                case "map": try OriginalAnnotationNativeMapKeyGuard.validate(vector.bytes)
                default: throw ControlFailure.failed("unknown control kind")
                }
            } catch { actual = String(describing: error) }
            guard actual == vector.failure else {
                throw ControlFailure.failed("\(vector.name): expected \(String(describing: vector.failure)), actual \(String(describing: actual))")
            }
            results.append(["name": vector.name, "status": "PASS"])
        }

        let message = UUID(uuidString: "AE617A8C-EA6F-44C0-A24F-F14CB6972D92")!
        let scope = try TorahAnnotationNativeScope(destination: "maktabah", account: "account", space: "space",
                                                   namespace: "torah", annotationUUID: message)
        let identity = try TorahAnnotationNativeIdentity(scope: scope, objectID: "native-object")
        let commitment = try TorahAnnotationNativeCommitment(scope: scope, messageID: message, mutationID: message,
            revision: 7, sourceDigest: String(repeating: "a", count: 64), payloadDigest: String(repeating: "b", count: 64))
        for (name, digest) in [
            ("caller-supplied payload digest cannot manufacture body proof", commitment.payloadDigest),
            ("arbitrary valid snapshot digest cannot manufacture body proof", String(repeating: "c", count: 64))
        ] {
            let candidate = try TorahAnnotationNativeCandidate(identity: identity, nativeTypeID: "annotation-type",
                objectState: .present, classification: .annotation, creationAttemptID: message,
                creationCommitment: commitment, appliedCommitment: commitment, nativeSnapshotDigest: digest)
            let result = TorahAnnotationCreateRecovery.assessApplied(commitment: commitment,
                expectedIdentity: identity, candidate: candidate, annotationTypeID: "annotation-type", ownerIsCurrent: true)
            guard result == .bodyApplicationUnproven else { throw ControlFailure.failed(name) }
            results.append(["name": name, "status": "PASS"])
        }
        let report: [String: Any] = ["status": "PASS_NEW_NATIVE_BODY_BOUNDARY_CONTROLS",
                                    "tests_run": results.count, "tests": results,
                                    "native_executions": 0,
                                    "scope": "Actual Foundation boundary and policy source with synthetic archive/map inputs; no native export, full graph decode, Owner, mapping or ACK acceptance"]
        let data = try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys])
        print(String(decoding: data, as: UTF8.self))
    }
}
