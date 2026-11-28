# Heart Notes: actual UI journey coverage

Status: implemented source-only extension; compilation, XCTest execution and visual acceptance are NOT_RUN.

## Change

The existing T5 Note lifecycle method creates, edits, opens, unlinks and cold-reopens a real Note through In Documents. It did not select the newly exposed Notes tool. This commit adds one positive detour after the original related-result Open/return sequence and before the original unlink block.

The detour selects the actual Notes segment, observes its real Add control, requires the single real Notes row on the fresh origin, captures the row's actual association identity, and opens it. The original document and body checks must prove that it navigated to the same Note already created and edited by the journey. It then returns through the ordinary navigation and reasserts the original linked-result set before resuming every original unlink/relaunch/retention assertion.

The Notes association identity is observed from the actual row. It is not substituted from the related-result ID, object ID or fixture target association. The query explicitly excludes the overlapping `torah-inspector-note-unlink-` prefix and verifies the exact observed row is unique, enabled and hittable before tapping.

## Exact input and preservation

Parent: `84577c91e2949aead1d3e209ae7a45488e868edf`, which supplies the eight-byte Heart Notes tool visibility correction. Product prerequisite: `TorahEditorHostModifier.swift` 5,364 B / `adf601dc09bd2abee727fce05b3141f7e9344dfb2dd45b8731f99461cc7caf99`.

Test input: `PinkhaStage1Acceptance/Tests/PinkhaT5NativeAcceptanceUITests.swift`.

| Body | Bytes | SHA-256 |
| --- | ---: | --- |
| Original | 34,629 | `b43f97b3c1283f05b728b15cc9871bfecc1692ca55563f1e2c1f1886ecd38d5e` |
| Updated | 38,096 | `2a71529b40bd0ae074bd891ad6b7705cf6372c17ef499b01b00ba2312f51c1a1` |

`replacements.json` contains one exact 3,467-byte insertion. Its complete inverse restores the entire original file. The two core method names and third R08 method, every original statement/helper/fixture/setup, all 13 literal observation-append sites and the original seven/six runtime stage contracts remain unchanged. The new JSON and AX/screenshot attachment names are separate; no seventh Note receipt stage is added. The authoring correction for the local `add` name shadow uses `self.add(notesAttachment)` and remains documented in the unchanged author handoff.

## Actual acceptance

Keep the original `PinkhaStage1AcceptanceUITests` selections:

- `PinkhaT5NativeAcceptanceUITests/testCurrentSpaceRowsAndExactBlockNavigation`
- `PinkhaT5NativeAcceptanceUITests/testAddNoteEditOpenUnlinkAndRetainAfterRelaunch`

The original controllers, evidence parser, native fixture, source/run/process requirements and 300-second method / 900-second outer UI limits are unchanged. W3 must explicitly admit the changed full UI file and matching compiled App/UI products. This packet supplies no current source-admission override and no runtime pass.

The detour adds no new object creation, unlink, cold process, test method or direct fixture/HTTP operation in the test. The actual Notes presentation and navigation still use the application's existing provider reads. Its positive list/open evidence does not establish Notes-specific unlink execution, mixed-language/RTL matrix, VoiceOver or physical-device acceptance. The original In Documents unlink and retained Note/body checks remain required. Preserve the historical T5 36+9 calls and the first Apple 22/34 -> preparation -> four Stage1 UI order.

The original proposal and author handoff are retained byte-for-byte. `root-source-review.json` records independent source checks and the separate completion of one transient primary-read error. All original source and test failures remain separate from this unexecuted successor.
