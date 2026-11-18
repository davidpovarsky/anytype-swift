# Generated RPC account lifecycle — source stage

This lane extends the proven four-process disposable account lifecycle through the actual generated `PinkhaTorahOperationsAppend` and `PinkhaTorahOperationsReadTarget` byte functions. It uses two independently built native binaries in the original order: new-create, new-reopen, legacy-edit, new-recover. It does not enable the App capability or claim two synchronized App clients.

## Scope and isolation

The common account fixture and the legacy fixture remain byte-identical. The legacy binary receives only the immutable r14 native patch and those two original fixtures. It never receives the new RPC schema, mapper, generated bindings or account-wire helper. It retains its explicit unsupported marker and must preserve the original signed private history while making the same ordinary document edit.

Only the new binary receives a separately inventoried 64-line fixture patch plus one new helper. The patch selects actual wire creation of the first and only private operation, adds wire read/retry/collision checks before typed replay on reopen, and adds wire target/Space/AccountStop denials. It keeps the original typed/direct factory/history checks and accurately records that initial creation was through RPC. No claim of typed creation is relabelled as wire acceptance.

Before the first valid wire append, the helper observes absence of the private root after each read/rejected call: no local history, absent/unknown protocol version, unspecified/unknown Kind, missing block and empty payload. A valid append must create the same canonical per-Space root and one actual signed change. Reopened reads must retain the native account-derived author, exact canonical bytes, claim ID, signed head, local watermark and explicit LOCAL_VERIFIED_TREE scope. Collision has a non-NULL RPC error while retaining its complete receipt; retry and collision cannot add another signed change. Deleted targets, deleted Spaces and stopped accounts cannot return cached snapshots or accept an operation.

## Exact composition and evidence

The existing pinned generator runs on the host and produces a receipt for the same source SHA, workflow run ID and attempt. The new lane accepts only the three exact generated-file hashes already proved by run 44255980141, from the unchanged RPC inventory. It verifies the registry/RPC composition before applying r14 and rejects any path overlap, including new native overlay paths. The existing Go/musl/Tantivy/genproto closure is preserved.

The baseline controller receives only two explicit extension parameters with unchanged defaults: an exact expected runtime observation in `validate_phase`, and a phase validator in `run_sequence`. The RPC wrapper constructs the entire expected observation from the known contract and original state. Source, account identity, PID/nonce, private history, signed heads, ordinary edit, search, strict exports, native shutdown, target/Space cleanup and RPC-count checks still run. Secret scanning and the evidence allowlist remain the existing implementations; private keys, mnemonic, account stores, generated source and build/work/cache directories are not uploaded.

Both source-specific ELF binaries retain the existing native runtime/fixture identities. Only the new binary also contains the linked RPC schema inventory and generated endpoint symbols. Original fixture hashes, transformed fixture hashes, binary hashes and source hashes are verified before and after execution. Every native phase must produce its exact named PASS and same original account/Space/doc/block/root identity; a zero exit alone is insufficient.

## Source validation

The new Go helper was parsed/formatted with the existing gofmt executable over stdin; no Windows build or toolchain hydration occurred. Six new Python rejection/cancellation controls and all 17 existing baseline controls passed on Linux (23 PASS, no skips). They prove that correct wire metadata cannot hide damaged baseline history, identity, exports, cleanup or shutdown; missing/wrong wire fields and foreign generation receipts are rejected. A real SIGTERM through the account-wire command path produces CANCELLED/finished_at and leaves account-wire acceptance NOT_RUN.

The generated protocol/component proof from run 44255980141 and typed-account proof from 44247736314 remain separate. This new account-wire lane is **NOT_RUN** until executed on its own exact source. App capability remains **OFF**; two App clients, iOS and full T2 remain NOT_RUN.
