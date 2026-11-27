# Host exact Unicode readback: actual source2 result

**Two actual XCTest methods passed, covering four controlled HTTP flows.** The full source-bound Linux Host component is qualified by the separately executed, zero-child completion. The first source2 receipt remains `FAIL`: its compiler-evidence validator expected the component directory while every actual SwiftDriver command used the owned parent directory. No compiler, test, HTTP fixture or historical process probe was repeated to complete qualification.

## Exact inputs and result

- Product fix: `cde0b83a3f04f36232eed93e6ab2cb7be0e692a5`.
- Source2 inputs: `1e559d715ed82107d3cc98352ce1e7429336febb`; stager: `f69c05a1063fe45e21551a4402f7eb5374c9d1d4`.
- Executed driver: `fc6dba3c88cdc599df16421264629070f6107348d4d7705e31983806cc20b881`; packet: `3a23e8da2f0126c567bf4c1f78d265400a78c65226281b75b25094b7297fedb3`.
- Actual job: `job_7c36e01057d6`, 2026-11-27 17:19:39–17:20:07 UTC. The Swift command exited 0; XCTest reported 2 tests, 0 failures, 1.488 seconds. The build log reports 21.38 seconds.
- Original source2 receipt: `1903e2725437835136dd14f4b072a012df7f8773febc54ee131236deb54b3b5c` (`originals/attempt1/receipt.json`). Its `FAIL` and `safeToReleaseRuntimeSlot: false` fields remain unchanged.
- Actual zero-child completion: `137c17f247fe146122a9b2acee832f0b39a3ae63773f9d21023592a2e90bbd41` (`completion-result.original.json`), 0.717 seconds at 17:26:26 UTC, `PASS_REUSED_HOST2_WITH_COMPLETE_SOURCE_AND_HTTP_EVIDENCE` and `safeToReleaseRuntimeSlot: true`.
- Completion source: `efc72d19cb9315f0ed26be0f39a3b8fc79e1b61a586fa992fa2deaf1f1fd6a6e`; independent source review: `ced306723de93fc40b04827e5a8c4d9e4f6861601519a8057a3c463bdfd38adc`.
- Final independent qualification: `bbbabb8db6671a42b7e2a947c9f79810f2813fa7998d97ae569aed6515115b15` (`torah-independent-actual-qualification.json`).

The build was **not warning-free**. Its retained stderr contains a nonfatal unnecessary `try` warning at `NativeHostTests.swift:289` for the nonthrowing `AnyApplicationSession` initializer; repeated diagnostic/caret lines refer to the same source warning. The verbose Package manifest command is also printed under a `warning:` wrapper. The actual two tests still passed. This evidence publication changes no source to remove the warning; any one-token cleanup is a separate source change with no automatic acceptance credit or replay.

## Behavior actually exercised

The two unparameterized methods are `NativeTextEditReadbackHTTPTests.testCanonicalEquivalentTextReadbackCannotCertifyWriteOrMintUndo` and `NativeTextEditReadbackHTTPTests.testExactUnicodeTextReadbackRetainsVerifiedReceiptAndExactInverse`.

Each performs the real Host read, prepare, conditional PATCH and readback using the original HTTP/session/target checks. Latin composed/decomposed text and Hebrew combining-mark order provide four looped fixtures, not four enumerated XCTest cases. All retain the same ASCII semantic-anchor URL.

For a canonical-equivalent but byte-different reply, the Host cannot qualify the write or mint Undo. For the exact requested bytes, the verified receipt and exact inverse/redo text remain available. Each raw fixture proves one conditional PATCH, actual requested UTF-8 bytes, the versioned response, and its owned server's matching start/EOF-exit journal. All four fixture stderr files are empty. No older test method ran.

## Why the original qualifier failed

The original compiler validator required `-working-directory COMPONENT`. All seven real SwiftDriver commands explicitly used the fixed owned `ROOT`, while their source lists and source paths still identified the exact component files. The completion changes this single assertion in memory to `-working-directory ROOT`. It preserves every other compiler-witness check and retains the complete inverse. It does not change the executed controller or any product/test source.

The completion rechecked 63 original artifact files, all 30 before/after/final source inventory entries, the 102 actual Crypto originals/aliases/copies, seven compiler modules, 28 complete production/test Swift inputs plus two generated test inputs, emitted module/object hashes, all four HTTP flows and the original resource limits. It reused the recorded normal-exit group-absence evidence; it did not probe the old group. It wrote only a new completion receipt. Root released the runtime slot in Asana story `1220959505328953`.

The earlier source1 alias-layout failure (`2287f915…`) and its separate retention/slot-release audit (`ac83d091…`) remain in the preceding source2 publication. Neither historical failure is replaced or removed.

## Acceptance boundary

This is actual full-file **Linux Foundation Host component** acceptance against bounded controlled HTTP fixtures. It is not a full Anytype App/package build, a Native engine/account/database test, peer-sync acceptance, an Apple UI test, IME coverage or structural split/merge coverage. The fixed UI flush independently rejects wrong readback bytes; this Host correction closes the more permissive Host receipt path.

The original 27 production Swift files, complete Host test file, generated test discovery and retained Crypto closure are bound in the input and compiler evidence. The completion template containing a placeholder is intentionally excluded; the actual executed `complete_retained_execution.py` is retained. The already passed component methods need no replay solely because the unchanged original receipt contains its evidence-qualification failure.
