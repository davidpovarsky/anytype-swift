# Editor and RTL acceptance: exact remaining scope

This is a source/retained-evidence audit, not a new acceptance result. The first
shared source `6aab20344fcf1c645d7c96e0b9ec034ef07003a9` failed its App build;
its UI phase and XCTest suites did not execute. The marker compiler repair is
`ecd3eae7764129fa5f958a361b32c9c4826c76e6`; its exact hosted source pins are
published in `2c74f5a05ca39cade16b685fce37d7f9c73be0e5`. The unchanged source
before/after and original failed result remain retained.

## Existing executable coverage

All selectors below describe what their current source actually asserts.
They do not create a PASS merely by being selected, compiled or enumerated.

| Selector | Supported scope when actually passed | Scope it does not establish |
| --- | --- | --- |
| `AnytypeTests/TextBlockFocusLifecycleTests` | 22 methods / 34 literal cases: input ownership, reuse/composition, native refusal, window/attachment/layout readiness, initial and explicit focus handoffs, superseded callbacks | Real keyboard gestures, split/merge, native save, real UI history or visual RTL acceptance |
| `AnytypeTests/PinkhaTextBlockLeadingMarkerTests` | 2 methods / 4 cases: original numbered marker alignment after opposite-direction attachment, mounted direction changes, 1/20 threshold, context removal and non-numbered reuse | A real list in the app, bullets/indentation, text editing or accessibility |
| `AnytypeTests/AnyNativeEmptyParagraphDirectionTests` | 4 methods / 6 cases: real hosted input's empty style/focus, UIKit attribute/selection resets, composition/nonempty exclusion, block reuse | The real Any document's keyboard, native persistence or every block style |
| `AnytypeTests/AnyNativeTextRendererTests` (reviewed direct-source hosted bridge) | **3 XCTest methods**, as declared in the frozen source: equal text changes attributes while retaining selection; changed text clamps selection; marked input remains unchanged | A package-runner execution, a four-case suite, or an app UI selection result |
| `PinkhaStage1AcceptanceUITests/testAppWideDirectionPersistenceAndInteractiveBack` | On three prepared Heart document kinds: typed text, app/OS mismatch, SwiftUI/navigation/UIKit direction diagnostics, cancelled/completed full-screen and edge-back gestures, cold reopening | Mid-text split/merge, Undo/Redo, range replacement, block style controls, orientation, theme or accessibility audit |
| `PinkhaStage1AcceptanceUITests/testMultiBlockEnterCreationAndTypingLifecycle` | Three document kinds; five alternating Hebrew/English Enter-created blocks, distinct IDs, empty next-row focus/caret/typing-direction diagnostics, reopened identical IDs | Mid-text Return, selection deletion, Backspace merge, editor Undo/Redo or list/heading/quote geometry |
| `PinkhaStage1AcceptanceUITests/testDocumentSourcesEntryOpensExistingSearch` | Exactly one source-entry control, real existing search field and localized document-scope heading for each kind | Search error/retry, active-space search completeness, long labels, keyboard overlap or reader selection |
| `PinkhaStage1AcceptanceUITests/testUnifiedEngineSwitchRetainsHeartDocumentAndColdReopen` | Real Heart→Any→Heart scene host; native account readiness; inactive Heart input not hittable; same document/block IDs and cold content reopening | Editing inside Any, unsaved-draft recovery, structural edits, orientation/window transitions |
| `PinkhaTorahQuoteAcceptanceUITests/testNativeQuoteUndoRedoDragAndRelaunch` | Actual provider text; long-press Insert; separate native quote/source-metadata Undo and Redo; retained quote IDs; editable focus; two real source drops; unchanged neighboring anchor; background/foreground and cold reopening without duplicate quote writes | This method explicitly requires **English UI**; it inserts the whole provider segment and does not select a substring. It does not prove Hebrew menus, every RTL visual surface, or generic block drag-reordering |
| `AnytypeComprehensiveAcceptanceUITests/testSourceChipOpensAndClosesInspector` | Existing Inspector appearance and dismissal from a canonical source chip, with kept screenshot/AX evidence | Text range selection, rotation, compact window transition or an accessibility audit |
| `AnytypeComprehensiveAcceptanceUITests/testInspectorEmbeddedSearchOpenReturnAndDocumentLink` | Existing embedded reader/search route; query/results retained on Back; opening does not create a link; explicit link readback and unique association; reopening same source; keyboard absent after dismissal | Genuine provider failure/retry, cancelled in-flight search, stale result replacement or physical VoiceOver |
| `NativeLaunchTests/testExplicitHebrewDirectionAndAlignmentSurviveColdReopen` | Any paragraph: explicit opposite persisted direction, then RTL and center alignment, exact native readback status, unchanged content/ID and cold reopening; he/en exact UI values; two kept screenshots | Lists/headings/quotes, empty input typing direction, selected-range geometry, full accessibility, landscape or actual iPad window transition |
| Page154's original mounted and continuation selectors | Real selection/confirmation/cancel/create, semantic native identity; later link/edit/reopen/unlink native readbacks according to their six-stage profile | Whole-editor acceptance. Original passed stages remain evidence; the expired fixture's TTL requires a fresh complete six-stage prerequisite renewal on the new product |

The retained App15 21-method/32-case focus result is preserved. The new required
22/34 scope must execute against its changed focus source; neither historical
counts nor the hosted RTL components replace the original native editor
preparation and four real UI methods. The existing hierarchy drag PASS remains
retained and is excluded from the new NativeUI continuation. The separate
source-to-editor drag has its own scope and pending result.

## UI01–UI12 mapping

Authority: `Tools/PinkhaSimulatorGate/required-coverage.json`, SHA256
`ff6ed058777ef212e8241e3c4953d47c91653d3610d78d52466a6d4c38bb3775`.
Requirements below are preserved without relaxing their configuration-specific
criteria. Broad scenario IDs must not be completed from a narrower method.

| Requirement | Reusable existing control | Remaining evidence or work |
| --- | --- | --- |
| UI01 — actual launch, disposable identity | Existing native preparation and startup binding; Native account entry method | Successful new shared product; actual owned-simulator execution and matching fixture/account/Space identity |
| UI02 — Home/list/search/settings/open-back-close | Existing Inspector/library/navigation methods and original editor back gestures | Confirm each named route on required phone/tablet configurations; editor back alone does not establish all Home/settings/search routes |
| UI03 — create/edit/save/reopen, five mixed Enter blocks, caret/focus, Undo/Redo | Original editor methods plus quote history only for its quote scope | Prioritized additive Heart mid-text split/merge/range/history tranche below; actual save through distinct cold-process readback |
| UI04 — original properties and visual long-label layout | Existing native/canonical Properties UI and new picker fixes | Execute required native UI and visually review long label typography, tint and spacing in he/en configurations; component tests alone are insufficient |
| UI05 — source/topic/word, search states, link/unlink/reopen | Inspector search, native topic/word and Properties lanes | Torah lane owns exact missing states and Hebrew/visual coverage; no blanket credit from successful source lookup |
| UI06 — Inspector, quote selection, real drop, undo focus, finished animation | Existing source-chip, quote/drop and embedded search; Page154 selection is a distinct anchor scope | Actual pending quote/drop run; Hebrew and substring selection remain uncovered by its whole-segment English method. Keep native drag and generic block reorder separate |
| UI07 — backlinks/Notes, Space isolation, refresh/reopen | T5 UI/freshness + native related-document/Note controls | Torah's pending two UI cases, R08, freshness/index/isolation; do not repeat the retained 36 or nine native calls without a concrete change |
| UI08 — document/block target and return route | Existing related-document and Inspector return methods | Exact block-target opening and enabled/disabled capability states must be supported by their own current lane proofs |
| UI09 — mixed long RTL text, keyboard/sheet overlap, labels; iPad landscape/dark/accessibility type | Original typing/search screenshots and Native paragraph matrix provide partial inputs | Actual long mixed text with list/heading/quote geometry, keyboard/sheet intersection checks, true dark accessibility-sized layout, labels/audit and visual review |
| UI10 — compact controls, retained selection/presentation, orientation; actual iPad window transition | Existing retained-scene and selection tests cover a different lifecycle | Actual orientation change and iPad scene/window size transition with selection/presentation retained; resizing a screenshot or simulator display is not proof |
| UI11 — genuine controlled failure, error/retry, cancellation/stale response, no wrong-Space fallback | New native/model cancellation and search tests prove component behavior only | Genuine bounded UI failure followed by visible recovery on the owned fixture; independent cancellation/stale-response and Space assertions |
| UI12 — background/foreground, dismissal/reopening, termination/relaunch, no duplicates | Existing quote and Any lifecycle methods; original editor cold reopen and engine retention | Execute appropriate current methods and inspect exact object/block identity and duplicate counts; no credit for unsaved draft recovery unless actually exercised |

## Required language/device/appearance matrix

The user-required matrix has eight configurations per tested surface:

| App | OS | Device | Appearance |
| --- | --- | --- | --- |
| he | en | iPhone | light |
| he | en | iPhone | dark |
| he | en | iPad | light |
| he | en | iPad | dark |
| en | he | iPhone | light |
| en | he | iPhone | dark |
| en | he | iPad | light |
| en | he | iPad | dark |

The existing Native matrix controller verifies actual global-language settings
after reboot, actual device family/runtime and appearance readbacks. Its
`contentSize=large` is the ordinary system category, **not** an accessibility
size. Its two paragraph screenshots do not establish all listed RTL surfaces.
Heart's original methods require an opposite OS language; its future matrix
must retain the same actual settings evidence. Each required cell needs an
actual result and kept original images; no cells were executed by this audit.

Visible paragraph and empty-field behavior, numbered/bulleted lists, headings,
quotes, selected text, keyboard placement, native menus and navigation gestures
must be mapped to real images/actions independently. A component's direction
flag is not a visual result. The additional UI09/UI10 configurations still
require actual landscape/accessibility-type/compact-window evidence beyond
these eight ordinary cells.

## Prioritized future UI-only tranche

The draft appends two XCTest methods to the exact Stage1 source `d4ffc25e…`:

1. `testMiddleSplitMergeUndoRedoAndColdReopen`: creates a guard and target via
   the existing real input path; moves a caret with real keys; splits at an
   actual middle position; checks two exact texts/IDs; Undo/Redo; real
   Command-A/left/Backspace merge; checks the retired second ID, unchanged
   guard and retained first ID; Undo/Redo; distinct-process cold readback.
2. `testPartialRangeReplacementUndoRedoAndColdReopen`: real Shift-arrow range,
   one replacement key, exact unchanged prefix/suffix and same target ID,
   original native Undo/Redo UI, unchanged guard, cold readback.

Each method iterates the three existing prepared document kinds. These are
**two XCTest methods with six document flows**, not six XCTest cases. The
exact original four methods and startup helper remain byte-identical. The
draft does not change the App, native contract or preparation and does not
join the current rebuild freeze. ASCII target runs make physical arrow
traversal unambiguous across mismatched UI directions. Hebrew/mixed-script
range geometry remains a separate visual gap; it is not claimed from this
structural test.

Intermediate snapshots wait for the complete expected block set and text
before the next history action. They are explicitly `UI_STATE_ONLY`.
Pre-edit range is inferred from the exact resulting prefix/suffix/topology;
there is no claimed direct native selectedRange observation. Native storage
acceptance is the distinct-PID cold readback with the same Space/object/block
identities. Kept AX/screenshots and typed observations survive failures. The
draft still needs source review, actual UI-target compilation/enumeration and
execution on a separately qualified product/runner.

## Accessibility boundary

No physical iOS device was available in the current inventory, so physical
device and manual VoiceOver validation remain `NOT_RUN`. Do not infer that
Simulator VoiceOver is unavailable: the root found a new Xcode27 XCTest
VoiceOver service, and Interfaces owns checking the actual installed API and
its supported runtime behavior. Simulator accessibility audit, actual Dynamic
Type layout and bounded VoiceOver focus/speech each remain `NOT_RUN` until
their own evidence exists. An accessibility hierarchy dump is not a
VoiceOver traversal result.

## Evidence custody

The source audit uses frozen Stage1 SHA256
`d4ffc25ee659e03bd4dd76b7847faf4fecf343630edf094c0bc02fe060f00850`,
quote/drop `66c18c084ed66baf9b58d45b094e985127e77f8b627fc924f67be7201125f219`,
Inspector `066d45e4ba7198c878bb457f2c2c9f6423609451f4a85ac07da4d5d3657c30ad`,
and original Native RTL source `e32f68676df1330c0255aa7ffa93b71c16f158570250013c607084f440c54375`.
The Native Library insertion is separately inverse-proven and does not change
those original Native methods. Existing receipts, failures, source hashes and
passed drag evidence are not overwritten or relabeled by this audit.
