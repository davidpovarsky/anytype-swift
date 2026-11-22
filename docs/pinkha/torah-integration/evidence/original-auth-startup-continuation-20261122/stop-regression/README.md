# Original Auth Stop regression controls — 22 November 2026

The one executable run compiled and ran ten new Swift unit controls on SentinelX Windows `david_and_goldy` using the recorded Swift 6.3.3 compiler. Result: **10 PASS, 0 FAIL, 0 SKIP**. No previously passed controls were rerun.

The generated harness contains exact declaration fragments from Auth source `edded737125fea403d2a59674d56a70b6166cf16`: both `logout` bodies, the original attempt and transition ownership, original write lifetime/admission helpers, admission guards, and `LoginStateService.StartupTasks`. Its native queue, callbacks, account storage and login cleanup are explicitly controlled fixtures. This verifies the tested ownership and cancellation behavior at unit scope. It does not qualify the complete native Auth flow, Apple app startup, or persistence.

The cases cover caller cancellation before queued Stop dispatch and during actual cleanup, failed Stop allowing retry before the old startup drains, the failure guard after startup drain, pre-admission cancellation, and late membership installation being cancelled and drained. Both Auth actors are exercised for the overlapping Stop cases.

`SOURCE.json` records the fragment and source hashes. `AuthStopControls.swift` is the actual executed source; `EXECUTION.json`, `compile.stdout`, `compile.stderr`, `run.stdout`, and `run.stderr` retain the observed run. The executable hash and process ID are in the receipt.

That Swift 5 language-mode compile exposed two Swift 6 diagnostics about implicit `self` inside a nested dispatch closure. Commit `c689cf058cedcd683e12bd2736c196d6eda3ec17` changes only that closure's capture list to `[self]`. `CAPTURE_CHANGE.diff` reproduces the exact one-line harness change. `CAPTURE_COMPILE.json` records the follow-up **Swift 6 strict-concurrency typecheck, exit 0 with empty stderr**. This follow-up did not run the ten cases again. Their original receipt is preserved with its exact source identity.

The combined SDK source checkpoint is `9243500782566cd92df3a1468f460713ed8ea24b`. Full source, public/SPI, binary external import, and Apple resource gates remain mandatory in the single combined SDK workflow. Full native Auth acceptance remains a separate product gate.
