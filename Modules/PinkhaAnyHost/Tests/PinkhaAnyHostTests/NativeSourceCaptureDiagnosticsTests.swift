import Foundation
import XCTest
@testable import PinkhaAnyHost

final class NativeSourceCaptureDiagnosticsTests: XCTestCase {
    private func directory() throws -> URL {
        let path = FileManager.default.temporaryDirectory.resolvingSymlinksInPath()
            .appendingPathComponent("source-diagnostic-test-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: path, withIntermediateDirectories: false,
                                                attributes: [.posixPermissions: 0o700])
        addTeardownBlock { try FileManager.default.removeItem(at: path) }
        return path
    }

    func testFailureRedactsUnknownDomainAndTextWhileRetainingClosedNativeReason() throws {
        let observer = try AnyHeartNativeSourceCaptureDiagnostics(privateDirectory: directory())
        let secret = "private-seed-token-account-path-\(UUID().uuidString)"
        let error = NSError(domain: secret, code: 77, userInfo: [
            NSLocalizedDescriptionKey: secret + "\nnative source checkpoint changed during capture",
            "token": secret, "account": secret, "payload": Data(secret.utf8)
        ])
        XCTAssertTrue(observer.record(.nativeCapture, .failed, error: error))
        XCTAssertTrue(observer.record(.sessionGrant, .succeeded,
            authority: .init(accountMatches: true, full: true, appAssociated: false, tokenPresent: true)))
        let raw = try Data(contentsOf: observer.fileURL)
        let text = try XCTUnwrap(String(data: raw, encoding: .utf8))
        XCTAssertFalse(text.contains(secret))
        XCTAssertFalse(text.contains("checkpoint changed during capture"))
        let trace = try JSONDecoder().decode(AnyHeartNativeSourceCaptureDiagnostics.Trace.self, from: raw)
        XCTAssertFalse(trace.acceptance)
        XCTAssertEqual(trace.events[0].failure, .init(category: "other", numericCode: 77,
                                                      nativeReasons: ["native-checkpoint-changed"]))
        XCTAssertEqual(trace.events[1].authority, .init(accountMatches: true, full: true,
                                                       appAssociated: false, tokenPresent: true))
        let attributes = try FileManager.default.attributesOfItem(atPath: observer.fileURL.path)
        XCTAssertEqual((attributes[.posixPermissions] as? NSNumber)?.intValue, 0o600)
    }

    func testNativeBoundaryReasonsRemainClosedAndUnknownNativeErrorStaysUnclassified() throws {
        let observer = try AnyHeartNativeSourceCaptureDiagnostics(privateDirectory: directory())
        let secret = "private-native-payload-" + UUID().uuidString
        let joined = NSError(domain: "go", code: 1, userInfo: [
            NSLocalizedDescriptionKey: "current already-loaded native Space required\n"
                + "explicit current local ACL read permission required\n"
                + "unchanged private native source manifest required\n" + secret,
            "nativeContext": secret
        ])
        XCTAssertTrue(observer.record(.nativeCapture, .failed, error: joined))
        XCTAssertTrue(observer.record(.nativeCapture, .failed,
            error: NSError(domain: "go", code: 1, userInfo: [NSLocalizedDescriptionKey: secret])))
        let raw = try Data(contentsOf: observer.fileURL)
        let trace = try JSONDecoder().decode(AnyHeartNativeSourceCaptureDiagnostics.Trace.self, from: raw)
        XCTAssertFalse(trace.acceptance)
        XCTAssertEqual(trace.events[0].failure, .init(category: "native-go", numericCode: 1,
            nativeReasons: ["native-private-manifest", "native-space-not-loaded", "native-acl-read-permission"]))
        XCTAssertEqual(trace.events[1].failure, .init(category: "native-go", numericCode: 1, nativeReasons: []))
        let encoded = try XCTUnwrap(String(data: raw, encoding: .utf8))
        XCTAssertFalse(encoded.contains(secret))
        XCTAssertFalse(encoded.contains("nativeContext"))
        XCTAssertFalse(encoded.contains("explicit current local ACL"))
    }

    func testConcurrentObserverHasBoundedOrderedRecordsAndRejectsPublicRoot() throws {
        let root = try directory()
        let observer = try AnyHeartNativeSourceCaptureDiagnostics(privateDirectory: root)
        DispatchQueue.concurrentPerform(iterations: 150) { _ in
            _ = observer.record(.sourceReview, .failed, error: AnyHeartNativeSourceAccountError.invalidAuthority)
        }
        let trace = try JSONDecoder().decode(AnyHeartNativeSourceCaptureDiagnostics.Trace.self,
                                            from: Data(contentsOf: observer.fileURL))
        XCTAssertTrue(trace.truncated)
        XCTAssertFalse(trace.acceptance)
        XCTAssertEqual(trace.events.count, 128)
        XCTAssertEqual(trace.events.map(\.sequence), Array(1...128))
        XCTAssertTrue(trace.events.allSatisfy { $0.failure?.category == "invalid-authority" })
        try FileManager.default.setAttributes([.posixPermissions: 0o755], ofItemAtPath: root.path)
        XCTAssertThrowsError(try AnyHeartNativeSourceCaptureDiagnostics(privateDirectory: root))
    }
}
