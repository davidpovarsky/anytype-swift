# Stage 1 validation report — 2026-10-26

Overall status: **IMPLEMENTED / FINAL XCODE VALIDATION PENDING**. Owner-approved hooks H1–H10 and their downstream implementation are present locally. Current-worktree Xcode/CI and physical-device evidence are not claimed until the new commit and its own Xcode 27 run finish.

## Evidence identity

- Repository HEAD: `c2663ab6178044eab0b0a03faefa4f802fed932c`.
- Audit baseline `upstream/develop`: `d5650321577a209505a3277c8437b7608cff1cb9`; pre-commit refresh `b781a7734ecd70813cf19b10a5262ed193bb1e2b`. Every H1–H10 target blob is unchanged between them.
- The work is uncommitted and unpushed at this report snapshot; no merge or Asana write occurred.
- Current-HEAD CI run `40248543332` is green for committed SHA `c2663ab617`, but it **does not validate this worktree**.
- H1–H10 approvals, exact pre-edit blobs and rollback boundaries are recorded in `docs/architecture/UPSTREAM_EXCEPTION_REGISTER.md`.
- H8/H10 were applied exactly from the approved diff after revalidating `55c30c6a…`, `0ee63a66…` and `a7755dbf…`. `TextBlockIconVIew.swift` remains byte-identical at `12334d6d…`.

## Implemented behavior

- H1 preserves the complete existing `BlockFields` dictionary when converting `BlockInformation` to protobuf; it does not add or reinterpret fields.
- Pinkha editor activation is gated by cached manifest plus registered Pinkha document type. Ordinary Anytype documents receive a `nil` writing context.
- New/session-created blocks use an automatic direction marker. A locally fabricated unlinked virtual trailing row may render as new, but persistence still requires `SessionCreatedBlockIdsStorage` after successful materialization.
- A marker-less legacy block preserves its stored alignment and receives only display-time writing direction. Editing it does not create metadata or silently migrate it.
- Explicit alignment is committed first through the original `setAlign`; the best-effort Pinkha marker is written afterward. Metadata failure is caught and cannot roll back or fail the alignment operation. On a later marker-less reopen, the stored host alignment remains authoritative.
- The UIKit adapter copies existing paragraph styles before changing base direction/alignment, updates typing attributes, synchronizes the placeholder, and does not write canonical text, selection, focus, marked text or undo state. It skips paragraph/typing mutation during active IME marked text.
- The Back image uses one semantic RTL flip and `Loc.back` for accessibility.
- H8 runs after leading-marker recreation. Full-row semantic constraints place the marker on the physical right in RTL; 1/9/10/19 retain host centering, 20/99/100 use semantic alignment only for Pinkha RTL, and Pinkha LTR/ordinary Anytype restore the original host values during reuse.
- H10 keeps the original full-screen recognizer unchanged outside exact Pinkha RTL. Inside that gate it rejects only the custom recognizer and keeps the same public UIKit `interactivePopGestureRecognizer`, delegate and touch policy while setting its public edge to `.right`; leaving the document or changing the app layout direction restores the original edge and `.unspecified` semantic value.

## Executed checks

| Check | Result |
|---|---|
| Pre-edit blob SHA verification for H1–H10 | PASS — every approved context matched; H4/H8 matched their approved legacy/H4 contexts. |
| Full `swift test --package-path Modules/PinkhaKit` after H8/H10 | PASS — 155 tests, 19 suites, 0 failures. |
| Swift parser over all 11 changed/new Stage 1 app and native-test files | PASS — syntax only; UIKit/Services type checking remains an Xcode gate. |
| Focused source guards | PASS — H1 preserves fields; H7 alignment precedes metadata; marker-less legacy edits are never queued; metadata errors are caught; no adapter assigns canonical text, selection or focus; H8/H10 diffs match the approved hunks. |
| Workflow syntax and isolation | PASS — Pinkha-only workflow is absent from `upstream/develop`, remains on `xcode-27`, and now runs the focused native suites on iPhone/iPad in English LTR and Hebrew RTL before the unsigned device build. |
| Current-worktree Xcode build/native tests/CI | NOT_RUN at snapshot — must run on the new pushed SHA; prior run `40248543332` is not reused. |
| Physical iPad RTL/LTR and narrow Stage Manager | NOT_RUN — owner/device gate. |

## Tests added or updated

- `PinkhaWritingDirectionPolicyTests`: ambiguous legacy data preserves stored alignment and remains display-only.
- `PinkhaTextDirectionMarkerTests`: automatic/explicit encoding round-trip, malformed marker rejection, and proof-of-new persistence rules.
- `BlockInformationConverterFieldsTests`: known, unknown and empty fields survive conversion; alignment/children and `isLocked` remain intact.
- `PinkhaTextDirectionPersistenceTests`: host alignment precedes marker metadata, failed metadata cannot fail/roll back alignment, unrelated fields survive, and an explicit marker restores the choice after a simulated cold reopen.
- `PinkhaTextDirectionUIKitAdapterTests`: canonical text, selection, first responder and an existing undo operation survive styling; marked-text IME is untouched; placeholder/caret reuse follows runtime direction; ordinary Anytype is a strict no-op.
- `PinkhaTextBlockLeadingMarkerAdapterTests`: numbers 1/9/10/19/20/99/100, physical full-row side in RTL/LTR, constrained nested-row geometry, runtime direction change and ordinary-cell reuse.
- `PinkhaNavigationGestureBridgeTests`: exact document/language gate, public right-edge recognizer and original delegate identity, custom-recognizer exclusion, runtime LTR restore, root/ordinary/Inspector controls, and progress normalization.
- Existing navigation policy tests remain the pure evidence for signed RTL/LTR progress and root/conflict guards.

## Acceptance matrix

| ID | Status | Evidence / blocker |
|---|---|---|
| GIT-01 | PASS | 44-path divergence ledger retained; H1–H10 have explicit owner records; no unapproved original hunk was added. |
| RTL-01 | IMPLEMENTED / XCODE_PENDING | New, virtual and session-created Pinkha rows are styled through H2–H6; native caret/placeholder test is selected in final CI. |
| RTL-02 | IMPLEMENTED / XCODE_PENDING | H8 is active; full-row physical-side, 1–100, nested-width and reuse tests are selected in all four simulator runs. |
| RTL-03 | IMPLEMENTED / XCODE_PENDING | Paragraph and typing styles share one policy; Hebrew/English UIKit tests are selected. |
| RTL-04 | IMPLEMENTED / XCODE_PENDING | Pure marker/legacy tests pass locally; native cold-reopen, field preservation and injected metadata-failure ordering tests are selected. |
| RTL-05 | IMPLEMENTED / XCODE_PENDING | Native canonical-text, selection, focus, undo, IME and reuse guards are selected; copy/paste code paths are untouched. |
| NAV-01 | IMPLEMENTED / NOT_RUN | H9 applied; simulator/device LTR/RTL and VoiceOver remain. |
| NAV-02 | IMPLEMENTED / XCODE_PENDING | H10 is active; the public right-edge recognizer and exclusive custom-recognizer gate are selected on both device classes/directions. |
| NAV-03 | IMPLEMENTED / XCODE_PENDING | Root, document switch, runtime language, Inspector and ordinary controls are selected; final finger completion/cancellation remains part of the physical-device gate. |
| TOR-01 | IMPLEMENTED / XCODE_PENDING | Isolated native repository/search/layout/screenshot suites are selected in all four simulator runs. |
| TOR-02 | IMPLEMENTED / XCODE_PENDING | Quote/focus/drag production paths are unchanged; existing Torah native regression suites are selected. |
| ANY-01 | IMPLEMENTED / XCODE_PENDING | All hooks fail closed outside the exact Pinkha gate; ordinary Anytype controls are selected in native tests. |
| CI-01 | NOT_RUN | Green prior SHA is not presented as current verification. |
| DEVICE-01 | NOT_RUN | Owner physical-device gate. |

## Remaining gate

Commit/push the approved tree, obtain green Xcode 27 native/build/IPA evidence on that exact SHA, then leave physical iPad and Stage Manager as `NOT_RUN` for the owner. Stage 1 is not marked complete in this report snapshot.
