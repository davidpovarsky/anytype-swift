# Pinkha on Anytype — Test Matrix

## 1. Unit Tests

| Area | Test Suite | Target | Key Scenarios |
|------|------------|--------|---------------|
| Space Manifest | `PinkhaSpaceManifestTests` | `PinkhaKitTests` | Serialization, forward-compatibility, default role resolution |
| Schema Migration | `PinkhaSchemaMigratorTests` | `PinkhaKitTests` | Version upgrades, missing fields fallback |
| Hierarchy Engine | `PinkhaHierarchyTests` | `PinkhaKitTests` | Empty hierarchy, root nodes, nested tree, depth > 3, deterministic order, missing order fallback, append rank, midpoint insertion, dense rank rebalancing, valid reparent, move to root, self-parent rejection, direct cycle rejection, deep cycle rejection, subtree independence, safe folder deletion (empty destination, existing siblings, order preservation, nested grandparent), pathString disambiguation, large hierarchy scalability (>1000 items, 2550 objects), root writing document append ordering, mixed sibling reordering |
| Hierarchy Reconciliation | `PinkhaHierarchyReconciliationTests` | `PinkhaKitTests` | Exact real-device stale subscription race, multiple pending creations, optimistic mutations (rename/order/move), duplicate ID deduplication, optimistic writing document creation |
| Torah Association Codecs | `TorahAssociationCodecTests` | `PinkhaKitTests` | Document & block association JSON round-trip |
| Text Direction Resolver | `PinkhaTextDirectionTests` | `PinkhaKitTests` | Pure Hebrew, pure English, mixed sentences, fallback |
| Localization Suite | `LocTests` | `LocTests` | Localized string catalog resolution and accessor correctness |

> **Current Test Count**: 54 unit tests across 4 suites in `PinkhaKitTests` + 1 test in `LocTests`, all passing (0.29s).

## 2. Integration Tests

- **Bootstrap Idempotency**: Verify repeated bootstrap executions produce zero duplicated properties or types.
- **Sync Safety**: Verify manifest resolution across two independent clients.
- **Editor Invariants**: Typing, Enter, Backspace, autocorrect, and quote insertion without focus drops or keyboard flicker.
- **Unsigned Device IPA**: Verified via GitHub Actions on each phase.
