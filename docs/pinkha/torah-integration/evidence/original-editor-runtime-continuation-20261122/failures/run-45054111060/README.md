# Instrumented original-framework runtime continuation: actual launch failure

Run `45054111060`, attempt 1, used control source `0b792c7f2906f375e34b30a0cb42b85d98c0ba56`. Its original framework remains source `edce5b975b173059522f90adb71271fb95adf963`, run `45041382512`. The framework was not rebuilt. The original 245 source controls, 38 public/SPI requirements, 19 module maps and 1,394 declaration files remain attributed to that original producer. The 24 continuation controls and 14 instrumentation controls were admitted from their existing receipts without replay.

The actual new external consumer build completed in 41.354 seconds and its strict code signature verification completed successfully. The new owned simulator boot request and boot-status command both succeeded; boot status took 127.237 seconds under the unchanged 180-second budget. The sole installation succeeded in 40.694 seconds under the unchanged 300-second budget. Both installed application and data-container lookups succeeded.

The first English launch then failed in 4.880 seconds with exit code 3, without a timeout. `simctl` reported `NSPOSIXErrorDomain`, “No such process,” and that launch returned neither a process handle nor a launch error. No English or Hebrew resource observation was produced or verified. This packet does not qualify SDK runtime, StageB, or native editor UI acceptance.

Cleanup independently completed: the owned shutdown and targeted delete succeeded, a subsequent successful `simctl list` proved the exact owned UDID absent, and all owned process groups were drained. The primary launch failure remains a failure. Two diagnostic `simctl list` requests had earlier timed out at their separate eight-second read-only budget, while direct reads of the exact owned device plist retained native state 3. Host snapshots report 7 GiB and three logical CPUs, increasing compressed memory, and no configured swap. These observations do not identify a proven application or host cause; no crash report was captured.

## Retained evidence and signed consumer

The runtime evidence artifact is `14767271445`, 442,808 bytes, SHA256 `6c153f074318446a2a78cbf1807e177a113e0c7163c74a2ebe69e1c90be96967`. Its sole inner archive is 442,628 bytes, SHA256 `37ccba5016d8457da54945338e19e88b47f40909b2940cfbbf09f6c7ed6377b5`, Git blob `2eed122fe092fcf9781ec223d34d5cbb4d74b120`. All 210 inner members passed CRC verification, and all 209 indexed payloads match their original size and SHA256. The root review additionally verifies 206 evidence-index entries and all 85 main, cleanup, diagnostic, and GitHub command groups/streams, including two intentionally relocated binary downloads. The raw archive and all failed commands remain unchanged.

The signed consumer was archived before boot as a separate, explicitly unqualified artifact, `14766857451`. Its 141,885,343-byte outer archive has SHA256 `54e2a4b191d1248ab446273628f397bb2763c26efcf1c9648c208c3ae0469302`. The producer reports an inner `consumer-app.zip` of 141,705,455 bytes, SHA256 `ef49025e85cc27723738c0cb96cc91084412a952462627d9416bc7b3207068a1`, covering 642 files and 500,498,107 uncompressed bytes. That consumer build belongs to `0b792c7f` / run `45054111060`; any later runtime-only attempt must retain this separate provenance.

The first local signed-consumer transport attempt timed out at 180 seconds after receiving 104,087,552 bytes. Its prefix SHA256 is `7c33c5dbe342872d11d84ff11bcfcec1b6547df4f6b9d509e09d8d3f31099637`; the partial bytes and timeout are preserved. A separately recorded bounded continuation completed only bytes `104087552–141885342`, after checking HTTP 206 and the exact range/total. The full original outer SHA256, both ZIP CRCs, all 642 inventory hashes and 230 directory entries/modes then verified. The initial prefix was copied before continuation and independently verified unchanged afterward. This is transport recovery, not another build or runtime attempt.

Static inspection found a concrete relocation defect. The framework's actual `LC_ID_DYLIB` is `/Library/Frameworks/AnytypeOriginalEditor.framework/AnytypeOriginalEditor` (file offset 4,720, 104-byte load command). The linked consumer debug dylib has the same absolute path in its `LC_LOAD_DYLIB` (offset 3,680, also 104 bytes). The app embeds that framework under `Frameworks/AnytypeOriginalEditor.framework/AnytypeOriginalEditor`. `INSTALL_NAME_BINARY_EVIDENCE.json` retains the exact header/load-command bytes, offsets and hashes; `STATIC_INSPECTION.json` covers all 18 actual Mach-O files and the bundle plists. This is a real packaging defect and a plausible launch blocker; there is still no captured crash report proving the runtime cause. No retained signed binary was modified. The producer correction is prepared separately and requires a new genuine build.

## Review paths

- `PHASE_RECEIPT.json` and `TERMINAL_INTAKE.json`: compact actual outcome and provenance.
- `FAILURE_COMMAND_DETAIL.json`: exact build, signature, boot, install and launch command records plus raw launch stderr.
- `ROOT_LAUNCH_FAILURE_REVIEW.json` and `root_verify_launch_failure.py`: independent review of the unchanged archive and command evidence.
- `runtime-continuation-evidence.zip`: the complete original inner evidence archive.
- `SIGNED_CONSUMER_DOWNLOAD_FAILURE.txt`: original local transport failure.
- The transport and static-inspection receipts, when present, cover only the retained signed bytes. Static load-command inspection is not dyld execution or runtime acceptance.

No new simulator attempt, framework build, consumer build, or source/control test replay was initiated by this intake packet.
