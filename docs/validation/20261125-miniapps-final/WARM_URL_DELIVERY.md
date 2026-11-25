# Original Anytype warm URL delivery

The installed Xcode27 public XCTest headers define XCUIApplication.open as
launch-equivalent. The original MiniApps UI suite used it to open the source
document and deliver duplicate callbacks, which could turn a warm replay into
another launch.

Those two harness locations now call XCUIDevice.shared.system.open so the OS
delivers the existing application's URL. The main TextStudio journey continues
to launch and complete through the actual source picker and actual MiniApps
Return button. Its deliberate source termination, cold callback without manual
relaunch, cold document reopen, and all five original test methods are preserved.

The original native toolbar exposes its real process identifier only in DEBUG
and only with the existing explicit PINKHA_UI27_ROUTE_OBSERVATION test environment.
The warm return and each duplicate callback now assert that identifier remains
unchanged. Release behavior and normal accessibility values are unchanged.

The modified UI source passed the actual Apple Swift compiler typecheck on the
Scaleway Mac at 2026-11-25 08:03:32 UTC: exit0, 0.834 seconds, no diagnostics,
203,603,968-byte peak RSS. Source SHA256:
e9118c90d564dca10fe04e04f06c27d54298e620e8896c8a9c5228e511a57193.
The initial attempt lacked the installed XCTest Swift overlay path and is kept
alongside the corrected command/log records. This proves UI-source compilation
only; none of the five original native acceptance methods has run in this step.
