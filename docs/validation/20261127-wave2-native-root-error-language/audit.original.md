# Current RTL and language source audit

**One concrete source defect found and corrected in an isolated candidate; compiler, UI and visual acceptance remain NOT_RUN.**

The audit is bound to immutable `a72f2e1ee3032cc1170c3ab07a9ae6b0eefa2dfd`, tree `2adebea229e42c5ff56e50aaf0adebbacfbc4c41`. It reuses the retained mixed App/OS language and editor RTL work. Nineteen whole cached bodies were matched to current primary blob/byte identities; eight additional whole bodies were read at the same commit. The finite 27-file source manifest is custody for the traced symbols, not a claim that the entire repository was audited.

## Concrete finding and smallest correction

`AnyNativeRootModel.report(_:)` assigns six Hebrew-only dynamic String values. Its caller retains the original error/epoch/cancellation handling and the root alert renders the resulting `errorMessage`. These branches do not use the existing bilingual resolver, so they still supply Hebrew when the effective App language selects English. This finding does not depend on assuming that `Locale.autoupdatingCurrent` is OS-only.

The isolated candidate changes only those six assignments to `AnyUIErrorText.text(originalHebrew, english)`. The module already imports PinkhaAnyUI. All six original Hebrew literals, classifications, sanitized fallback, privacy comment, actions and lifetime code remain byte-identical. The exact full inverse in `source-change-proof.json` restores the complete 22,878-byte original; the candidate is 23,642 bytes, SHA256 `de2ab55e962ee7f17b6eb6ff8bc7e932b48eee6d03c6bca43a818b8c2fe68045`.

| Existing error branch | English counterpart |
| --- | --- |
| Recovery backup required | Save your recovery phrase before opening the Space. |
| Uncertain write | The result of the operation cannot be confirmed yet. Refresh the Space before trying again. |
| Runtime contract/version mismatch | This app version does not match the engine. Install a matching build. |
| Secure storage unavailable | Your account cannot be saved on this device right now. Keep the recovery phrase shown on the backup screen and try again. Documents will become available after saving is confirmed. |
| Busy | Another operation is still finishing. Try again after it completes. |
| Sanitized fallback | The operation did not complete. Try again or reopen the app. |

The original finding is retained separately in `native-root-error-finding.json`; the source candidate does not rewrite it. Root review and any publication remain separate. No new test seam or localization mechanism was introduced.

## Finite language and direction trace

| Surface or mechanism | Actual current source behavior | Audit result |
| --- | --- | --- |
| App entry and settings | AppScene, GlobalEnv and the engine scene do not install a separate custom language/direction preference in the inspected chain. The existing Settings/Appearance bodies contain no separate app-language override. | Reuses the prior source conclusion; no repository-wide absence claim. |
| Shared labels and errors | Loc resolves keys through its actual bundle. AnyUIErrorText chooses Hebrew or English using its existing effective-locale expression. The Heart Torah host forwards SwiftUI locale to its session on load/change. | No new resolver defect established. Native root's six bypassing assignments are the concrete exception above. |
| Heart navigation | AnytypeNavigationView passes SwiftUI layoutDirection to the existing bridge. The bridge sets the navigation view semantic direction. Back-swipe progress and acceptance use the corresponding sign of horizontal translation. | No new logical-versus-physical mismatch found in these bodies. Actual cancelled/completed gestures remain the existing UI obligation. |
| Heart empty editor | The UIKit adapter resolves explicit ancestor direction before a detached view fallback, then uses the shared writing policy. Attachment, typing-attribute and native-selection paths restore empty automatic paragraph alignment/base direction while preserving marked composition and explicit alignment. | No new OS-language lookup or direction defect found. Existing 22/34 and RTL acceptance are not rerun or relabelled. |
| Native empty editor | The representable supplies SwiftUI layoutDirection. The controller sets view/navigation semantics, invalidates rendered rows on direction changes, and resolves paragraphs through AnyNativeWritingPolicy plus the shared policy. Empty presentation is carried separately into typingAttributes and restored on focus/selection/insertion. | No new defect found. Explicit stored Native direction remains authoritative, and this audit does not claim a runtime caret result. |
| Native Properties | Ordinary values use SwiftUI TextField; structured values use TextEditor. Both remain in the inherited environment. Labels/actions use the existing bilingual helper; row value presentation uses logical trailing alignment. | No hardcoded OS preference or physical-left override found. Empty-field caret/keyboard behavior still needs the actual matrix. |
| Heart Properties | The existing TextPropertyEditingView uses a multiline SwiftUI TextField with inherited layout, logical leading/trailing toolbar placement, and original Loc labels. | No new source-proven direction defect; actual empty field/keyboard behavior remains pending. |
| Recovery phrase | Only the phrase's display subtree forces left-to-right presentation. | Intentional phrase-content treatment; it does not force the root, editor or Properties layout direction. |

For automatic empty paragraphs, the inspected shared policy maps effective RTL to right alignment/right-to-left base direction and effective LTR to left alignment/left-to-right base direction. Nonempty text may establish a natural base direction, and explicit user alignment or Native direction is preserved. This is the existing policy, not a new behavior.

## Remaining acceptance and limits

The required configurations remain App Hebrew / OS English and App English / OS Hebrew, each on iPhone/iPad and light/dark. No matrix cell was executed here. The original first Apple order and all existing source-bound selectors remain unchanged.

Actual current bundle localizations, effective locale/direction, empty-field caret geometry, keyboard language, gesture cancellation/commit, error presentation, theme/device layout and physical-device acceptance remain open. This six-message correction does not certify all other Native-root static localization keys or every screen. No new defect is asserted for unexecuted standard SwiftUI field behavior.

The work performed only Git primary reads, local source reads, whole-byte/hash comparisons and exact source replacement/inverse checks. No Swift/typecheck, compiler, Native operation, simulator, Mac/Oracle call, process query, test/control replay, runtime admission, final-ref change or publication occurred.

