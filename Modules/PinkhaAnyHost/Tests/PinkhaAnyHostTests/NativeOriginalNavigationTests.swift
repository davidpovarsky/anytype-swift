import Foundation
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration
@testable import PinkhaAnyHost

/// The exact retained originals are reused. Changed views are synthetic
/// projection controls and are never claimed to be original captures.
final class NativeOriginalNavigationTests: XCTestCase {
    func testFourOriginalContextsKeepTheirNativeIdentityAndRoundTripBinding() throws {
        let fixture = try load()
        let expected: [(AnyHeartOriginalNavigationBinding.Context, Int64)] = [
            (.workspace, 518), (.home, 32), (.archive, 48), (.widget, 112)
        ]
        XCTAssertEqual(AnyHeartOriginalNavigationBinding.Context.allCases.count, 4)
        for (context, type) in expected {
            let evidence = try fixture.evidence(context.rawValue)
            let binding = try AnyHeartOriginalNavigationBinding(evidence: evidence)
            try binding.requireSource(fixture.plan.source)
            XCTAssertEqual(binding.context, context)
            XCTAssertEqual(binding.evidence.snapshot.nativeType, type)
            XCTAssertEqual(Data(binding.evidence.snapshot.uniqueKey.utf8), Data(context.rawValue.utf8))
            XCTAssertFalse(binding.permitsDestinationWrites)
            XCTAssertFalse(binding.provesCurrentHomeSelection)
            XCTAssertEqual(binding.readContract, "pinkha-heart-original-navigation-v1")
            XCTAssertEqual(try JSONDecoder().decode(AnyHeartOriginalNavigationBinding.self,
                from: JSONEncoder().encode(binding)), binding)
        }
        try fixture.requireRetainedInputsUnchanged()
    }

    func testOriginalWorkspacePreservesExplicitEmptyHomepageAndAbsentLegacyDashboard() throws {
        let fixture = try load()
        let original = try fixture.evidence("ws")
        XCTAssertEqual(original.snapshotSHA256, "b454bdeefa2b0b58d037043939a4f1a757ff2bdf9a7032c01e0b5890010cd376")
        XCTAssertEqual(original.viewSHA256, "c83cb42037d49082901d9370cddc0c7f192e73f2ac82dc6ec9a77e44c0145736")
        XCTAssertEqual(original.snapshot.details["homepage"], .string(""))
        XCTAssertNil(original.snapshot.details["spaceDashboardId"])
        guard case .empty = AnyHeartOriginalNavigationSnapshot.project("homepage", snapshot: original.snapshot),
              case .absent = AnyHeartOriginalNavigationSnapshot.project("spaceDashboardId", snapshot: original.snapshot) else {
            return XCTFail("an explicit empty homepage must not activate an absent legacy value")
        }
        try fixture.requireRetainedInputsUnchanged()
    }

    func testProjectionRetainsAbsenceBuiltInsOpaqueObjectBytesAndUnsupportedValues() throws {
        guard case .absent = AnyHeartOriginalHomeValue.project(nil),
              case .empty = AnyHeartOriginalHomeValue.project(.string("")) else {
            return XCTFail("absence and empty must remain distinct")
        }
        for builtIn in AnyHeartOriginalHomeValue.BuiltIn.allCases {
            guard case .builtIn(let result) = AnyHeartOriginalHomeValue.project(.string(builtIn.rawValue)) else {
                return XCTFail("exact built-in identity was not recognized")
            }
            XCTAssertEqual(result, builtIn)
        }
        let opaque = "object-e\u{301} — שָׁלוֹם"
        guard case .sourceObject(let reference) = AnyHeartOriginalHomeValue.project(.string(opaque)) else {
            return XCTFail("original object reference disappeared")
        }
        XCTAssertEqual(Data(reference.utf8), Data(opaque.utf8))
        for value in [AnyJSON.null, .bool(false), .integer(0), .array([]),
                      .object(["future": .array([.integer(0), .null])]), .string("bad\nreference")] {
            guard case .unsupported(let retained) = AnyHeartOriginalHomeValue.project(value) else {
                return XCTFail("unsupported original value became a navigation target")
            }
            XCTAssertEqual(try wire(retained), try wire(value))
        }
    }

    func testWrongNativeDefinitionAndDecodedContextOrContractCannotOverrideIdentity() throws {
        let fixture = try load()
        XCTAssertThrowsError(try AnyHeartOriginalNavigationBinding(evidence: fixture.evidence("rel-origin")))
        let original = try AnyHeartOriginalNavigationBinding(evidence: fixture.evidence("ws"))
        let encoded = try JSONDecoder().decode(AnyJSON.self, from: JSONEncoder().encode(original))
        for (key, value) in [("context", AnyJSON.string("home")),
                             ("readContract", .string("unqualified-current-home"))] {
            var changed = try XCTUnwrap(encoded.object)
            changed[key] = value
            XCTAssertThrowsError(try JSONDecoder().decode(AnyHeartOriginalNavigationBinding.self,
                from: wire(.object(changed))))
        }
        try fixture.requireRetainedInputsUnchanged()
    }

    func testForeignAccountUnicodeIdentityFailsBeforeAnyNavigationRequest() throws {
        let composed = "account-caf\u{00E9}", decomposed = "account-cafe\u{0301}"
        XCTAssertEqual(composed, decomposed)
        let client = try AnyHTTPClient(baseURL: XCTUnwrap(URL(string: "http://127.0.0.1:1")),
            expectedAccountID: composed)
        let foreign = try AnyTorahWorkspace(accountID: decomposed, spaceID: "space")
        XCTAssertThrowsError(try AnyHeartOriginalNavigationStore(client: client, workspace: foreign)) {
            XCTAssertEqual($0 as? AnyHostError, .wrongWorkspace)
        }
    }

    private func load() throws -> NativeCanonicalSupplementFixture {
        let environment = ProcessInfo.processInfo.environment
        guard environment["PINKHA_NATIVE_DEFINITION_RETAINED"] != nil,
              environment["PINKHA_NATIVE_ORIGINAL156"] != nil else {
            throw AnyNativeImportedCatalogError.invalidOriginalPlan
        }
        return try NativeCanonicalSupplementFixture.load()
    }

    private func wire(_ value: AnyJSON) throws -> Data {
        try AnyDestinationDefinitionChecks.bytes(value)
    }
}
