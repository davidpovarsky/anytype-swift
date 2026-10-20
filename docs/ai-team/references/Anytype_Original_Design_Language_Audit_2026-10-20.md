# Anytype Original Design Language -- Source-Grounded Audit

**Date:** 2026-10-20  
**Purpose:** Prepare an exact original-Anytype UI design-language reference for future adaptation of Torah associations and TorahInspectorKit. **READ-ONLY AUDIT; no code, GitHub, agent-document or Asana changes.**  
**UX role:** Maya (`maya`) | **engineering:** Noam (`noam`) | **QA:** Roni (`roni`).

## 0. Scope, versions, and evidence standard

- **Original application, not the legacy Pinkha standalone app:** the upstream Anytype iOS/iPadOS app (`anyproto/anytype-swift`) and the user's fork (`davidpovarsky/anytype-swift`). The earlier Pinkha app's palette and serif reading styles must **not** be used as the visual authority here.
- **Fork baseline examined:** `develop` at `1b1043b3a810f6f528ec5147aeb1b29e17b840e7` (commit timestamp 2026-10-18).
- **Current project feature branch examined:** `pinkha/torah-functional-ui-single-device-2026-10-18` at `0c14bcf4ac06466b88ba9c823cac8e0002109898` (read-only branch metadata as of the audit).
- **Design-system identity proof:** `Modules/DesignKit` has the **same tree SHA** `904fd687ea517912f47fda535c7de25414a5f09d` in upstream and the fork's `develop` and feature branch. `Modules/Assets` also has exactly the **same tree SHA** `59b535c2a12bb8b346dbcb91a44e11feb3d80974`. Thus the **source** of the original design language is common across the compared versions.
- **Pinned standalone package:** `Modules/PinkhaKit/Package.swift` uses `TorahInspectorKit` revision `e8aefc626350c8ee0df9daf8d7de7e1dcd0ea418`, and currently depends on **`TorahInspectorCore` only**, not `TorahInspectorUI`. A newer separate candidate `0d4c3407182e18ca62c3280b3a04a2b905a51c93` is 11 commits ahead; it is not an approved upgrade.
- **Evidence level:** code and asset catalogs inspected using the GitHub connector; **no live app, Xcode simulator, device screenshot, physical iPad, or runtime typography measurement** was inspected. Numeric facts below are source values, not a visual pixel-matching certificate. A future runtime acceptance phase is mandatory.

### Governing references

- [DesignKit source](https://github.com/davidpovarsky/anytype-swift/tree/develop/Modules/DesignKit)
- [Assets source](https://github.com/davidpovarsky/anytype-swift/tree/develop/Modules/Assets)
- [Original UI implementation](https://github.com/davidpovarsky/anytype-swift/tree/develop/Anytype/Sources/PresentationLayer)
- [Anytype design taste and code rules](https://github.com/davidpovarsky/anytype-swift/blob/develop/TASTE_INVARIANTS.md)
- [Original color system documentation](https://github.com/davidpovarsky/anytype-swift/blob/develop/Anytype/Sources/DesignSystem/COLOR_SYSTEM.md)
- [AI team assignments](https://github.com/davidpovarsky/anytype-swift/blob/develop/docs/ai-team/PROJECT_ASSIGNMENTS.md)
- [Maya UX role instructions](https://github.com/davidpovarsky/anytype-swift/blob/develop/.agents/roles/maya.md)

## 1. Design character and governing rules

Anytype's native iOS interface is **minimal, restrained, editorial in hierarchy but utilitarian in controls**, with clear text contrast and quiet supporting metadata. It employs a content-first white / deep charcoal backdrop, an accent blue for affirmative actions, flat content surfaces and subtly separated regions. Material or Liquid Glass is primarily part of **navigation / floating controls**, not a replacement for every ordinary content row.

**Non-negotiable design rule for Torah UI:** **inherit/reuse host styles and existing components**, not approximate them with a new local palette, new font sizes, custom blue, shadow-heavy cards, or blanket `.regularMaterial`. Context is important: a 24pt widget radius does **not** mean every sheet row must have 24pt corners.

The repository's `TASTE_INVARIANTS.md` explicitly calls for `AnytypeText` in place of ordinary SwiftUI `Text` wherever applicable, semantic colors instead of arbitrary RGBA, `AnytypeFontBuilder` / `AnytypeFont` instead of raw `.font(.system(size:))`, asset-backed icons for custom icons, localization through generated `Loc`, and buttons for single-tap interactive affordances. Exceptions are documented for APIs requiring stock SwiftUI components.

## 2. Semantic color inventory (from actual asset values)

Values are **documentation only**. Future implementation must call semantic `Color` or `UIColor` accessors from Assets so light/dark variations and state changes remain dynamic. Alpha is included where a color is translucent.

| Role | Exact accessor | Light | Dark | Typical purpose |
|---|---|---|---|---|
| Main page | `Color.Background.primary` | `#FFFFFF` | `#000000` | Root content surface |
| Secondary page | `Color.Background.secondary` | `#FFFFFF` | `#1F1F1F` | Search and secondary-sheet content |
| Widget | `Color.Background.widget` | `#FFFFFF` | `#252525` at 75% opacity | Home widget cards |
| Navigation overlay | `Color.Background.navigationPanel` | `#FFFFFF`, alpha .60 | `#000000`, alpha .75 | Navigation backing |
| Light highlight | `Color.Background.highlightedLight` | `#4F4F4F`, alpha .04 | `#DADADA`, alpha .09 | Quiet states |
| Medium highlight | `Color.Background.highlightedMedium` | `#4F4F4F`, alpha .08 | `#DADADA`, alpha .14 | Search field, pressed controls |
| Primary text | `Color.Text.primary` | `#252525` | `#F3F3F3` | Primary content |
| Secondary text | `Color.Text.secondary` | `#949494` | `#909090` | Secondary metadata |
| Tertiary text | `Color.Text.tertiary` | `#BFBFBF` | `#646464` | Muted metadata and disabled hints |
| Secondary translucent text | `Color.Text.transparentSecondary` | `#252525` alpha .60 | `#F3F3F3` alpha .70 | Group labels on translucent surfaces |
| Tertiary translucent text | `Color.Text.transparentTertiary` | `#252525` alpha .30 | `#F3F3F3` alpha .40 | Very quiet hints |
| Main control | `Color.Control.primary` | `#252525` | `#F3F3F3` | Interactive icon/label |
| Secondary control | `Color.Control.secondary` | `#A7A7A7` | `#7B7B7B` | Low-emphasis control |
| Disabled/third control | `Color.Control.tertiary` | `#DCDCDC` | `#494949` | Inactive control |
| Brand action blue | `Color.Control.accent100` | `#377AFF` | `#377AFF` | Primary CTA |
| Accent 80 | `Color.Control.accent80` | `#699BFF` | `#2D63CF` | Secondary tonal action |
| Accent 50 | `Color.Control.accent50` | `#9BBCFF` | `#224C9E` | Mid tonal action |
| Accent 25 | `Color.Control.accent25` | `#CDDEFF` | `#18346E` | Very light tonal highlight |
| Primary shape | `Color.Shape.primary` | `#E3E3E3` | `#3A3935` | Visible strokes/fills |
| Secondary shape | `Color.Shape.secondary` | `#EBEBEB` | `#303030` | Intermediate surface |
| Tertiary shape | `Color.Shape.tertiary` | `#F2F2F2` | `#1F1E1D` | Subtle shape |
| Transparent primary shape | `Color.Shape.transparentPrimary` | Black alpha .11 | White alpha .24 | Outline/overlay |
| Transparent secondary shape | `Color.Shape.transparentSecondary` | Black alpha .05 | White alpha .16 | Hover/subtle fill |
| Widget divider | `Color.Widget.divider` | `#E3E3E3` | `#DAD7CA`, alpha .14 | Widget row separators |
| Widget metadata | `Color.Widget.secondary` | `#949494` | `#F3F2EC`, alpha .50 | Home preview subtitle |

Additional source namespaces exist for `Color.Light`, `.Dark`, `.Pure`, `.VeryLight`, `Additional`, `Shadow`, `ModalScreen`, `Auth`, `Widget`, and more. These are **semantic or intended UI category namespaces**; they are not a mandate to introduce a new arbitrary Torah-category color scheme. The exact source is `Modules/Assets/Sources/Assets/Resources/SystemColors.xcassets/` and typed accessors in `Modules/Assets/Sources/Assets/Generated/Color+Assets.swift`. Never manually edit generated `Assets.swift`, `Color+Assets.swift`, or `UIColor+Assets.swift`.

### Implications for the Torah area

- Use `Color.Background.primary/secondary/widget` for the appropriate host surfaces; do not globally force `.regularMaterial` on the Torah inspector.
- Use `Color.Text.primary/secondary` for source references and explanatory metadata.
- Use `Color.Control.accent100`, not an unscoped SwiftUI `.accentColor`, for action emphasis that must exactly match the host.
- Use host `Color.Widget.divider` or section-specific separators as appropriate; do not invent a new hairline gray.
- Verify reading contrast in both themes and within a trailing sheet, where translucency/background may change the apparent result.

## 3. Typography: exact native Anytype hierarchy

Primary UI family: **Inter**. Code: **IBM Plex Mono**. **Riccione Xlight** and larger Inter variants serve special marketing/banner uses rather than routine notes and inspector rows. The legacy standalone Pinkha app's serif reading typography is *not* the native Anytype style.

**Sources:** `Modules/DesignKit/Sources/DesignKit/Fonts/Config/AnytypeFont.swift` and `AnytypeFontConfig.swift`. Render via `AnytypeText(_, style:)` (SwiftUI), `AnytypeFontBuilder`, or `UIKitFontBuilder` (UIKit). These apply font family/weight, point size, kerning, line height, and deliberate vertical spacing. `AnytypeText` should be the default host UI text, not `Text(...).font(.body)`.

| Token | Family and weight | Size/line height | Tracking | Typical role |
|---|---|---|---|---|
| `.title` | Inter Bold | 28 / 32 | -0.48 | Editor main title and H1 |
| `.heading` | Inter Bold | 22 / 26 | -0.36 | H2 |
| `.subheading` | Inter Bold | 17 / 24 | -0.28 | H3 |
| `.contentTitleSemibold` | Inter Semibold | 28 / 32 | -0.48 | Strong content header |
| `.previewTitle1Medium` | Inter Medium | 17 / 22 | -0.41 | Larger preview |
| `.previewTitle1Regular` | Inter Regular | 17 / 22 | -0.41 | Larger preview, regular |
| `.previewTitle2Medium` | Inter Medium | 15 / 20 | -0.24 | Widget/list row title |
| `.previewTitle2Regular` | Inter Regular | 15 / 20 | -0.24 | Secondary preview |
| `.bodyRegular` | Inter Regular | 17 / 24 | -0.41 | Main editor body and standard text |
| `.bodySemibold` | Inter Semibold | 17 / 24 | -0.41 | Strong row/cell text |
| `.calloutRegular` | Inter Regular | 15 / 22 | -0.24 | Callout |
| `.relation1Regular` | Inter Regular | 15 / 20 | -0.24 | Rich relation main |
| `.relation2Regular` | Inter Regular | 13 / 18 | -0.08 | Relation/preview secondary |
| `.relation3Regular` | Inter Regular | 12 / 15 | 0 | Compact metadata |
| `.uxTitle1Semibold` | Inter Semibold | 17 / 24 | -0.41 | Navigation header |
| `.uxTitle2Semibold` | Inter Semibold | 15 / 20 | -0.24 | Section title |
| `.uxTitle2Medium` | Inter Medium | 15 / 20 | -0.24 | Home section heading |
| `.uxTitle2Regular` | Inter Regular | 15 / 20 | -0.24 | Less prominent heading |
| `.uxBodyRegular` | Inter Regular | 17 / 24 | -0.41 | Form text, search |
| `.uxCalloutMedium` | Inter Medium | 15 / 22 | -0.24 | CTA details |
| `.uxCalloutRegular` | Inter Regular | 15 / 22 | -0.24 | Supplemental UI body |
| `.caption1Semibold` | Inter Semibold | 13 / 18 | -0.08 | Metadata heading |
| `.caption1Medium` | Inter Medium | 13 / 18 | -0.08 | Metadata badge |
| `.caption1Regular` | Inter Regular | 13 / 18 | -0.08 | Search grouping |
| `.caption2Regular` | Inter Regular | 11 / 14 | +0.07 | Fine-print metadata |
| `.caption2Medium` | Inter Medium | 11 / 14 | -0.07 | Fine-print metadata |
| `.caption2Semibold` | Inter Bold* | 11 / 14 | -0.07 | Small emphatic metadata |
| `.button1Medium` | Inter Medium | 17 / 24 | -0.41 | Primary large CTA |
| `.button1Regular` | Inter Regular | 17 / 24 | -0.41 | Secondary CTA |
| `.codeBlock` | IBM Plex Mono Regular | 15 / 22 | -0.24 | Editor code |
| `.navigationBarTitle` | Inter Semibold | 15 / 20 | -0.24 | Alternate narrow nav title |

`*` `caption2Semibold` is **actually defined** with `Inter.bold` in the inspected `AnytypeFontConfig.swift`, despite its semibold token name. Preserve the actual token rather than silently normalizing it. Other specialized authentication/banner tokens exist; they are outside the functional Torah relationship UI.

### Typography caveats and Hebrew

- Exact spacing must come from `AnytypeText`: simply calling `Font.custom("Inter", size: ...)` omits typography adjustments and can misalign baselines.
- The source stores fixed point sizes in `AnytypeFontConfig`. The app uses some `@ScaledMetric` elsewhere but **universal Dynamic Type compliance cannot be assumed**. Verify user accessibility sizes rather than claiming they are supported.
- Hebrew, vowel marks, mixed Hebrew/English references, truncation, and actual fallback glyph metrics require on-device or simulator inspection. Do not assume Inter contains perfect Hebrew glyph coverage; do not arbitrarily replace host UI typography with another Torah font.
- Torah primary *source text* may benefit from a separately approved reading-font policy; the **surrounding UX** should always share Anytype typography and colors, and new reading settings must be explicit rather than an accidental different UI.

## 4. Buttons and interactive components

**Source:** `Modules/DesignKit/Sources/DesignKit/Components/StandardButton/{StandardButton.swift,StandardButtonConfig.swift,StandardButtonStyle.swift}`.

| Button variant | Height | Radius | Text and behavior |
|---|---:|---:|---|
| `.primaryLarge`, `.secondaryLarge`, `.warningLarge` | 52pt | 26pt | Primary & modal full-width actions, semantic text and pressed/disabled visuals |
| `.primaryMedium`, `.secondaryMedium`, `.warningMedium` | 44pt | 22pt | Mid-sized actions |
| `.primarySmall`, `.secondarySmall`, `.warningSmall` | 36pt | 18pt | Small contextual actions |
| `.primaryXSmall`, `.secondaryXSmall`, `.warningXSmall` (+ some stretched variants) | 28pt | 14pt | Inline actions |
| `.borderlessLarge` / `.borderlessSmall` | 48pt | 0pt | Secondary text actions |
| `.linkLarge` | 52pt | 0pt | Link-style action |

`StandardButton` also supports a progress state, bordered secondary styles, disabled state, label/information badge, and pressed animation scale **0.94** with **0.15s** ease-out. Its primary background is `Color.Control.accent100` and text white. These interaction details are part of the design language, not merely colors.

Other native/reusable primitives: `RoundedButtonView`, `AnytypeToggle`, `AnytypeCheckbox` and `AnytypeCircleCheckbox`, `AnytypeTextField`, `DragIndicator`, `ScreenStateView`, `EmptyStateView`, shared `SearchBar`, `NavigationHeader`, `IconView`, `StandardButton`, `AsyncStandardButton`, `DotsView`, and toast/snackbar patterns. In the host `Anytype` app many of these views are app-internal; verify module access before choosing reuse, rather than copying source into a separate package.

**Torah mapping:** 'Add note' => host `StandardButton` appropriate size/state; open reference / reveal commentary => existing icon/button and list styles; remove relation => destructive host system action; disabled/empty/loading/error => host state patterns. Do not automatically replace every icon-only control with an oversized primary CTA.

## 5. Layout, densities, spacing and surfaces

Anytype uses **context-specific values**, not a universal spacing token grid that should be imposed on all feature screens.

| UI element | Verified source geometry / treatment | Source |
|---|---|---|
| Native app navigation header | 44pt height; 44pt button frames; horizontal padding 16; centered title with balanced left/right widths; optional top blur | `NavigationHeader.swift` |
| Navigation title | `AnytypeText(..., style: .uxTitle1Semibold)` and `Color.Text.primary` | `NavigationHeaderTitle.swift` |
| Home content width | 20pt horizontal insets + `.fitIPadToReadableContentGuide()` | `HomeWidgetsView.swift` |
| Bottom floating controls | 48pt control frame; 24pt horizontal inset; iOS 26 native glass wrapper and bottom blur | `HomeBottomBarMetrics.swift`; `HomeBottomNavigationPanelView.swift` |
| Home widget cards | `Color.Background.widget`; 24pt continuous corner radius; 40pt header; collapse transition | `LinkWidgetViewContainer.swift` |
| Home widget group heading | `.uxTitle2Medium`; 22pt top / 12pt bottom padding; `Color.Text.transparentSecondary` | `HomeWidgetsGroupView.swift` |
| Standard home list row | 72pt height; 48pt object icon; 16pt horizontal padding; 12pt icon/text gap; `.previewTitle2Medium` title | `ListWidgetRow.swift` |
| Home tree row | 40pt height; 18pt icon; level indentation `16 * (level + 1)`; 8/12pt gaps | `TreeWidgetRowView.swift` |
| Search bar | `AnytypeTextField(..., font: .uxBodyRegular)`; `Color.Background.highlightedMedium`; radius 10; asset search and clear icons | `SearchBar.swift` |
| Search results | `LazyVStack` rows, grouped `.caption1Regular` section header; 300ms typing debounce | `SearchView.swift` |
| Simple empty state | `.uxBodyRegular` primary/secondary, optional illustration, `.secondarySmall` action, horizontal padding 20 | `EmptyStateView.swift` |
| Legacy styled bottom sheet | `anytypeSheet` as fullScreenCover; 38pt radius on iOS26, 34pt earlier; shadow radius 20; horizontal inset 8 | `SheetView.swift` + `View+Sheet.swift` |
| Editor text block horizontal margins | 20pt either side; internal quote vertical content inset 10; standard block 4 | `TextBlockContentConfiguration.swift`; `TextBlockLayout.swift` |

**Critical distinction:** The legacy generic Anytype sheet geometry is **not** permission to replace the agreed iPadOS 27 *native trailing side sheet*. For Torah associations, retain the native trailing sheet's three detents and background interaction, and **make the sheet's inner content Anytype-consistent**, avoiding a duplicate card around the entire sheet and double toolbar.

### iPad readability and narrow widths

Use the host `.fitIPadToReadableContentGuide()` and examine `HorizontalReadabilityPadding.swift`, which targets roughly 70 characters of readable line length and uses a `@ScaledMetric` reference. Avoid `UIScreen.main.bounds`, hard widths, forced min width 320, and iPad-only assumptions. Test same-device Stage Manager / split window width changes and iPhone compact layout **in the actual integrated host**, not just a standalone kit preview.

## 6. Icons and semantic affordances

- Original app icons and symbols are generated from `.xcassets` into typed `Image(asset: .X18...)`, `.X24...`, `.X32...`, `.CustomIcons...`, `.RightAttribute.disclosure`, etc. Source: `Modules/Assets/Sources/Assets/Generated/ImageAssets.swift` and the Assets resource catalogs.
- `IconView` / `ObjectIconView` represents host document identity; where a Torah item is an Anytype object, use existing document icon rendering rather than a substitute generic symbol.
- SF Symbols **are** used by upstream Anytype in native `Menu` and some system contexts; avoid an absolute ban. Match the existing icon asset for recurring app-level affordances such as close/back/ellipsis/search/disclosure/plus where one exists.
- Icon sizes, tappable frame sizes, tint and hierarchy should follow the corresponding parent component. A 30pt bespoke dismiss button in a separate kit is not a substitute for the host's 44pt header button target.

## 7. Interactions, navigation, search, text editing

- Navigation shell is mixed SwiftUI + UIKit. `AnytypeNavigationView.swift` wraps `FullScreenSwipeNavigationController`, preserving full-screen interactive pop behavior. The Torah feature must avoid a second independent faux navigation chrome inside the right-hand sheet.
- Home toolbar uses `GlassEffectContainerIOS26` and `.glassEffectInteractiveIOS26(in: ...)`; native glass is concentrated on controls and navigation. Content cards remain primarily flat/opaque according to host surface tokens.
- `LinkWidgetViewContainer` and `TreeWidgetRowView` use `.disclosure` and `.disclosureSmall` motion; existing row actions support context menus and drag/reorder. Reuse interaction character and keyboard/context handling, do not invent busy animation.
- Search defaults to a 300ms debounce on nonempty typing, immediate initial empty list, reusable search field, grouped search cells, consistent no-result states. Torah source/topic/word pickers should match this where product behavior is comparable.
- Text editing is custom UIKit. `TextBlockContentView.swift` takes care to maintain the caret during model echoes, avoid resetting the autocorrect buffer, preserve marked-text IME composition and avoid unsafe synchronous first-responder acquisition in cell dequeue. Torah quote/link insertion **must preserve these invariants**. Read-only source excerpts must not suddenly bring up the keyboard.
- Editor text styles are mapped centrally by `TextContent+Font.swift`: H1 `.title`, H2 `.heading`, H3 `.subheading`, regular/quote/callout `.bodyRegular`, code `.codeBlock`. Avoid treating quote as a different standalone editor typography without product approval.
- Respect native `.contextMenu` actions, VoiceOver actions/labels, selection/copy behavior, tapping versus double-tap semantics and save/uncertain/conflict states.

## 8. Standalone TorahInspectorKit: concrete design gaps

The **pinned** `TorahInspectorKit` is a reusable `.iOS17/.macOS14` package. UI code: `Sources/TorahInspectorUI/TorahSegmentDetailView.swift`, `TorahSourceReaderView.swift`, `TorahInspectorView.swift`. These are **source-audited potential visual inconsistencies**. Since the UI target is **not yet host-wired** in the examined feature branch, do **not** call them already visible defects in the running fork.

| Kit observation (source) | Original Anytype rule | Desired integration treatment |
|---|---|---|
| Generic `Text(...).font(.title3/.subheadline/.caption/.system(size: 15))` | `AnytypeText` + typed `AnytypeFont` | Host rendering adapter / typography injection; preserve localized Hebrew readability |
| Unscoped `Color.accentColor`, `Color.primary.opacity` | Semantic `Color.Text.*`, `Color.Control.accent*`, `Color.Background.*` | Token-based color bridge; match dark/contrast behavior |
| `.background(.regularMaterial)` applied to entire panel plus a bespoke outer rounded 22pt/shadow container | Actual host content surface semantics; native glass on chrome | For `.embeddedSheet` no duplicate panel chrome; align content and sections to Anytype |
| Custom card radius 12/14pt, padding 12/13/18pt | Contextual native Anytype row/list/widget geometries | Select **the correct host context**; do not blindly use universal 24pt widget radius |
| `.buttonStyle(.borderedProminent)` on Add Note | `StandardButton` primary/small/medium with disabled/pressed/loading visuals | Use host action component or justified equivalent |
| Bespoke close glyph in 30x30 frame | Host header/nav 44pt action frame | Reuse host navigation header action sizing; avoid double-close |
| `.pickerStyle(.segmented)` and generic `DisclosureGroup` | Match Anytype's local list/chip/tab idioms | Audit screen context and choose native host-consistent tool selection and expand behavior; do not reject native controls automatically |
| `Image(systemName:"book.closed"/"tag")` for reference/topic | Host asset icon system | Map recurring affordances to host asset/symbol vocabulary with semantic meaning |
| Generic `ContentUnavailableView` error and empty states | `EmptyStateView`, `ScreenStateView`, loading & error components | Host-aligned error/empty/retry presentation |
| UIKit editor quote is a separate host concern | Preserve `TextBlockContentView` handling | Add actual Anytype Quote and no-autofocus behavior once architectural gates pass |

### Package dependency architecture caution

`TorahInspectorKit` cannot simply `import DesignKit` from the Anytype host app, because the standalone package is separately reusable, including macOS, while Anytype's local DesignKit is iOS-only. Choose a narrow host-side bridge or explicit injectable appearance/rendering strategy, respecting SwiftPM product visibility and the kit's portability. A future engineering audit must establish the exact viable integration point **before** implementing. Do not duplicate static Hex colors or copy entire Anytype views into the kit.

### Stable three-stage sheet requirement

For the new iPadOS 27 implementation (a separate planned T3 task), preserve `.sheet` with `.presentationPlacement(.trailing)` and detents **155pt / medium / large**, background interaction, real drag indicator, RTL physical right side, iPhone/iOS26 fallback, and narrow Stage Manager width. These presentation constraints are **independent** of color/typography changes. The new UI must not regress them or replace with the earlier `.inspector` approach.

## 9. Asana current-state cross-reference (read-only)

**Project:** [Pinkha x Anytype -- Torah Integration (T0-T7)](https://app.asana.com/1/1219597879016953/project/1219604672449660). Last seen project status updated 2026-10-18, with 19 tasks / 5 completed / 14 incomplete as recorded by Asana; Asana status alone is not evidence of a latest code feature passing.

| Related task | Asana task ID | Seen status / dependency | Logical lead |
|---|---|---|---|
| T2-L single active writer storage | `1219610263458741` | In progress / native middleware acceptance gate unresolved in branch record | Noam; Eitan/Dana/Roni review |
| T3 native TorahInspectorKit UI | `1219604675985547` | Planned; gated on T2-L | Maya UX / Noam implementation / Roni QA |
| Native iPadOS 27 trailing side sheet | `1219633037678176` | Planned; no narrow physical iPad validation | Maya UX |
| T4 Anytype Quote/no focus | `1219604770637161` | Planned | Maya UX / Noam implementation |
| T5 Notes + reverse Torah knowledge | `1219604672452265` | Planned | Noam, with Maya UX input |
| Selected-word semantic anchor | `1219610432822791` | Planned/open; stable anchoring unproven | Eitan architecture |
| E2E/iPhone/iPad/RTL/CI/IPA | `1219610263566419` | Planned, not yet new-feature verified | Roni QA |
| Original safe cross-device T2 | `1219604770636937` | Still blocked; independent from T2-L | Eitan architecture |

**Responsible role:** **Maya** is the explicitly assigned Native UX owner in both `docs/ai-team/TEAM.md`, `docs/ai-team/PROJECT_ASSIGNMENTS.md` and `.agents/roles/maya.md`. **Noam** implements and tests, **Roni** verifies. Roles are **logical**, not provisioned Asana user accounts. The Asana tasks' `assignee` fields were generally null when read; ownership here follows repo handoff documents.

**No Asana or repository changes were made during this audit.**

## 10. Future proposed update to Maya's agent instructions (NOT APPLIED)

When the project owner explicitly requests updates, add a tightly scoped *Anytype Visual Consistency Contract* to `.agents/roles/maya.md` and/or a new reusable design-system reference linked from that role. Do **not** replace general `TEAM.md`, `AGENTS.md`, or unrelated global settings. Candidate requirements:

1. For any native UI change, read the **actual active** `DesignKit` and `Assets` files, and compare relevant upstream home, editor, search and sheet components before writing views.
2. Prefer `AnytypeText`/`AnytypeFont` and semantic host `Color.*` tokens; no arbitrary `Font.system(size:)`, raw hex, duplicate theme or broad `.accentColor` unless justified.
3. Reuse `StandardButton`, native labels, search, header, empty/error state, icon and list components where module visibility allows. Otherwise build only a minimal host adapter.
4. Preserve Anytype interaction states, focus/caret/IME behavior, gesture navigation, toolbars, accessibility, localization, RTL, light/dark modes and compact iPad window reflow.
5. Preserve three-detent trailing iPadOS27 sheet and device fallbacks; visual changes must not alter application/data/repository contracts or the sync-safety gate.
6. Require a named screen-by-screen comparison against the original host using actual screenshots in both schemes on iPhone and iPad; use source token assertions/focused tests where feasible.
7. Separate **design review** (Maya), **technical implementation** (Noam) and **evidence-based acceptance** (Roni); do not claim a feature is integrated before it is visibly run.
8. Avoid upstream code changes when a narrow downstream host bridge is sufficient; flag any required core/Heart/protobuf change for owner approval.

## 11. Proposed visual QA and acceptance matrix (NOT RUN)

| Scene | What to compare | Essential variants |
|---|---|---|
| Anytype home widgets vs Torah knowledge cards | Text, hierarchy, icon positions, corner radii, backgrounds, divider treatment | Light/dark, iPhone/iPad |
| Anytype editor + read-only Torah Quote | Existing editor font, quote styling, keyboard/no-autofocus, selection/copy | Hebrew niqqud, mixed RTL/LTR, edit/undo/relaunch |
| Original search vs source/word/topic selector | Search bar radius/field, grouped results, row height, empty/error/loading and keyboard | Initial empty, typing debounce, no results, long text |
| Original navigation header vs Torah inspector | Bar height, centered title, 44pt hit targets, back/dismiss, native glass | iOS26/iOS27, RTL physical side, VoiceOver |
| Anytype action buttons vs Add Note/Unlink | CTA heights, states, pressed scale, text weights, priority color | Enabled, disabled, saving, failure, uncertain |
| Original content area vs trailing sheet | Sheet inner content style, safe-area, background interaction, no double chrome | 155pt/medium/large, Stage Manager narrow window, landscape |
| Notes and reverse knowledge lists | Host row, object icon, metadata, count badge, destructive action | Multiple Spaces, 0/1/many results |
| Accessibility | Contrast, Dynamic Type, button labels, reading order and touch targets | Accessibility sizes, VoiceOver, dark mode |

### Required proof gate

A visual match is **not complete** on code inspection alone. Record before/after screenshots from an actual compiled host build at exact commit SHA, test narrow-window on the **same real iPad** where required by Asana, check RTL physical-right presentation and text selection, and provide Roni's explicit verification evidence. Gate T3 implementation on T2-L native persistence/permission/reopen proof. Leave original multi-device sync T2 marked blocked until its independent criteria pass.

## 12. Source file path index

All paths relative to `davidpovarsky/anytype-swift` `develop` unless otherwise noted.

```text
Modules/DesignKit/Sources/DesignKit/Fonts/Config/AnytypeFont.swift
Modules/DesignKit/Sources/DesignKit/Fonts/Config/AnytypeFontConfig.swift
Modules/DesignKit/Sources/DesignKit/Fonts/Config/SwiftUIFont.swift
Modules/DesignKit/Sources/DesignKit/Fonts/Config/UIKitFont.swift
Modules/DesignKit/Sources/DesignKit/Components/AnytypeText.swift
Modules/DesignKit/Sources/DesignKit/Components/AnytypeTextField.swift
Modules/DesignKit/Sources/DesignKit/Components/StandardButton/StandardButton.swift
Modules/DesignKit/Sources/DesignKit/Components/StandardButton/StandardButtonStyle.swift
Modules/DesignKit/Sources/DesignKit/Components/StandardButton/StandardButtonConfig.swift
Modules/Assets/Sources/Assets/Generated/Color+Assets.swift
Modules/Assets/Sources/Assets/Generated/ImageAssets.swift
Modules/Assets/Sources/Assets/Resources/SystemColors.xcassets/
Anytype/Sources/DesignSystem/COLOR_SYSTEM.md
Anytype/Sources/PresentationLayer/Common/SwiftUI/Navigation/NavigationHeader.swift
Anytype/Sources/PresentationLayer/Common/SwiftUI/Navigation/NavigationHeaderTitle.swift
Anytype/Sources/PresentationLayer/Common/SwiftUI/Navigation/NavigationHeaderLeftButton.swift
Anytype/Sources/PresentationLayer/Modules/HomeWidgets/Container/HomeWidgetsView.swift
Anytype/Sources/PresentationLayer/Modules/HomeWidgets/Container/Views/HomeWidgetsGroupView.swift
Anytype/Sources/PresentationLayer/Modules/HomeWidgets/Widgets/Common/LinkWidgetViewContainer.swift
Anytype/Sources/PresentationLayer/Modules/HomeWidgets/Widgets/List/Common/Content/Subviews/ListWidgetRow.swift
Anytype/Sources/PresentationLayer/Modules/HomeWidgets/Widgets/Tree/Common/Rows/TreeWidgetRowView.swift
Anytype/Sources/PresentationLayer/Modules/HomeNavigationContainer/Panel/HomeBottomBarMetrics.swift
Anytype/Sources/PresentationLayer/Modules/HomeNavigationContainer/Panel/HomeBottomNavigationPanelView.swift
Anytype/Sources/PresentationLayer/Common/SwiftUI/Search/Common/SearchView/SearchBar.swift
Anytype/Sources/PresentationLayer/Common/SwiftUI/Search/Common/SearchView/SearchView.swift
Anytype/Sources/PresentationLayer/Common/SwiftUI/BasicComponents/EmptyStateView.swift
Anytype/Sources/PresentationLayer/Common/SwiftUI/BasicComponents/HorizontalReadabilityPadding.swift
Anytype/Sources/Design system/SheetView/SheetView.swift
Anytype/Sources/Design system/SheetView/View+Sheet.swift
Anytype/Sources/PresentationLayer/Common/SwiftUI/NavigationView/AnytypeNavigationView.swift
Anytype/Sources/Design system/TextComponents/TextContent+Font.swift
Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/TextBlockContentView.swift
Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/TextBlockContentConfiguration.swift
Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/Views/TextBlockLayout.swift
Anytype/Sources/Pinkha/Home/PinkhaHomeSectionsView.swift [feature branch]
Anytype/Sources/Pinkha/Home/PinkhaHierarchySectionView.swift [feature branch]
Modules/PinkhaKit/Package.swift [feature branch]
TASTE_INVARIANTS.md
docs/ai-team/TEAM.md
docs/ai-team/PROJECT_ASSIGNMENTS.md
.agents/roles/maya.md
```

Pinned Kit paths relative to `davidpovarsky/TorahInspectorKit` at `e8aefc626350c8ee0df9daf8d7de7e1dcd0ea418`:

```text
Sources/TorahInspectorUI/TorahInspectorView.swift
Sources/TorahInspectorUI/TorahSegmentDetailView.swift
Sources/TorahInspectorUI/TorahSourceReaderView.swift
Sources/TorahInspectorUI/TorahInspectorAppearance.swift
Sources/TorahInspectorUI/TorahInspectorPresentation.swift
Sources/TorahInspectorUI/TorahInspectorHostActions.swift
```

---

**Status:** Source-backed audit and future migration map prepared. **Not yet:** a working integrated Torah UI, screenshots, physical narrow-iPad proof, final visual verification, or agent-doc/Asana edits.
