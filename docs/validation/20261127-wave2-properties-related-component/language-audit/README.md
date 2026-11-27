# Mixed application / OS language: bounded source audit

**Result: no defect in the two audited locale selections has been proved. No product change is proposed from this audit.** Current Apple documentation explicitly states that `Locale.autoupdatingCurrent` considers the app-specific locale chosen in Settings, the system locale, and the languages available to the app. Treating this API as an OS-language-only source would be incorrect. This source conclusion does not grant mixed-language UI acceptance.

The immutable App source examined is `e4556ba1edbf7c698eb04cb1ecc9caaeed34e1ff`, tree `e4781f05f8700d506317d6f43aeadbeb0c89dee9`. `source-manifest.json` binds 22 selected files, 468,299 bytes, to primary Git blobs and SHA-256. The completed Properties lifetime source `21d63bef8950f8b927f0d8d3b4b052758bc98fcb` and separately reviewed attachment accessor preserve the audited locale expressions; neither was edited during this audit.

## Actual resolution path

| Boundary | Exact source fact | Consequence and limit |
|---|---|---|
| App entry | `AnytypeApp` uses the ordinary `WindowGroup`; the dual-engine path wraps the original coordinator in `PinkhaEngineSceneView`. | The inspected entry path does not install a custom application language or a SwiftUI locale override. |
| Existing global environment and scene | `GlobalEnvModifier` supplies window, keyboard, dismissal and interface-style services. `SceneDelegate` handles quick actions. `PinkhaEngineSceneView` coordinates engine presentation. | None of these inspected bodies overrides `locale`, writes `AppleLanguages`, or selects a separate language preference. This is a finite call-path observation, not a repository-wide absence claim. |
| Original localized strings | `Loc.tr` calls `BundleToken.bundle.localizedString`; its Swift package uses `Bundle.module`. `Locale.current` is then used for formatting arguments. The package's development localization is English. | Original `Loc` resource-language selection is bundle-driven. Its formatting-locale use is not a replacement for resource lookup. |
| Source localization declarations | Main App resource metadata contains both `en.lproj` and `he.lproj`. The exact existing `Auth.xcstrings` blob `86c6301e…` contains both languages, unchanged from retained primary evidence. | The source has these language resources. This audit has not inspected a newly built `.app` bundle or run per-app language selection. |
| New-engine error helper | `AnyUIErrorText.text` reads `Locale.autoupdatingCurrent.language.languageCode?.identifier` and selects the Hebrew or English argument. | For the audited Hebrew/English requirement this follows the documented current app locale. No source evidence proves it ignores the per-app choice. |
| Related-document title | The Document passes `.autoupdatingCurrent` to the existing `TorahAssociationDisplayFormatter.label`. That formatter chooses the appropriate stored Hebrew/English label, then the existing alternate/canonical fallback. | This also uses the documented current app locale. Native canonical IDs, stored values and identity are not translated or rewritten. |
| Properties rows and shared Torah presentation | Properties rows pass their SwiftUI `@Environment(\.locale)` directly to the same formatter. Heart `TorahEditorHostModifier` and Native `AnyTorahInspectorLayer` pass the environment to `session.updateEffectiveLocale`, including locale-change handling. | Both engines already share the presentation formatter and session locale seam. The code does not require two independent language resolvers. |

The inspected Settings and Appearance source contains no separate in-app language selector. The relevant platform path is the app-specific language/locale setting described by Apple. No `UserDefaults` mutation, system setting, simulator or device action was performed to establish that behavior at runtime.

## Platform contract checked directly

Apple's current [`Locale.autoupdatingCurrent`](https://developer.apple.com/documentation/foundation/locale/autoupdatingcurrent.md) discussion includes the app-specific Settings choice and supported-language availability in its resolution. It also says that the locale follows changed preferences but does not itself notify consumers that settings changed. The corresponding [`Locale.current`](https://developer.apple.com/documentation/foundation/locale/current.md) discussion describes the same inputs for a snapshot value.

SwiftUI exposes the [current view locale](https://developer.apple.com/documentation/swiftui/environmentvalues/locale.md), and its [environment documentation](https://developer.apple.com/documentation/swiftui/environmentvalues/) permits an explicit subtree override. That distinction matters: a future caller that deliberately overrides only a SwiftUI subtree could give the row formatter a locale different from the model's `.autoupdatingCurrent`. No such application-language override was found in the inspected production entry/settings path, so this hypothetical difference is **not** promoted to a current product defect.

The documentation was opened from Apple's primary Markdown pages on 2026-11-27. `platform-contract.json` records the exact URLs and the limited conclusion. The older source/API name alone was not used to infer OS-only behavior.

## Acceptance still required

| App language | OS language | Remaining actual observation |
|---|---|---|
| Hebrew | English | Verify the matching shared product's declared/bundled Hebrew resources, actual current app locale, existing Properties row and related-list title, and a known `AnyUIErrorText` message in the same owned fixture. Check RTL visually under the existing coordinated acceptance lane. |
| English | Hebrew | Verify the corresponding English resource/locale/title/message identity and LTR presentation on the same qualified product. |

Reuse the already planned mixed-language acceptance lanes and their actual App/device identities. This audit does not replace them, add a new broad test suite, or count source resources as compiled/UI evidence. Runtime language, layout, keyboard, VoiceOver and device acceptance remain pending their original owners and product admission.

If actual acceptance demonstrates a divergence, the smallest proposal is to use the already available effective-locale / `Loc` seam at the specific failing caller. There is presently no evidence justifying a global language override, a translation rewrite, changes to Native data, or alterations to the published lifetime/upload tranches.

## Evidence and boundaries

- `source-manifest.json`: all 22 selected sources and immutable primary blob references.
- `reused-primary-sources.json`: three previously retrieved source files independently matched to the current primary subtree before reuse.
- `platform-contract.json`: exact official API contract and inference boundary.
- `audit.json`: finite call-path conclusion and outstanding runtime checks.
- `discovery-notes.json`: default-branch search limitations and corrected source-path lookup attempts; none is treated as a product or acceptance failure.

No product files were changed. Oracle, Mac, compiler, Native, simulator and XCTest operations: **0**. No new product/runtime admission, no old-test replay, and no visual acceptance are claimed.
