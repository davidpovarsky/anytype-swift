# Native-root static labels follow the existing App-language choice

**One-file source candidate over published `770bc4e4`; compiler, Native, UI and visual acceptance remain NOT_RUN.**

## Concrete finding

The current Native root has 27 SwiftUI lookup sites using 26 distinct Hebrew keys, plus one direct Hebrew fallback for an unnamed Space. Editor's retained source/resource audit found no English default-table translation path for those keys in the declared standalone or combined product resource chains. This is a source finding, not an inspection of a compiled bundle. It does not treat `Locale.autoupdatingCurrent` as OS-only or introduce a different language preference.

The exact finding is `evidence/finding.json` (`12f709c7…`); its resource custody is `evidence/resource-source-custody.json` (`7d1791d0…`). The original discovery is a72-bound. Its complete view body is identical in the published six-error successor `770bc4e4a38ec299a8f0ebcc3cc5e8f0c170dabc`, which is this candidate's sole intended parent.

## Small correction

Only the 28 identified text arguments change to `AnyUIErrorText.text(originalHebrew, english)`, using the existing public helper and existing PinkhaAnyUI import. The English wording was separately reviewed by Root in `wording-proposal.json` (`4ecf60fb…`). Every original Hebrew literal remains exact. The unnamed-Space fallback changes only its display text; nonempty raw Space names and persisted values are untouched.

The complete candidate is:

`Modules/PinkhaAnyNative/Sources/PinkhaAnyNative/AnyNativeRootView.swift`

SHA-256 `54cd42c28ef5d5dce53e1a52495f97a87cc06af68c58bfa5bebb9a51b8b458b8`, 25,011 bytes; Git blob `112250ced570144979043c9c0a5c58c4af33e22c`.

All modifiers, roles, binding/action closures, field settings and the eleven stable accessibility identifiers remain exact. The recovery phrase retains its existing left-to-right presentation, privacy treatment and copy behavior. The entire original model is byte-identical, including the six dynamic error branches published in `770bc4e4`. No account, Space, journal, lifecycle, navigation or Native behavior changes.

`source-inverse.json` contains all 28 exact byte replacements and restores the complete 23,642-byte `de2ab55e…` preimage. It also binds the unchanged full model, published six-error function, identifiers and recovery-phrase presentation. `source.patch` is the review diff; no formatter or unrelated cleanup was applied.

## Existing UI consumers

The sealed `evidence/ui-consumer-compatibility.json` (`40a084eb…`) examines the exact d99 NativeLaunch source and all ten current a72 Stage1 UI bodies. None contains an exact reference to these Hebrew root labels. The relevant journeys use the existing stable identifiers and owned nonempty Space names. The candidate preserves them; no test edit or selection widening is introduced.

The separately retained `evidence/editor-six-message-source-review.json` (`fd6bfeb8…`) is follow-on provenance for the already published six-message correction. It does not rewrite that earlier packet or claim review of this new candidate. Root's source review of the new candidate is still required before publication.

## Acceptance boundaries

No resource catalog, Package/PBX, source inventory, controller, test or runtime gate changes. This candidate adds no tests. Actual App Hebrew / OS English and App English / OS Hebrew behavior, iPhone/iPad and light/dark layout, VoiceOver, caret/keyboard, compiled resources and physical-device observations remain pending. No old test was replayed, no compiler or host operation was performed, and the first-Apple queue remains unchanged.
