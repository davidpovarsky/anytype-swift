# Actual generated RPC in a disposable native account — 18 November 2026

**PASS for the registered byte RPC inside the original four-process account lifecycle.** This is not acceptance of two separate native/App clients, iOS, or full T2. The App capability remains **OFF**.

## Exact source and original evidence

- Fixture source: `38edcbf61131b3f34316a4c0323ddf86a2a4d99c`.
- Source integration: `d4ed32f3aee33afe190acebb5ded5596acc87cd9`.
- Actual workflow source: `a16bdc5de003aff97209c83d5fbc6a5934c5e873`.
- [Original run 44260628655, attempt 1](https://github.com/davidpovarsky/anytype-swift/actions/runs/44260628655).
- Artifact `Pinkha-T2-Account-RPC-44260628655-1`, ID `14408891304`, 59,192 bytes.
- Original ZIP SHA-256: `9cd9bffb074b9bce6a96791c1392410df83f4b99df1092c3132169517ada80e1`.
- Native receipt finished at `2026-11-18T07:52:19.091478+00:00`; GitHub completed the run at `07:52:39 UTC`.

The original ZIP digest was checked against GitHub metadata. Its raw reports, native logs, exports and generation receipt were examined in connected-host memory. The raw artifact remains on GitHub; this directory contains only sanitized verification metadata.

## Observed native execution

| Phase | Native runtime | Actual PID | Named native result |
| --- | --- | ---: | --- |
| new-create | r14 + private registry + generated RPC | 9688 | PASS |
| new-reopen | Same new binary | 9709 | PASS |
| legacy-edit | r14, without private registry/RPC | 9722 | PASS |
| new-recover | Same original new binary | 9735 | PASS |

There were **two distinct actual ELF binaries, four distinct processes and nonces, four named PASS results, zero native failures and zero native skips**. The Linux controller suite separately passed **23 tests with no skips**.

All four processes used the same original synthetic account, Space, document, block and private root. The immutable state hash is `b78a750da2b6ae965eb26a834c8e2e1c16a6cc825d88c1e7d3a12268e0e97338`. The original signed root and sole operation bytes, canonical claim, and head remained intact. The legacy runtime edited the ordinary document, preserved the unknown private history, and reported the new handler as unsupported.

## What the generated RPC proved

The new runtime invoked the actual generated gomobile byte entry points, with real protobuf serialization and responses. Missing history and rejected version/kind/target/payload requests left the private root absent before the first valid wire append. A real native account supplied the author identity; the request supplied no author or root.

The later new processes read the original operation before replay. Exact retry returned the existing claim without a new signed change. A different-payload collision returned a non-NULL RPC error **and the complete collision receipt**, retaining the original state. The snapshot explicitly reported `LOCAL_VERIFIED_TREE`; it did not claim a remote acknowledgement.

After target removal, Space cleanup and actual AccountStop, the generated read/append boundary rejected access without a stale snapshot or receipt. The unchanged typed/native checks also ran.

## Search, export and lifecycle checks remained strict

Across the four phases, **eight actual private ObjectExport calls** (JSON and Protobuf in each phase) returned native error code **1** and **zero Result bytes**, whose SHA-256 was the empty-content digest. These facts were checked directly in the original native diagnostics, not inferred from a top-level success status.

The **eight ordinary JSON/Protobuf export files** existed, matched their reported hashes, and contained no private journal token, private root, operation ID or claim ID. The native fixture decoded those exports and checked the ordinary document and original block. Ordinary fulltext remained a positive control; the private root remained absent from search and rejected by normal Show.

Final target deletion preserved orphaned private history. The existing Space cleanup removed both the native Space and provider-owned projection, followed by verified AccountStop in every phase.

The original controller scanned account key and mnemonic needles before publication. This review independently verified the exact evidence allowlist and every uploaded account-file digest. No account-key, mnemonic inventory, database, cache or generated workspace was uploaded.

## Source and generation verification

The same-run generation receipt was bound to workflow source, run ID and attempt. Its **54 registry/RPC/generated source hashes** matched the exact Git inventories and overlays. The legacy binary used **35 r14 paths**, and the new binary used their disjoint **89-path composition**. Baseline fixture hashes and the new helper/patch hashes matched the exact integration source.

All three generated outputs matched the already proven pinned generator outputs. The eight protobuf input hashes and compiler identity matched the independently verified original RPC artifact `14405574920` from [run 44255980141](https://github.com/davidpovarsky/anytype-swift/actions/runs/44255980141). The generator used protoc 3.21.12 and the reviewed gogo replacement; Go 1.26.5, the exact musl image, Tantivy archive and genproto module checks remained unchanged.

The machine-readable file includes the original receipt/log/export hashes, binary hashes, phase-specific wire observations and source checks.

## Remaining acceptance and next concrete step

Two independent native stores and peers have not yet exchanged this account's history in this lane. The existing two-process SyncTree proof and this four-process account/RPC proof remain separate. App binding, iOS and full T2 are open.

An independent **read-only review of the public, unauthenticated official Heart source at the exact pin** confirmed the feasible next route: a fresh second root uses WalletRecover with the same account key, followed by AccountSelect; Heart creates its missing device key and distinct PeerID itself. AccountRecover is not an extra prerequisite. LocalOnly has no configured remote nodes and uses native LAN discovery/transport. Its cold startup can wait for a warm peer, so the next fixture must keep the first client alive, bound the byte call and cancel native startup/owned containers on timeout. This is a source-contract finding, not a new runtime PASS.

Official source references at `d98420b1113536afd08cde6de9a5816f6d27ffff`:

- [Wallet device identity](https://github.com/anyproto/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/core/wallet/wallet.go)
- [Cold AccountSelect](https://github.com/anyproto/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/core/application/account_select.go)
- [Native startup](https://github.com/anyproto/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/core/application/app_start.go)
- [Native local discovery](https://github.com/anyproto/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/space/spacecore/localdiscovery/localdiscovery.go)

No product capability, user data, release or deployment was changed by this proof.
