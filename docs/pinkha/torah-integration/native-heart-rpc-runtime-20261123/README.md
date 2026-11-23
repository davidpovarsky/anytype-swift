# Original Heart native lifetime continuation — 2026-11-23

## Scope and current status

This packet prepares two new native cases against the original Heart application, wallet, account-directory lease, regular Space and protobuf importer. Runtime status is **NOT_RUN**. It preserves the 28 production afterimages compiled at `afe22a1ed462b6e3601f866b582802fe514b31dd` in run [45060542322](https://github.com/davidpovarsky/anytype-swift/actions/runs/45060542322). That historical result is compilation only; its executable was not retained.

The exact baseline is original Heart `d98420b1113536afd08cde6de9a5816f6d27ffff`. The retained original r14 layer, six-file origin layer, fifteen-file owned-import layer and eight-file lifetime layer preserve their verified preimages and complete hashes. The resulting 28-file production closure is unchanged. This new gate installs one additional test source in `core/application` inside a fresh disposable original checkout.

The prior 50, 7, 26 and 23 isolated control cases are not selected or replayed. No shared Anytype product, SDK06 enumeration, Page154 consumer, T2 or T5 lane is modified.

## New actual native cases

1. **OriginalProtobufImportAndReentrantRetirement.** Create a genuine LocalOnly account and two real regular Spaces. Create an original native page, copy its real protobuf snapshot and run the actual owned protobuf importer into the second Space. Require the original copied source mapping and actual native object readback. A second genuine import updates that original destination object and reaches its existing `HookBeforeApply` extension point. The callback reenters `AccountStop(RemoveData: true)`; the test requires pending drain, retained app/lease and an open original `Done` while the actual Apply is blocked. After releasing the real callback, require actual cancellation/return before the subsequent successful native Stop and lease release.

2. **RegisteredPreStartCancellationRequiresActualReturn.** Build a real operation from the actual app/wallet/lease and real disposable Space before Start. A lifecycle request must return pending and keep the actual operation uncompleted. Start the already-canceled original Execute, await its actual return, then perform the original final retirement. Cancellation alone cannot supply completion.

The callback gate schedules a real original Apply; it does not replace execution, fabricate a native result or supply an ACK. Disposable data is removed only after actual owned executions drain and native account shutdown succeeds. The runner retains only source/toolchain/compiler/runtime streams and bounded phase receipts, excluding wallet and account database files.

## Execution and evidence boundary

`run_native_lifetime.py` imports the unchanged, SHA256-bound process owner and dependency-closure reader from the prior native compile driver. Each child has one bounded process group, a shared absolute deadline and verified drain before temporary cleanup. The new source is compiled with the real original Go module, Darwin ARM64 compiler, Xcode 27 and exact retained Tantivy archive. The selected executable is hashed before actual execution; Go JSON events must show exactly the two new leaf cases once, with no failures, skips or historical selectors.

Forty-two original inputs (approximately 407 KB total) are retained byte-for-byte to avoid fetching unrelated historical source during CI. Their source revision, path, Git blob, byte length and SHA256 are all recorded. The actual checkout bytes and new control inputs are checked against the committed source; no generated RPC output is handwritten or substituted.

A successful result establishes only these original local import and lifetime boundaries. It does not enable a production caller, establish archive permission, promise full semantic-body equality or durable mapping, or grant ACK authority. Native schema endpoint, generated service integration, Swift Invocation and selected-Space composition remain a distinct next gate pending the genuine RPC-generation artifact.
