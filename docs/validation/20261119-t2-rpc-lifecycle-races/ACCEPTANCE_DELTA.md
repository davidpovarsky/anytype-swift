# T2 generated-byte lifecycle race acceptance

The original artifact from [run 44590443646](https://github.com/davidpovarsky/anytype-swift/actions/runs/44590443646) qualifies **three bounded native lifecycle races** at source `cbebcd5464fc43b4cda46d4f915bf16ccefd64f9`. The product implementation remains `16b7493fa05bdc3abbae190c6e6c364c81874eea`, built over pinned Heart `d98420b1113536afd08cde6de9a5816f6d27ffff`. The additional observations exist only in a separately compiled test overlay.

The full hash-bound result is [`VERIFIED_RPC_LIFECYCLE_RACES_44590443646.json`](VERIFIED_RPC_LIFECYCLE_RACES_44590443646.json), SHA256 `159e29aec050973cf1346edd5c4ddac6ad551c966091fee800befaf18076e9cd`. It verifies the original GitHub archive, all 59 members, source manifests, build and phase receipts, native test logs, trace order, history, export boundaries and owned cleanup. The runtime executable bytes were not retained in the archive, so this is an audit of their original source/build/phase identity chain rather than an independent binary rebuild.

## Original evidence and counts

Artifact `14564286488` is 82,123 bytes. Its official and observed ZIP SHA256 is `e4089c45899d2a8b1b4af815e046d7abfe30f9a49a0818327bbe9c17dba766de`; CRC and all member hashes passed. The published source manifest is `4e7eaaced03ae70bd12b9dfadc7f1c18b014df8e276f119d214db743f4e9756e`.

The original uninstrumented account-wire baseline passed first: two native binaries, four distinct processes, four exact named native test passes and eight JSON/protobuf exports. Its creation, reopen, legacy ordinary edit, recovery, original signed history, generated-byte rejection/retry/collision, private visibility and native cleanup assertions remain required. The race binary is a third distinct binary and runs in a fifth process. Its one named `TestT2GeneratedByteLifecycleRaces` invocation passed in 1.98 seconds and contains the three cases below. Counts are therefore five named native passes, zero native failures or skips, and 39 Python controls, with baseline and added case counts kept separate.

## Three verified cases

| Case | Actual boundary proved | Limit of the result |
|---|---|---|
| Block deletion wins first ADD | The real deletion completes after target preload and before the append acquires its lease. The original generated-byte append returns `TARGET_UNAVAILABLE` without a receipt. Native private-root lookup remains absent. | This is one deterministic interleaving. It does not prove settings deletion, movement or every target lifecycle permutation. |
| Existing commit wins block deletion | A deletion attempts the exact same live SmartBlock mutex while the original append is paused before durable storage. It cannot acquire before the once-only storage call succeeds. Signed history grows from two to three changes, prior changes are preserved, both operations succeed, and later read/retry are denied without changing retained history. | The trace proves durability before deletion acquires. It does not assert the order of native or byte response delivery relative to deletion. The retained report contains final hashes; the source-bound original native test checks both before hashes and post-denial equality. |
| Existing commit wins AccountStop | The actual application service writer attempts acquisition while append holds its application lease. Both original signed-change hashes remain in the retained two-to-three map. Durable storage and the native append result precede Stop acquisition; the original Stop succeeds and later read/retry return `NOT_LOGGED_IN` without results. | The native result is protected by the lease. Generated response-byte encoding can finish after the Stop writer acquires. This is concurrent AccountStop, not account switching or an independently initiated Space.Close. |

Every observed stage occurred exactly once, all bounded barrier waits completed, and the trace identifies the same live target/application instances. The controller retained the four allowlisted, secret-scanned race evidence files and observed successful process exit before removal of its owned disposable account.

## Changes to the sixteen-row acceptance map

This result updates the previously published [remaining-acceptance map](../20261119-t2-lifecycle-followup/REMAINING_ACCEPTANCE.md) without rewriting its historical source or receipts.

- **Row 8, target lifecycle:** the two concrete generated-byte block-deletion races described above are now native PASS. Same/cross-Space movement, signed settings deletion, template uninstall, the full deletion matrix and a public orphan/read-by-ID API remain open.
- **Row 15, account lifecycle:** append versus actual AccountStop is now native PASS. Account switch with in-flight calls/subscriptions, stale cursor/decrypted cache isolation, backup/import and restore remain open.
- **“Concrete next coverage” item 3:** the three-case candidate has now been compiled, executed and qualified from the original artifact. Its earlier `NOT_RUN` state remains historical.

Other acceptance rows retain their existing status. The bounded result does not supply causal display ordering, a reverse-source query/index, cursor/index-watermark APIs, compaction/GC, a backup contract, 1,000/10,000-operation performance evidence, independent member ACL transport, iOS acceptance or new-engine parity. The standalone Space.Close case involving an already-closing cache entry remains unresolved.

**Full T2 remains OPEN. App capability remains OFF.** No additional broad product change or repeated baseline dispatch is required to establish the scope already proved here.
