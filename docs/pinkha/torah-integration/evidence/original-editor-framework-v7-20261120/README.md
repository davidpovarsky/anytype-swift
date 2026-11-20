# Original editor framework v7 — observed simulator signing format

## Status and source

This is an isolated source preparation for the next actual Apple run. **The new 143 Python controls and all v7 Apple build/signature/consumer/runtime gates are NOT_RUN.** No reviewed executable branch, workflow dispatch, retry or integration ref was created by this preparation.

- Source commit: `5f7383722ad4eefd4e249c7c00665d9e422ff6d8`.
- Source tree: `e6566a6a366ae2b8d8e614311123b095eca31574`.
- Sole parent: `f179a616e5e22fc785bb97dc5ffa5ec1621441b3`, the immutable failed v6 source.
- Proposed reviewed branch: `codex/otzaria-original-editor-framework-v7-reviewed-20261120`. Activation belongs to Root after independent review.
- The actual source tree changes exactly eight existing CI files and adds one source-control runner. All 9,284 other parent leaves and modes are unchanged. All six app/test/project/Modules/framework trees are unchanged.
- All 30 execution input blobs were fetched from actual immutable Git objects. UTF-8 lengths, Git blob hashes and SHA-256 digests were recomputed in authoring memory; total input size is 539,951 bytes.

This route still uses the historical framework application tree `bd7385d4e7f9741a1b2bb900ec30bc84cc975d22`. It does not qualify the separately verified 49-constructor application union, the prepared editor host, a mounted editable consumer, a live account, CloudKit or cross-app exchange.

## Why the v6 parser failed

Actual run **44822310098**, attempt 1, job **136586017214**, finished FAILURE. Its original 131 Mac Python controls passed. The genuine original framework build exited zero, with 2,238 recorded original Swift inputs plus one generated input, the original 44 package pins and verified Heart dependency. Those historical results belong only to v6.

The checksum-pinned Amplitude simulator input was already missing two resources required by its original resource seal. Native strict checks on original/exported input therefore failed as expected. The explicitly constrained signing operation on the owned export then exited zero:

```text
codesign --force --sign - --timestamp=none <owned AmplitudeCore.framework export>
```

The next preservation parser rejected `Unexpected or nonzero signature allocation padding`. The post-sign native strict gate had not executed. Neither had other framework signature checks, the public symbol graph, external consumer compilation, simulator boot/install/launch or final SDK comparison. No distribution was qualified.

The retained actual post-sign bytes establish three format facts:

| Field | x86_64 | arm64 |
| --- | ---: | ---: |
| Fixed signature data offset | 292,784 | 307,792 |
| New SuperBlob length | 2,558 | 862 |
| New signature allocation | 2,576 | 880 |
| Slack after the SuperBlob | 18 bytes | 18 bytes |
| Code page exponent | 12 | 14 |
| Independently checked code pages | 72 | 19 |
| New LINKEDIT file size | 184,768 | 177,600 |
| New LINKEDIT virtual size | 196,608 | 180,224 |
| Original virtual size | 212,992 | 212,992 |

The x86 slack is zero; the ARM slack is exactly `985bdf0e89c28a8981dd3f5d4fe0d7338b45`. Both equal the prior input bytes at the exact same thin-file offsets. Both lie after the new SuperBlob length and wholly inside the resized signature allocation. Code page hashes, all three special slots, the fixed identifier, ad-hoc flags and absent entitlements were independently inspected. This was read-only byte analysis, not another codesign execution.

## Narrow correction and unchanged hard gates

The original checksum-pinned input parser still requires zero padding. Only the post-sign preservation comparison, supplied with the already authenticated original slices, can admit retained slack. It requires:

- The same exact architecture/subtype and signature data offset.
- A signature allocation divisible by 16, with exactly 18 bytes after the meaningful SuperBlob.
- The allocation end no greater than the parsed original thin-file end.
- Every slack byte equal to the prior byte at that same offset; arbitrary nonzero padding, zeroing the genuine nonzero residue, changed offsets and extra payload remain rejected.
- SHA-256 code pages of exponent 12 for x86_64 and 14 for arm64, with every page and special-slot digest checked.
- LINKEDIT virtual size exactly `ceil(newFileSize / 16384) * 16384`, no greater than the original virtual size. The address is unchanged, so the new span cannot exceed the original segment boundary.
- The original 20-byte prefix mask only: LINKEDIT virtual/file sizes and signature allocation size. Every other executable-prefix byte, including symbols/fixups, remains exact.
- Exact FAT placement using the original alignment, zero inter-slice padding and no trailing payload.

The contemporary Apple Security source explains both the page policy and allocation behavior. Its allocator copies the original slice, replaces the allocation size and rounds LINKEDIT to a fixed 16 KiB for **both** architectures. The older grow-only/architecture-alignment assumption was incorrect for this actual signing path. `PRIMARY_SOURCE_AUTHORITY.json` binds the exact Apple commit, Git blobs and excerpts; the historical v6 source/results remain untouched.

Only the owned Amplitude simulator export is eligible. The original upstream package is not edited, missing swiftmodules are not fabricated, and CodeResources is not deleted. All 11 ordinary Amplitude resources must remain exact. The original strict post-sign check, all other framework failures, complete source/resource isolation, external consumer and runtime gates remain mandatory. Native commands, SDK, Heart, compiler flags and time budgets are unchanged.

## Actual control identity and result gate

The updated source declares 143 controls:

| Test file | Declared controls |
| --- | ---: |
| test_framework.py | 44 |
| test_framework_duplicates.py | 35 |
| test_framework_flow.py | 10 |
| test_framework_source_retention.py | 7 |
| test_framework_temporary_paths.py | 3 |
| test_amplitude_simulator_signing.py | 44 |

The prior 99 controls retain their assertions. One installer-branch literal changes to v7 so its original exact inverse tests the new branch against the complete v6 installer. In the 32 signing controls added by v6, the shared native-tool fixture and two allocator policy expectations are corrected to the actual documented format. Four direct parser calls now supply the required original-slice comparison context. Twelve new controls cover exact residue, altered/zeroed residue, prior allocation bounds, wrong page policy despite valid hashes, page/special hash changes, wrong virtual rounding, segment overlap, trailing payload, unaligned allocation and failed-signing observation retention.

All 143 methods were statically mapped as direct members of top-level `unittest.TestCase` classes with an indentation/block-aware authoring reader. This is **not** a Python AST or execution result. The new runner uses the same actual unittest discovery directory/pattern and verbosity, requires the exact 143 discovered IDs, and then requires the exact started/passed IDs plus `testsRun == 143`, with no skipped, failed, errored, expected-failure or unexpected-success outcomes. A caught pre-freeze issue is retained in the review notes: an escaping `SystemExit(0)` could bypass `except Exception`; the final runner catches `BaseException`, retains FAIL/traceback and returns nonzero.

The workflow preserves its ordinary verbose stdout/stderr logs and adds a structured source-control result. No new controls have been executed in this preparation.

## Complete observation versus qualification

The driver now records the complete distribution inventory after signing, including when the signing/preservation function fails. The record is explicitly `OBSERVED_ONLY_NOT_QUALIFIED`. Failure to record it does not mask the original exception. The original successful-path two-file-change restriction and all qualification gates remain.

V6 retained all 13 Amplitude post-sign files, proving the 11 ordinary resources there were unchanged. Its two distribution inventories are both before-state inventories. There is no full post-sign observation for the other 1,011 distribution files. **This packet does not claim that all 1,022 nonsignature distribution files were re-observed after signing.**

## Retained failure authority and runtime outage

The original v6 artifact is immutable artifact **14673741380**, 2,291,733 bytes, SHA-256 `d8904f64340f027fa3e34d361884a88539d8f46343664061aee1a94862a2d17c`. Its inner archive is 2,403,205 bytes, SHA-256 `b914fe8c5303b20a8bc5ccb4b14d50c84547d3fef9be91ebbdf229b0bc8e48ef`, with 92 members. Full download/hash/CRC checks and static inspection completed before the local runtime became unavailable.

This preparation publishes the complete retained canonical run/jobs/artifact metadata and job log, plus immutable archive identity and the precise observations/limits. **It does not republish the full binary ZIP.** The original ZIP and selected bytes remain locally retained but inaccessible during the outage. The attempted local v6 README write failed; its follow-up packet replay never started and the final local publication index was not sealed. No ambiguous write was replayed. The preliminary unexecuted verifier's rounding formula still requires the fixed 16 KiB correction. The signed download URL file is excluded.

## Reviewing this preparation

`SOURCE_PROPOSAL.patch` contains all nine CI file changes. `EXACT_REVERSE_EDITS.json` and `SOURCE_INVERSE.json` bind complete inverses; `SOURCE_TREE_PROOF.json` records the actual Git tree comparison; `SOURCE_INPUTS.json` binds all 30 execution inputs.

`VERIFY_PREPARATION.py` is a read-only verifier for packet hashes, actual Git inputs, complete source inverses, protected trees and Python AST declaration membership. It never imports or executes candidate tests. It was prepared during the runtime outage and is **NOT_RUN**. Authoring-memory byte/hash/inverse checks are separately identified.

Root must independently read back the publication and create the reviewed executable ref. Actual v7 source controls, native signing verification, full build and external consumer execution remain the next evidence.
