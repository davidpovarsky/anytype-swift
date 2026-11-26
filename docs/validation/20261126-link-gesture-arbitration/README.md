# Same-input link selection and navigation ordering

## Actual failure and retained evidence

The exact Link-child double tap in the original App14 semantic sources test selected all six characters of Anchor, while the first tap had already started the production source-navigation task. The retained observer records navigation admission before the native full-range selection and edit-menu presentation; the source sheet subsequently takes first responder. The actual result remains one failed method (40.362 seconds), zero passed or skipped methods, and zero Sources menu action taps. The remaining three methods were not run.

The original preparation and mounted native Apply/readback passes remain separate. The private account, complete original command outputs, xcresult attachments and observer evidence are retained off the Mac with a SHA-256 inventory. Public evidence in this directory contains hashes, counts and bounded observations only. The original two-hour fixture expired at 04:40:20.247091 UTC. A new source qualification needs a fresh real account.

## Product change

The existing owned link double-tap recognizer now has public UIKit failure priority over the same input's single-tap recognizers and native gestures expressly exposed by UITextInteraction.gesturesForFailureRequirements. The delegate admits only the owned attached recognizer, a link interaction requiring two taps, and gestures attached to that input or its descendants. Native gesture membership also requires that UITextInteraction.textInput is the same input. Parent and sibling gestures are excluded.

The first touch must hit an existing attributed glyph rectangle. Unlinked text therefore does not acquire a link-selection delay. Ordinary single taps still proceed when the double-tap recognizer fails. Existing URL dispatch, source-session authority, editing policy, actual range selection and source mutation code are unchanged. Removed interactions detach their exact recognizer; stale or transferred recognizers cannot retain priority on a reused input.

No private recognizer class names, delayed navigation timers, forced selection, additional native calls or fake acknowledgements are introduced.

## Verification and limits

The actual production source compiled against UIKit in the iOS 27.0 simulator SDK. The five new Swift Testing methods also typechecked against that exact module, with zero tests executed. The original missing Testing-module and macro-plugin setup failures are retained unchanged alongside the successful continuation.

The new methods cover same-input single-tap priority, foreign/unrelated recognizers, native UITextInteraction ownership, removal/reattachment, and the independent mention/object single-tap handlers. Their runtime execution and the complete original six-stage semantic UI/native sequence remain required on the next shared App producer. This checkpoint claims neither App acceptance nor resolved gesture behavior from typechecking alone.

The separate reviewed UI donor ca1ad2f68e0e00ef32f2c3ad67623ed0a9befa43 targets the unique exact Link child and retains every original result assertion. Its use must be bound explicitly to the next full UI source; it is not silently substituted into the historical App14 result.

## Public UIKit contract

- [Preferring one gesture over another](https://developer.apple.com/documentation/uikit/preferring-one-gesture-over-another)
- [UIGestureRecognizerDelegate failure ordering](https://developer.apple.com/documentation/uikit/uigesturerecognizerdelegate/gesturerecognizer(_:shouldberequiredtofailby:))
- [UITextInteraction.gesturesForFailureRequirements](https://developer.apple.com/documentation/uikit/uitextinteraction/gesturesforfailurerequirements)

These APIs support failure dependencies on owned recognizers and UIKit's explicitly exposed text-interaction gestures. Actual App behavior is still verified by the original UI method, not inferred solely from the documented contract.
