# G07 — source-drop preview authority

## Concrete defect and correction

At immutable source `2207b131f45d305ba828c93deb0633e275e59cba`, Heart's collection drop preview checks only `canEditBlocks`. Actual source insertion requires block editing, relation-value editing and `details.isReadonly == false`. The original `ObjectPermissions` constructor allows the concrete `.details` restriction to deny relation writes while retaining block editing. A user can therefore see an accepted COPY cursor for a source that the editor subsequently refuses to insert.

The existing downstream `TorahEditorSafetyPolicy` now owns that exact insertion predicate. The existing drop delegate supplies all three permission inputs to a new overload; its original internal MOVE route still uses only the original block-edit/placement decision. Both existing insertion guards call the same predicate with unchanged boolean meaning. Final session/repository authorization remains in place. This is a UI advertisement correction; it does not grant write authority or change the native service contract.

Changed production files are the downstream policy and the two original integration hooks in `EditorPageController+DragNDrop.swift` and `EditorPageViewModel.swift`. The four-file source inverse restores every exact2207 preimage. The original policy's full three-argument drop-operation implementation stays byte-identical.

## Focused regression source

Two methods are appended to the existing App-hosted source `AnyTypeTests/Pinkha/TorahAssociationNativeRepositoryTests.swift`. Its complete original 68,698-byte prefix, existing methods and assertions are unchanged.

| Exact method | Concrete rows and expectations |
| --- | --- |
| `sourceDropPreviewHonorsNativePropertyRestrictions()` | Real `ObjectPermissions` construction for no restriction, `.details`, `.blocks`, and both restrictions. Only the unrestricted source drop offers COPY. Internal MOVE follows original block permission, including the details-only case. |
| `sourceDropPreviewRequiresExplicitWritableDetails()` | Real `ObjectDetails` with readonly false/true, and absent details. Source COPY requires explicitly writable details. Internal MOVE remains unchanged; invalid placement stays forbidden for both transfer kinds. |

These are **2 new methods / 2 cases**, containing 7 explicit permission/detail matrix rows. Their exact future selectors are `AnytypeTests/TorahAssociationNativeRepositoryTests/sourceDropPreviewHonorsNativePropertyRestrictions()` and `AnytypeTests/TorahAssociationNativeRepositoryTests/sourceDropPreviewRequiresExplicitWritableDetails()`.

No Swift/Apple test was run by this tranche. The local source workspace has no `swiftc`, and the coordinated Oracle compiler window belongs to Wave1. No compiler, Native call, simulator, account or old accepted test was invoked. The original test target already contains this file; a future matching shared product must compile its exact changed source and execute these two methods. No new PBX registration or generic test-control framework is added.

## Bounded G07 source audit

The original first-block path is reachable when the mounted editor has no block model: `insertTorahSource` calls the original `BlockService.addFirstBlock`, which delegates native block creation immediately after `header`. It does not request cursor focus. The other target/append branches already pass `setFocus: false`. The general-update cursor path only reinitializes on object type change; this insertion changes no Type. No first-block autofocus defect was established by this source audit.

The actual UIKit external-drop callback captures a per-gesture session action before asynchronous provider decoding. The shared session binds the originating document epoch, and Inspector insertions additionally bind their presentation epoch and selection. A new gesture receives a new claim; a delayed callback cannot acquire a new document lifetime. Actual block creation is followed by separate metadata authorization. A denied/failed metadata write preserves already-created user text and reports a partial/uncertain insertion instead of destructively deleting it. These mechanisms and the shared session are unchanged.

The original quote UI method `PinkhaTorahQuoteAcceptanceUITests/testNativeQuoteUndoRedoDragAndRelaunch` already selects a real provider segment, performs two-step Undo/Redo, two real drops, background/foreground and cold identity checks against the original owned fixture. Its actual historical failures before quote input remain failures; its English scope is not Hebrew/RTL/VoiceOver evidence. This audit neither reruns nor relabels it. Accepted hierarchy drag and Native Quote/Note outcomes remain separate evidence.

The missing G07 runtime acceptance is still explicit: empty-document first quote with actual focus/keyboard observations; cancellation at the actual presentation/window boundary; a controlled partial metadata failure with original text/association readback; and return to the exact originating document/block. The audited source paths alone do not prove those mounted outcomes. Root separately owns G04 reader/navigation work.

## Source custody and integration

`source-custody.json` records exact source reads at2207; `source-inverse.json` binds all four edited preimages and restores them exactly. Fresh upstream develop was independently read as `d857b23ea540be33d6faab4f7a7a1a260ab578c1`. Original Anytype files remain classified upstream-owned; the scoped exception documents why the existing delegate must pass the missing inputs. No schema, native engine, SDK/Hanlin, document Type, source body, citation text or UI design changes are included.

The exact base source map has129 rows, SHA`a2b59291…`. This tranche updates only rows55/110 for the existing VM/test files and appends the policy and drop-hook rows, producing131 rows. The other127 rows are retained. Torah's independently reviewed G05 map changes are not copied into this branch; Wave3 must merge the finite row changes into the actual source union, preserving every other current source hash. Source retention is provenance, not semantic or UI acceptance.

The package retains Asana T4's original open criteria and the original queue's G07 gap classification. No task should be completed from this source change. The actual future producer/source inventory and runtime dispatch remain Wave3-owned.

## Completed source review and gate

The unchanged source-retention verifier actually passed on the staged source tree `4f99661bff52323f4dc00b4a51823f6ef5403749`: 131 rows, zero errors and zero unreviewed changed sources. The exact original receipt is `source-retention.json`, SHA-256 `5d39066ed62017f9df9ade7dfd204f751b8ab839cd9f8f53ff1a242c2a8b96c6`. Subsequent additions are review/handoff documentation; the reviewed Swift and map bytes are unchanged.

Root's independent production/call-site/map review is `fd0e56a3…`; Torah's separate appended-test API/actor review is `7668fe3b…`. Both are source-only and found no remaining concrete blocker in their stated scopes. The earlier `candidate-source.json` is retained as its original preparation checkpoint; `handoff.json` records the later review state. Runtime readiness remains false, and both new methods remain unexecuted.
