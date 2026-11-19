# Baseline editor scope and native UI acceptance audit

This audit separates implemented custom behavior, inherited editor functionality, and plans that were never implemented in the pinned baseline. It does not certify full application parity or an Apple UI run.

The baseline is `586c98bcc17dee425664224e508fc0e8df277678`. The historical comparison point is `0c14bcf4ac06466b88ba9c823cac8e0002109898`, the parent of the retained first Torah trial commit `e3ae8bd441`. The source manifest alongside this document records exact Git blobs. Current published port checkpoint: `27b4b2c3917aa6802ca042e6e63914b2f0aac52c`; subsequent changes described below remain separate worktree changes until the next root-owned checkpoint.

## 1. Partial formatting and styled whitespace

The new inline Markdown adapter deliberately refuses a partial formatting-toggle crossing or a change that cannot retain the visible text and all unaffected formatting. It now supports recognized cross-style text replacement: replacing the selected middle of `**ab** cd` to obtain visible `aZd` preserves the exact result `**aZ**d`. These two statements must not be collapsed into a claim that all cross-style editing is unsupported.

The old general editor has broader attributed-range semantics. `BlockMarkupChanger.toggleMarkup` chooses whether to add or remove the selected mark; `MarkStyleModifier.apply` enumerates the selected attributed subranges; `AttributedTextConverter` serializes native mark ranges. Those paths do not impose the new Markdown representability restrictions.

The following source blobs are identical at the historical comparison point and the pinned baseline:

| Source | Identical blob |
|---|---|
| `Anytype/Sources/ServiceLayer/Block/BlockActionHandler/Markup/BlockMarkupChanger.swift` | `a6747eccc0a5739ab6cb67352363819cc5f0c82c` |
| `Anytype/Sources/Design system/TextComponents/Markup/MarkStyleModifier.swift` | `6d363b547782c1efd576595848b83021300fd624` |
| `Anytype/Sources/Models/Documents/Parsers/AttributedTextConverter.swift` | `950f3525b0310234b23edf9e91141ff4ab4a0edf` |
| `Anytype/Sources/Design system/TextComponents/Markup/MarkupState/NSAttributedString+Markup.swift` | `147dd4ab2ca2d3c2053eaf823190c9313b16e992` |
| `Anytype/Sources/PresentationLayer/TextEditor/AccessoryView/EditorAccessoryView/MarkupModeView/MarkupAccessoryViewModel.swift` | `44d1602c759f0bcd38a603871e67c1169e7235d5` |
| `Anytype/Sources/PresentationLayer/TextEditor/AccessoryView/EditorAccessoryView/MarkupModeView/MarkupKind.swift` | `525957df20c7a3ff8c5e6a5a9fa8e640b7540106` |
| `AnytypeTests/TextBlockApplyMarkup/MarkStyleModifierTests.swift` | `1441b6828ba406a1b0b2a0b8bd75e1e2958793fc` |

The last test file is entirely commented out; its presence is not evidence of executed tests. The separate diff of `AnytypeTests/Markdown/InlineMarkdownListenerTests.swift` replaces `UITextView()` with the existing `MarkdownTestTextView()` fixture and does not add a partial-formatting or styled-whitespace capability.

**Classification:** the native adapter is narrower than the original general editor, and that limitation remains explicit. This comparison found no evidence that those arbitrary formatting operations were a newly added Pinkha capability. It therefore remains a general editor/full-application parity limitation, not evidence that an implemented custom formatting addition was silently removed.

The actual custom tests are different in scope. `AnyTypeTests/Pinkha/PinkhaTextDirectionUIKitAdapterTests.swift` checks display-only direction, explicit alignment, glyph/hit-test behavior, canonical attributes, selection, and active marked input. `AnyTypeTests/Pinkha/TextBlockFocusLifecycleTests.swift` checks current lock state, real attachment/key-window readiness, one-shot focus, newer requests, and stale row lifetimes. The new native model and UIKit tests target those concrete contracts. Eleven marked-text/focus UIKit methods are written; their execution still requires the Apple gate.

## 2. Quotes are editable in the implemented baseline

The historical design description of a read-only `NativeQuote` must not override the current source:

| Baseline evidence | Implemented behavior |
|---|---|
| `EditorPageViewModel.swift`, blob `8baf1dbe2cb71db66589b0f2ac6f74908124cab3` | `TorahQuoteContentPolicy.editableBody(for:)` returns the provider text. Insertion creates an ordinary native `.text(.plain(..., contentType: .quote))` and uses `setFocus: false`. |
| `TextBlockContentView.swift`, blob `05e3e4c43a7cb8c75e17472c2ec03a058ca4b1f2` | The text editing lock follows `state.isLocked`; there is no special source-quote lock. |
| `TorahAssociationNativeRepositoryTests.swift`, blob `c324e390f31bf794e5fdc44869481667fde5b788` | The test “Locale changes display only and new quote bodies do not freeze a citation” asserts the exact editable provider text and keeps the citation out of that body. |
| `TorahQuoteInsertionTests.swift`, blob `c9736b8faf0835f6f49557a49f8ad342f9a82881` | The test “A completed quote keeps its canonical source and exact editable text” checks the separate canonical source record and quote text. |

The native Any path keeps editable `quote` text, separate canonical provenance, distinct intentional quote instances, and no forced focus. Its untargeted placement follows the last reachable visible block's parent; targeted insertion remains before the selected target. A new read-only restriction would change the implemented baseline, so no such restriction was added.

## 3. Inspector host mapping and concrete wiring corrections

The exact old host is `Anytype/Sources/Pinkha/Torah/UI/TorahEditorHostModifier.swift` (blob `bf6063cbc59ab5f689486d29c9dd1661b44173bc`), together with `TorahSourcesSearchView.swift` (blob `7ca51ec42fd9d77168ab0b776858910127a204f8`). The native host is `AnyTorahInspectorLayer` and `AnyNativeSourceSearchView` in `Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeDocumentView.swift`.

| Baseline host field or behavior | Native binding or deliberate adaptation |
|---|---|
| Optional current document session | The coherent native document constructor supplies its validated native workspace session; there is no Heart-ID fallback. |
| Search and selection binding guarded by presentation host | The `.editor`/`.properties` owner gates both reads and writes. Search dismissal also checks the owning host. |
| Repository, entry mode, selected tool and selected detent | The actual shared session and pinned `TorahInspectorUI` receive these same values. |
| Commentaries, links and related documents | The same tools are configured. Native also exposes the already implemented Notes action explicitly. |
| Inline full-source navigation | Enabled through the same pinned capability. |
| `actions.search` and `TorahInspectorEmbeddedSearchView` | The audit found this missing in the first native wrapper. It is now wired through `TorahInspectorSearchCapability`, uses the baseline `documentAssociationContext`, and navigates inside the Kit's stack. Standalone Sources retains its own stack. |
| Shared insert, add/open/unlink Note, related-document open/unlink and close actions | The original `TorahEditorSession` owns their request/selection/authority guards. The native layer only wraps the actual sheet dismissal callback to complete an owned route. |
| Localized source errors on the owning host | Restored in the native layer using the same `Loc` strings; properties errors are no longer presented solely from a covered document view. |
| Locale updates | Initial and changed locale propagation is present without reactivating a retired document. |
| Document activation and deactivation | The actual native UIKit mounted surface, account/scene lifetime and explicit route handoff own activation. Covered, owned sheets do not accidentally retire the source. |
| Opportunistic refresh after inspector selection disappears | Native `AnyDocumentPresentation.startObservation` refreshes the complete object-scoped canonical snapshot on the guarded native watch, and successful mutations read back their result. The old dismissal-triggered refresh is not replayed after navigation deactivates the source. |
| Search list reflects canonical changes | The existing presenter receives `canonicalSnapshot` changes and calls its original `synchronizeSnapshot()`. |
| Waiting/saving/conflict/uncertain/error feedback and saved announcement | Restored with the baseline `Loc` labels. A saved state does not masquerade as an error or remain as a spurious status chip. |
| Separate open/link/unlink actions in result rows | Each button has plain styling, preserving distinct actions inside a native List row. |
| Anytype-specific theme | The new standalone native application uses the pinned native theme. Exact original application visual parity has not been claimed. |
| Old opt-in Heart route-observation diagnostic | The retained old application keeps that diagnostic. The separate native app has native identifiers and real UI assertions; the old Heart-specific diagnostic is not a native authorization or migration mechanism. |

The audit also found a real route defect: appending a new document to a NavigationStack did not itself dismiss the old inspector or remove the source controller from its parent. The new `AnyNativeDocumentNavigation` keeps the exact destination and original mounted owner, waits for actual sheet-dismissal callbacks, dismisses child related results before their properties parent, and retires the source before publishing one route. Wrong-owner callbacks cannot cancel a reopened owner's route. A lost foreground/lifetime check retires the old mounted scope while retaining draft recovery; it never retries navigation automatically.

The related-results sheet is presented by the properties panel that owns the action. No timer, synthetic completion, test-only route, new journal, or modified pinned Kit is involved.

## 4. Actual acceptance coverage and its limits

The first four `NativeLaunchTests` methods were preserved byte for byte. The fifth, `testSourceInspectorQuoteAndNoteSurviveColdReopen`, is now written and uses normal onboarding and the real public provider:

1. Create an isolated account, acknowledge backup, create a Space, and install the normal workspace schema through the app.
2. Create an empty document, search for `Genesis 1:1`, then search again inside the actual pinned inspector stack.
3. Use the source reader's real Insert action. Compare the native quote's visible text with the actual reader text, require its canonical source badge, and capture the actual native block ID.
4. Use the real Notes tool to create and navigate to the Note. Require its source line, canonical source context, and indexed related rows for the origin and Note.
5. Terminate and reopen the same account/Space. Require the same quote ID/text, exactly one origin Note backlink, the same Note source-line ID/text, and both related rows without issuing another create action.

The test uses no seeded transfer, replacement provider, direct HTTP mutation, synthetic mounted owner, or permission bypass. The immutable Kit is unchanged. The actual five NativeLaunch methods are still **pending Apple execution**.

The five native-package tests cover real linked-engine lifecycle, Keychain/account failure recovery, protected Hanlin creation, and direct native Torah workflows. Their synthetic presentation owners and direct service calls do not substitute for the fifth actual UI scenario. They also remain subject to the recorded Apple execution state.

## 5. Evidence boundaries

- `native-ui-portable-components-v3.json` proves 21 actual cases in five suites: marker policy 5, quote placement 4, bounded archive EOF 3, unmapped recovery 2, and property value codec 7. The exact compiler, logs and runner are archived. Its successful compilation also typechecked all then-current portable UI test bodies. UIKit/SwiftUI bodies were inactive.
- `native-navigation-components-v2.json` proves eight exact-source planner/route cases before the final stale-owner predicate refinement. The compile failure in v1 is retained. A later receipt must certify the refinement; these counts are not reused for edited sources.
- `native-inspector-ui-source-v1.json` proves the earlier ten-file parser pass and preservation of the first four UI tests. Subsequent embedded-search/navigation refinements need their own parser receipt; parsing is not a UIKit semantic build.
- The latest root native T5 receipt `native-torah-workflow-20261119-201618-378627.json` built successfully but ended **FAIL after 10 completed runtime checks** with a network timeout. It must not be presented as a complete T5 success; the later diagnostic rerun is separate.
- The actual a5a Apple package counts, native v7 Go/peer proofs, public-provider requests, and canonical archive/property proofs remain scoped to their individual source manifests. They are not summed into a new revision's acceptance result.

General application parity (`APP-01`), whole Heart body/file migration (`MIG-01`), and durable semantic anchors (`EDITOR-02`) were explicitly unimplemented baseline goals. No newly discovered unsupported general editor operation turns those plans into previously implemented custom features. This bounded review corrected concrete native wiring omissions; it does not remove the remaining Apple interaction, broad device, or whole-application acceptance gates.
