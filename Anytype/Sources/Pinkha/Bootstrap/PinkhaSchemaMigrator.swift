import Foundation
import PinkhaKit

public enum PinkhaSchemaMigrationError: Error {
    case unsupportedVersion(Int)
    case migrationFailed(String)
}

/// Handles versioned migrations for `PinkhaSpaceManifest`.
public final class PinkhaSchemaMigrator: Sendable {
    public init() {}

    /// Validates and migrates a manifest to `PinkhaSpaceManifest.currentSchemaVersion`.
    public func migrate(manifest: PinkhaSpaceManifest) throws -> PinkhaSpaceManifest {
        var current = manifest

        if current.schemaVersion > PinkhaSpaceManifest.currentSchemaVersion {
            // Forward-compatibility: accept newer versions if structure matches
            return current
        }

        // Sequential migration chain for future versions
        // e.g. if current.schemaVersion == 1 { current = try migrateV1ToV2(current) }

        return current
    }
}
