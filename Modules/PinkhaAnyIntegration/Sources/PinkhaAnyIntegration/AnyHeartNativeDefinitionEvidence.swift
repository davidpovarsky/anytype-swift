import Foundation
import PinkhaAnyEngine

/// Definition provenance for one fully verified captured bundle. Neither case
/// grants a source session, destination lease or permission to execute a plan.
/// A directly captured complete census is never represented as recovery.
public enum AnyHeartNativeDefinitionEvidence: Sendable {
    public enum Kind: String, Sendable {
        case capturedComplete = "captured-complete"
        case recoveredOriginal = "recovered-original"
    }
    case capturedComplete
    case recoveredOriginal(AnyHeartNativeRecoveredDefinitions)

    public var kind: Kind {
        switch self {
        case .capturedComplete: .capturedComplete
        case .recoveredOriginal: .recoveredOriginal
        }
    }
    public var recoveredDefinitions: AnyHeartNativeRecoveredDefinitions? {
        if case .recoveredOriginal(let value) = self { return value }
        return nil
    }
    public var recoveredManifestSHA256: String? { recoveredDefinitions?.manifestSHA256 }

    /// The containing immutable capture supplies descriptor provenance. The
    /// exact native producer exports this closed, ordered census, including an
    /// explicit null/empty declaration when it used no compiled descriptors.
    public func catalog(bundle: AnyHeartNativeSpaceBundle) throws -> AnyHeartNativeDefinitionCatalog {
        switch self {
        case .recoveredOriginal(let recovered):
            // Keep the historical nonempty-missing-set validation unchanged.
            return try .init(bundle: bundle, recoveredDefinitions: recovered)
        case .capturedComplete:
            let used = bundle.bundledDefinitionsUsed.map { Data($0.utf8) }
            let captured = bundle.bundledDefinitions.map { Data($0.identity.utf8) }
            guard bundle.rawManifest["BundledDefinitions"] != nil,
                  used == captured, Set(used).count == used.count,
                  captured == captured.sorted(by: { $0.lexicographicallyPrecedes($1) }),
                  !bundle.issues.contains(where: {
                      $0.code == "compiled-definition-descriptors-not-captured"
                  }) else { throw AnyHeartNativePreservationError.binding }
            return try .init(bundle: bundle)
        }
    }
}
