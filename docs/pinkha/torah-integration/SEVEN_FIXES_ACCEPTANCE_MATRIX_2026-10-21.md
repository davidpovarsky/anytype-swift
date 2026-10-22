# Anytype Torah seven-fix and native-parity follow-up acceptance matrix

Date: 2026-10-21

This matrix records evidence for the seven owner-reported physical-iPad defects
on top of the earlier eight-fix stage. `EXECUTED_PASS` means a deterministic
portable check actually ran. `CI_PENDING` and `DEVICE_PENDING` are not passes;
the workflow appends the exact Anytype and TorahInspectorKit identities to the
uploaded copy.

| ID | Pre-CI status | Evidence / remaining gate |
|---|---|---|
| F1-A | EXECUTED_PASS / DEVICE_PENDING | Sanitized Genesis 1:5 fixture decodes two `thinsp` plus `nbsp` at the provider display boundary. Real Anytype reader comparison remains an owner-device gate. |
| F1-B | EXECUTED_PASS | Portable PinkhaKit tests pass named, decimal, lower/upper hex, bounded double encoding, malformed/unknown entities, niqqud, raw payload identity and text longer than 4,096 characters. |
| F2-A | CI_PENDING / DEVICE_PENDING | The bespoke detail title row was removed; the native navigation title is the single header and the selector region disappears as a unit. Xcode compilation and host scroll capture remain. |
| F2-B | CI_PENDING / DEVICE_PENDING | Existing hysteresis, upward reveal, manual tools action, short-content guard and iOS 17 preference fallback remain. Runtime anchor/jitter requires host/device evidence. |
| F3-A | CI_PENDING / DEVICE_PENDING | Root relationship mode derives the Book action from empty navigation path and places it in the native leading toolbar slot with a 44pt target. Hebrew physical-right placement remains visual acceptance. |
| F3-B | CI_PENDING / DEVICE_PENDING | Any non-empty route path removes Book and leaves native Back; full-source pushes on the same stack. Three-deep Back/viewport behavior remains runtime acceptance. |
| F4-A | CI_PENDING / DEVICE_PENDING | Host picker is now a native sheet composed from Anytype DragIndicator, TitleView, SearchBar, PlainList, ListSectionHeaderView, AnytypeText, assets and semantic tokens; GroupBox and prominent blue row CTAs were removed. |
| F4-B | CI_PENDING / DEVICE_PENDING | Session queues inspector/search transitions through actual sheet dismissal so only one modal owns presentation. Existing document/block scope, link/open/unlink and error paths remain under focused host tests. |
| F5-A | CI_PENDING / DEVICE_PENDING | Panel demand maps Commentaries→links, Links→links+topics, Notes→notes and In Documents→related documents; repository cache reuse has a deterministic fetch-count test. |
| F5-B | EXECUTED_PASS / CI_PENDING / DEVICE_PENDING | Typed request tokens reject stale completion and cancellation restores idle/cached state. Portable GET retry/backoff/cancellation tests pass for 429/503, timeout recovery and non-transient status; UI state tests await Xcode. |
| F5-C | CI_PENDING / DEVICE_PENDING | Every links response recomputes grouping, topic error/loading renders independently of usable links, and source changes reset every typed state. Repeated live A↔B opens remain device acceptance. |
| F6-A | CI_PENDING / DEVICE_PENDING | Accessory uses Anytype book asset, semantic control/shape colors, caption font, 44pt target and truthful 1/2/10+ count helper. Visual comparison to IMG_0105 remains. |
| F6-B | CI_PENDING / DEVICE_PENDING | EditorViewListCell owns/removes only its Torah accessory, preserving unrelated accessories during reuse. Live edit/scroll/move/undo remains device acceptance. |
| F7-A | CI_PENDING / DEVICE_PENDING | Peek and initial reader resolve stored Hebrew presentation metadata before network content; unresolved Hebrew routes show neutral localized “Source”, never canonical English. |
| F7-B | CI_PENDING | Presentation metadata is additive and explicitly excluded from selection equality/hash/id; host association/search/resolved-reference routes carry Hebrew/English labels. |

## Preserved boundaries

- No Heart/protobuf/CRDT, association schema, native writer, permission,
  signing, entitlement or bundle-identity changes.
- Earlier reader restoration, Peek detents, related-documents limitation,
  no-autofocus quote insertion and legacy Otzaria tool/default APIs remain.
- Space-wide reverse-index item T04 remains out of scope and unresolved.
- No physical-device claim is made by CI or by the standalone Kit demo.

## Native UI parity follow-up — 2026-10-22

Identity before implementation:

- Anytype branch: `pinkha/torah-associations-native-ux-persistence-localization-2026-10-20`
- Anytype prompt baseline: `58bf811bbff08c3f3044108ebfdf569ebbdfd979`
- Anytype actual clean/upstream-equal implementation baseline: `16faea754a3b821671f7b8db92934c06f47468b6`
- TorahInspectorKit pin: `59b6f4629da6a7edd625de0ae004d04dbbc037de`
- Implementation commit: the workflow appends the exact `GITHUB_SHA` to the uploaded copy of this matrix.
- Physical reference files `IMG_0184.jpeg`, `IMG_0185.jpeg`, and `IMG_0168.jpeg` were not present in the supplied local filesystem. Their described provenance is retained, but no photographic comparison is claimed.

### Sheet presentation parity trace

| Property | Original “Link To” | Torah search after follow-up | Source result |
|---|---|---|---|
| Host presentation | Coordinator `.sheet(item:)`; no detent override | Stable host `.sheet(isPresented:)`; no detent override | Same native adaptive sheet sizing; outer runtime bounds remain `DEVICE_PENDING` |
| Inner shell | `SearchViewShell`: `DragIndicator` → `TitleView` → `SearchBar` → content | The same `SearchViewShell` in the same order | Source-equivalent |
| Background / safe area | `Color.Background.secondary`; no custom width or safe-area offsets | Same shared shell; no custom width or safe-area offsets | Source-equivalent |
| Search field | Shared `SearchBar`, focused, native padding/radius/divider | Same exact instance type and position | Source-equivalent |
| Results | Native `SearchCell`, 68pt full row | Native `SearchCell`, 68pt full row, 44pt trailing link action | Torah-only action is the justified difference |
| Extra function | None | Compact segmented source/topic/word selector after search; linked items only when present | Search input is no longer displaced by the former preamble |

### Requirement matrix

`SIMULATOR_PASS` below is conditional on the consolidated workflow completing successfully at the appended `GITHUB_SHA`. `DEVICE_PENDING` remains mandatory for visual and physical-iPad criteria even after green CI.

| ID | Native comparator / new component | Source reference | Expected metric / behavior | Executed or selected test and screenshot reference | Actual result |
|---|---|---|---|---|---|
| A1 | Link-To coordinator sheet / Torah host sheet | `EditorPageCoordinatorView`, `TorahEditorHostModifier` | No Torah detent, width, drag-indicator or safe-area override | Workflow source-contract gate; IMG_0184 unavailable | `EXECUTED_PASS` source trace / `DEVICE_PENDING` bounds |
| A2 | `SearchView` / shared `SearchViewShell` | `SearchView.swift`, `TorahSourcesSearchView.swift` | Identical drag/title/search/background sequence | Windows Swift parser; Xcode host compilation selected | `EXECUTED_PASS` parse / `SIMULATOR_PASS` when workflow green |
| A3 | Native adaptive `.sheet` / same adaptive presentation | `TorahEditorHostModifier.body` | No `.medium/.large` search override and no hidden system drag-indicator modifier | Negative grep in consolidated workflow | `EXECUTED_PASS` source / `DEVICE_PENDING` visual |
| A4 | Link-To search-field placement / Torah search-field placement | `SearchViewShell.body` | Search field directly follows title; Torah controls follow search | Source inspection; IMG_0184 unavailable | `EXECUTED_PASS` structure / `DEVICE_PENDING` visual |
| A5 | Native `SearchCell` / Torah result `SearchCell` | `SearchCell.swift`, `TorahSearchCellData` | 68pt full row, 48pt host icon slot, separate 44pt trailing link target | Host compilation and accessibility smoke selected | `SIMULATOR_PASS` when workflow green / `DEVICE_PENDING` VoiceOver |
| A6 | Native modal lifecycle / existing queued Inspector transition | `TorahEditorSession.presentInspector`, `searchDidDismiss` | Never overlap search and Inspector; preserve pending save and scope | Existing focused session/search tests in native suite | `SIMULATOR_PASS` when workflow green / `DEVICE_PENDING` keyboard |
| A7 | Original Link-To unchanged / additive shell extraction | `LinkToObjectSearchView`, `SearchView` | Original call site and search semantics unchanged | Compilation plus existing native search smoke; comparison capture pending | `SIMULATOR_PASS` when workflow green / `DEVICE_PENDING` screenshot |
| B1 | Original text/quote/callout types / unchanged block models | `TextBlockContentConfiguration`, `TextBlockLeadingStyle` | No type conversion, focus or selection semantic change | Diff inspection; existing quote/no-autofocus tests selected | `EXECUTED_PASS` source / `DEVICE_PENDING` interaction |
| B2 | Callout 20pt leading icon / Torah block ornament | `TextBlockLeadingView`, `TorahBlockAccessoryButton` | New glyph 20×20pt; transparent target and reserved width 44×44pt | `compactBlockOrnamentGeometry`; IMG_0185/0168 unavailable | `SIMULATOR_PASS` when workflow green |
| B3 | Text-block-owned leading decoration family / text-block-owned trailing ornament | `TextBlockContentView.setupLayout` | No cell-wide slab; deterministic 44pt maximum reservation | Runtime layout test plus host build | `SIMULATOR_PASS` when workflow green / `DEVICE_PENDING` reflow |
| B4 | Text layout plumbing / no `UICellAccessory` | `EditorPageController.configureTorahAccessory` | No screen offsets and no list-cell accessory negotiation | Negative grep workflow gate | `EXECUTED_PASS` source |
| B5 | Quiet inline icon / no visible count label | `TorahBlockAccessoryConfiguration` | Full 1/2/10+ count only in accessibility value | Reuse/accessibility unit test | `SIMULATOR_PASS` when workflow green / `DEVICE_PENDING` VoiceOver |
| B6 | Native selection and reuse / block-local button | `TextBlockContentView.updateTorahAccessory` | One-tap route; stale closure/label cleared on reuse | `blockOrnamentReuse`; existing route tests | `SIMULATOR_PASS` when workflow green / `DEVICE_PENDING` gestures |
| B7 | Callout visual family, not component impersonation / book glyph | `TextBlockIconView.createCalloutView`, `.CustomIcons.book` | Semantic secondary tint, 20pt glyph; Callout and quote rule untouched | Source diff + device comparison capture pending | `EXECUTED_PASS` source / `DEVICE_PENDING` visual |
| C1 | No detached overlay / stable modal host only | `TorahEditorHostModifier` | Zero `.topTrailing` Torah overlay or 54/16 offsets | Negative grep workflow gate | `EXECUTED_PASS` |
| C2 | Existing sync/settings glass siblings / BOOK glass sibling | `EditorNavigationBarHelper`, `UIEditorBarButtonItem` | Three 44pt circles, 8pt gaps, native book asset | Xcode build; RTL stack test | `SIMULATOR_PASS` when workflow green / `DEVICE_PENDING` glass visual |
| C3 | Controller-owned current view model / document-scope dispatch | `EditorPageController.navigationBarHelper` | Callback resolves `viewModel.torahSession` when tapped, never a captured session | `navigationActionUsesCurrentDocument` | `SIMULATOR_PASS` when workflow green |
| C4 | Measured editor container / existing settings overflow | `EditorNavigationBarView.canFitUntruncatedTitle`, `additionalMenuItems` | Candidate trio width 148pt; title and real left/right widths determine bar vs overflow; never both | `navigationFitUsesMeasuredWidths`, `navigationPlacementIsExclusive` | `SIMULATOR_PASS` when workflow green / `DEVICE_PENDING` Stage Manager |
| C5 | Existing editing-state machinery / gated Torah entry | `editorEditingStateDidChange` | Only editing/readonly may expose entry; selecting/moving/table/loading hide it | Placement-state test plus native compilation | `SIMULATOR_PASS` when workflow green / `DEVICE_PENDING` transitions |
| C6 | `UIEditorBarButtonItem` semantics / localized BOOK | Navigation helper and `Loc.Pinkha.Torah.title` | 28pt visible native control in 44pt glass; no count bubble; localized accessibility label | Host compilation; VoiceOver pending | `SIMULATOR_PASS` when workflow green / `DEVICE_PENDING` VoiceOver |
| C7 | Existing block actions / independent document action | `EditorPageBlocksStateManager`, controller callback | Top BOOK always `.document`; `.torahLink/.torahOpen` remain block scoped | Source diff and existing route tests | `EXECUTED_PASS` source / `SIMULATOR_PASS` when workflow green |
| C8 | Owner-approved physical order / adaptive narrow fallback | `EditorNavigationBarEditingControls`, settings menu item | RTL physical order ellipsis → book → sync; narrow mode has menu action only | `rtlControlOrder`; owner captures unavailable | `SIMULATOR_PASS` when workflow green / `DEVICE_PENDING` physical iPad |

### Measured geometry and diagnosis

- The rejected implementation combined an image, visible count title, padding and background inside a trailing `UICellAccessory.CustomViewConfiguration`. That mechanism negotiates width at the `UICollectionViewListCell` level, outside the text block's leading/text constraints, which is why it could reserve a cell-wide region rather than an inline ornament. The original bad runtime width cannot be truthfully recovered without the missing physical screenshot/runtime build.
- The replacement is measurable in the focused UIKit test: 20×20pt visible asset glyph, 44×44pt transparent hit target, and exactly 44pt maximum trailing text reservation. It has no visible slab or number.
- The navigation bar remains the existing 44pt `GlassContainerViewIOS26`. The three candidate controls are 44pt each with two real 8pt gaps, totalling 148pt before the measured title/left-slot gaps.
- Modal outer dimensions are intentionally not hardcoded. Both search surfaces now delegate those dimensions to the same native SwiftUI `.sheet` adaptation; exact runtime bounds and corner radius remain `DEVICE_PENDING`.
