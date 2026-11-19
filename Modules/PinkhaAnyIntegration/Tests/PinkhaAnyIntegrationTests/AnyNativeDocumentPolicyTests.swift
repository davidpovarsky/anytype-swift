import Foundation
import Testing
import PinkhaKit
import PinkhaAnyEngine
@testable import PinkhaAnyIntegration

@Suite("Explicit current native document definition policy")
struct AnyNativeDocumentPolicyTests {
    private let workspace = try! AnyTorahWorkspace(accountID: "account", spaceID: "space")
    private func proof(type: String = "custom-editor", eligible: Bool = true,
                       writable: Bool = true) -> AnyJSON {
        .object(["contract": .string("pinkha-torah-native-v1"), "version": .integer(1),
            "policy": .string("canonical-editor-module-v1"), "spaceId": .string("space"),
            "objectId": .string("document"), "typeId": .string(type), "eligible": .bool(eligible),
            "canonicalEditorDataset": .string("editor_blocks"), "collections": .array([]),
            "canWrite": .bool(writable), "readiness": .object(["version": .integer(1),
                "state": .string("ready-local-snapshot"), "generation": .string(String(repeating: "a", count: 64))])])
    }
    private func row(type: String = "custom-editor") -> AnyJSON {
        .object(["id": .string("document"), "spaceId": .string("space"),
                 "any": .object(["type": .string(type), "name": .string("מסמך")])])
    }

    @Test func customDocumentUsesNativeProofWithoutBroadeningLegacyAllowlist() throws {
        let native = try AnyNativeDocumentTargetProof(response: proof(), workspace: workspace, objectID: "document")
        #expect(native.typeID == "custom-editor")
        try native.requireMatchingRecord(row())
        #expect(throws: TorahAssociationRepositoryError.targetNotFound) {
            try AnyHTTPTorahTargetAccess.validateObject(
                .object(["objectId": .string("document"), "record": row()]),
                target: .object(objectId: "document"), workspace: workspace,
                allowedTypeIDs: ["page"], excludedCollectionIDs: ["bin", "template"])
        }
    }

    @Test func nativeReadPermissionCannotAuthorizeAWrite() throws {
        let raw = proof(writable: false)
        #expect(try !AnyNativeDocumentTargetProof(response: raw, workspace: workspace,
                                                 objectID: "document").canWrite)
        #expect(throws: TorahAssociationRepositoryError.permissionDenied) {
            try AnyNativeDocumentTargetProof(response: raw, workspace: workspace,
                                              objectID: "document", intent: .write)
        }
    }

    @Test func foreignScopeAndIncompleteOrBooleanVersionsFailClosed() throws {
        for field in ["spaceId", "objectId", "version", "readiness"] {
            var raw = proof().object!
            switch field {
            case "spaceId": raw[field] = .string("another-space")
            case "objectId": raw[field] = .string("another-object")
            case "version": raw[field] = .bool(true)
            default: raw[field] = .object(["version": .integer(1), "state": .string("incomplete"),
                                          "generation": .string(String(repeating: "a", count: 64))])
            }
            #expect(throws: AnyNativeDocumentPolicyError.self) {
                try AnyNativeDocumentTargetProof(response: .object(raw), workspace: workspace, objectID: "document")
            }
        }
    }

    @Test func metadataMustStillMatchTheProvedNativeTypeAndCollections() throws {
        let native = try AnyNativeDocumentTargetProof(response: proof(), workspace: workspace, objectID: "document")
        #expect(throws: AnyNativeDocumentPolicyError.dependenciesChanged) {
            try native.requireMatchingRecord(row(type: "changed-type"))
        }
        var modified = row().object!
        modified["any"] = .object(["type": .string("custom-editor"), "collections": .array([.string("later")])])
        #expect(throws: AnyNativeDocumentPolicyError.dependenciesChanged) {
            try native.requireMatchingRecord(.object(modified))
        }
    }

    @Test func ineligibleCatalogTypeNeverBecomesAnEligibleDocument() throws {
        let raw = proof(eligible: false)
        let type = try AnyNativeDocumentTypeProof(response: raw, workspace: workspace, typeID: "custom-editor")
        #expect(!type.eligible)
        #expect(throws: AnyNativeDocumentPolicyError.self) {
            try AnyNativeDocumentTargetProof(response: raw, workspace: workspace, objectID: "document")
        }
    }

    @Test func guardedPolicyCannotBeAppliedToAnUnprovedEditorDataset() throws {
        let client = try AnyHTTPClient(baseURL: URL(string: "http://127.0.0.1:1")!, expectedAccountID: "account")
        #expect(throws: AnyEngineError.self) {
            try AnyHTTPTorahTargetAccess(client: client, workspace: workspace, allowedTypeIDs: ["page"],
                editorDataset: "another_editor", documentTypePolicy: .nativeCanonicalEditorV1)
        }
        _ = try AnyHTTPTorahTargetAccess(client: client, workspace: workspace, allowedTypeIDs: ["page"],
            editorDataset: "another_editor", documentTypePolicy: .explicitTypeAllowlist)
    }
}
