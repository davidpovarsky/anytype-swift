# Native computed links: retained original graph and cold-process proof

This milestone adds an exact source-definition binding for Heart's computed
`links` and `backlinks` fields and a read-only Host adapter over the native
link index. It qualifies this changed adapter boundary. Complete C migration,
historical semantic admission, Apple UI presentation and global peer
completeness remain open.

## Changed behavior

`AnyHeartNativeComputedRelationBinding` keeps the captured protobuf and JSON
definition bytes, rejects altered source semantics, and selects one closed
read-only native provider. It creates no mutable SDK property shadow.

`AnyNativeComputedRelationStore` validates account, Space and process lease
before and after reading. It uses the native typed links adapter with complete
bounded responses; truncated native results are refused. Revoked sessions do
not deliver values. Native property-value references retain their existing
legacy `any://<objectID>` representation; link-index targets retain their
canonical `any://o/<spaceID>/<objectID>` representation.

The underlying Engine contracts are root Wave1 commits
`6fdcabeff7a39bc206ce250b069cc076a1d29895` (HTTP response authorization) and
`4416ef1515dba0149a03d9a2f8441015d77e9da0` (typed native link index).
The equivalent dependency cherry-picks on this isolated branch are
`b32f82b7f7bdd259a7f68fd19d480c07432d1a75` and
`75bfb53fa4573d13be9d9f4bc5e199b6725e6c66`.
Integrators should use one copy of each dependency.

## Actual new checks

- Four component methods passed, zero failures and zero skips. They include
  exact original source definitions, Codable identity validation and refusal
  of changed computed semantics. The existing 20 derived-property controls
  were not rerun.
- One new native method ran twice: an initial read and a separate cold
  process. Both passed using unchanged compiled Products and the same
  qualified native binary. There were zero prepared operations and zero
  conditional relation writes.
- The adapter returned the accepted outgoing relation, its backlink, exact
  property/declaring-Type identities and canonical target URI. A narrowed
  property query returned the same edge; the target's outgoing set was empty.
- Both native children inherited the OS outbound-denial seccomp policy and
  no-new-privileges setting. Positive TCP/UDP baseline controls ran first;
  denied controls returned EPERM. Native peer counts were zero. Both native
  groups and both test groups were positively absent at completion.
- The retained original account and accepted receipts stayed unchanged.
  Its 26-entry copied account inventory matched bytes and modes. No account
  initialization or Space creation occurred.
- The 1,594 qualified native source members, four original definition files
  and Swift source closure remained unchanged. Native minimum free space was
  2,822,668,288 bytes, above the unchanged 2 GiB floor.

## Exact test-source formatting join

After both successful runs, one terminal blank line after `#endif` was removed
from `AnyDestinationNativeGraphTests.swift` for the repository whitespace check.
`source-equivalence.json` retains the exact executed bytes and verifies that
the committed file plus that one newline is byte-identical. No executable
token or assertion changed. Original build/runtime source manifests remain
untouched; production Swift and runtime-controller hashes are identical.

## Exact receipts

| Scope | SHA-256 |
| --- | --- |
| Four-method component result | `71fdeb4fcfafdf1f9467960974ca6fd16aff381bbe8840c93edf3a801ba946c0` |
| Component log | `d03bfd783f7cd0e26385100c180bd78799c8b2853d2ca195ac3c0fb3febf908e` |
| Native runtime result | `b1473317fabd37b5e69a3da4eaf697eb9f72c3cc01363302f3d8a7ac1b3f8713` |
| Initial/cold graph comparison, byte-identical | `5eb354a6e4b899da2a5a9362baf692e84fdaa60ac23f81eab978bed1c291e58c` |
| Native binary | `1dc1803c656da2215760477dadd26bf0e829b6ee592e337db6fa0295a6ed9636` |

Private runtime roots remain:
`/var/lib/pinkha-w1-functional-migration-20261127/graph-bindings-attempt1`
and
`/var/lib/pinkha-w1-functional-migration-20261127/graph-native-attempt1`.
Private native logs and account material stay there; the public result retains
their hashes and custody assertions.

## Evidence reused without migration replay

The accepted 182 operations, 159 heads, 156 snapshots and 332 archive records
were not rerun. Their receipt remains
`f7f4a5b34465907c3285229a266a488229a92eb1c3a7c04c5b4cdd162ed1b32b`;
the original native graph/content comparison remains
`7c39a72aec3e9c87cef67ffabbe982cd76501f195d36aafd354bea13e5a71ac5`.
The coherent captured-source member audit remains
`68319ff3adca0da6191ce0a4df8ff9654bac6d5be745306922662da5d5454244`.

The family map in `docs/architecture/heart-native-type-families-20261127.md`
records the remaining exact native correspondences and blockers. This
milestone supplies the engine read contract to Wave2/Wave3 without changing
their applications, granting new authorization, or promoting archive
preservation to full functional migration.
