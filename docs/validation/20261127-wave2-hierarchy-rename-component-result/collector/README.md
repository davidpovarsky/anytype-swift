# Hierarchy attempt1 completion custody — preparation only

The published execution packet is unchanged. This folder supplies an exact historical launch locator and one **new**, small read-only collector. The original Property4 transfer and ten-file inventory were retained, but its producing collector source was not identified. There is no claimed source inverse to that unavailable body.

## Exact original launch envelope

`original-launch-envelope-locator.json` binds the original Property4 `dispatch.json`, 408-byte `launcher.py` and completed Sentinel notification. Both dispatch custody and the actual notification record an outer timeout of **360 seconds**; the original runner's internal Swift deadline is **300 seconds**. The wrapper verifies the fixed stager bytes, then uses `os.execv` without adding a timeout child or process manager. The original release/job are historical evidence only. Root owns any new launcher, actual coordination literal and dispatch.

## Finite collector interface

`collect_original_attempt.py` has no executing entrypoint. Root may call:

```python
collect(completed_job_raw, offset=0, expected_gzip_sha256=None)
```

`completed_job_raw` must be the exact UTF-8 bytes of root's actual completed Sentinel `notifications_get` JSON. Before any filesystem access the function requires the recorded Oracle host, `script_run`, a completed `succeeded` or `failed` envelope, nonempty completion timestamp, actual integer exit code, 360-second outer envelope, complete output, and an original output record binding the exact hierarchy root/packet or attempt receipt. Other notification formats fail closed for review. This function does not fetch a result or wait/poll for a job. Root must supply the result only after explicit completion; neither the prior Property4 job nor a scheduling notice authorizes collection or execution.

The only original content paths are these fixed files under:

`/mnt/development/projects/evidence/pinkha-wave2-hierarchy-rename-20261127/attempt1`

| File | Purpose |
|---|---|
| `actual-dependency-copies.json` | Recorded exact dependency copies |
| `command.json` | Actual command and environment |
| `process.json` | Retained original process record; no live queries |
| `receipt.json` | Original runner result and compiler proof, if emitted |
| `resource-samples.json` | Actual original samples |
| `source-inputs-after.json` | After-command source inventory |
| `source-inputs-before.json` | Before-command source inventory |
| `source-inputs-final.json` | Final retained source inventory |
| `stderr.original.log` | Raw original diagnostics/compiler log |
| `stdout.original.log` | Raw original test log |

The fixed root/attempt directories must be physical. Each original must be a singly linked regular physical file. Reads use read-only/no-follow/nonblocking descriptors; device, inode, mode, owner/group, link count, size and nanosecond modification/change times must agree before open, on the open descriptor, and after reading. File bytes, SHA-256 and these identities are retained. Access-time preservation is not claimed. There is no directory walk, source/cache read, runner import, child creation, process/session query, signal, cleanup or original-file write.

Reads are bounded to 2 MiB per file and 8 MiB aggregate, with a one-byte EOF/growth check; excess or missing files produce explicit incomplete custody with available observations retained. The completed-job input is capped at 256 KiB and the JSON transport at 13 MiB. These are collection bounds, not changes to the execution resource envelope. No file is invented if absent. No assertion that there are no other files is made.

## Lossless transfer and outcome boundary

The collector returns deterministic gzip/base64 in 48,000-character chunks. The first response gives complete raw/gzip hashes and encoded length. Each later explicit call must supply the first `gzipSHA256` and the next aligned offset; a changed byte or retained identity rejects reassembly. There is no automatic repeated read or retry. The bundle includes the complete original completion notification, every collected original byte, stat observations, and explicit missing/read errors. Root preserves the raw response and performs local exact decompression/readback.

Collection success is independent of test outcome. `runnerReportedStatus`, `commandExitObserved`, recorded `testResult`, presence of a compiler proof, original errors and `safeToReleaseRuntimeSlotObserved` are copied only from the exact source-bound receipt. If a final notification summary exists, the receipt must also match its original hash. A zero command exit does not imply passing test qualification; a runner `FAIL` does not by itself prove a compiler or assertion failure. Compiler/test acceptance and any safe-release decision remain independent review tasks. No process observation is made, and no previously recorded process-group identifier is probed.

The new four-method/eight-case run remains pending. Root must provide its actual completed job before this collector is invoked. Preparation involved local source/AST/data inspection only: no host call, collector invocation, compiler, tests, upload or runtime request.
