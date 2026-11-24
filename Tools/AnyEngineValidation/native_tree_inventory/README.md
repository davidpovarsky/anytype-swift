# Native tree identity inventory — bounded continuation

## Scope

This route compiles and runs only three new methods in Heart's
`./core/pinkha/localstorewitness` package. It uses actual native SpaceStorage,
native ownership capabilities, signed opaque native tree records, detached
read-transaction witnesses, and actual native head updates. It does not replay
Heart document semantics or claim whole-Space migration, account/session
authorization, history semantics, file completeness, or destination write
authority. The pre-existing FixtureOnlyAuthority census remains unchanged.

Selected methods:

- `TestNativeTreeInventoryBindsDetachedNativeHeads` — original root and heads,
  deep-copy isolation, six mismatched source-identity refusals, same checkpoint,
  changed native checkpoint refusal, and conservative public receipt.
- `TestNativeTreeInventoryRefusesMalformedNativeHeads` — unknown and duplicate
  heads, unknown deletion status, and retained deleted identities that cannot
  be admitted as live objects.
- `TestNativeTreeInventoryRefusesUnownedOrCorruptCapture` — missing ownership,
  fixture-only authority, changed witness digest, cancelled or absent context.

The first method has six subtests, the second has four, and the third has none.
All ten must execute and pass. No old C4 or other previously accepted method is
selected. Private fixtures, compiler logs, generated test main and binary are
retained under the existing private custody recipient.

## Exact source

Original source archive and compiler are admitted by the unchanged qualified
C4 helper. The complete 59,826-file original source census must pass first.
The existing exact-byte context correction binds Heart
`24dc6393b30e6d1d80ec28ff624060af9bb4327a` to
`256d3fd6cb4c2b0df67f67e01edfd8f9b76726f4`.

The new `source-delta-v1.json` then admits exactly two additive files from
Heart `d8e609b9faf2ea7307178676ebecfcd6da524159`. Both complete byte strings,
Git blob identities, lengths and modes must match. Any overwrite is refused.
The source directory is mounted read-only for compilation and execution, and
the admitted source stat census is rechecked afterward.

The qualified helper remains at
`../loaded_account_witness/portable/run_native.py`; its SHA-256 is pinned by
this controller. The original C4 controller, auditor, source bundle, manifests,
context delta, four-method receipts and custody recipient are not modified.

## Dispatcher contract

Intended central input value: `native-tree-inventory-arm64`.
Intended inline job name: `native-tree-inventory`.

- Runner: `ubuntu-24.04-arm`; genuine GitHub Actions at the immutable source SHA.
- Checkout this subtree plus
  `Tools/AnyEngineValidation/loaded_account_witness/portable`.
- Set `EXPECTED_SOURCE_SHA` to the actual `github.sha`.
- Supply existing `PINKHA_NATIVE_COMPILER_URL` and
  `PINKHA_NATIVE_SOURCE_URL` secrets. Refresh signed URLs from the same
  immutable private carrier assets immediately before dispatch.
- Run `python3 Tools/AnyEngineValidation/native_tree_inventory/run_native.py`.
- Upload `${{ runner.temp }}/pinkha-native-tree-inventory/public` even on
  failure. Suggested artifact: `native-tree-inventory-${{ github.run_id }}-${{ github.run_attempt }}`.
- Suggested job limit: 45 minutes; internal compile ceiling is 1,800 seconds,
  each native method ceiling is 240 seconds. Docker is restricted to 1 CPU,
  4 GiB, no network, a read-only root and explicitly scoped mounts.

A new reusable workflow reference is not required; the central repository
already uses its 50-reference budget.

## Public artifact

`public/result.json` uses schema `native-tree-inventory-portable-v1`.
Only `THREE_NATIVE_INVENTORY_METHODS_PASS` exits successfully; any source,
compiler, runtime, assertion, cleanup or custody failure remains `FAIL`.
It records the controller/run identities, exact source derivations, actual
generated main digest, actual ARM64 Go 1.26.5 binary digest, binary method
listing, and individual method audits. It explicitly leaves wider source
admission and migration flags false.

`public/private-evidence.cms` uses the original recipient and AES-256-GCM /
RSA-OAEP-SHA256 custody path. Source fixtures and raw binary/logs remain inside
that encrypted evidence. The receipt's custody readback starts pending until
the private recipient decrypts and independently verifies it.

## Current source preparation status

The two Go files were parsed/formatted by gofmt. This controller was parsed and
imported, and its source manifest, copied Git blobs, helper binding and method
selection were checked. Native compilation and execution are NOT_RUN until a
genuine published Actions run supplies their receipts.
