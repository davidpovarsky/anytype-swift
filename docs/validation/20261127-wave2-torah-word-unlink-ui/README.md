# G02 — original Properties Word cancellation, unlink and cold retention

This is a future test-only addition on the isolated Wave2 Torah UI branch. It appends a new suite to `PinkhaStage1Acceptance/Tests/AnytypeComprehensiveAcceptanceUITests.swift`. The entire previously published G03 file remains its byte-identical prefix. It does not change App behavior, the original NativeDerived preparation, a Native contract, storage, or the current frozen shared product.

## Scope and actual fixture

The original `TorahNativeDerivedProductIntegrationTests/originalProductPipeline` writes `pinkha-native-derived-ui-fixture.json`. Its `documents` dictionary supplies the three distinct `chiddush`, `article` and `research` objects. Each retains its original Type. `names` supplies their real names. `typeSwitch.types[role]` supplies observed Type-row metadata for all three roles; only that metadata is reused. The separate reserved Type-switch object is never opened or edited by these cases.

The original preparation removes its three document-level Source/Topic/Word seed associations before handoff. It leaves a block-scoped Exodus 3:2 association on the chiddush document. There is no prepared Tag/value baseline for these three writing objects. This addition therefore seeds or observes the actual canonical selections through their original UI and creates one ordinary native Tag option per role through the original Add property/option UI. The later native baseline must preserve all additional block associations and unknown native fields.

## Four stages on one owned fixture

| Order | Execution | Required evidence |
| --- | --- | --- |
| 1 | UI `testSeedOriginalWordUnlinkFixturesThroughProperties` | Actual original Source/Topic/Word picker selections, original Tag creation, subscribed parent property rows, cold reopen, Type-value identity and kept JSON/AX/PNG attachments for all three objects. |
| 2 | Separately gated read-only hosted baseline | Actual ObjectShow identities/Space/Types/native values, canonical document records and all additional records, derived projections/labels, ordinary Tag options/property metadata, original installation/fixture/source custody, and the validated actual stage-1 UI receipt. |
| 3 | UI `testChangedQueryPickerCancelThenWordUnlinkAndColdReopenForAllWritingTypes` | Exact raw native UI-baseline bytes/hash, real changed-query picker dismissal, retained sole Word selection, original immediate Remove link, distinct-PID cold reopen, empty Word picker plus retained other displayed rows for every role. |
| 4 | Same read-only hosted selector in postflight phase | Baseline minus exactly the selected document Word record/projection; preserved Source/Topic/Tag/Type/name, block associations and unrelated native fields. Any genuinely mutable engine-clock fields must be explicitly retained and reported by the native verifier. |

There are **two new XCTest methods and two XCTest cases**, each iterating the same three original writing roles. These loops are not reported as six separately enumerated XCTest cases. Stage 1 has a 900-second allowance; stage 3 has a 600-second allowance. Original methods and their budgets remain unchanged.

The native baseline/postflight is owned by the editor agent and is a separate source tranche. This UI source is not sufficient to report persisted-value acceptance. The four-stage consumer remains closed until those source/receipt bindings and an actual compiled Apple product are qualified.

## UI selectors

```text
PinkhaStage1AcceptanceUITests/PinkhaTorahWordUnlinkAcceptanceUITests/testSeedOriginalWordUnlinkFixturesThroughProperties
PinkhaStage1AcceptanceUITests/PinkhaTorahWordUnlinkAcceptanceUITests/testChangedQueryPickerCancelThenWordUnlinkAndColdReopenForAllWritingTypes
```

Use the original English `properties` lane and its exact shared disposable startup binding. Stage 1 additionally requires `PINKHA_G02_UI_PHASE=seed`; stage 3 requires `PINKHA_G02_UI_PHASE=unlink`. No stage may substitute a synthetic fixture, omit the original successful preparation/owned simulator/admission evidence, or replay accepted unrelated T5/quote/Topic/drag journeys.

The later controller must enumerate these exact selectors from the actual admitted complete Stage1 UI product. Source linkage or syntax parsing does not establish that the selectors are compiled or runnable.

## Actual observations and receipt boundary

UI JSON attachments use `pinkha-g02-word-ui-observation-v1`. The final seed attachment is `word-unlink-seed-complete`, with `documents[role]` fields:

```text
objectID, typeID, name, sourceLabel, topicLabel, wordLabel,
tagPropertyName, tagName,
sourceAction, topicAction, wordAction, observedRows, appPID
```

Source/Topic expected labels come from the real fixture. The selected Word label is read from the sole selected canonical preview, rather than guessed from the search query. Existing earlier original Properties selections may be observed; an absent selection is linked through the real fixed-scope picker. Ambiguous/multiple selections fail. The receipt records whether each selection was linked here or observed already present.

Each ordinary Tag is named `G02 <role> <first-eight-startup-token-characters>`. The existing original Tag property is selected under `Existing properties`, never the new-property-format row. The document's original Tag value must initially be empty. No existing Tag is cleared or replaced. The native baseline must establish that the actual property key is the ordinary native Tag key and that the actual selected Tag option matches this name; a visible label alone does not establish native identity.

`PropertySelectedOptionsModel` publishes its selected IDs before awaiting the property write. Therefore this test does not use the list's `Clear` button as a persistence barrier: it dismisses that exact observed Tag sheet, waits for the parent document's subscribed original Tag row, and then cold-reopens it.

The compact native baseline has schema `pinkha-g02-word-native-ui-baseline-v1` and is retained as `pinkha-g02-word-ui-baseline-<TOKEN>.json`. Stage 3 receives the exact raw compact bytes in `PINKHA_G02_BASELINE_UI_JSON` and their hash in `PINKHA_G02_BASELINE_UI_SHA256`. It binds the full `nativeBaselineSHA256`, actual `seedUIReceiptSHA256`, Space and original controller evidence. Its per-role native-derived fields include:

```text
objectID, typeID, name, sourceLabel, topicLabel,
wordRecordID, wordIdentity, wordLabel,
tagPropertyName, tagID, tagName
```

The native Word chip exposes a human label, not its record ID. Accordingly, the UI asserts the sole matching label in the exact document/fixed Word scope and records native IDs expressly as **native-baseline provenance**. The native postflight establishes which stored record was removed. The shared original English display formatter resolves labels; it is not reimplemented in the readback.

The controller dictionary retains these original startup keys:

```text
SOURCE_SHA, RUN_ID, RUN_ATTEMPT, TOKEN, SIMULATOR_UDID, LANE,
ADMISSION_SHA256, PREPARATION_SHA256, INVOCATION_SHA256,
OWNED_SIMULATOR_SHA256, FIXTURE_SHA256
```

The native verifier and future controller must bind these to actual source/products, original preparation, actual owned installation, successful UI result and exact retained attachment bytes. Supplying an arbitrary JSON object with plausible hashes is not admission.

The hosted reader is gated by `PINKHA_G02_NATIVE_READBACK=1` and `PINKHA_G02_NATIVE_PHASE=baseline|postflight`. Both phases consume the exact original fixture, the eleven original controller values, and `PINKHA_G02_SEED_UI_JSON`/`PINKHA_G02_SEED_UI_SHA256` from the actual successful seed-complete attachment. All native preparation/account-creation flags must be zero. Postflight also requires `PINKHA_G02_BASELINE_SHA256` for the retained full native baseline and `PINKHA_G02_UNLINK_UI_JSON`/`PINKHA_G02_UNLINK_UI_SHA256` from the actual successful unlink-complete attachment. Its exact native source/selector receipt is a separate companion and remains required.

## Cancellation and completion semantics

Cancellation means typing a distinct query, then closing the existing fixed-scope picker through its observed sheet chrome without tapping Link or Remove link. It must return to the parent Properties in the same App process and retain the baseline Word and other displayed values. This is not a test of a confirmation dialog: the original Remove link action commits immediately.

Before unlink, the exact Word preview must contain one selected chip and one enabled/hittable Remove link control. Completion requires the original persistence strip to disappear; a waiting, saving or error strip does not pass. Every document is then reopened in a different observed App PID. Word must be empty in both the original property row and its fixed-scope picker, while Source, Topic, Tag and the exact original Type remain displayed.

Each method terminates its owned App and awaits process exit before a native host may open the same store. It does not create, restore or switch accounts. The original exact two-action middleware-warning helper remains the only permitted startup-warning handling.

## Evidence and remaining gates

The exact prefix/append inverse proves that all seven original/G03 test methods and helpers remain unchanged. Keep all syntax attempts and source-review receipts, including earlier candidates; later source must not silently replace their hashes.

Status before Apple execution: **Apple typecheck, actual compiled enumeration, XCTest UI, visual review, native baseline/postflight, and physical-device acceptance are NOT_RUN**. The bounded Linux Swift syntax parse is explicitly syntax-only. No Simulator/App build or launch was performed by this tranche.

Actual acceptance requires all four stages to pass on the admitted shared build with the same owned fixture, preserved full xcresult/log/JSON/AX/PNG evidence, and subsequent visual inspection. Rendered labels and an empty field alone do not prove persisted retention. This case does not cover Hebrew/VoiceOver, cross-Space authorization, Topic/Word navigation destinations, or the separate remaining Page154/T5 contracts.
