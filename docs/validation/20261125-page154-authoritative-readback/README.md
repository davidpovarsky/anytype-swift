# Page154 authoritative post-Apply projection — 25 November 2026

Current qualified status: 27/27 affected Swift host controls, 4/4 independent collector controls, and actual Apple Page154 preparation + original mounted UI + original native boundary comparison all passed. The successful Apple run is 45536229185 at exact source 781340ad. Broader Task E remains open; see the qualification and remaining scope below.

## Exact product source

`fed5a8d709e9e42dbf25f4717f2d92afb926cf3d` on `codex/chatgpt-wave15-page154-final-20261125`, based on the shared `8da18fce1b59a10a9bd46f0dc3becd810d45dc80`. Root's reviewed control-only changes through `406fd73ae137f4a6966bc85b3d4567f0bf99db25` were subsequently merged without changing these product trees. The DEBUG Simulator observer additionally retains the pending value until its three original results are copied, then releases it (`52a8b46fc01398687f25531f63612ffd89442126`). The entire ProtobufMessages tree remains byte-identical to the host-tested product tree. The Page154 manifest now binds each compiled product tree to that exact current product commit and each helper input to its reviewed bytes. Native154 and the original UI journey are unchanged.

## Actual failure and source explanation

The original build/run `45498082340` at `96fadb1945a33e8c7bfa6153cae1cd6124604fdd` built successfully and passed fresh fixture preparation, but the mounted journey failed after an applied native reply at `validatingEvent`, before document publication.

A local read-only LLDB observation of those exact retained original App/UI products captured one 2,302-byte applied reply. Its SHA-256 is `c371d9b5255e5c3149fd3ebcda726772c551be3086dc22a3fb9e7fe090f8e178`. The event contains nine distinct allowed Torah metadata keys with explicit values and no unknown KeyValue wire fields, followed by the original marks-only update. Byte-qualified native-image breakpoints identify the exact rejection: `validateTorahProjection`, source line 106, function offset 3368. Given the independently inspected entry shape, the failed condition is lookup of a metadata key in preflight. No value-equality/mark/hash comparison has yet failed at that point. The exact preflight payload was not recovered by this debugger attempt.

The materialized native source explains this distinction: `smartBlock.Show/fetchMeta` returns the current `CombinedDetails`; Apply runs `injectDerivedDetails` and `injectTorahDetails`, which may materialize local derived metadata after the prior read. A same-object read taken before Apply is therefore not an authority for newly materialized post-Apply cache fields.

The successful diagnostic is retained privately at `/Users/m1/builds/_diagnostics/page96-validation-3gfd3c7t`. `result.json` SHA-256 is `89ea4f4408abac4ba60f32d42fa9c951d908548b95a2f24628b1f13c3a4fdd60`; `reply-observation.json` SHA-256 is `a4e99f6f6731dfe9c10231804349f24b96f3a96434bc83fc512270bac14b75a3`. Original inputs remained identical and the owned simulator/processes were cleaned. Diagnostic attempts at `page96-validation-2780wbon` (debugger timing) and `page96-validation-r8w9yca7` (observer attached too late) remain recorded failures. No diagnostic run receives acceptance credit.

## Product behavior

- Retain the original pre-dispatch owner/runtime check, complete-block and all-mark CAS, one-shot pending intent, and cancellation behavior.
- Use the already-required authoritative ObjectShow readback before event publication. There is still one capture and two apply-path reads; no additional read is introduced.
- Check owner lifetime and verify the entire returned target block, intended mark mutation and receipt digest before publication.
- For the two-message native event, independently require valid preflight and post-Apply rows for the exact object, empty sub-object/unknown fields, exactly nine unique allowed typed metadata entries, and byte equality of every original event value with authoritative readback. A missing, foreign, stale, malformed, denied or concurrently changed readback fails without publication.
- Publish the unchanged original native event once through the existing fenced Invocation handler; no event/ACK is synthesized, and no failed capture is retried.

## Evidence added for the actual Apple run

The existing DEBUG Simulator mounted observer copies the actual client call results only when the existing owned mounted diagnostic is enabled. It performs no native operation. Original Preflight protobuf, original native reply JSON, and original readback protobuf are written as private App Support files and bound to the capture receipt by byte count/SHA-256. The controller preserves them under `work/private-native-boundary` with mode 0700/0600 before simulator cleanup. Raw payloads are outside the uploaded evidence directory. The uploaded comparison contains only identities already bound by the existing fixture checks, field names/counts and cryptographic digests.

The independent Python reader checks actual object/space/block scope, the native receipt against the UI receipt, all nine event values against post-Apply protobuf values, and marks from all three boundaries against the original fixture/UI result. It records which projection keys were absent preflight. The original UI test bytes, actions, assertions and deadlines are unchanged.

## Validation performed

The retained Swift package/cache was reused after archiving and verifying its prior source and nine original compiled products/resources. Incremental build took 124.64 seconds. The 27 selected tests passed in 6.73 seconds: 22 client lifecycle/publication controls, four projection/wire controls and the observation phase/error matrix. Source manifest, original build/test receipts and named test log are in `host-controls/`. These are Swift host controls; the native SDK body, App wrapper, mounted editor and simulator were not executed by them.

The four independent collector tests use the unchanged native fixture plus explicit negative mutations. Their source digests and observed original SentinelX result are in `boundary-controls.json`. They prove parsing/qualification behavior only.

Outstanding at the initial source checkpoint (the subsequent Apple result is recorded below): source-bound Apple build, original mounted Cancel/Create/one-publication/cold-reopen journey, exact private boundary comparison, broader Task E integration requirements and final integrated release qualification. No physical-device, shipping or full Task E success is claimed here.

The inactive Oracle compiler output cache was removed after preserving and verifying all nine current compiled test products (169,285,147 bytes). The current product preservation receipt is retained beside the source/test receipts; reproducible compiler intermediates were the only removed data.

## Actual Apple qualification — run 45536229185

GitHub Actions completed successfully on `781340ad1efb62fb4d8515345b501081c3f22c21`:
https://github.com/davidpovarsky/anytype-swift/actions/runs/45536229185

The original App and UI runner were built once against the unchanged qualified native154 runtime. The original preparation method passed 1/1. The unchanged `testActualTextSelectionCancelThenCreateAndColdReopen` passed 1/1 in 50.345 seconds, with zero failures or skips, on ARM64 iPad Pro 13-inch M5 / iOS 27.0 (24A434), Xcode 27.0. It exercised actual native text selection, Cancel without Apply, one explicit Create, one ordinary document publication, the rendered native mark, and reopening the same persisted page in a different App process (486 → 784).

The independent comparison of all three actual client results also passed. It now directly proves the missing fact from the earlier debugger observation: **all nine Torah projection fields were absent in the real preflight and materialized after Apply**. The original native two-message event contains exactly those nine typed fields, each byte-equal to the independent authoritative post-Apply readback. The before/event/after mark comparisons, receipt bindings and exact publication count also passed. No diagnostic engine calls or synthetic acknowledgments were used.

| Original private result | Bytes | SHA-256 |
| --- | ---: | --- |
| ObjectShow preflight | 4,407 | `1a46a21553032f41d491ba1b59e3437f898335289f85c803168d2d352416ab98` |
| Native applied reply | 2,302 | `9027802808687fe168fc111e87398a511b001e21c5295c6876ca13be278418e9` |
| ObjectShow readback | 5,123 | `e005d51501935afad1a7cf0217b9d251833d69d8800c7cca194cd334f7170e97` |

The complete source and original 5,006 App / 29 UI product entries remained unchanged after execution. Cleanup completed successfully, with no owned process groups left and the owned simulator deleted. After the workflow and artifact upload finished, the complete run root was atomically retained on the same filesystem at:

`/Users/m1/builds/_retained-anytype/45536229185-1/build/current-page154-45536229185-1`

This includes original Products, derived inputs, both xcresults, all receipts and the private raw boundary directory. The original directory inode and 11 critical receipt/descriptor/private-file hashes were verified across the move. Retention receipt SHA-256: `becd2206e966dc53dc9b70f96c37a312655307ff0b5dfaff1132f37a749f4015`.

The GitHub evidence artifact is `14988372464`, 736,117,517 bytes, SHA-256 `f6c7e3a11c04338eeefdd4dfa4868c2154d26d4ba61d20b45bcc08bdba0b1e56`. The raw three boundary payloads remain outside uploaded evidence and are not committed. `actual-apple-45536229185/` contains the exact original xcresult summary/test exports, bounded comparison and retention receipts, and a source-bound qualification record. Its eight-file transfer manifest was verified on Mac and Oracle; `QUALIFIED.json` SHA-256 is `fc557f26c0f1284b3c038f5677097db5833d32390539ab9b57b4df6d74fee691`.

### Remaining Task E scope

This qualifies the repaired Heart Page154 mounted capture and cold reopen at the exact tested source. The prior `45498082340` failure remains unchanged. Full Task E is still open: arbitrary post-capture editing/content changes and synchronization in the actual UI, native Any editor anchor integration, final combined-runtime compatibility, and physical-device acceptance require separate proof. The next Any integration is isolated source work and receives no acceptance credit from this Heart run.
