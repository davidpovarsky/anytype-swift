import Foundation
import PinkhaAnyEngine
import PinkhaAnyIntegration

/// Exact original variant of one verified native Heart file. The draft is
/// inert; the enclosing complete source plan and current authorization still
/// control execution. Other variants require their own separately bound items.
public struct AnyHeartNativeFileBinding: Sendable {
    public let sourceAccountID: String
    public let sourceSpaceID: String
    public let captureManifestSHA256: String
    public let sourceWitnessSHA256: String
    public let fileID: String
    public let variantPath: String
    public let payloadPath: String
    public let payloadSHA256: String
    public let size: Int64
    public let name: String
    public let mimeType: String
    public var permitsDestinationWrites: Bool { false }
    public var sourceKey: String {
        "heart-native-file:" + AnyContentDigest.sha256(AnyPreparedMigrationPlanBinding.material([
            "pinkha-heart-native-file-binding-v1", sourceSpaceID, fileID, variantPath
        ]))
    }
    public var reference: AnyDestinationReference { .mapped(sourceKey: sourceKey, slot: .fileID, encoding: .fileURI) }

    public func destinationItem(ownerSourceKey: String) throws -> AnyDestinationMigrationItem {
        guard AnyPreparedMigrationPlanBinding.validOpaque(ownerSourceKey, maximum: 4096) else {
            throw AnyHeartNativeDefinitionPlanError.invalidValue(fileID, "native file owner")
        }
        return .init(sourceKey: sourceKey, sourceObjectID: fileID,
            operation: .file(owner: .mapped(sourceKey: ownerSourceKey, slot: .objectID, encoding: .rawID),
                name: name, mime: mimeType, size: size, contentSHA256: payloadSHA256))
    }
}

extension AnyHeartNativeFileBinding {
    public init(bundle: AnyHeartNativeSpaceBundle, fileID: String) throws {
        let variants = bundle.fileVariants.filter { Data($0.fileID.utf8) == Data(fileID.utf8) && $0.isNativeOriginal }
        guard variants.count == 1, let original = variants.first else {
            throw AnyHeartNativeDefinitionPlanError.invalidValue(fileID, "one captured native original file required")
        }
        self.init(sourceAccountID: bundle.sourceAccountID, sourceSpaceID: bundle.sourceSpaceID,
            captureManifestSHA256: bundle.manifestSHA256, sourceWitnessSHA256: bundle.sourceWitnessSHA256,
            fileID: original.fileID, variantPath: original.variantPath,
            payloadPath: original.payload.path, payloadSHA256: original.payload.sha256,
            size: Int64(original.payload.byteCount), name: original.name, mimeType: original.mimeType)
    }
}
