# T5 current-Space Inspector UI acceptance

## Scope and status

This is an optional, real native UI lane after the same-source Apple r14/r15
account compatibility pair and its fifth host freshness phase. The default
four-phase and optional five-phase pair keep their existing behavior.

Source and controller controls are ready. Native preparation, Apple compilation,
the new UI methods and visual acceptance are **NOT_RUN**. Python controls use
synthetic metadata only and cannot count as native, runtime or UI acceptance.
The product lookup capability stays **OFF**. Both paired App builds already use
the identical test-only `PINKHA_NATIVE_T5_LOOKUP_V1` compile flag.

The Kit dependency is `4e59e909dd22685bb46f9396bc57e5f8c627d773`. It adds stable
related-row/unlink identifiers and an additive `noteActionUnlinksSource` option
that defaults to false. Anytype opts in in its Session alongside all six Kit
pins. Other hosts keep their existing Delete behavior. The parent integration
owns that Session change, dependency pins and the UI project's source registration.

## Entry and account boundaries

The reusable workflow adds `include_native_ui: false`. Its CLI option is
`--include-native-ui`, which requires `--include-freshness`. UI begins only after
two App builds, five distinct native processes and five exact named tests pass,
with eleven bounded host freshness observations and complete native secret scans.

Before UI, `continue_with_native_ui` writes an independent `pair-result.json`,
records its SHA-256 and leaves its original pair counts intact. A UI failure or
cancellation cannot turn that pair proof into a UI pass or overwrite the pair
result. The overall route fails when requested UI fails. A successful automated
UI lane reports `T5_NATIVE_UI_PASS_VISUAL_REVIEW_PENDING`; manual visual review
remains an explicit next acceptance step.

The pair simulator is shut down. Its final ledger must match the actual fifth
process's `nextLedgerSHA256` before UI and remain byte-identical afterwards. The
controller never boots, clears or mutates that paired account for UI work.

UI owns a newly created simulator whose name, UUID, type, OS runtime and absence
from the original inventory are checked. No App data container may exist before
installation. The fresh container, native account, Space and root hash must be
different from the pair. The controller shuts down only this owned UI simulator;
it does not delete simulators, account stores, caches or user data.

## Reuse of actual App products

The retained `new/Products` App and native XCTest products come from the exact
same published source as the pair. Source SHA, runtime version, flags, Hanlin
snapshot, Kit pin and installed executable-carrier hashes remain bound to the
original r15 build. The App is not rebuilt for UI.

Only the independent existing UI-runner project is built. The original UI
project must include `PinkhaT5NativeAcceptanceUITests.swift`, and its bytes must
remain unchanged. The retained and installed App executable hashes are checked
before preparation and after the UI runner build and actual UI execution.

Every selected xctestrun is written with a unique `UI27-T5-` filename beside its
original Products configuration, preserving `__TESTROOT__`. Only the selected
target receives explicit `OnlyTestIdentifiers`, an empty `SkipTestIdentifiers`
and the existing environment injection. The original xctestrun is untouched.
CLI selection and the nonzero original XCTest case/count gate independently
require the intended methods. No host route or UI action is bypassed.

## Native preparation

`TorahT5UIAcceptancePreparationTests/prepareFreshNativeUIFixture` runs once through
the existing AnytypeTests bundle against the actual r15 middleware. It creates a
fresh local-only account using real Wallet/Auth services, installs the Note type,
bootstraps the real schema and creates two Spaces. The public fixture contains
no wallet credentials. Both credentials are masked in invocation logs and saved
only in a private job-owned file for the publication scan.

The primary Space has five expected current-source targets:

| Role | Actual native object | Association and expected navigation |
|---|---|---|
| Page | Page | Exact canonical document source; open document |
| Note | Note | Exact canonical document source; open Note |
| Writing | Bootstrapped writing type | Exact canonical document source; open document |
| Block | Page with 24 leading paragraphs | Block-only source; open distant associated block |
| Quote | Page with 24 leading paragraphs | `sourceQuote` block; open distant quote block |

The sourceQuote text is explicitly synthetic fixture content. This lane proves
native discovery and navigation of an already persisted sourceQuote. Actual
provider search, insertion, drag/drop, undo/redo and quote provenance keep their
existing separate real-provider UI lanes.

Three additional documents must not appear: a different verse, a different
provider, and the exact same source in the other Space. Native canonical
readbacks, live block reachability and the real related-document service must
yield exactly the five expected identities. Coverage remains
`indexedTargetsOnly` with `indexFreshnessUnverified`, never `spaceWide`.

## Actual UI methods and observations

`PinkhaT5NativeAcceptanceUITests/testCurrentSpaceRowsAndExactBlockNavigation`
collects seven observations. The actual source chip and Inspector are used from
Page, Note and writing documents to verify the same exact five related rows.
For each of the block/sourceQuote targets, ordinary document entry first proves
that the first paragraph is visible and the distant target is not hittable.
Then an actual Inspector row tap must display the exact object and target block,
with its actual persisted text hittable on screen.

`PinkhaT5NativeAcceptanceUITests/testAddNoteEditOpenUnlinkAndRetainAfterRelaunch`
collects six observations. It taps the real Add Note action, identifies the
new editor object, types a body through the native text view, returns through
the actual Back control, and opens the new sixth row through Inspector. The
row's real context menu must offer Unlink source and remove only the link.
After terminating and relaunching the App, the source list stays at five rows.
Ordinary navigation to the retained Note must show the same typed body without
a source chip; focusing the actual text view must reveal the keyboard.

The two core UI methods are English-only and simulator-only. The separate R08
extension below adds bounded Hebrew/light/dark selections. VoiceOver, physical
iPad, cancellation/permission edge cases, full-Space freshness and remaining
R01-R09 criteria keep their explicitly separate acceptance boundaries.

## Evidence and failure behavior

One exact preparation method and two exact UI methods must pass with zero
failed/skipped cases on the selected arm64 OS27 device. Original XCTest summaries
and test trees are parsed; names or status labels supplied by a fixture cannot
substitute for executed tests.

The two UI receipts are bound to source SHA, run ID, unique token, Space, coverage
and exact ordered observations. Thirteen original screenshots and thirteen
accessibility snapshots must be attached to the correct actual XCTest methods.
Observed App PIDs distinguish the two UI methods and the Note relaunch; the
preparation PID must also be distinct. Installed executable bytes stay unchanged
through those lifetimes; per-lifetime vmmap identity is not claimed.

Only an explicit allowlist of original logs, summaries, test trees, fixture,
receipts, screenshots and accessibility snapshots may be published. Before any
copy, every candidate is checked against both disposable credentials in UTF-8,
UTF-16LE and UTF-16BE. Symlinks, path escapes, raw xcresults, `.app` bundles and
`secrets.json` are rejected. Missing credentials or a leak withhold all private
UI evidence and fail UI acceptance. Account data and raw xcresults remain private.

The controller reuses the pair's bounded owned-process runner. KeyboardInterrupt
from execution, cleanup or evidence publication is recorded as cancellation and
re-raised after final receipt handling. Private original diagnostics remain
available locally; a cancellation cannot be silently returned as PASS.

## Validation recorded for this source

The source handoff records **20 Python test functions / 80 subtests, zero failures,
errors or skips**, on Linux. These are controller and evidence rejection controls,
including both xctestrun layouts, original-path preservation, exact source/test
identity, unrelated simulator rejection, offscreen-to-visible assertions,
Note retention, all credential encodings, all-before-copy publication and
cancellation at cleanup/publication. The independent pair receipt is checked
before and after successful, failed and cancelled optional UI.

Root reviewed both Swift fixtures; the SDK agent independently reviewed the
helper/evidence contract and the two concrete fixes. No local Swift compilation
was attempted during the Windows disk/RAM incident. Native preparation, the two
UI methods and visual acceptance still require their actual Apple run.


## R08 extension: Hebrew, long titles, Light and Dark

The two original English core UI methods remain separate and keep their exact
seven related-target and six Note-lifecycle observations. After they both pass,
the runner freezes `core-result.json` with its original source, device, counts
and installed executable identity. R08 cannot rewrite that receipt. The
independent `pair-result.json` remains protected by the existing pair hook.

R08 adds one XCTest method, selected twice without rebuilding the App or the UI
runner: `testHebrewRelatedRowsLongTitlesAndReadOnlyNavigation`, first with Hebrew
App language and Light appearance, then Hebrew and Dark. It runs on the same
fresh, job-owned UI iPad/account. The paired account remains on its shut-down
simulator and its final ledger hash remains unchanged. This is two bounded
presentation selections, not a device or full accessibility matrix.

### Reuse and the exact gap

The existing production Inspector already provides Hebrew localization, stable
related-row/source/unlink identifiers, source coverage notices and the Anytype
theme. Existing App observations expose actual preferred App localization and
SwiftUI/navigation/UIKit writing direction in the native editor's AX label.
Those components are reused; no additional theme, Inspector or direction
implementation is introduced.

Before this extension the T5 UI selection hard-required English, generated only
short document names and did not set/read simulator appearance. The production
related-row title also had no line limit, while its context snippet already had
a two-line limit. The isolated Kit delta adds a two-line limit to the title Text
and an explicit full-title accessibility label on that Text. The parent Button,
its stable identifier, context/date accessibility content and navigation closure
are unchanged.

### Actual fixture additions

The fresh native fixture retains the same five positive targets, three negative
controls and canonical source. Its Page and writing targets receive fixed long
Hebrew/English titles, each over 160 characters. Their exact names are read back
from real ObjectShow details and from the actual related-query rows. The Page
also receives one Hebrew/mixed-text paragraph whose actual ID, text and graph
reachability are checked before exporting `presentationProbe`. This does not
turn the Page's document association into a block association. Original block
and quote offscreen navigation controls retain their original text and scope.

No fixture or account is recreated between the core methods and the two R08
selections. R08 only opens existing documents, taps existing related rows,
scrolls and reads controls. It never taps Add Note or Unlink and never types.
The Note ID, body ID and text come from the already-validated final core Note
receipt; both R08 selections must reopen that same unlinked Note unchanged.

### Presentation evidence

Before and after each R08 selection the controller queries the exact owned
simulator through `simctl ui`. Appearance must read back the requested `light`
or `dark`; content size is set and read back as `large`. Original command logs
and their hashes are retained. An unknown CLI representation fails closed.
This is actual simulator setting evidence, not an App trait assertion: visual
review of the original screenshots must still confirm the App and Inspector
rendered the corresponding appearance.

The four ordered observations per selection are:

1. Five exact current-Space rows, a Hebrew Add Note label, complete native title
   accessibility labels, reachable/enabled controls and original row frames.
   The row must be fully visible after bounded native scrolling, at least
   44 points high and 160 points wide, and no more than 160 points high at the
   fixed Large content size. Both long titles have original screenshots.
2. An actual related-row tap opens the fixture Page. Its real paragraph has the
   exact native text and App observations `app-language-he`, `swiftui-rtl`,
   `navigation-rtl`, `uikit-rtl` and `content-rtl`. The corresponding original AX
   snapshot must contain that native body ID and the observed direction label.
3. Ordinary navigation reopens the core-created, already-unlinked Note. Its
   object ID, body ID and exact UI-typed text are unchanged, and it has zero
   source chips of any label. The original retained-note AX snapshot must also
   contain no `torah-document-source-chip-` identifier; a false receipt cannot
   hide a localized Hebrew source chip. This step is not claimed as navigation from a related result.
4. Reopening the original source's real Inspector tab again shows exactly the
   baseline five rows, with no resurrected Note relationship or foreign result.

Four required named original screenshots and four AX snapshots are bound to
each method's original XCTest attachment manifest: the Page title, writing
title, native RTL navigation and retained Note. The existing final attachment
helper may retain an additional final screenshot/AX snapshot. A selection must
use one actual App PID across its four required snapshots. Light and Dark use
two distinct App PIDs, neither reused from preparation or any of the three
core UI lifetimes. Per-selection XCTest counts are exactly 1 passed, 0 failed,
0 skipped and 1 total; the two core methods remain exactly 2/0/0/2.

### Separate outcomes and limitations

`r08-result.json` records the two actual selections separately from core. A
failed/cancelled R08 selection retains its original failure evidence and cannot
rewrite or delete the prior pair/core receipts. All new command logs, summaries,
receipts and selected attachments pass the existing complete credential scan
before publication. Account data, secrets, raw xcresults and App bundles stay
private. No additional App build is introduced.

The successful execution state is `R08_HEBREW_UI_PASS_VISUAL_REVIEW_PENDING`.
Original images require visual inspection for Light/Dark rendering, readable
compact rows, mirroring, clipping and contrast. AX metadata and hit-target
checks do **not** constitute actual VoiceOver interaction. Every R08 receipt
requires `voiceOverStatus=NOT_RUN`, `visualReviewStatus=PENDING`,
`physicalDeviceAccepted=false` and `dynamicTypeScope=fixed-large-only`.
Physical iPad, real VoiceOver traversal, larger accessibility text sizes and
full dynamic type coverage remain open. Coverage stays `indexedTargetsOnly`
with its existing incompleteness notice; the product lookup flag remains OFF.

At source handoff, all new Swift compilation, native fixture additions and
R08 XCTest executions are NOT_RUN. Python negative controls verify only the
evidence and orchestration gates and must not be counted as Apple UI passes.
