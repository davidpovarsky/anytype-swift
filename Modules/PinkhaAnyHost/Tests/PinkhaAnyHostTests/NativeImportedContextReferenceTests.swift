import Foundation
import XCTest
import PinkhaAnyEngine
import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// These references are persisted locators, never native authorization. Current
/// account/run/READ and exact journal/archive validation occur in owner.open.
final class NativeImportedContextReferenceTests: XCTestCase, @unchecked Sendable {
    func testClosedReferenceWireRejectsMissingExtraDuplicateAndMalformedFields() throws {
        let fields = validFields()
        let bytes = try wire(.object(fields))
        let reference = try AnyNativeImportedContextReference.decode(bytes)
        XCTAssertFalse(reference.grantsNativeAuthority)
        XCTAssertEqual(try reference.encoded(), try AnyNativeImportedContextReference.decode(reference.encoded()).encoded())
        XCTAssertEqual(reference.binding.planSHA256, fields["planSHA256"]?.string)
        XCTAssertEqual(reference.archiveBytes, 4096)

        var extra = fields; extra["binding"] = .object(["accountID": .string("foreign")])
        XCTAssertThrowsError(try AnyNativeImportedContextReference.decode(wire(.object(extra))))
        var missing = fields; missing.removeValue(forKey: "checkpointSHA256")
        XCTAssertThrowsError(try AnyNativeImportedContextReference.decode(wire(.object(missing))))
        var duplicate = Data("{\"contract\":\"pinkha-native-imported-context-v1\",".utf8)
        duplicate.append(bytes.dropFirst())
        XCTAssertThrowsError(try AnyNativeImportedContextReference.decode(duplicate))
        let invalidFields: [(String, AnyJSON)] = [
            ("contract", .string("pinkha-native-imported-context-v2")),
            ("checkpointSHA256", .string(String(repeating: "A", count: 64))),
            ("archiveSHA256", .string("not-a-digest")),
            ("archiveBytes", .integer(4095)),
            ("archiveBytes", .integer(Int64(AnyHeartNativePreservationArchive.maximumBytes) + 1)),
            ("archiveBytes", .string("4096")),
            ("destinationNetworkID", .string("")),
            ("sourceAccountID", .string("bad\u{0}identity"))
        ]
        for (key, invalid) in invalidFields {
            var changed = fields; changed[key] = invalid
            XCTAssertThrowsError(try AnyNativeImportedContextReference.decode(wire(.object(changed))), key)
        }
        XCTAssertThrowsError(try AnyNativeImportedContextReference.decode(Data()))
        let overLimit = Data(repeating: 0x20, count: AnyNativeImportedContextReference.maximumBytes + 1)
        XCTAssertThrowsError(try AnyNativeImportedContextReference.decode(overLimit)) { error in
            XCTAssertEqual(error as? AnyEngineError, .readLimit)
        }
    }

    func testReferenceBindingKeepsOpaqueUTF8AndNeverAuthenticatesAChangedCheckpointHash() throws {
        var fields = validFields()
        fields["destinationAccountID"] = .string("caf\u{e9}")
        fields["sourceSpaceID"] = .string("source-e\u{301}")
        let composed = try AnyNativeImportedContextReference.decode(wire(.object(fields)))
        fields["destinationAccountID"] = .string("cafe\u{301}")
        let decomposed = try AnyNativeImportedContextReference.decode(wire(.object(fields)))
        XCTAssertFalse(AnyNativeImportedContextReference.sameBinding(composed.binding, decomposed.binding))
        XCTAssertNotEqual(Data(composed.destinationAccountID.utf8), Data(decomposed.destinationAccountID.utf8))
        XCTAssertNotEqual(try composed.encoded(), try decomposed.encoded())
        let expected = try decomposed.expectedArchiveBinding()
        XCTAssertEqual(Data(expected.spaceID.utf8), Data("source-e\u{301}".utf8))
        fields["checkpointSHA256"] = .string(String(repeating: "f", count: 64))
        let changedLocator = try AnyNativeImportedContextReference.decode(wire(.object(fields)))
        XCTAssertNotEqual(changedLocator.checkpointSHA256, decomposed.checkpointSHA256)
        XCTAssertFalse(changedLocator.grantsNativeAuthority)
        XCTAssertEqual(changedLocator.binding.planSHA256, decomposed.binding.planSHA256)
        // Decoding a syntactically valid locator is deliberately insufficient.
        // owner.open must compare this hash to the exact completed checkpoint.
    }

    private func validFields() -> [String: AnyJSON] {
        [
            "contract": .string(AnyNativeImportedContextReference.version),
            "destinationNetworkID": .string("fixture-network"),
            "destinationAccountID": .string("fixture-account"),
            "destinationSpaceID": .string("fixture-space"),
            "storeID": .string("fixture-store"), "planID": .string(String(repeating: "2", count: 64)),
            "planSHA256": .string(String(repeating: "a", count: 64)),
            "checkpointSHA256": .string(String(repeating: "b", count: 64)),
            "sourceAccountID": .string("source-account"), "sourceSpaceID": .string("source-space"),
            "captureManifestSHA256": .string(String(repeating: "c", count: 64)),
            "sourceWitnessSHA256": .string(String(repeating: "d", count: 64)),
            "recoveredManifestSHA256": .string(String(repeating: "e", count: 64)),
            "archiveSourceKey": .string("source-archive"),
            "archiveSHA256": .string(String(repeating: "1", count: 64)),
            "archiveBytes": .integer(4096), "supplementalCanonicalDefinitions": .array([])
        ]
    }

    private func wire(_ value: AnyJSON) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        return try encoder.encode(value)
    }
}
