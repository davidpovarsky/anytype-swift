# Bookmark missing-two continuation1 — actual failure, no new acceptance

The direct continuation launched the selected Integration runner and **failed with child exit 69**. Both captured logs are empty, and the original controller stopped before test-result qualification. This packet preserves the actual failure. It does not establish a per-test assertion failure, a skipped result, or either method passing.

## Actual result

| Field | Recorded observation |
| --- | --- |
| Job | `job_57ce10beab09` |
| Interval | 2026-11-28 00:06:09.560633–00:06:13.433233 UTC |
| Outer duration / exit | 3.87 seconds / 1 |
| Controller duration | 1.085 seconds |
| Child exit | 69 |
| stdout / stderr | 0 bytes / 0 bytes |
| Test evidence | No observed start/pass events; no `testResult` field |
| Original receipt | `original-continuation1/receipt.json`, 4,021 bytes |
| Receipt SHA256 | `fe4dcf305e035f38b237b198e9db956aff63aa8bd8e4f34a6ff539f2b9d5bb64` |
| Outcome | Original **FAIL**, unchanged |

The selected methods were `creationOverrideRejectsAnotherWorkspaceBeforeDispatch` and `creationOverrideAndDefaultCreatorShareTheExistingMutationQueue`. The actual child is the retained Integration executable `c5334175861cc165de9751240d4532e2eea73d4ac850756074f7ffb150d91b34`, with the qualified test library `5eac396345bc469d9712ec7a776e10671652cc1366aa6f08b4269ff49f8f70ab`. Exact argv, cwd and environment remain in the original command record. No compilation or SwiftPM build was requested by this continuation.

The earlier four positive XCTest cases remain in their original attempt1 envelope; its six-method result remains FAIL. The earlier compiler-custody completion retains its original scope. This continuation adds no Swift Testing, aggregate, Native, HTTP, Apple or mounted-UI acceptance. These actual artifacts do not establish exit69's cause; a later source diagnosis must be separately labeled and must not replace this failure.

## Originals and lossless custody

All nine complete originals, totaling **495,425 bytes**, appear once under `original-continuation1/`. All three independently created witness files are retained at their original names despite identical bytes. Both zero-byte logs and exactly one original receipt are present. `artifact-index.json` binds their full sizes, SHA256 and Git blobs. Full original job, dispatch, grant, upload and notification records are under `custody/`.

`transfer-provenance.json` retains every collection metadata field except duplicated encoded bodies, together with the complete raw/gzip/base64 hashes. Reinserting standard base64 from the nine originals and terminal-job body and applying the documented serialization reconstructs the entire **670,209-byte** collection record byte-for-byte; this was verified locally. The 127,285-byte gzip and its base64 wrapper are omitted. Their decoded originals and lossless bindings remain, and the original local transports are unchanged.

The before, after and final witnesses are byte-identical: **438 paths**, SHA256 `ce9a153b4656baf71f3fe316e758a9fd56a9fc2607ae6cd1674f2d05ce3a05b8`. Independent review joins them to 90 frozen inputs, 85 Package/source copies, 150 compiler artifact paths, 102 Crypto copies, ten previous originals and the existing compiler-custody completion. `inherited-evidence.json` references those immutable authorities without recopying the old 90 inputs or earlier ten originals.

## Resources and closed ownership

All four recorded resource samples meet their applicable unchanged gates. Minimum ROOT free space was 2,346,201,088 bytes; minimum DEV free space 1,433,419,776 bytes; minimum available memory 4,273,704,960 bytes. Maximum owned allocation was 217,595,904 bytes, below the unchanged 256 MiB cap with its 1 MiB final-evidence reserve. These are historical samples, not continuous telemetry or a current capacity reading.

The original helper recorded positive `ABSENT_ESRCH` for new group **2862993** at **00:06:12.465711 UTC**, `PASS_OWNED_GROUP_ABSENT`, and `safeToReleaseRuntimeSlot=true`. No termination signal is recorded. Neither this closed group nor historical group2634766 is queried again. The included grant authorized only this completed attempt; it grants no retry or future runtime.

## Source, reviews and publication boundary

The executed 34,063-byte controller `0e8fa19767222fef6f954bf4bfdb34e58a77986251e69cf461b29f7311f01627` remains inherited unchanged from parent `e01176b6a15bdb6a8ff7fedbca5c880634a773ef`, along with its reviewed inverse. This packet includes the small launcher, nine-file collector, complete collector inverse, dispatch/launch plans and their source review. Historical preparation status labels are preserved verbatim.

Root actual review `82b5ccd6…` and independent actual review `48d9ace6…` both preserve the failure and distinguish custody/cleanup from test acceptance. A separate local packet-inspection stop records an array-order comparison mistake; complete map equality plus canonical Git tree serialization corrected that inspection, with no source or runtime failure.

This is a docs-only result packet. No product, tests, Package, gates, controller, limits or original evidence changes are included. `parent-inverse-plan.json` specifies complete inherited-tree preservation and exact removal of this one new evidence subtree to recover the parent. A separate root complete-packet review and fresh GitHub checks precede any publication. Preparing this packet performed no Git or host mutation.
