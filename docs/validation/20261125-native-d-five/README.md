# Native D: five independent remaining journeys

Product source: `e0c88c3224c88484b6cacf0f8f834057a81ff26c`, based on shared `8da18fce1b59a10a9bd46f0dc3becd810d45dc80`.

## Change and admission

The List reordering callback is now nil outside editing mode. This removes the system List move interaction while the explicit folder drop handler is active. Drag payload, workspace/write guards, native move, context-menu move, and original XCTest assertions are unchanged. This is a proposed product fix pending an actual Apple result.

One current App/UI build selects exactly five original methods: hierarchy drag, Hanlin selected context and separate creation consent, archive Files roundtrip, custom type, and history. Each receives an independent original result. Type/history no longer depend on unrelated picker or provider success. Source/dependency identity and cancellation remain hard gates, and aggregate success still requires every stage and provider contract to pass. Archive runs on a fresh owned simulator to distinguish system Files/provider carryover from the original strict navigation failure. No picker target, deadline, gesture, validation, or archive assertion was changed.

## Retained evidence

The unchanged context-menu hierarchy Move journey passed in run [45472843335](https://github.com/davidpovarsky/anytype-swift/actions/runs/45472843335), source `fb5b40a5e91c68520d0f2921600a9f04b1e25439`. Exact original `tests.json`, `summary.json`, and `execution.json` are preserved in `Tools/CurrentAppleValidation/retained-hierarchy-move/`. The original run remains FAIL (one PASS/two FAIL in its first three methods); historical evidence is never relabeled as a current test.

The admission hashes all three originals, requires the exact native test/app tree, and checks the reviewed five-file Modules delta. Four changed files concern Heart semantic anchors, outside this native journey. The sole Any UI delta is the reviewed List callback change; the context-menu move service and operation remain exact. Any new dependency delta fails reuse and must be reviewed.

## Validation performed before Apple

- Python parse of three changed controllers: PASS.
- `git diff --check`: PASS.
- Existing source identity/retained product controls: 6/6 PASS.
- Exact five unique selectors, retained hierarchy result hashes and dependency delta qualification: PASS.
- New Apple compilation and five UI journeys: PENDING. No product acceptance is claimed here.

## Other observations

The original archive failure was inspected in actual xcresult activities, screenshot and AX: Files synthesized the single Pinkha folder icon tap but stayed in On My iPad; no export callback occurred. The product already creates and validates Documents/Exports before presenting its native file exporter. This controller isolates the system environment while keeping every original assertion.

MiniApps integration owner is active in Asana task 1220820444037166. Its Heart bridge/worktree is preserved; AnyNative scope was explicitly queried. The shipping Anytype target currently has no linkage to PinkhaAnyUI or AnyNativeRootView, which are present only in NativeApp. Shared root composition is being developed separately so the D diagnostic source stays immutable.
