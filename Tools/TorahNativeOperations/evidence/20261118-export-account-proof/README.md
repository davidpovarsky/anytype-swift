# Verified native export and account lifecycle proof ? 2026-11-18

Both runs used exact App source `e7bb02742cb188cda1d5b44a8700b51fa2930421`, pinned Heart `d98420b1113536afd08cde6de9a5816f6d27ffff`, native patch `4d470b31854ae2af3360676a1dabb06d60207ed2d4afddabad412bdc35adebc3` and inventory `be2805bc76e87a6fb96b4b3d40794c677e1620e2e23f6a33a68d97720f433637`.

## Component and registry

[Run 44245133433](https://github.com/davidpovarsky/anytype-swift/actions/runs/44245133433) completed SUCCESS.

- Registry: 22 top-level + 36 subcases = **58 PASS, 0 FAIL, 0 SKIP**. All 19 terminal export-related cases passed, including both getter variants, scoped context, private single exports, list and Collect.
- Component: 23 top-level + 45 subcases = **68 PASS, 0 FAIL, 2 helper SKIP**. The skipped top-level helpers are `TestNativeTreeProcessHelper` and `TestCommittedProcessExitHelper`. Isolated loopback transport proof is not two App clients.
- Terminal counts were recomputed from raw Go JSON, not copied from a job badge. ZIP SHA-256, receipt/source identities, package failures and exact patch/inventory hashes were independently checked.
- Exact artifact IDs, hashes, test names and bounded claims are in `native-tests.json`.

## Same-account private history lifecycle

[Run 44245137022](https://github.com/davidpovarsky/anytype-swift/actions/runs/44245137022) completed SUCCESS. Artifact **14401512374**, SHA-256 `f196240f6d4f5ad115e51564267957590852db666ee27e8ad80ad3f02a41c37e`.

Two distinct native binaries executed four actual passing test processes:

| Phase | PID | Native runtime |
| --- | ---: | --- |
| new-create | 16036 | r14 + private T2 registration |
| new-reopen | 16061 | r14 + private T2 registration |
| legacy-edit | 16078 | unchanged r14 |
| new-recover | 16093 | r14 + private T2 registration |

All phases retained the same original disposable account, account root, Space, document, block and private root. Each used a distinct nonce. The original state file, signed root plus one operation, raw change hashes and one head were unchanged. The old runtime rejected the unknown private type while preserving its bytes. Its ordinary document edit survived new-runtime recovery. Fixture source hashes were checked against the exact Git source used by CI.

Public search omitted both the private root and private payload; private ObjectShow was rejected. Every private ObjectExport call in both JSON and Protobuf returned code 1, empty Result and the SHA-256 of empty bytes; report status FAILED, succeed 0 and one object error were recorded. Eight real ordinary document exports were saved and checked. Their JSON snapshots retain the real block and expected document name; no private root, operation ID or claim identity appears in either export format.

The final phase deleted the target block, verified that the journal remains, then deleted the disposable Space and observed cleanup of the native Space store and projection database. AccountStop and AppShutdown completed in all four phases. The evidence-copy secret scan passed and no account key or mnemonic was uploaded.

This is **same-account private-history lifecycle and old-client preservation acceptance**. It is not simultaneous two-client replication, iOS acceptance, generated RPC acceptance, or the successful typed-handler path added by the following fixture change. App capability remains OFF; full T2 stays open.

## Preservation and prior failure

Raw ZIPs, logs, snapshots and exports remain in GitHub artifacts. They were parsed in memory on the connected host; this directory contains only sanitized verification metadata, hashes and explicit scope. `account-lifecycle.json` records the independently checked result.

The prior account run 44237407166 failed on a private export Error.NULL assertion before Result was recorded. It proved neither leakage nor correct omission. That failure and its immutable hashes remain in `../20261118-account-export-boundary/`. The production export guard was added without relaxing the original rejection or empty-result assertions. This passing run provides the missing actual native export evidence.
