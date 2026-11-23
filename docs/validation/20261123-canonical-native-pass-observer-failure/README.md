# Anytype original native/UI acceptance passed; runtime observer remains failed

## Exact outcome

[Workflow 45163976036](https://github.com/davidpovarsky/anytype-swift/actions/runs/45163976036), attempt 1, executed host `aefb9740c0ac8d52aa2dbd89d389930851396104` with canonical SDK `d49a4fd4115b8335105d2991bf74ab4d7f6aad2d` and qualified runtime producer 45091223011. The real app build passed. Original native preparation `HanlinNativeAcceptancePreparationTests/prepareRealHostFixture()` passed in 8.294 seconds, and original UI method `HanlinNativeAcceptanceUITests/testRealNativeConsentCreatePageAndAuthorityRevocation()` passed in 107.066 seconds. Each selector executed exactly once, with no failures or skips. These are actual iPad Pro 13-inch (M5), iOS 27.0 simulator results, not Python control results.

The overall workflow remains **FAILURE** because the separate actual-UI runtime observer did not complete its required live-process mapping. No full SDK/runtime-binding pass is asserted. The passed preparation/UI selectors must not be replayed merely to hide or compensate for this observer failure.

## Native behavior and visual evidence

All 22 original final native checks are true. They include explicit read consent, cancel-without-write, exact page creation, replay deduplication, original-document return, real background/foreground revocation, fresh presentation consent, pending consent invalidation on document departure, original-document-only access, source permission changes, workspace changes and logout. Provider configuration was deliberately absent; this is not live-model acceptance.

Original XCTest entry/final hierarchy headers, partial native phase and final native receipt all identify PID 55649 and the same fixture/session/source. The current source inputs agree with the exact Git commit. The candidate identity map uses SHA256 of Git mode and blob identity, whereas the compiled-source inventory stores raw file SHA256; both encodings were checked correctly. The inventory remains an observation of products/inputs, not an independent permission to skip a future app build.

The original Home action was followed by real `com.apple.springboard` activation. The state receipt records Anytype in background and SpringBoard foreground 2.344 seconds into the unchanged shared 10-second admission budget, with 7.656 seconds remaining. The actual UIKit scene observations record one background event and one foreground/activation event; the same PID survives the return. No synthetic notification or termination was used.

Ten relevant original PNGs were inspected directly through Oracle: create/cancel confirmations, read/create completion, original-document return, full SpringBoard, foreground return, pending consent before departure, created-document presentation, fresh consent state, and the final authentication screen after logout. `visual-review.json` binds each observation to the exact original file, timestamp and SHA256. The diagnostic banner belongs to the existing acceptance harness. Permission enforcement claims come from the original assertions and native receipt, not from screenshot pixels alone.

## Exact unresolved observer boundary

The fresh installed-source verification returned after 19.462 seconds and matched the built executable and code-carrier hashes. Process mapping then ran 40.585 seconds and raised TimeoutExpired at 11:48:17.168UTC. This was 9.787 seconds before the native journey finished at 11:48:26.954 and 19.039 seconds before the UI test passed at 11:48:36.207. The retained evidence therefore does not attribute the timeout to teardown.

The original helper first reads process identity through two `ps` commands and then executes `/usr/bin/vmmap -w 55649`. It writes the mapping file only after the command returns. The authenticated original archive contains no `live-runtime-vmmap.log`, `live-runtime.json`, or completed qualification file. The evidence packager would retain those `.log`/`.json` files if present. Existing diagnostics retain the first earlier data-container poll timeout; that poll subsequently recovered, but its metadata masks the exact later fatal command. It is therefore not honest to identify the failing command as `ps` or `vmmap` from this artifact alone.

The successful UI receipt, same-PID hierarchies, installed-byte hashes and scene events are retained. They do not supply the missing required live mapped module/process-start proof, so no retrospective synthetic binding or gate waiver is applied. No timeout was raised again, no additional app launch or native/UI replay was performed by this readback, and the observer-only resolution remains open.

## Original artifact custody

GitHub artifact 14815786945 is 16,439,629 bytes, SHA256 `1a0393ade38a2a424d2b6052300023fc08458b87937d992decd2964e3bce7164`. Its original nested evidence ZIP is 16,466,625 bytes, SHA256 `ac57f6ed023f0286000f4cc7e516348e7ddf54e8e83ab976f742ad5865f44cb1`. Both CRC inventories and archive-path checks passed; each was extracted exactly once. The nested archive has 179 entries and 26,910,710 uncompressed bytes. Originals remain on Oracle with the source-bound records.

The complete original job log is 1,119,546 bytes, SHA256 `f6938d07da127501724c2f0adbb2c248054e2b0840cb1a8b2c20be3bf011da49`. Its retained gzip was verified lossless before removing only the newly downloaded duplicate raw file. `files.json` seals the copied original summaries, test details, UI command log, native receipts, source hashes and readback. The later host dependency upgrade to SDK 32da is separately verified for installation/source; these native results remain bound to SDK d49. SDK06's other owner’s 23/32 + ACK work is untouched.
