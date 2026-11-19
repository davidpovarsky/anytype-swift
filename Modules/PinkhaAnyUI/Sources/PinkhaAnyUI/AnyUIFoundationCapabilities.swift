
import Foundation
import PinkhaAnyEngine
import PinkhaAnyHost
import PinkhaAnyIntegration

public enum AnyUIActivationError: Error, Equatable, Sendable {
    case missingCapability(String)
    case unexpectedRuntimeContract
    case incompatibleSchema
    case wrongWorkspace
}

/// Validated against the custom runtime, not synthesized from client feature flags.
public struct AnyUIFoundationCapabilities: Sendable, Equatable {
    public let mobileManagedTokenGateway: Bool
    public let allowedTargetTypes: Set<String>
    public let maximumClaimRecords: Int
    public let maximumClaimBytes: Int
    public static let contract = "pinkha-torah-native-v1"

    public init(response: AnyJSON) throws {
        guard response["contract"]?.string == Self.contract,
              response["bundleId"]?.string == "pinkha/torah-native/v1",
              response["module"]?.string == "pinkha_torah_native",
              response["dataset"]?.string == "pinkha_torah_claims_v1",
              response["dataVersion"]?.string == "pinkha-torah-native-claims-v1",
              response["nativeSemanticPayload"]?.string == "canonical-associations-v2-single-record" else {
            throw AnyUIActivationError.unexpectedRuntimeContract
        }
        for name in ["nativeSignedClaims", "spaceWideOperationConflictDomain",
                     "currentACLCommitFence", "targetTreeCommitFence",
                     "nativeDocumentProperties", "nativeIndexedSourceQuery",
                     "nativeRelatedVersion", "conditionalBlockPatch",
                     "conditionalPropertiesSet", "conditionalBlockCurrentWriterFence", "currentWriterObjectCreate", "currentWriterBlockCreate", "nativeClaimsSnapshot", "nativeClaimsWatch", "nativeObjectClaimsSnapshot", "nativeObjectClaimsWatch",
                     "nativeDocumentTypePolicy", "nativeDocumentMembership",
                     "conditionalMembershipSet", "nativePropertyPresentation"] {
            guard response[name]?.integer == 1 else { throw AnyUIActivationError.missingCapability(name) }
        }
        guard response["documentTypePolicy"]?.string == "canonical-editor-module-v1",
              response["propertyPresentationCollection"]?.string == AnyNativePropertyStore.presentationCollectionID,
              response["propertyPresentationHiddenProperty"]?.string == AnyNativePropertyStore.hiddenPropertiesID,
              response["associationBlockDataset"]?.string == "editor_blocks",
              let types = response["allowedTargetTypes"]?.array,
              !types.isEmpty, types.count <= 128,
              types.allSatisfy({ $0.string?.isEmpty == false }),
              Set(types.compactMap(\.string)).count == types.count,
              let recordLimit = response["nativeClaimsMaxRecords"]?.integer,
              recordLimit == 10_000,
              let byteLimit = response["nativeClaimsMaxBytes"]?.integer,
              byteLimit == 16_777_216 else { throw AnyUIActivationError.incompatibleSchema }
        guard let gateway = response["mobileManagedTokenGateway"]?.integer, gateway == 0 || gateway == 1 else {
            throw AnyUIActivationError.missingCapability("mobileManagedTokenGateway")
        }
        self.mobileManagedTokenGateway = gateway == 1
        self.allowedTargetTypes = Set(types.compactMap(\.string))
        self.maximumClaimRecords = Int(recordLimit)
        self.maximumClaimBytes = Int(byteLimit)
    }

    public static func verify(client: AnyHTTPClient, session: AnyApplicationSession) async throws -> Self {
        guard client.expectedAccountID == session.workspace.accountID else {
            throw AnyUIActivationError.wrongWorkspace
        }
        return try await session.perform { lease in
            let response = try await client.requestJSON(method: "GET", path: ["v1", "pinkha", "capabilities"],
                                                         authorize: { try await lease.validate() })
            let result = try Self(response: response)
            try await lease.validate()
            return result
        }
    }
}
