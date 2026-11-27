# Wave 2 editor and RTL: source and actual-UI evidence envelope

Status: source review and two scoped RTL corrections; **actual next-build
acceptance is pending**. This report does not convert historical XCTest,
Python controls, source inspection, accessibility labels or screenshots from
another product into current acceptance.

## Eight required presentation configurations

Each row requires the actual app language, opposite simulator OS language,
device family and appearance to be observed. The same qualified application
product should serve all rows. Each engine has its own UIKit editing surface,
so a successful Heart row does not prove the Any editor.

| App language | OS language | Device | Appearance | Heart editor | Any editor |
| --- | --- | --- | --- | --- | --- |
| Hebrew | English | iPhone | Light | Pending | Pending |
| Hebrew | English | iPhone | Dark | Pending | Pending |
| Hebrew | English | iPad | Light | Pending | Pending |
| Hebrew | English | iPad | Dark | Pending | Pending |
| English | Hebrew | iPhone | Light | Pending | Pending |
| English | Hebrew | iPhone | Dark | Pending | Pending |
| English | Hebrew | iPad | Light | Pending | Pending |
| English | Hebrew | iPad | Dark | Pending | Pending |

The original host controller already creates a fresh owned simulator, writes
the opposite `AppleLanguages`/`AppleLocale`, reboots, reads `NSGlobalDomain`
back, verifies the installed app's carrier hashes, and sets/reads actual
appearance and fixed `large` content size. These controls can serve the eight
rows after Wave 3 supplies the new exact product admission. `large` is the
normal size category; it does not prove accessibility text sizes.

## Existing exact editor selectors

The prerequisite is
`AnytypeTests/PinkhaStage1AcceptancePreparationTests/prepareRealApplicationState`.
The complete affected focus suite is 22 methods/34 cases, preserved in the
source-bound profile from commit `f18773674732b2456db3cffeb87620b0a2772b9d`.
The actual original preparation failed on App15 with `waitingPresentation`;
the fix in `2fbc3e1a` and those 22/34 cases still need actual Apple execution.

The existing `first-editor` plan selects exactly these four methods in the
`PinkhaStage1AcceptanceUITests` target and same-named class:

| Method | What its actual assertions cover | Important limits |
| --- | --- | --- |
| `testAppWideDirectionPersistenceAndInteractiveBack` | Opposite app/OS languages; Pinkha/Note/Page layouts; actual input direction; full-screen and edge back cancel/commit; save and cold reopen | No numbered-list, heading or quote fixture; no VoiceOver or window transition |
| `testMultiBlockEnterCreationAndTypingLifecycle` | Five alternating Hebrew/English lines; five distinct real blocks; empty new-block first responder, typing direction and caret side; first insertion; exact IDs after cold reopen | Enter creation is covered; selection-driven mid-block split/join, long press and formatting are not asserted |
| `testDocumentSourcesEntryOpensExistingSearch` | One original Sources entry on each document; existing search presentation; localized document scope | Does not cover all loading/empty/error/selection or Inspector journeys |
| `testUnifiedEngineSwitchRetainsHeartDocumentAndColdReopen` | Actual Any runtime reaches enabled account creation; same mounted Heart object/block returns unchanged; cold reopen | Does **not** open or type into an Any-engine editor |

Preserve those declarations and assertions. Initially run the original
preparation and four-method plan on one admitted product/configuration after
the affected focus suite succeeds. A first failure is retained and repaired
before multiplying the lane across presentation configurations. No historical
21/32 pass replaces the required 22/34 result.

## Source findings and changes

Both UIKit surfaces already call the shared `PinkhaWritingDirectionPolicy`.
Application direction determines automatic alignment, nonempty text can keep
its natural base direction, explicit alignment wins, and presentation does
not request persistence. The native adapter also preserves explicit native
direction. A second writing-direction policy is unnecessary.

1. **Numbered-marker attachment:** the old Heart adapter resolved the number
   label during configuration, while only the text view refreshed after
   attachment. Commit `4d3e2a8c38bfb99c02bac668ac6dc96d3d585e66` re-evaluates
   the same existing UILabel policy on attachment/layout, with weak capture,
   an equality guard and callback clearing on nonnumbered reuse. The original
   style builder and all 22/34 focus source are unchanged. Two new UIKit
   methods/four cases are written and independently source-reviewed; they
   have not been compiled or run.
2. **Any empty paragraph attributes:** `AnyNativeEditor.attributed` puts its
   paragraph attributes on an attributed string. For an empty string, the
   equal-text renderer enumerates zero attributes and no `typingAttributes`
   path exists in the module. Therefore it does not carry the resolved empty
   alignment/base direction or heading font into the input. This is a source
   defect, not a measured current-device failure. Read-only Git objects show
   the original editor, renderer and renderer tests were unchanged from a089
   through the coordinated integration source
   `a82fa890a0114990e474b48830e4a2de3e32c79d`. Wave 3 confirmed writer
   availability in HQ51 story `1220940805400426`. The companion source
   correction carries the same resolved source attributes separately for an
   empty current block, restores them at render/focus/selection/insertion,
   and preserves marked or nonempty text, native state and focus ownership.
   Four new hosted UIKit methods/six cases are independently source-reviewed
   and await compilation and execution. The generic renderer and its
   existing package tests remain unchanged.

## What UI01–UI12 still require

`Tools/PinkhaSimulatorGate/required-coverage.json` defines criteria, not twelve
test selectors. Its original historical kit/native metadata must not be
silently rewritten or treated as the selected next-build identity.

| Case | Existing relevant journey | Additional actual evidence needed |
| --- | --- | --- |
| UI01 | Native preparation and original launch | Explicit home/account/Space identity on the selected product |
| UI02 | Original back cancel/commit and reopen | Home list/search/settings navigation, open/back/close with identity |
| UI03 | Five mixed Enter blocks and cold reopen | Actual selection split/join, Undo/Redo and the formatted/empty states not asserted by the original methods |
| UI04 | Native Properties and three document-type suites | New add-property failure/retry fix in original picker; required Hebrew/iPad visual labels and long-label layout |
| UI05 | Sources entry and Inspector source-search suites | Standalone/embedded loading, empty, selection and link/unlink/hidden-to-visible evidence in the scoped configurations |
| UI06 | Original quote/drop journey | Retain the already accepted drag proof; repeat only a concretely affected focus/Undo path, plus actual Inspector close/animation observations |
| UI07 | T5 core UI and note lifecycle | Current source-bound backlinks/note unlink retention, Space exclusion and refresh/cold reopen; preserve accepted native nine-call proof |
| UI08 | T5 exact-target navigation | Actual enabled document/block target and preserved return route after the Wave 3 warning fix is bound |
| UI09 | Existing mixed text/caret screenshots | Long formatted text, keyboard/sheet overlap, real production accessibility labels, iPad landscape/dark/accessibility-size evidence |
| UI10 | None of the four editor methods | Actual iPhone orientation and iPad full/compact window transitions while retaining text selection/presentation |
| UI11 | Scoped failure/retry suites | Genuine controlled error, visible retry/recovery, cancellation/stale-response rejection and no wrong-Space fallback |
| UI12 | Original cold reopen and retained switch | Background/foreground and dismiss/reopen observations with persisted identity and no duplicate writes |

## Minimum new evidence, without historical replay

- Reuse one source-qualified build for all eight configurations. The core
  focus suite, two new marker methods and four native-empty methods need
  targeted hosted native execution;
  repeated pure-policy runs do not add visual coverage.
- Add a formatted-editor observation on each engine: numbered items around
  19/20, bullet/checklist, heading, quote, an empty field and long mixed
  Hebrew/English content. Preserve actual screenshots for the eight
  configurations and inspect them for marker placement, selection handles,
  truncation, menu direction, contrast and keyboard/sheet overlap.
- Reuse those actual documents for selection, long press, mid-block
  split/join, deletion, Undo/Redo, save/reopen and block insertion. Capture
  exact object/block identities before and after. This adds missing behavior
  rather than replaying accepted unrelated drag/native calls.
- Add actual orientation and iPad window transitions plus accessibility text
  size. Passing a reduced-width view in a unit test does not prove an actual
  iPad window transition.
- Record real VoiceOver interaction for both languages and device families.
  An accessibility audit or queried label is not VoiceOver interaction.
  Disable the stage1 diagnostic-label override for production-label review:
  that flag replaces UITextView accessibility labels with direction evidence.
- Keep the 36 historical and nine newly accepted T5 native calls and the
  passed drag receipts. Re-run only affected UI, R08, freshness or a named
  changed path. The warning UI correction is owned by Wave 3.

All new source/model/UI results must be recorded independently. Actual
XCTest result bundles, logs, screenshots, native identities and negative
outcomes stay intact. There is no physical iOS device in the root's current
inventory; simulator evidence can be completed, while physical-device
acceptance remains explicitly missing.
