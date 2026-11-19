
import XCTest
import PinkhaAnyEngine
@testable import PinkhaAnyUI

final class AnyUIActivationTests: XCTestCase {
    private var complete: [String: AnyJSON] {
        var value: [String: AnyJSON] = [
            "contract": .string("pinkha-torah-native-v1"),
            "bundleId": .string("pinkha/torah-native/v1"),
            "module": .string("pinkha_torah_native"),
            "dataset": .string("pinkha_torah_claims_v1"),
            "dataVersion": .string("pinkha-torah-native-claims-v1"),
            "nativeSemanticPayload": .string("canonical-associations-v2-single-record"),
            "associationBlockDataset": .string("editor_blocks"),
            "documentTypePolicy": .string("canonical-editor-module-v1"),
            "propertyPresentationCollection": .string("pinkha_presentation_v1"),
            "propertyPresentationHiddenProperty": .string("hiddenProperties"),
            "allowedTargetTypes": .array([.string("page")]),
            "nativeClaimsMaxRecords": .integer(10_000),
            "nativeClaimsMaxBytes": .integer(16_777_216),
            "mobileManagedTokenGateway": .integer(0)]
        for key in ["nativeSignedClaims", "spaceWideOperationConflictDomain",
                    "currentACLCommitFence", "targetTreeCommitFence", "nativeDocumentProperties",
                    "nativeIndexedSourceQuery", "nativeRelatedVersion", "conditionalBlockPatch",
                    "conditionalPropertiesSet", "conditionalBlockCurrentWriterFence", "currentWriterObjectCreate", "currentWriterBlockCreate", "nativeClaimsSnapshot", "nativeClaimsWatch", "nativeObjectClaimsSnapshot", "nativeObjectClaimsWatch",
                    "nativeDocumentTypePolicy", "nativeDocumentMembership",
                    "conditionalMembershipSet", "nativePropertyPresentation"] {
            value[key] = .integer(1)
        }
        return value
    }

    func testRequiresEveryNativeAuthorityAndCASCapability() throws {
        for key in ["nativeSignedClaims", "spaceWideOperationConflictDomain",
                    "currentACLCommitFence", "targetTreeCommitFence", "nativeDocumentProperties",
                    "nativeIndexedSourceQuery", "nativeRelatedVersion", "conditionalBlockPatch",
                    "conditionalPropertiesSet", "conditionalBlockCurrentWriterFence", "currentWriterObjectCreate", "currentWriterBlockCreate", "nativeClaimsSnapshot", "nativeClaimsWatch", "nativeObjectClaimsSnapshot", "nativeObjectClaimsWatch",
                    "nativeDocumentTypePolicy", "nativeDocumentMembership",
                    "conditionalMembershipSet", "nativePropertyPresentation"] {
            var response = complete
            response.removeValue(forKey: key)
            XCTAssertThrowsError(try AnyUIFoundationCapabilities(response: .object(response)), key)
            response[key] = .bool(true)
            XCTAssertThrowsError(try AnyUIFoundationCapabilities(response: .object(response)), key)
        }
    }

    func testRejectsStockAndGenericBundle() {
        XCTAssertThrowsError(try AnyUIFoundationCapabilities(response: .object(["version": .string("v0.5.0")])))
        var response = complete
        response["bundleId"] = .string("pinkha.torah.operations/v1")
        XCTAssertThrowsError(try AnyUIFoundationCapabilities(response: .object(response)))
    }

    func testAcceptsVersionedContractWithFutureUnrelatedFields() throws {
        var response = complete
        response["future"] = .object(["irrelevant": .bool(true)])
        let capability = try AnyUIFoundationCapabilities(response: .object(response))
        XCTAssertEqual(capability.allowedTargetTypes, ["page"])
        XCTAssertEqual(capability.maximumClaimRecords, 10_000)
        XCTAssertFalse(capability.mobileManagedTokenGateway)
        response["mobileManagedTokenGateway"] = .integer(1)
        XCTAssertTrue(try AnyUIFoundationCapabilities(response: .object(response)).mobileManagedTokenGateway)
        response["mobileManagedTokenGateway"] = .bool(true)
        XCTAssertThrowsError(try AnyUIFoundationCapabilities(response: .object(response)))
    }

    func testRejectsAmbiguousTypesMultipartBodyAndUnknownWindow() {
        for (key, value) in [
            ("allowedTargetTypes", AnyJSON.array([.string("page"), .string("page")])),
            ("associationBlockDataset", .string("custom_part")),
            ("nativeClaimsMaxRecords", .integer(100_000)),
            ("documentTypePolicy", .string("client-type-guess")),
            ("propertyPresentationCollection", .string("unverified")),
            ("propertyPresentationHiddenProperty", .string("guessed"))
        ] {
            var response = complete; response[key] = value
            XCTAssertThrowsError(try AnyUIFoundationCapabilities(response: .object(response)))
        }
    }
}
