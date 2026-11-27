# Numbered-marker direction after attachment

The original numbered-marker adapter selected `.natural` for automatic RTL
numbers from 20 upward, `.left` for LTR or rows without writing context, and
`.center` for smaller numbers. It applied that choice only while configuring
the text block. A row configured off-window could therefore retain a choice
made before inheriting its actual application container's direction. The
editor's text input already reapplies its own direction after attachment;
the marker had no equivalent lifecycle update.

The fix retains the original `TextBlockLeadingView`, marker UILabel, font,
color, number and style builder. A weak callback re-evaluates that existing
alignment policy during window attachment and layout. It writes only when
the alignment differs, so its invalidation settles. Reuse as a nonnumbered
block clears the callback. Rows without writing context retain Anytype's
original alignment behavior. There is no persistence, native contract,
selection, keyboard, focus or engine change.

The original `TextBlockLeadingView.update` body and all original focus code
and 22-method/34-case test source remain byte-identical. No historical test
evidence or source profile is relabeled as current acceptance.

## Targeted Apple verification required

Two new Swift Testing methods define four cases:

- `PinkhaTextBlockLeadingMarkerTests/oppositeDirectionAttachmentRefreshesMarker`
  with `false` and `true`: configure a marker off-window in the opposite
  direction, attach it to a real UIWindow, then check inherited direction,
  refreshed alignment and the retained native label/text/font/color.
- `PinkhaTextBlockLeadingMarkerTests/directionChangeAndReusePreserveMarkerPolicy`
  with `1` and `20`: change the mounted container direction, retain the
  small-number policy, restore the no-context policy and clear the callback
  when reusing the view for a body block.

These methods have not been compiled or run. They require the next shared,
source-bound Apple product selected by Wave 3. The independent interfaces
agent reviewed actor isolation, lifetime, bounded layout invalidation and
reuse behavior without finding a source-level blocker; that review is not
UIKit execution or visual acceptance. Actual numbered-list screenshots in
both app/OS language mismatches remain part of the RTL coverage work.
