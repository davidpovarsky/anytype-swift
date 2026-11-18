# Wave 15: shared build and stronger Properties assertions

This source change adds `remaining-release` to the existing dispatch lane field. It builds the App/native bundle once and the selected UI runner once within one job. The six existing lanes then execute with separate newly created iPads and native account fixtures. Frozen source, package locks, runtime receipt, App, test bundles, UI runner, and original xctestruns are checked before and after each lane. No earlier build artifact is reused.

The exact profile is Inspector (5), Inspector Search (1), Properties (3), Properties Set (2), Canonical Properties (1), and Editor English (3): 15 UI methods with six independent native preparations. It retains the existing 120-minute step and 150-minute job limits. The worker is bounded to 105 minutes plus three minutes for owned cleanup. Lanes that cannot fit are explicitly not run; a failed test remains a failure. Setup or identity failures abort continuation. Repeated TERM/INT signals cannot bypass bounded cleanup, and only the worker's process group and its owned simulators are terminated.

The freshness receipt records positive construction of a new device before its first App installation. A failing `simctl get_app_container` call is recorded as `NEGATIVE_UNCLASSIFIED` with its original stderr; no undocumented exit code is treated as proof of absence.

Properties now compares the reopened Word row with the actual canonical item chosen by the UI before closing its picker. It rejects placeholders and raw storage values; Source and Topic retain independent fixture label expectations. The Universal document test checks all three values together after cold reopen. Type Source addition must survive cold reopen, and prior object-local additions must not have changed the Type. Test method names and selectors are unchanged. The adjacent audit lists remaining criteria without attributing UIKit proof to native/view-model checks.

## Validation

Root independently reviewed the frozen source and ran 38 controller tests against the canonical module imports exported read-only from the clean integration source: 38 passed, zero failed, zero skipped. This includes 22 batch controls and two real POSIX process-group cleanup controls. Python AST, YAML, LF byte hashes, and the existing dispatch count of ten inputs were verified. These are controller/source results, not App acceptance.

Apple compilation and execution of this new batch are NOT_RUN at publication. A lightweight Windows Swift parse attempt through stdin hit a compiler assertion that accepts only `.swift` inputs, before parsing the source; it provides no source syntax verdict. Actual Apple compilation will validate the test changes.

## Publication under the local storage block

Windows C and G reported zero free bytes. The reviewed exact files were published to the already authorized isolated integration branch through GitHub's Git Data API, using the expected parent and a non-forced ref update. No local worktree or index was changed. The Windows integration checkout remains at `09e4287e78fb79937a83f5ed50b5d34800bc50f6` until a normal fast-forward can be performed with free space. Existing WIP and branches are retained.
