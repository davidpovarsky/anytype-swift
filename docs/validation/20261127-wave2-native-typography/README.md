# Native editor typography — isolated future core repair

This tranche follows the separately published Add block creation commit
`dc582ba3239d6dcb66dbe1f7098b95349e4289f9`. It repairs the existing renderer's
uniform heading font and ordinary code font through the original Anytype
DesignKit catalog. It changes no Native/Host contract, block conversion API,
stored text, native style, writing-direction policy or marker alignment.

## Canonical source

The original `TextContent+Font.swift` maps first-, second- and third-level
headings to `.title`, `.heading` and `.subheading`; ordinary text, lists and
quotes use `.bodyRegular`; code uses `.codeBlock`. The actual
`AnytypeFontConfig.swift` supplies these nominal fonts:

| Native content | Original Anytype style | Original nominal face/size |
| --- | --- | --- |
| Heading level 1 | title | Inter bold, 28 pt |
| Heading level 2 | heading | Inter bold, 22 pt |
| Heading level 3 | subheading | Inter bold, 17 pt |
| Ordinary text, lists, quotes | bodyRegular | Inter regular, 17 pt |
| Code | codeBlock | IBM Plex Mono regular, 15 pt |

`source-references.json` binds the original source files. The older prose
typography table differs from the actual code and is retained only as context.
The code catalog is the authority; no copied font-size table is introduced into
the renderer. Unknown or missing native heading levels retain the previous
title2 scale; received native values are never rounded or rewritten.

## Rendering and Dynamic Type

One downstream `AnyNativeTextTypography` policy obtains the original nominal
bundled font and scales it once through `UIFontMetrics` for the controller's
actual trait collection. Every render starts from the nominal DesignKit font,
so a previously scaled font is never scaled again. The iOS-only DesignKit
product dependency is explicit for both the UI and its tests.

The controller observes `UITraitPreferredContentSizeCategory` and calls its
existing render path. A row's presentation cache includes its applied content
size category and native block type, in addition to the existing text/style
identity. A size change or an externally changed type can therefore update
attributes even when the text is unchanged. The cache advances only after the
existing renderer accepts the attributes. Its marked-text guard remains in
charge, so a composing buffer receives its deferred presentation update through
the normal render after composition ends. Reuse clears both added cache fields.

Unmarked runs retain the exact base font. Body emphasis uses the original
`MarkStyleModifier` → `UIFont.bold` policy: apply that policy to the original
nominal DesignKit font, then restore the already-scaled point size. This keeps
body semibold and heading bold at every category. Native italic font traits
remain as before; the original Heart modifier's separate synthetic-obliqueness
behavior is not added by this tranche. Code uses the original IBM Plex Mono
resources, selecting and
registering the exact regular, bold, italic or bold-italic face through
`UIKitFontBuilder`. This avoids asking the descriptor to synthesize a face
whose separate font resource has not been registered in a fresh process.
The original paragraph style, links, strikethrough, selection and text-storage
update path remain intact. Marker, source-label and status-label scaling is
enabled without changing their existing alignment.

Apple's public APIs consulted for the wrapper and observation are:

- https://developer.apple.com/documentation/uikit/uifontmetrics/scaledfont(for:compatiblewith:).md
- https://developer.apple.com/documentation/uikit/uitraitchangeobservable-67e94/registerfortraitchanges(_:handler:).md

## Focused future validation

Two new UIKit methods are prepared:

1. Actual original bundled heading/code/text faces at large and the largest
   accessibility category, distinct heading sizes, and unchanged native records.
2. Actual code face registration, body emphasis and heading emphasis, followed by an attribute
   refresh through `AnyNativeTextRenderer` that retains RTL paragraph style,
   links, strikethrough, UTF-16 selection and the existing composition guard.

These are source preparations. **Apple compilation, both UIKit methods, live
controller trait refresh, visual review and physical-device acceptance are
NOT_RUN.** The composition check exercises the actual renderer's authoritative
guard; it does not claim a live IME or focus journey. The current shared App and
the previously accepted drag/Torah journeys are unchanged and are not rerun.
