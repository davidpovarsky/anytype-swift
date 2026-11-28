# Use the existing App-language resolver for Native-root errors

**Source reviewed. Compiler, UI, visual and device acceptance are NOT_RUN.**

This is a one-file correction over immutable parent `a72f2e1ee3032cc1170c3ab07a9ae6b0eefa2dfd`, tree `2adebea229e42c5ff56e50aaf0adebbacfbc4c41`, proposed on owned branch `codex/chatgpt-wave15-wave2-native-root-error-language-20261127`.

## What changes

`AnyNativeRootModel.report(_:)` previously supplied six Hebrew-only dynamic String values, including when the existing App-language resolver would select English. Only those six assignments now call the already public and imported `AnyUIErrorText.text(originalHebrew, english)`. The affected categories are recovery backup, uncertain write, runtime mismatch, secure storage, busy, and the sanitized fallback.

All six Hebrew strings are preserved byte-for-byte. The original error cases, privacy protection, actions, cancellation/epoch guards, ownership and persistence remain intact. The correction adds no locale mechanism, Native contract, dependency, test seam or error details. Its exact full source SHA-256 is `de2ab55e962ee7f17b6eb6ff8bc7e932b48eee6d03c6bca43a818b8c2fe68045` (23,642 bytes).

The existing resolver remains unchanged: it chooses the Hebrew or English argument using `Locale.autoupdatingCurrent.language.languageCode`. This packet does not assert that this API is OS-only or certify its compiled application's current locale. The defect is the six paths that bypassed it. Root independently checked the current full original source, helper visibility/platform scope, caller and complete six-rule inverse; its source review is retained unchanged.

## Bounded audit and evidence

The original finding, English wording, audit and source manifests are preserved without rewriting their earlier preparation status. `audit.original.md` describes the finite current language/direction and empty-field trace across both engines. No further concrete source defect was found in that trace; it is not a repository-wide localization or runtime claim.

`source-change-proof.json` contains the six exact forward/reverse replacements. Applying its inverse to the published source reconstructs the entire original 22,878-byte source, SHA-256 `f2d21c15f0da8a5d3ca72326078637b79134298b150985a6cfb89d4cc1743ef9`, Git blob `4d13391adc0df3d0cb1cfb8abb7028fc708d3082`. The public helper excerpt is retained with exact byte offsets in its unchanged original source.

`primary-source-provenance.json` provides immutable repository paths, commit URLs, SHA-256/Git blob/byte identities for all 27 whole audited bodies. Their complete source and raw API envelopes remain locally retained and retrievable from those immutable Git references; this compact publication does not repeat the 548,687-byte source tree. The provenance record explains how historical preparation paths map into this packet. This packet and its embedded Swift excerpt are evidence, not an execution package.

## Integration and remaining acceptance

Only `Modules/PinkhaAnyNative/Sources/PinkhaAnyNative/AnyNativeRootView.swift` and this new evidence prefix may differ from the parent. Package/PBX, source inventories, tests, controllers, resource floors, and final integration refs are untouched. The separately published standalone Bookmark UI tranche is not a dependency of this correction; W3 owns integration of the two independent children.

The required App Hebrew / OS English and App English / OS Hebrew configurations remain pending on iPhone/iPad and light/dark, including actual error labels, inherited direction, empty-field caret/keyboard behavior, navigation gestures and visuals. Other Native-root static localization keys are outside this six-message finding. No old or new test was run, and no Apple/Native/whole-App acceptance is added. The existing first-Apple order remains unchanged.
