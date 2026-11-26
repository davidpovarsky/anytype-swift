# Native empty-paragraph direction after Return — 2026-11-25

The exact recovered original build from run45535451242 / source406fd73 executed
the original F4 methods. Return3 passed with zero failures/skips. The original
prepareRealApplicationState method failed with three pre-insertion RTL assertions:
lines2,3,4 had typingDirection0 before the first native delegate; that delegate
restored direction1 and all five line values/carets/native echoes remained correct.
The original test and its expectations are unchanged.

Apple documents that UITextView clears typingAttributes on selection changes:
https://developer.apple.com/documentation/uikit/uitextview/typingattributes

The existing product intercepts application-originated attribute setters and the
first insertion delegate, but the observed failure exists between those points.
This candidate restores only the policy for an empty, attached, focused,
non-composing row after the original native caret callback. It preserves explicit
alignment, all unrelated typing attributes, original selection, characters and
focus ownership. A per-view context guard prevents reentrant callback recursion.
The diagnostic records direction only; it does not modify tests or fabricate ACKs.

Status: product candidate; requires actual Apple compile and the unchanged original
native preparation. No current acceptance is asserted by this source change.
Original results are preserved under
/Users/m1/builds/_retained-anytype/45535451242-1/f4-recovered-attempt1.
