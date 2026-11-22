# Prepared original inline-file native qualification

## Result and scope

Twelve new top-level native controls passed, together with seven directly
affected pre-existing native commit-guard controls. This is an isolated,
native-only addition to the frozen prepared object/block v1 bundle. It
admits ordinary original inline payloads of 0–4095 bytes under a live ordinary
object. It leaves the public HTTP file capability at `0` and
`networkVerified` at `false`.

The original object/block qualification artifact is unchanged:
`95777bc294903b1bd5dede421a80af6e949a85e2d1e2de41d1e2f77a4d054ff0`.
Its 25 new controls plus one existing route control retain their original
source and evidence scope. They were not rerun or counted as new inline-file
controls. No any-sync or any-store patch was introduced.

## Source ownership

The additive source has nine SDK files and one Any test file. The only
modified pre-existing production file is `internal/commitguard/guard.go`.
The exact explicit path set, before/after Git blobs, SHA-256 hashes and
patch hashes are in the two adjacent source manifests. Read-only cached
upstream files are excluded from both patches.

The final native source census compares every Go source, `go.mod` and
`go.sum` in the isolated tested copy against the immutable object/block
copy. Any has one new test file; SDK has eight new files and the single
guard change. No other tracked native Go/module source was changed or
removed. The final census and native hashes are retained in the raw evidence
archive; candidate Apple composition has its own independent complete
overlay manifest.

## Passing controls and evidence

| Stage | Actual scope | Result |
| --- | --- | --- |
| 1, `job_0f371e5f400e` | Five real native-ledger controls: concurrent first reservation/reopen, cross-kind intent/stage isolation, immutable plan/spec/entity binding, injected checkpoint failure, strict native tier boundary | 5 passed |
| 1, same job | Four actual native-guard controls: durable append before updater, strict payload/class/mode rejection, final current ACL/rekey/revocation/cancellation, lost-ACK history recovery with current authority | 4 passed |
| 2, `job_f0a4ecce55d6` | First actual SDK file journey and oversize/changed-owner/carrier refusal | 2 passed on the then-current owner-read source; preserved unchanged |
| 2, same job | Five existing `TestPreparedRaw*` controls plus the existing actual ACL-final-fence and ACL-held-through-commit controls | 7 passed; source branches and scope retained |
| 3, `job_f89564411c63` | Additional real ordinary `Objects.Delete`/cascade while a prepared call waits for the native carrier lock, before the extra owner head re-read | 1 passed; no old failure was reproduced |
| 4, `job_28f86d9e646b` | All three actual SDK inline fixtures after adding the owner head re-read | 3 passed; final production qualification |

Stage 4's actual file journey took 1.49 seconds. It prepares a 4095-byte
binary payload, closes and reopens the real SDK/native and projection stores
at the root and row boundaries, and drives six concurrent commit callers.
The ordinary native `Files.Get` and `Files.Open` return the exact metadata
and plaintext stream; an independent SHA-256 check confirms the returned
bytes. The known native row is reused after another close/reopen. A second
zero-byte file uses the existing carrier and one row stage. Ordinary native
file deletion followed by retry does not resurrect it.

The final oversize/current-owner test took 0.80 seconds. Both 4096 and 4097
bytes refuse before reservation or append. Advancing owner properties,
advancing the payload carrier through ordinary Attach, and deleting the
owner refuse the pending envelope.

The final deletion-during-lock-wait control took 1.00 second. It uses a real
ordinary owner, an existing native payload carrier, a native held read
snapshot and ordinary `Objects.Delete`. It observes the real queued
deletion while the prepared call is blocked, releases the carrier lock,
and requires refusal with no new file. The old implementation also passed
this cascade because its carrier fence already rejected the exercised
deletion. The added owner re-read is an explicit read/lock completeness
improvement; this report does not call it a reproduced failing regression
or claim a separately exercised owner-only queued state.

## Exact main logs

| Log | SHA-256 |
| --- | --- |
| Stage 1 SDK new ledger/guard controls | `0a88a6bc0a00b0bf78ce6b4bc549c0892b50ae5f35a87c31e40fe4a7818b450b` |
| Stage 2 actual native SDK file controls | `1e6516ffee683a4d20cb843e9b850c1d52356b4bde1c6465f1b7f3f015476c78` |
| Stage 2 affected pre-existing guard controls | `4dac6891291f3a26bd134fade63f1ed26d7278d8ebe4478db71e0de6ff644400` |
| Stage 3 pre-correction deletion/cascade probe, passed | `563ac37ac3f196f1633deab1cc2e2f6ef26e19f17cd4d216a5a07f1ac6ce4c0a` |
| Stage 4 final actual native SDK file controls | `6f3d8f98436fbf1cd24e09b7b9071fe1811fa7c2d1e4d74f7cffe3b25950ed26` |

The final owner-route SHA-256 is
`66725d902f31d49f10b2666fc135ecb427edf969e714481963dcc40d09c72eb0`;
the final Any fixture SHA-256 is
`c9dfa9f627515313985e21ac654693a66d2d6402a0b7a2760ff0f378a590ec30`.
Stage 1's ledger, inline guard and existing guard sources are byte-identical
to the final source; only their directly affected existing guard controls
were rerun in stage 2. Stage 4 requalifies the changed owner route through
the actual SDK. Packages reported as `[no tests to run]` are compilation
observations only and are not included in the control counts.

## Preserved attempt and toolchain details

The first Any attempt stopped before compilation because the isolated
`migration.inline.mod` contained two SDK replacements. The correction used
`go mod edit -modfile=migration.inline.mod -replace=...` to replace the
single SDK module mapping. This was build-only isolated configuration;
the production `go.mod` and frozen object/block source were unchanged.
The original failed log remains in evidence with SHA-256
`1530a380bf6ea31538817222d4b649bdc8061e3f066a737d0343f1ed310f78bc`.

Actual SDK controls used Go 1.26.5 on Linux amd64. Actual Any SDK integration
used Go 1.27.1 on Linux amd64, with the explicit isolated SDK module mapping.
Both builds used `GOTOOLCHAIN=local`, `GOMAXPROCS=4`, `-p4` and exact test
selectors. The raw evidence includes the module override, sums, toolchain
version receipts, job results, original logs and source censuses.

## Boundaries still open

The evidence proves orderly native SDK/database close/reopen, not an abrupt
OS-process kill or physical power-loss persistence. Checkpoint failure is
injected at the native checkpoint interface and must refuse preparation;
there is no additional storage-media fsync claim.

File network delivery, full-tier blobs and upload transport, variants,
derived owners, local file-status subscription publication, HTTP/Swift
file exposure, Apple runtime linkage, multi-version file compatibility and
whole-Space source snapshot consistency remain unqualified. The existing
archive planner must continue to refuse unsupported or incomplete plans
before target writes. This native slice does not complete MIG-01.
