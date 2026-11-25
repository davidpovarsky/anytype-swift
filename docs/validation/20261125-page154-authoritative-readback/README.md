# Page154 authoritative post-Apply projection — 25 November 2026

Status at this source checkpoint: product fix implemented; 27/27 affected Swift host controls and 4/4 independent collector controls passed. Full Apple mounted UI acceptance remains required. Task E is not complete.

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

Outstanding: source-bound Apple build, original mounted Cancel/Create/one-publication/cold-reopen journey, exact private boundary comparison, broader Task E integration requirements and final integrated release qualification. No physical-device, shipping or full Task E success is claimed here.

The inactive Oracle compiler output cache was removed after preserving and verifying all nine current compiled test products (169,285,147 bytes). The current product preservation receipt is retained beside the source/test receipts; reproducible compiler intermediates were the only removed data.
