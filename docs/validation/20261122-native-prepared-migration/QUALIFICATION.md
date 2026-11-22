# Prepared migration candidate: qualified native slice

The isolated native object/root/bootstrap and one editor-block implementation has **25 new focused top-level controls passing**, plus **one preserved ordinary v10 create-route regression passing**. This is a source candidate for integration, not a published runtime or full MIG-01 acceptance. File capability remains `0`; `networkVerified` remains `false`.

## Apply the exact source composition

1. Any upstream `88fae2e5ae7d0f46d6707567a3123081faa8de9a`, then the retained v10 authorized-operation patch SHA256 `64f7da56fb4f30b78baae8afe850fa0429dccde4b977bd3c7e30fc03d26dfa5e`, then `prepared-migration-v1-any-additive.patch`.
2. SDK upstream `854df54cdadd76006ae823cbd1b1d923138356d0`, then the retained v9 SDK property-receipts patch SHA256 `b9021dc305ab150501e86243270df73f3d6a27490ec343cf6252e5a214f5a461`, then `prepared-migration-v1-sdk-additive.patch`.
3. Resolve Any against that exact SDK source. The native qualification used a separate build-only `migration.prepared.mod`; the original Any `go.mod` remains unchanged. No any-sync or any-store patch is present.

| Additive patch | Files | SHA256 |
|---|---:|---|
| `prepared-migration-v1-sdk-additive.patch` | 17 | `4b4d45010374a52d928c7ed5de9eb025e164062172e3021fbf818c6b24221fc6` |
| `prepared-migration-v1-any-additive.patch` | 9 | `08b8253e755efedc09ae9123394acb8a3022aab81b94109aacfc318d68fb1249` |

The adjacent `*-source.json` files record upstream pins, retained overlay identities and every modified/new file's before/after Git blob and exact SHA256. Both additive patches passed `git diff --check`, applied cleanly to isolated copies of their exact sparse overlay baselines, and reproduced all 26 qualified file hashes. This packaging check did not modify a production checkout.

`prepared-migration-v1-composed-source.json` additionally covers all retained overlay files plus this addition: 61 Any and 53 SDK paths. The retained Any manifest originally recorded Windows working-tree SHA256 values; all 52 unchanged Any Git blobs matched the native LF source exactly. Their original worktree hashes are retained as `baseWorktreeSHA256`, separately from the actual Linux build-byte `sha256`. No source was edited to resolve that metadata distinction.

Final native-worktree verification `job_1d1fb0dece3a` checked all 61 Any and 53 SDK paths against both the composed SHA256 and Git blob identities: zero mismatches. Its result is retained in `../evidence/composed-source-verification-job.json`.

## What the candidate establishes

The exact signed root or change bytes, content-addressed IDs, native operation fingerprint and immutable plan/entity scope are reserved in the actual private SDK projection database before the native mutation. A full checkpoint must succeed before append, and commit repeats that barrier. The journal is never wrapped around native tree/index publication in an outer transaction.

Current writer authority is required for preparation, status, commit and idempotent recovery. The final native append rechecks current ACL/read-key authority. The prepared envelope must still match native definition heads, predecessor heads, parent/schema policy, signed author/CID/timestamp and independently decrypted operation payload. A different valid signed operation cannot substitute for the reserved payload. Production deferred-updater configuration is required so projection callbacks follow durable native storage.

An object advances one durable stage per HTTP POST: root-prepared → root-committed → bootstrap-prepared → complete. The fingerprint, source spec SHA, plan and object ID remain stable. The root CID remains stable through root commit; the bootstrap CID remains stable from its reservation through completion. A block has one prepared → complete transition. Status reconciles exact native raw history and current materialization; it never signs replacement bytes.

The private ledger atomically binds a full `planSHA256` to the logical plan and one intent ID to `(planId, sourceKey, kind)`. Changed plans/specs, alternate intent IDs for an existing entity, replaced stores and cross-Space reuse refuse. Modified or deleted committed records halt rather than resurrecting content. An unavailable purged tree is conservatively obsolete. The HTTP boundary rejects duplicate/unknown/case-aliased fields, trailing JSON, excessive depth, invalid UTF-8/base64/digests and JSON numbers that lose value in the native float64 representation.

## Executed evidence and reuse

| Final evidence | New top-level controls | Result and scope |
|---|---:|---|
| Stage6 `stage6-journal.log` | 9 | Actual AnyStore v2 restart, reservation concurrency, collision/rollback, scope, checkpoint failure and numeric precision. Test envelopes are opaque strings; this layer does not prove signatures. |
| Stage6 `stage6-recovery_spec.log` | 1 | Original JSON number tokens survive native spec recovery. |
| Stage7 `stage7-append.log` | 10 | Actual signed native ACL/storage/encrypted append, deferred updater, current ACL, revoked writer, lost ACK, concurrency, deleted/modified/obsolete and valid-signed-payload substitution controls. |
| Stage7 `stage7-production_and_peer.log` | 2 | Actual SDK close/reopen through all object/block stages (2.42 s); actual two-store local P2P delivery and receiver readback (1.37 s). |
| Stage7 `stage7-http_and_existing_create.log` | 2 | Strict exact-spec parser/digest controls. Existing ordinary-route test skipped here because its nodeconf fixture was absent. |
| Stage8 `stage8-http_native.log` | 1 | Real HTTP/Echo route → production SDK object stages → ordinary readback → one block → exact retry and status (0.84 s). |
| Stage8 same log | 0 new; 1 existing | Preserved v10 ordinary current-writer object/block create route really executed and passed (0.99 s). |

Unique total: **25 new**, **1 existing**, **0 final selected skips**. Subtests are not counted as separate top-level controls. Editor package compilation is not counted as a test. The unchanged stage6 ledger/spec evidence was reused; only affected signed-append/production/peer controls were requalified after the final payload-binding check. The added stage8 HTTP fixture changed only its test source, not product code.

Raw logs are in `../evidence/raw/`; their hashes are in `../evidence/unit-raw-manifest.json` and `../evidence/native-raw-manifest.json`. Full job/result receipts are retained in `../evidence/stage6-*`, `stage7-*` and `stage8-*`. Source file hashes are in `../evidence/final-tested-source-manifest.json`.

| Job | Meaning |
|---|---|
| `job_b210e3c6ff01` | Initial exact retained-source check: 54 Any + 41 SDK blobs, zero mismatch. |
| `job_79ae6524cb75` | Stage6 ledger/spec and initial native qualification. |
| `job_be5a39ce0777` | Final signed-payload-bound product qualification. |
| `job_df06372ee80f` | Final real HTTP new + retained route qualification. |

The environment was Linux/WSL Ubuntu on the isolated host workspace. SDK controls used official Go 1.26.5; the actual Any native/HTTP fixtures used official Go 1.27.1 because its pinned module requires that version. Download SHA256 values: 1.26.5 `5c2c3b16caefa1d968a94c1daca04a7ca301a496d9b086e17ad77bb81393f053`; 1.27.1 `63d339f0da5ab53635a56f2490a7984dfe12dfcff22ad749f63edaf590168445`. `GOTOOLCHAIN=local`, `GOMAXPROCS=4`, package parallelism 4. The exact separate Any modfile is preserved with the raw evidence.

The stage8 original-server fixture used a temporary node configuration derived from the checked-in local fixture, with all endpoints rewritten to an unreachable loopback port. It contained no staging-service credentials. Its hash and removal are recorded in the receipt; it was removed after testing. The new production SDK/peer fixtures use their checked-in explicit local node configuration.

## Historical outcomes are retained

Stage4 Any HTTP compilation was blocked by Go 1.26.5 being older than the pinned Any requirement. Stage5 exposed a revoked-writer error-ordering failure, then fresh Go 1.27.1 native/HTTP compilation exceeded its bounded initial timeouts. The writer check was moved before envelope inspection, compilation completed with the cached exact toolchain, and the affected tests were explicitly requalified. The stage7 ordinary-route SKIP is not relabeled; stage8 is the separate actual pass. See earlier job receipts for the original failures/timeouts.

## Limits and remaining gates

Clean SDK close/reopen is proven; abrupt OS-process kill and physical-media/power-loss survival were not tested. The native full checkpoint implementation synchronizes its WAL and fully backfilled database, but the receipt alone is not a power-loss certification. Injected checkpoint failure proves no native append begins through this route.

The peer fixture runs two real SDK instances with independent initially empty stores and distinct device keys in one OS process. Discovery is virtual; actual peer transport is loopback, and coordinator/node endpoints are unreachable. The receiver uses ordinary native read/history APIs and never calls the migration API. That is a source/controller observation, not a global native append counter: incoming replication necessarily writes receiver storage. WAN/coordinator, real mDNS, separate processes, mixed versions, cross-account ACL propagation, Apple and physical-device behavior remain separate gates.

This candidate supports only ordinary object root/bootstrap and six admitted editor block semantic types. It does not claim template/meta-Type creation, all schemas/markup, file payloads, complete Heart archive conversion, coherent whole-Space snapshots, reviewed mapping completeness, or full migration acceptance. MIG-01 remains under Any C Asana task `1220709844846577`. Publication, Apple producer/consumer qualification and final acceptance belong to the integrating root task.
