# Native-root static labels use the existing App-language resolver

**Source reviewed. Compiler, Native, UI, compiled-bundle, visual and device acceptance remain NOT_RUN.**

This separate one-file successor has sole parent `770bc4e4a38ec299a8f0ebcc3cc5e8f0c170dabc`, tree `c30e7e168db50c0f5ee7a0085b41ea701f0259ae`, on proposed owned branch `codex/chatgpt-wave15-wave2-native-root-static-language-20261127`. It inherits the prior six-error correction intact.

## Source defect and correction

The Native root declares 27 static SwiftUI lookup sites with 26 distinct Hebrew keys, plus one direct Hebrew display fallback for an unnamed Space. The retained resource audit establishes that the declared standalone and combined inputs provide no English default-table translation path for these keys. This is source/resource evidence, not an inspection of a compiled bundle.

Only those 28 text arguments now call existing public `AnyUIErrorText.text(originalHebrew, english)`. English wording covers opening, accounts, restore/backup, Space controls and the empty display fallback. Restore guidance continues to distinguish account identity from the separate document-import process; recovery guidance preserves its privacy meaning. Every original Hebrew literal remains byte-for-byte unchanged.

All modifiers, roles, actions, bindings, field settings and eleven stable accessibility identifiers remain exact. Nonempty raw Space names and persisted values are untouched. The recovery phrase retains its original left-to-right display, privacy protection and text-selection behavior. The entire 14,043-byte model, including the 2,237-byte six-error report body, is byte-identical to the parent.

The modified source is `Modules/PinkhaAnyNative/Sources/PinkhaAnyNative/AnyNativeRootView.swift`: 25,011 bytes, SHA-256 `54cd42c28ef5d5dce53e1a52495f97a87cc06af68c58bfa5bebb9a51b8b458b8`, Git blob `112250ced570144979043c9c0a5c58c4af33e22c`. The exact28-site full inverse reconstructs the complete published `de2ab55e…` preimage. No formatter or unrelated cleanup was applied.

## Review and existing UI consumers

Root source review `c054a188…` verified the complete published preimage, all28 forward and inverse byte replacements, wording, identifiers and preserved model. Editor's finding `12f709c7…` and consumer compatibility `40a084eb…` are retained unchanged. The latter reads the exact d99 NativeLaunch source and all ten current a72 Stage1 UI bodies: no inspected source depends on these exact Hebrew labels. Existing stable identifiers and owned Space names support the current journeys, so no test edit or selector widening is introduced.

`editor-six-message-source-review.json` is explicitly follow-on evidence for the already published six-error change, not a claim of peer review of this new source. Original preparation records retain their earlier pending status; the later root review records the accepted source outcome. `wording-proposal.original.json` retains the reviewed English/Hebrew mapping.

## Compact provenance and acceptance boundary

`primary-source-provenance.json` binds immutable URLs, Git blobs, SHA-256 and byte counts for the original source, nine resource/declaration bodies and eleven UI consumers. Their complete retained bodies remain retrievable from those exact Git references; this packet does not duplicate them or the ancestor's27-file direction trace. Raw directory-metadata custody remains pinned in the original resource record. `source-inverse.json` reconstructs the full original product file, and `source.patch` supplies its review diff.

Only the one existing Native-root source and this new evidence prefix may differ from the parent. No resource catalog, Package/PBX, test, source inventory, controller, Native contract, language mechanism or runtime gate changes. W3 owns integration; this descendant carries both Native-root language corrections and can be integrated independently of the d99 Bookmark fixture sibling.

Actual App Hebrew / OS English and App English / OS Hebrew behavior, iPhone/iPad and light/dark layout, VoiceOver, caret/keyboard, compiled resources and physical-device observations remain open. No tests or compiler/Native/host operations were performed. The first-Apple22/34 → real preparation → original four UI sequence remains unchanged.
