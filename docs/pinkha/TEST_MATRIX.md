# Pinkha on Anytype — Test Matrix

## 1. Unit Tests

| Area | Test Suite | Target | Key Scenarios |
|------|------------|--------|---------------|
| Space Manifest | `PinkhaSpaceManifestTests` | `PinkhaKitTests` | Serialization, forward-compatibility, default role resolution |
| Schema Migration | `PinkhaSchemaMigratorTests` | `PinkhaKitTests` | Version upgrades, missing fields fallback |
| Hierarchy Sibling Order | `PinkhaOrderRankTests` | `PinkhaKitTests` | Sparse rank generation, rebalance thresholds |
| Hierarchy Move & Cycle | `PinkhaCycleDetectionTests` | `PinkhaKitTests` | Self-parenting, direct cycle, deep cycle prevention |
| Torah Association Codecs | `TorahAssociationCodecTests` | `PinkhaKitTests` | Document & block association JSON round-trip |
| Text Direction Resolver | `PinkhaTextDirectionTests` | `PinkhaKitTests` | Pure Hebrew, pure English, mixed sentences, fallback |

## 2. Integration Tests

- **Bootstrap Idempotency**: Verify repeated bootstrap executions produce zero duplicated properties or types.
- **Sync Safety**: Verify manifest resolution across two independent clients.
- **Editor Invariants**: Typing, Enter, Backspace, autocorrect, and quote insertion without focus drops or keyboard flicker.
- **Unsigned Device IPA**: Verified via GitHub Actions on each phase.
