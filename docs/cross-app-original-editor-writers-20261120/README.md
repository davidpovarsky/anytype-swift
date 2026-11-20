# Original Anytype editor: instance writer services and local events

Source: e73fc242ecb50010ea973c25ae242fb528b7a678. Parent: 841bc1d635673378289165ce7805497041b1b77a. This continues the original EditorPageController / EditorPageView assembly. It does not create a substitute editor or enable an Otzaria annotation consumer.

## Actual result

The standalone Windows Foundation fixture executed 41 controls: 41 passed, zero failed. Its original 29 controls and their main-function body are unchanged; the additional 12 check injected event ownership, ordering after a successful style write, refusal to publish after failure/cancellation, no early split publication, two independent publishers, and the five original default event payload mappings. The compile ran in Swift 6 strict-concurrency mode. The same Foundation source projection also typechecked in the original app's Swift 5 language mode with no diagnostics. The original DocumentMode declaration is unchanged.

Thirty-two complete Swift source/test files parsed in Swift 5 mode. This is syntax validation, not Apple typechecking. The UIKit controller, full component bodies, Factory resolution and Combine event bus were not executed in this portable fixture. Its explicit boundary doubles remain recorded in RESULT.json; the event recorder is a double, while the new publisher and TextServiceHandler bodies are the actual source.

Apple typecheck, Apple unit execution, Native editor mounting, annotation durability, and Otzaria in-process integration remain NOT_RUN or not yet implemented. No positive Native claim is made.

## Source changes

Nine existing components now accept immutable instance dependency bundles: BlockActionHandler, KeyboardActionHandler, EditorPageViewModel, EditorPageBlocksStateManager, BlockViewModelBuilder, SimpleTableDependenciesBuilder, SlashMenuActionHandler, ObjectHeaderViewModel and EditorRouter. Each original constructor retains its original per-component factory defaults.

An explicit prepared-document assembly overload accepts these dependencies and the existing BlockActionService dependency bundle. Optional service fallback is evaluated at each original construction point. It does not replace the renderer, reorder original construction or change the default entry.

The original UndoRedoView/UndoRedoViewModel and PasteboardBlockDocumentService also accept their original service explicitly. Existing coordinator callers keep their defaults. No global Factory registration is changed.

Seven existing local event dispatches are routed through EditorLocalEventPublishing: one style event, one post-focus split refresh, one toggle, one optimistic text update and three loading events. OriginalEditorLocalEventPublisher sends the same original EventsBunch payloads. The split registration and focus still precede refresh; style publication still follows successful service completion; optimistic text publication remains before its original write.

Twelve component method-body comparisons are identical, except the explicit event-route inverse for BlockActionHandler. The original BlockActionService and TextServiceHandler methods also match after the exact event-call inverse. Exact service-argument inverses recover the original assembly. Original EditorPageView body, default StateObject initializer, original controller and renderer remain unchanged.

## Apple declarations and exact path casing

The existing 11 declarations are retained. Five additional SwiftTesting declarations are in AnytypeTests/Markdown/EditorLocalEventPublisherTests.swift, suite AnytypeTests/EditorLocalEventPublisherTests. They check successful event order, failure, cancellation, split publication ownership and separation between two supplied publishers. All 16 remain unexecuted on Apple at this commit.

The Windows repository has existing case aliases. Before commit, the new test was explicitly registered under lowercase AnytypeTests and both new Python/JSON helpers under uppercase Scripts/CI. SOURCE_COMMIT.json records exact blobs and the corrected uncommitted aliases. No duplicate files or project registration changes were introduced.

## Remaining integration work

These are instance construction seams, not a completed ownership or authorization boundary. Routed property/icon/cover/object/settings sheets and external coordinator outputs still use their original native dependencies. The custom TextServiceHandler and aggregate action publisher must be assembled with the same document owner. Metadata reads, the original document's live subscriptions, native runtime lifecycle, cancellation/revocation, structured durable rich-block backing, consumer target and real host remain to be integrated and qualified. No global factory override, external account operation, unrelated Space write, live DB access, signing change or Save hook is performed.

The source-only peer review of TextBlockActionHandler/TextBlockViewModel and simple-table descendants found their core text, paste and table writes follow the supplied handler/services. It did not establish full isolation, Apple compilation or runtime behavior.

## Reproduction and evidence

Run Scripts/CI/run-original-editor-boundary.py with --swiftc and a new --output directory. The driver retains the original 29 controls, validates the source inverses, runs all 41 current controls and parses the complete changed files.

RESULT.json, REVIEW.json and INPUTS.json bind the result to this exact source. raw contains deterministic gzip copies of logs, compiled boundary projections and the original raw report. RAW_FILES.json records compressed and decompressed hashes. source.patch.gz preserves the exact Git diff. No compiled libraries, caches or native runtime binaries are included.
