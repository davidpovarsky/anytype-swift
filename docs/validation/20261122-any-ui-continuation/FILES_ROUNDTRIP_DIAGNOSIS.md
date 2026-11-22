# Files roundtrip: original failure and minimal candidate

The original case has two concrete problems: its import picker opens a different directory from the actual preceding export, and its 360-second whole-test limit expires before the full multi-phase journey can complete. This is an original failed case, not a flaky pass or full migration evidence.

## Original source and evidence

Run `45038244641`, job `137256671984`, App commit `07c3568f9f9cf4044dd81163cd374d4ad35330cb`. The root verified the original artifact SHA256 `631272ec9be40f243645009f181ee3f83dbbb0eb57e47a6ab92e59aca0d1a3cb`. Its original `archive-roundtrip.xcresult` reports one case, zero passes, one failure, exactly 360 seconds, with the issue “Test exceeded execution time allowance of 6 minutes”.

The current source was fetched separately at `e5f4697c9e8cbda7448e9cba59e64de5535ec28e`. `Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeArchiveTransfer.swift` is byte-identical to original07c: Git blob `499a86475aa176488949b95e917ff93d92d05b5b`, SHA256 `613a85b5fab49ed8fe3bd15b9987c8c965b63a3f318e37e6164364d56c3b631d`.

`BOUNDED_FILES_EVIDENCE.json` records exact original activity IDs, selected system folder observations, hashes and scope. `APP_STDOUT_MANIFEST.json` and `RUNNER_DIAGNOSTICS_MANIFEST.json` identify the read-only extracted original diagnostic files. The post-import system UI evidence is in the original runner session log, not inferred from a cached pre-tap screenshot.

## What actually happened

| Original point | Observation |
|---|---|
| Export dialog, 16:16:14–16:16:42 | Live DocumentManager `21478` has the current-folder button `Pinkha, תפריט פעולות`. The save_READY screenshot independently shows the same folder and the typed unique source filename. |
| Test +266.43 s | Actual system Save tap. |
| Test +270.80 s | `any-native-archive-exported-file` matches the complete unique source `.json` filename. This is the real successful export callback, not modal coverage. |
| Test +290.28–305.56 s | Destination is created and its native body reaches `saved`. |
| Test +316.56 s | Actual `any-native-archive-import` tap. |
| Import dialog, 16:17:41–16:18:15 | Fresh system AX has `Exports, תפריט פעולות` and the empty-folder label. Exact filename queries keep returning no match. |
| Test +360 s | Global case allowance expires while the importer is still waiting for the filename. |
| Runner +373.34/373.91 s | The per-condition failure handler records import_NOT_READY AX/screenshot activities in the runner log. These late attachments were not preserved in the test database's original activity/attachment rows. |

The last four exported snapshot attachments all precede the import tap and share the same decoded hash. They contain old exporter controls; that does not establish that the exporter remained open. Fresh post-import runner-session AX resolves the ambiguity: a live import browser is open in **Exports**, and it is empty.

The repeated missing-remote-process `57557` warning appears from +16.69 seconds and also around successful export actions. It is not evidence that this failure was random. The useful folder evidence comes from a different live system process, `21478`.

The captured spindump places the test runner in `importUsingFiles`' filename expectation, then in its diagnostic capture after that condition expires. It does not show a migration append hanging. The archive has not been selected, mapped or imported at this point.

## Why the source permits the mismatch

`userExportsDirectory()` creates and validates the user-visible `Documents/Exports` directory. The view chains a `fileExporter`, a `fileImporter`, and then a single `fileDialogDefaultDirectory(exportsDirectory)` modifier. The importer observably receives Exports while the exporter opens Pinkha.

Apple documents this modifier as configuring a file export/import/move dialog's initial directory and lists iPadOS17+ availability. Its public documentation does **not** explicitly describe the precedence of two chained dialog modifiers. Therefore, identifying the outer importer as the consumer of the sole current configuration is a source-and-runtime inference, not a claimed documented implementation guarantee.

Primary API documentation: https://developer.apple.com/documentation/swiftui/view/filedialogdefaultdirectory(_:).md

## Minimal product candidate

`archive-dialog-default-directory.patch` adds one line immediately after the exporter:

```swift
.fileExporter(/* existing arguments and completion */)
.fileDialogDefaultDirectory(exportsDirectory)
.fileImporter(/* existing arguments and completion */)
.fileDialogDefaultDirectory(exportsDirectory)
```

Both dialogs keep the real system picker. Filename editing, export success URL, user file selection, security-scoped reading, bounded coordinated read and explicit mapping remain intact. There is no injected file URL, direct file selection, automatic import or new cross-account preference storage. Users can still choose another directory and navigate to it manually.

The candidate is in `implementation/Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeArchiveTransfer.swift`, based on the exact e5 source. `PATCH_MANIFEST.json` records before/after hashes. No shared/root merge file was edited. This one-line candidate still requires the real mounted Apple roundtrip; static inspection does not certify SwiftUI presentation behavior.

## Focused test correction

Root selected a **1,800-second cap for this case only**, covering three real exports, one import, explicit mapping, native receipt/body checks and one process cold restart. Keep individual readiness and filename waits bounded, including the current 45-second filename wait. The dedicated archive workflow's `-default-test-execution-time-allowance` and `-maximum-test-execution-time-allowance` must both be 1800; setting XCTest's per-case property alone cannot overcome a lower CLI maximum.

The current source export reaches its success callback only at +270.80 seconds, and destination/import presentation consumes the next ~46 seconds. Even immediate filename discovery would leave ~43 seconds for mapping/confirmation, native receipt, all cold reads and two further exports under the old cap. Raising this case cap is needed independently of the directory fix; it does not repair filename discovery on its own.

`NATIVE_LAUNCH_INSERTIONS.swift.txt` supplies separate review-only insertions for the root-owned merged test: per-case allowance, actual Exports current-folder checks, and import presentation capture after a real system Cancel control is ready, before the filename wait. The existing complete mapping/body/cold-reopen/three-export proof stays intact. Capturing the actual picker early avoids losing the decisive directory snapshot after the global deadline.

Run only this failed archive case after integrating the product candidate and the already planned shared UI changes. Use the existing named execution verifier and `verify_archive_roundtrip.py` postflight to inspect the three actual exported JSON files and receipt. Do not reuse the first successful export as full roundtrip acceptance or rerun unaffected passed suites just for this one-line change.

## Scope

This UI journey transfers canonical source associations and proves explicit mapping while preserving both native document bodies. Its own product text says document body content and attachments are not part of the archive. It is separate from the native full-Space migration work; native prepared `file` capability remains `0`, and MIG-01 is not completed by this roundtrip.
