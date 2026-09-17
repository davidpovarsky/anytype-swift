import Foundation

/// Handles versioned migrations for `PinkhaSpaceManifest`.
public final class PinkhaSchemaMigrator: Sendable {
    public init() {}

    /// Validates and migrates a manifest to `PinkhaSpaceManifest.currentSchemaVersion`.
    /// Throws `PinkhaSchemaMigrationError.unsupportedVersion` if manifest schemaVersion > current.
    public func migrate(manifest: PinkhaSpaceManifest) throws -> PinkhaSpaceManifest {
        if manifest.schemaVersion > PinkhaSpaceManifest.currentSchemaVersion {
            throw PinkhaSchemaMigrationError.unsupportedVersion(manifest.schemaVersion)
        }

        let current = manifest

        // Sequential future migrations:
        // if current.schemaVersion == 1 { current = try migrateV1ToV2(current) }

        return current
    }
}
