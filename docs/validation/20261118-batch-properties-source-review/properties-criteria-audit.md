# Source audit against Properties acceptance 01–06

Task: https://app.asana.com/0/0/1220541253593988

Audit source: `09e4287e78fb79937a83f5ed50b5d34800bc50f6` in `davidpovarsky/anytype-swift`. The task was read without modification. This is a source audit, not an Apple execution result. The frozen correction beside this document changes only the three identified assertion gaps; it does not turn the wider criteria into accepted results.

## Selected UI coverage

The existing `properties` lane selects three methods of `PinkhaNativeDerivedAcceptanceUITests`; `properties-set` selects two more methods of that suite; `canonical-properties` selects one method of `PinkhaTorahPropertiesAcceptanceUITests`. The source is `PinkhaStage1Acceptance/Tests/PinkhaStage1AcceptanceUITests.swift`. Their six names remain unchanged in the proposed correction.

| Task criterion | What those actual UI methods require | Additional Native/model preparation | Remaining limit |
|---|---|---|---|
| 01: Add Property on Page, Note and a custom Type; ordinary catalog survives Pinkha lookup failure | Universal objects begin without the properties, open the actual object Add Property picker, select the three native rows and subsequently open the canonical value pickers. | `originalProductPipeline` creates actual Page/Note/custom objects, provisions the native catalog, and routes empty rows through the production view models. | No selected UI method induces or observes a catalog failure while selecting an ordinary Anytype property. A healthy-catalog UI PASS cannot establish the failure-isolation clause. |
| 02: three properties discoverable with empty, Hebrew and English searches; correct object/type context | Universal object UI uses empty Add Property search; the Type picker shows all three labels and actually selects Source. The proposed patch checks that object-local additions left the Type unconfigured and that the selected Type Source persists after cold reopen. | The Native preparation calls catalog and `PropertyCreationViewModel.search` for Hebrew/English aliases, adds all three properties to an object, verifies its Type and sibling remain unchanged, and separately adds/removes all three Type properties. | The selected UI methods do not type Hebrew/English into the Add Property search. Type Topic/Word selection is Native preparation coverage, not UIKit coverage. |
| 03: empty row opens canonical picker; value persists as a real chip, filters Set, survives relaunch | Writing documents use real source/topic/word pickers. Source and Topic are checked against fixture labels. Source filters are edited through the actual Set picker, and matching documents disappear/reappear after relaunch. The canonical lane separately links/unlinks Source and Topic for all three writing Types while retaining the other value. | Native readback verifies derived IDs and human chip models; real search/subscription state changes when canonical associations are added/removed. | The original Word assertion could compare a placeholder/wrong row value with itself, and Universal checked only Source after reopen. The proposed correction captures the chosen canonical Word independently and checks all three Universal values after reopen. Set predicates are exercised for Source only; there is no UI Topic/Word filter proof. |
| 04: Hidden→Show without duplicates; object-only addition leaves sibling unchanged | Object-only Add Property is exercised, and the proposed Type precondition confirms the Type was not implicitly changed. | The real Native/view-model preparation hides the Type Source, observes Hidden on Type and document, reveals it from the document, and checks visible membership. Universal Native preparation checks the untouched sibling and original Type. | No selected UI method taps Hidden→Show, counts duplicates, or inspects an untouched sibling after the object-only action. Native visible-membership checks use set inclusion and do not by themselves prove absence of duplicate UI rows. |
| 05: real failure exposes reason and Retry without breaking ordinary catalog | No selected method exercises this failure path. | Core parity tests cover internal-identity loading/failure/recovery and catalog identity rules. | These are not a UI proof of `PropertyCreationViewModel` catalog failure, logging/reason, Retry, or continued ordinary catalog operation. |
| 06: internal fields hidden, Space isolated, focused tests and real UI plus physical iPad | Some UI phases exclude the old projection row, the visible canonical-context label, and raw `providerID` text. Exact document routes include the fixture Space/object marker. | Native preparation and Core parity exercise internal order/canonical identity by ID/key and Space-scoped policies. | The selected UI methods do not inspect every internal field by identity, attempt cross-Space reuse, or run on a physical iPad. Physical acceptance and the requested final verified IPA are separate gates. |

## Significant assertion boundaries

`testRemainingUniversalTypePickersAndMixedSet` retains a historical name but currently exercises Set columns/membership only. Its comment is clarified by the patch; current Type persistence checks belong to `testUniversalPageNoteCustomPropertiesAndMixedSet`.

`testSourceHeaderSelectionAndOverflow` opens the real compact Add search, but its overflow portion only taps and takes a screenshot. That portion does not assert the entire overflow content or a successful item selection. The narrower claim must remain visible even if the method passes.

The two property lanes correctly use separate freshly prepared fixtures. Universal UI mutates initially blank P2 documents; the Set-resume methods require untouched blanks and the independently linked P1 documents. Reusing one account/fixture across those two lanes would invalidate their preconditions. The reviewed batch design retains separate native preparation, Space and container for each lane.

## Source references

- `Tools/PinkhaSimulatorGate/run_wave15_acceptance.py`: exact selectors and fixture preparation contracts.
- `PinkhaStage1Acceptance/Tests/PinkhaStage1AcceptanceUITests.swift`: six selected UI methods and the row/picker/reopen helpers.
- `AnyTypeTests/Pinkha/TorahNativeDerivedProductIntegrationTests.swift`: `originalProductPipeline`, `verifyUniversalProperties`, actual Native readback, Type changes and subscription/filter checks.
- `AnyTypeTests/Pinkha/PinkhaStage1AcceptancePreparationTests.swift`: isolated canonical writing-Type fixtures with initially empty native values.
- `AnyTypeTests/Pinkha/TorahNativeUIParityTests.swift`: model/catalog/internal-field policy checks; this is not the UI failure/Retry path.

All references above are to the immutable audit source. Results of a later run must be bound to that run's actual source SHA and original xcresult before changing acceptance status.
