# Files queue: preserve an acknowledged retry during active work

**Reviewed source only. No formatter, compiler, component test, native process, account, or cloud request has run for this carrier.**

This isolated carrier adds a correction and six meaningful controls for the existing Files background queue. It is a normal additive child of native64 source composition commit `412d8e77e54ddd4c8f138643d4d4bab18c684aec`. It changes no active application source, execution controller, or published native64 map. [ADOPTION_MAP.json](ADOPTION_MAP.json) describes the exact two prospective source actions; it does not apply them.

## Concrete defect and correction

The original Queue makes Retry and Enqueue due immediately by storing `next=0`. An attempt that was already running can later settle its captured failure and overwrite that acknowledged wake with a future backoff. In particular, an active attempt returning `ErrLimited` can postpone the accepted Retry for another ten minutes. This is a source-derived interleaving. It is not evidence that this race caused the retained Alice quota-zero observation or any loss of file bytes.

The correction binds one private identity to each actual runner invocation. The existing durable row format and the public Queue API remain unchanged.

- Worker capacity is acquired before current due-row selection. Selection and running-ID claim happen under the same mutex, closing the stale selection gap.
- Retry and immediate Enqueue write the existing due value before acknowledging the caller and coalesce a retry marker for active work.
- A later failure still records its real error, attempt count, and LIMITED classification. A newer acknowledged retry prevents only the stale backoff write.
- Remove invalidates that attempt's settlement and cancels it, while retaining its running-ID fence until its callback actually returns. A replacement row cannot overlap or be settled by the old callback.
- Success remains terminal even after Retry; a retry request is not permission to repeat a successful upload.
- Notifications remain outside the queue mutex. The original CancelFunc running map and the complete original test file are preserved.

The original four-worker limit, due batch, fairness selection, scan interval, per-kind timeouts, backoff cadences, and no-file-node behavior remain unchanged. There is no new overall retry-count cap.

## Complete source and inverse

[The derivation proof](proofs/SOURCE_DERIVATION.json) retains all fifteen exact old/new literal replacements and verifies the whole reverse transformation to the original 15,094-byte Queue.

| Body | Carrier path | Role |
| --- | --- | --- |
| Original Queue | [before/queue.go](before/queue.go) | Exact before-image; also the original regression subject |
| Original tests | [before/queue_test.go](before/queue_test.go) | Complete unchanged file; four affected methods selected |
| Corrected Queue | [sources/queue.go](sources/queue.go) | One prospective production replacement |
| New tests | [sources/queue_retry_generation_test.go](sources/queue_retry_generation_test.go) | One prospective qualification-only addition |
| Root independent peer | [reviews/ROOT_SOURCE_PEER.json](reviews/ROOT_SOURCE_PEER.json) | Whole source, literal inverse, ownership, and test-design review |

Both original files are exactly bound by Runtime18 manifest3552 and the final native64 maps. The adoption descriptor requires the old Queue row and complete before-image, requires the new test path to be absent, retains the original test bytes, and preserves every unrelated row and mode. It records computed prospective full/native and SDK map identities plus exact reverse checks. The existing map files in this repository remain byte-identical.

Prospective source counts would be 1,648 native production / 755 SDK inputs and 1,658 qualification / 758 SDK inputs. Those counts are a checked source recipe, not a compiled product or an adopted native64 successor.

## Selected component workload

[TEST_SELECTION.json](proofs/TEST_SELECTION.json) enumerates all twenty compiled parent declarations and selects exactly ten parents with zero subcases: six new controls and four affected original controls. Ten unrelated original methods remain unselected.

The new controls check active Retry followed by LIMITED, active Enqueue followed by a transient failure, coalescing, removed-attempt settlement isolation and drain, an acknowledged retry across orderly database close/reopen, and terminal success after Retry. They inspect actual persisted due values and classification while callbacks are controlled; they also assert no same-ID concurrent worker.

The test harness uses real isolated AnyStore databases and fake runners. Its gates deliberately allow a callback to remain blocked after attempt cancellation. Cleanup releases every private gate and joins Queue.Close before closing the database. A test-process timeout or cleanup failure is a failure, not evidence of a successful join. The reopen control checks the saved row before Run can reset it; it does not claim injected crash or power-loss testing.

The same new test file uses the original Queue API and fields. A separate negative control can therefore compile the exact original Queue with the complete original and new test files, selecting only `TestQueueKickDuringLimitedAttemptKeepsRetryDue`. Its expected assertion failure must specifically reproduce the active-Kick/backoff overwrite. A compiler, setup, timeout, or cleanup failure is not an accepted reproduction. **The negative control and all ten candidate methods are currently NOT_RUN.**

An actual component invocation still needs an exact source/dependency/toolchain manifest, separately admitted resources and cache ownership, and the existing owned-process completion checks. The explicit-file route uses this complete small package rather than importing unrelated SDK/account packages. No dependency version or source gate is changed by this carrier.

## Files and cloud acceptance boundary

The [retained Files acceptance matrix](../../../docs/validation/20261128-native-quota-broker-source/FILES_ACCEPTANCE_MATRIX.md) remains the authority for the earlier passed transfer and permission cohorts. It is not replayed here.

Fresh retained-account quota observation, cloud durability of the original 49,363-byte and 8 MiB pending files, and their cloud-only interrupted/restarted transfer evidence remain outstanding. This source correction supplies no current quota answer, cloud receipt, account authorization, upload-resume result, native64/ABI acceptance, or application adoption. The original full native/Files resource gates and E's cache-release conditions remain unchanged.
