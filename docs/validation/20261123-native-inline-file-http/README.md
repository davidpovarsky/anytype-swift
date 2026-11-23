# Prepared inline-file HTTP candidate

The native public HTTP implementation is qualified by three new top-level controls and 18 strict-input subcases on Linux ARM64. The real Swift-to-native handoff is also qualified by one actual Swift XCTest and one independent native bridge test. The first fixture failure is retained; public client and native production sources were unchanged. Apple and network acceptance remain open.

The immutable source manifest deliberately retains `OPT_IN_SOURCE_CANDIDATE_PENDING_QUALIFICATION`. Qualification receipts describe actual executions separately, so later evidence does not change the native source identity.

## Source identity

| Input | Identity |
| --- | --- |
| Candidate version | `v0.5.0-pinkha.prepared.inline.1` |
| Source manifest SHA-256 | `86598a7046ef135fa5dd2d0c2e559750f89ed8517fe4c1c753ce4457c13a009b` |
| Any upstream | `88fae2e5ae7d0f46d6707567a3123081faa8de9a` |
| SDK upstream | `854df54cdadd76006ae823cbd1b1d923138356d0` |
| Any effective tree | `0445217b25b4f4fcf4d2ce86e3a4eecfcfc5cd10` |
| SDK effective tree | `8b9df2cdcefb5aee3973df11a326652f5a2378f4` |

The new manifest and full Any/SDK patches are under `Tools/AnyEngineValidation/evidence/native-prepared-inline-file-http-v1-candidate-*`. Both patches were applied independently to clean checkouts of the exact upstream pins. Their complete staged trees and all changed source bytes matched the recorded candidate.

[Source retention](source-retention.json) records 61 unchanged v11 Any overlay paths, one changed registration path and four additions. The SDK retains 60 unchanged overlay paths and changes only its inline commit publication wrapper. [Reconstruction](source-reconstruction.json) proves the full patches stand alone. The frozen v11 manifest, patches and controller are not changed.

## Executed native scope

| New control | Result |
| --- | --- |
| `TestPreparedInlineFileHTTPStrictInput` | PASS, including 18 named rejection subcases and valid 0/4095-byte input. |
| `TestPreparedInlineFileHTTPNativeLifecycleAndPublication` | PASS: real HTTP prepare/root/row commit, native status/Get/Open inside the callback, exact Unicode metadata and bytes, ordinary HTTP content, unchanged retry identity, one event per new row. |
| `TestPreparedInlineFileHTTPRefusesBeforeNativeReservation` | PASS: 4096/4097 bytes refused before intent reservation, no event, general file/network capabilities remain disabled. |

The original Go JSON records exactly three top-level passes, zero failures and zero skips. Package execution took 2.038 seconds; the cold compilation plus execution took 910.294 seconds. Compiler: Go 1.27.4, Linux ARM64, host GCC/glibc, `GOMAXPROCS=1`, `-p=1`, `-count=1`. The original exact localhost-only node configuration was verified byte for byte. Source hashes were unchanged.

See [core qualification](core-native-qualified.json), [original command and source hashes](core-native-status.json), and [compressed original Go JSON](core-native-original.jsonl.gz). This scope does not rerun or relabel the older object/block, inline-native or Swift portable evidence.

## Swift bridge boundary

The opt-in native bridge is protected by the `pinkha_inline_http_bridge` build tag and a separately selected test name. It is compiled with the new core controls but not run by their selector. It owns a fresh loopback HTTP server, publishes a complete nonce-bound handshake atomically, and waits at most five minutes for the separately executed Swift client.

The first live attempt is preserved in [bridge-attempt1-original](bridge-attempt1-original/failure.json). The empty file completed. The next preparation correctly reported `file-root-committed` because the same owner's payload root existed, while the Swift live fixture incorrectly required `file-prepared` again. The client reported failure; the native verifier refused acceptance and closed its owned server. No native source correction was made.

A successful bridge qualification requires both the original one-method Swift XCTest receipt and the original native bridge pass, with independent native receipt/specification/Get/Open/status-event verification. It is not established by a `completed` JSON field alone.

## Joined real Swift and native qualification

[The joined qualification](bridge-qualified.json) binds both original terminals to the same fresh nonce, handshake and exact result bytes. The repaired live fixture required the exact first-file file-prepared stage, the second-file file-root-committed stage, the shared payload root and distinct row/file identities.

The original Swift XCTest passed once in 0.284 seconds, using the already compiled opt-in binary with all source and binary hashes unchanged. The independent native bridge passed once in 34.86 seconds including handoff wait. It re-read both original specifications, complete/committed receipts and plaintext streams through the real SDK, and observed exactly two durable/cached local events. The owned native process group was gone afterward.

Original Swift receipt/log, native status/log, fresh handshake and client observations are preserved in [bridge-attempt2-original](bridge-attempt2-original/native-qualified.json). Only the failed live integration method was repeated. The core 3/18 and portable Swift 12 scopes remain separate retained executions; they were not rerun for this fixture correction.

## Capability boundary

[CONTRACT.md](CONTRACT.md) records the four routes, exact five-field specification and stage semantics. Original inline plaintext is bounded to 0 through 4095 bytes. General file capability remains zero and network verification remains false. Local status callbacks are transient live notifications, not a durable outbox.

The explicit Apple runtime selector, new original Apple native build, C linkage, simulator/device execution, network delivery and whole-space snapshot acceptance are separate gates. This candidate changes no default runtime selection.
