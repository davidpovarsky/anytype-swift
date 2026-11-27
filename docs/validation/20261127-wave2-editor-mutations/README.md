# Future Heart editor UI mutation tranche

**Source-ready, Apple execution pending.** This is an isolated future test-only
branch based on published source `c95395aec96214dfabd73d55755baa95689cc6d3`.
That base is not represented as a successfully built or tested product. The
current shared warm retry is unchanged; Wave3 owns later integration and the
actual matching App/UI producer selection.

The only Swift change appends two methods and their UI helpers to the already
compiled `PinkhaStage1AcceptanceUITests.swift`. Its original 86,201 bytes
(SHA256 `d4ffc25ee659e03bd4dd76b7847faf4fecf343630edf094c0bc02fe060f00850`)
remain an exact prefix. Removing the 17,519-byte append restores every
original byte. All ten existing test methods in that file, including the four
original editor methods, and the disposable startup helper remain unchanged.
There is no App, Native, Hanlin, project-file or preparation change.

The final source SHA256 is
`c1e37371ce061cfec1ec6d30fc2f55a0df0e477f9727ffd96d635f46e91e0906`;
the append SHA256 is
`68ad800228afbbb8520151fd9991cd68f52dd3442a5b6984e1e9c5012adc7332`.
The independent Torah review binds those exact bytes, reports no concrete
source-level blocker and explicitly records that no compilation or tests
were performed.

## Selection and behavior

| XCTest selector in `PinkhaStage1AcceptanceUITests` target | Real actions and expected outcomes |
| --- | --- |
| `PinkhaStage1AcceptanceUITests/testMiddleSplitMergeUndoRedoAndColdReopen` | Create a guard and editable target through the existing UIKit path; physical keys position a middle caret; Return splits into two exact texts and distinct IDs; native UI Undo/Redo restores both topologies; physical Command-A/left/Backspace merges into the preceding block; guard and surviving ID remain; Undo/Redo; distinct-process cold readback |
| `PinkhaStage1AcceptanceUITests/testPartialRangeReplacementUndoRedoAndColdReopen` | Physical Shift-arrow selection and one replacement key; exact unchanged prefix/suffix and same target ID; native UI Undo/Redo; unchanged neighboring guard; distinct-process cold readback |

Each method iterates the existing `pinkha`, `note`, and `page` fixture kinds.
There are two XCTest methods and six document flows, not six XCTest cases.
Each new method has a 1,200-second execution allowance; no old allowance or
assertion changed. Both reuse the original native preparation
`PinkhaStage1AcceptancePreparationTests/prepareRealApplicationState`, its
unchanged fixture and the existing bound startup-warning path.

After every mutation, the full expected block-ID/text set must appear before
the next history action. Explicit distinct-ID guards prevent a duplicate-key
dictionary trap from hiding a useful test failure. Captured JSON contains
both expected and actual observed block dictionaries, exact unobscured
fixture Space/object, actual App PID and startup-binding hash. Kept original
AX and PNG attachments are captured at milestones and on function exit.

Intermediate text is explicitly `UI_STATE_ONLY`. No native save credit is
claimed from an optimistic UITextView. The separate cold readback terminates
the previous process, proves a different PID, reopens the same native fixture
and requires the exact persisted text/block topology. The pre-edit range is
inferred from physical actions plus exact prefix/suffix/topology; there is no
direct native `selectedRange` observation and no programmatic selection
setter. ASCII runs make the arrow traversal unambiguous across mismatched
app/OS directions. This tranche does not claim mixed-script selection
geometry, list/heading/quote layout, accessibility audit or VoiceOver.

## Actual acceptance still required

The matching source must be included in a separately reviewed actual UI
build. The admitted compiler FileList and original swiftc log must prove
that exact Stage1 file, then XCTest enumeration/results must prove both new
selectors without skips or a broader-suite count shortcut. Existing shared
source/Native/SDK/product custody and original native preparation gates remain
mandatory. No historical App/UI product or declaration-only profile can
stand in for that admission.

When the root schedules execution, preserve original xcresult, process and
build logs, all typed mutation observations and screenshots. Bind attachment
manifest rows to their actual test selector and owned device; require every
document flow's phase chain and distinct-PID cold readback. Visually review
the actual screens. No Apple build, simulator launch, XCTest result or
physical-device result is asserted by this source delivery.
