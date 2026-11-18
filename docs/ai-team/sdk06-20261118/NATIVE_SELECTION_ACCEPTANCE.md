# Independent Hanlin selected-block acceptance

This is a separate Debug simulator lane. It does not change the existing 22-check document-only lane or its acceptance schema. After full content review and verification that every target was new, the six-file transparent structured patch was allowed and applied to the SDK worktree. All six hashes were independently verified against the reviewed manifest. The earlier opaque bundle operations remained rejected and were not retried.

## Exact execution selection

| Item | Required value |
| --- | --- |
| Proposed lane | `hanlin-selection` |
| App configuration | `Debug-Anytype`, existing `PINKHA_NATIVE_DERIVED` simulator build contract |
| Preparation selection | `AnytypeTests/HanlinSelectionAcceptancePreparationTests/prepareSelectedBlockFixture()` |
| UI selection | `PinkhaStage1AcceptanceUITests/HanlinSelectionAcceptanceUITests/testRealSelectedBlockReadAndReturn` |
| Preparation count | One actual selected test, no failure or skip |
| UI count | One actual selected test, no failure or skip |
| Companion fixture | `pinkha-hanlin-selection-fixture.json` in the fresh app's Application Support |
| Result | `pinkha-hanlin-selection-result.json` in that same app container |
| App final phase | `HANLIN_SELECTION_ACCEPTANCE_PASS` |
| Status accessibility ID | `pinkha.hanlin.selection-acceptance-status` |
| Result validator | `Tools/PinkhaSimulatorGate/hanlin_selection_evidence.py` |

The caller must retain its existing immutable source/runtime/dependency/executable identity checks and its actual xcresult method/count/no-skip checks. Receipt validation alone is explicitly not an XCTest, UI, or full SDK acceptance result. Run independently on the requested phone and tablet before claiming both form factors.

## Preparation and environment

The new preparation calls the existing real `HanlinNativeAcceptancePreparationTests.prepareRealHostFixture()` as a helper. That helper requires a fresh empty account, disables native logging, creates a disposable local-only account/Space/page, writes the first unique paragraph, and reads it back through the real native service. The new method creates a second paragraph through the same `BlockService`, reads back both exact IDs/texts, closes the document, and saves the companion fixture without overwriting an existing fixture.

Preparation environment:

- `PINKHA_PREPARE_HANLIN_SELECTION_UI=1`
- `PINKHA_SIMULATOR_UI_DISPOSABLE=1`
- `PINKHA_SIMULATOR_ACCEPTANCE_PREPARATION=1`
- The existing helper may keep `PINKHA_HANLIN_NATIVE_PREPARATION=1`.
- `PINKHA_HANLIN_SELECTION_SOURCE_SHA`, `PINKHA_HANLIN_SELECTION_RUN_ID`, `PINKHA_HANLIN_SELECTION_RUN_ATTEMPT` bind the exact run.
- `PINKHA_HANLIN_NATIVE_SOURCE_SHA`, `PINKHA_HANLIN_NATIVE_RUN_ID`, `PINKHA_HANLIN_NATIVE_RUN_ATTEMPT` must have the identical three values for the reused helper. The new method explicitly compares them before calling it.
- `PINKHA_HANLIN_NATIVE_UI` must not be enabled.

Fixture JSON has exactly `base`, `excludedBlockID`, and `excludedText`. `base` is the existing 14-field native fixture, unchanged. `excludedBlockID` must differ from `base.sourceBlockID`; `excludedText` is `Hanlin unselected body ` plus the same fixture UUID. The original selected paragraph is `base.sourceText`.

The validator exposes the same two entry points as the document-only helper:

```python
fixture_environment(value, source_sha, run_id, run_attempt, now, raw_json)
validate_result(value, fixture, source_sha, run_id, run_attempt, now)
```

`fixture_environment` returns `PINKHA_HANLIN_SELECTION_UI_TESTING=1`, disposable flag, the exact original JSON in `PINKHA_HANLIN_SELECTION_FIXTURE_JSON`, and the three selection source/run keys. The UI test cold-launches the app with `PINKHA_HANLIN_SELECTION_UI=1`, `PINKHA_HANLIN_SELECTION_FIXTURE_ID`, the same three identity keys and the existing route-observation flag. It never enables the document-only driver.

## Native UI and authority proof

The test waits for the actual Home control before using the existing object URL. It requires the exact full Space/object editor marker via `NSPredicate`, finds both prepared text views by their exact synthetic values, and performs a real 0.6-second long press on the selected paragraph. It requires the production `pinkha.hanlin.open.selection` button to become hittable and taps that button. The driver requires the actual editor mode and context to contain exactly the prepared block ID; it never sets selection.

Read is denied before consent. XCTest presses the existing Share control and the actual native Allow button. The canonical dispatcher then reads the native host. Acceptance requires `selectedTextBlocksOnly`, exactly the selected block ID/text, the current revision/object/Space/title, and exclusion of the second paragraph. Only the text's SHA256 is retained in the read receipt; the host's own metadata receipt must contain no payload.

XCTest presses the production Return button. The driver asynchronously observes the production handoff's completed metadata receipt; it never invokes `acknowledgeMounted` or constructs a navigation result. It requires the original request, session, context, document and selected block. The original editor, exact datasource item, visible index and cell in the same foreground scene must exist. The UI independently requires the original editor, selection entry and visible text frame after dismissal. Two new valid read invocations against the closed host must remain denied while the original selection still exists. This is two measured post-close denial observations, not a claim of executing an old approval callback or testing arbitrary future timelines.

Nine required checks:

1. `middleware_logging_disabled`
2. `native_single_block_selection_context`
3. `read_denied_before_native_consent`
4. `native_selected_text_read`
5. `unselected_text_excluded`
6. `read_receipt_contains_metadata_only`
7. `native_selected_block_mounted_on_return`
8. `closed_selection_host_denies_read`
9. `no_provider_configuration`

The result binds fixture/source/run/attempt/session/PID and dates, original navigation context, the selected read metadata, the native return metadata, and three distinct valid denial invocation IDs (one before consent, two after close). Extra receipt fields, unmounted or mismatched return, whole-document or multi-block scope, wrong digest, missing checks, duplicate denial identities, provider configuration and inconsistent dates are rejected.

## Source integration

`Anytype/Sources` and `AnytypeTests` use existing synchronized Xcode root groups. The new app driver/fixture and preparation test therefore require no manual App-project membership change. The new UI file requires a normal four-entry registration in `PinkhaStage1Acceptance/PinkhaStage1Acceptance.xcodeproj/project.pbxproj`; proposed unused IDs are `B71000000000000000000001` (build) and `B71000000000000000000002` (file), to be rechecked before applying.

The only existing app-file hook is two lines in `PinkhaHanlinChatPresentation.didMount`, under its existing `#if DEBUG && targetEnvironment(simulator)`, calling the new driver's gated `startIfRequested`. There is no change to production selection/navigation handlers or the original UI22 schema. `Services` explicitly re-exports `Factory` in `Modules/Services/Sources/ServicesDI.swift`; the preparation uses the same import pattern as the existing native preparation.

The separate production selection-fence correction is already published as `2041cd135f87702d5ef3d6b95a5e40de701ae106`: SDK inventory 67 methods, four explicitly required selection-transition tests, 33 Python controls passed. This UI source has 13 validator controls passed on both Linux and the actual Windows worktree. The Windows raw log and source hashes are retained under `selected-block-ui/`. Swift parsing/typecheck, the four new component executions, native preparation and actual selected-block XCTest are all still NOT_RUN. Root owns the UI-project registration and new caller/workflow lane; those must be integrated before dispatch.

Provider networking, live model calls, arbitrary multi-block/table UI selection and existing-document writes are outside this narrow lane's acceptance claim.
