# Any native UI continuation: original evidence and bounded corrections

The original run [45038244641](https://github.com/davidpovarsky/anytype-swift/actions/runs/45038244641), at `07c3568f9f9cf4044dd81163cd374d4ad35330cb`, executed **19 actual cases: 12 passed, 7 failed, zero skipped**. Ten focus methods and the native entry passed; one of seven later journeys passed; the six remaining journeys and the canonical Files roundtrip failed. Eight earlier unaffected UIKit methods were retained, not executed in this run. Custom Type did not execute.

The complete original artifact is `14763060546`, 310306892 bytes, SHA256 `631272ec9be40f243645009f181ee3f83dbbb0eb57e47a6ab92e59aca0d1a3cb`, containing 4742 files. `ORIGINAL_RESULT_AUDIT.json` binds the original per-case SQLite results, Apple summaries/trees, named admission, and logs. The selected ZIP retains the small original result and provenance records; it does not replace the full original artifact. Later runner restart summaries do not erase failed cases.

## Corrections tied to observed failures

| Journey | Original evidence | Current correction |
|---|---|---|
| Hebrew alignment | Saved native style survived cold reopen; the nested menu action lacked the selected accessibility trait. | Native inline SwiftUI Picker binds to the acknowledged saved common alignment. All five choices and existing write path remain. The original acceptance assertions remain unchanged. |
| Hanlin connection | The real mounted endpoint/model text fields returned empty accessibility labels. | Shared Hanlin UI supplies localized labels and stable identifiers to the original endpoint/model/SecureField. The controller uses those fields and also asserts their actual labels. Consent, provider, SecureField and normal Connect flow remain. |
| Hierarchy move/properties | The real Hebrew edit menu said `בחירת הכול`. | Include that observed label in the existing Select All query. |
| Hierarchy drag | The recorded drag moved 52 points in 104 ms without destination dwell; the context menu remained open. | Keep the real source/destination and long press; use explicit slower velocity and destination hold. Native hierarchy/result/cold reopen assertions remain. This remains a candidate until actual execution. |
| Source drag | The real quote and source badge were visible above the unchanged target, under the expanded inspector. | Collapse the inspector through the existing helper before reading the editor. Source identity/order/body/cold reopen assertions remain. |
| Topic/word related results | The global negative label query matched the underlying navigation `BackButton`, not a result row. | Add identifiers to the real Related list and rows, and restrict this test's positive/negative queries to that list. Query/backend behavior remains unchanged. |
| Canonical Files roundtrip | Source export used `Pinkha`; fresh post-import Files AX showed empty `Exports`. The first export succeeded at +270.80 s; the full test stopped at 360 s. | Apply the default directory separately to exporter and importer. Verify the actual Exports header in each dialog, capture the actual importer before waiting, and allow 1800 s for this case. Existing 45 s filename waits, real row selection, explicit mapping, exact bodies, cold reopen and all three exports remain. |

The Files modifier placement diagnosis is an inference from the original directory mismatch. Apple documents `fileDialogDefaultDirectory(_:)` as the initial directory for fileExporter/fileImporter/fileMover, but does not explicitly document precedence of two chained dialogs. Actual mounted execution must verify the repair. Primary source: <https://developer.apple.com/documentation/swiftui/view/filedialogdefaultdirectory(_:)>.

The alignment Picker follows the native adaptive-menu pattern: <https://developer.apple.com/documentation/SwiftUI/Populating-SwiftUI-menus-with-adaptive-controls>. Source reasoning is not Apple execution evidence.

## Retained and required execution

The continuation gate must retrieve and verify the original artifact identity and original raw test results. It retains the passed focus10, entry1, quote/Note1, and older unaffected8 only after exact reviewed product/dependency closure and test-helper checks. It never manufactures a passing receipt for the original failed seven-method batch.

Only the six failed follow-up methods, the Files method, the previously unexecuted Custom Type method and one new mounted history method need new execution. The current App and runner must build once, retain their exact identities, and be used unchanged for all current journeys. Native Any remains the previously qualified runtime. The new history reader/presentation's 16 portable controls retain their actual source-bound evidence; SwiftUI bodies and native history HTTP still require Apple qualification.

The root merge contains eleven Swift files. `ROOT_MERGED_SOURCE_MANIFEST.json` binds them to the actual canonical Git source, including the exact original NativeLaunchTests SHA256 `f4cc433fe98ab1e6ffe9af3c6d3db0a46e71ec7f0f61ddd1e6d4c29cc1b33f53` (112202 bytes). An earlier fetch appended one newline; it was removed only after matching this recorded original hash. The merged source is not claimed to be tested before the new Apple run.

## Limits

Canonical association transfer does not prove full Heart Space migration. Native history is read-only saved-text preview, with no restore/write action. Full T2, T5, SDK06, Any C–F, MIG-01, APP-01, EDITOR-02, physical iPad and release remain open until their own evidence qualifies. Raw onboarding videos and full app stdout are excluded from this publication; they may contain recovery information.
