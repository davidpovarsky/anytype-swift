# Real native quote/drop UI selection ? source handoff, 2026-11-18

## Scope

The quote-drop lane uses the existing SimulatorAcceptancePreparationTests fixture:
a fresh local-only account, its actual Space, an ordinary blank Page and a
separate source-bearing writing document. The selected source is Genesis 1:1
from the real source reader and provider. No fake source provider, alternate
insertion route or test call into a mutation service is added.

The UI method types its own anchor through the production UITextView, inserts
one source through its existing context-menu action, requires native Undo to
remove that quote and Redo to restore its block identity and citation, then
performs two actual UIKit drag gestures of the same source. Each gesture must
create exactly one additional quote. The original anchor must remain unchanged.
Background/foreground and a cold app relaunch must preserve the three exact
block identities and their one-source accessories, with no duplicate writes.
The original editable UITextView must accept focus and expose a visible caret.

The suite is explicitly English-only at this stage. A passing selection would
cover its named assertions on its actual device; it does not establish Hebrew,
all iPhone/iPad configurations, IME, compact-window, full T5, T2 or SDK acceptance.

## Product changes

TorahInspectorKit 07bdf7ca3f3318d729a855c0c75137773f16d0bf adds two accessibility
identifiers to the existing source row and Insert action. In Anytype, existing
Undo, Redo and object action menu controls receive identifiers. No mutation,
permission, navigation, drag or Undo handler is replaced.

The six active Kit pins are updated together. The new XCTest file is explicitly
registered in the UI target's Sources phase. The real UI-only project generator
was exercised on a temporary copy and retains the new source reference.

The existing PINKHA_STAGE1_ACCEPTANCE bridge supplies observation-only block
identity/focus/caret labels; source inspection found its production uses in the
text direction diagnostics, not an alternate account or navigation flow.
The complete Space/object marker is queried by exact NSPredicate so that long
native identifiers are not truncated by XCTest's direct identifier shortcut.

## Executed checks and outstanding evidence

- Swift syntax parsing passed for the two App identifier edits, the Kit reader
  edit, and the new test using the UI target's Swift 6 language mode.
- Seven selector/fixture controls passed with zero failures or skips.
- The generated UI project retains the new test in its actual Sources phase.
- Whitespace validation passed.
- Independent source review is pending at this commit.
- Apple type checking and this UI selection: NOT_RUN.

Actual integration run 44225044460 on fcdf0cb5 failed in three pre-existing
Hanlin host source files during Apple compilation. The SDK owner is correcting
those specific errors before another App/UI run. This new UI source does not
claim to repair them.

Screenshots and accessibility trees are attached at each meaningful UI
transition and on failure. The existing runner binds results to the exact Git
source, Kit pin, verified Heart artifact, simulator and executable identities.
A future XCTest pass still requires review of those raw artifacts and images.
