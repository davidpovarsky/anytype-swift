# Any native UI continuation: three original failures

## Result and scope

The two approved controller corrections are frozen in `NativeApp/UITests/NativeLaunchTests.swift`; all original assertions are retained. Their exact diff and before/after source identities are in `CONTROLLER_FIXES.patch` and `CONTROLLER_FIXES_MANIFEST.json`. No new Apple execution has occurred. All three original methods in run `45038244641` remain failed, and APP-01 remains open. Root owns further edits to the full test file.

The original artifact is `14763060546`, 310306892 bytes, SHA-256 `631272ec9be40f243645009f181ee3f83dbbb0eb57e47a6ab92e59aca0d1a3cb`, generated at commit `07c3568f9f9cf4044dd81163cd374d4ad35330cb`. This review reuses that artifact and does not repeat product tests. The exact 13-file source review map is `SOURCE_REVIEW_MANIFEST.json`; the exact original full test has SHA-256 `f4cc433fe98ab1e6ffe9af3c6d3db0a46e71ec7f0f61ddd1e6d4c29cc1b33f53`.

## Property-name controller

The original video at PTS 145.011667 shows the standard native Hebrew Select All action labeled **בחירת הכול**. The frozen predicate accepted `Select All`, `בחר הכל`, and `בחר הכול`, so it timed out before replacement text, save, visibility, or native move could execute. The correction adds only the observed fourth label. The original exact saved value, type, body, move, and reopen requirements remain unchanged.

Evidence: `extracted/property-name-failure-state.png`, SHA-256 `765298b161e04aa787687aae5e06ea67c50c135fad4418d1fb36b5907a5cb9f4`. `FRAME_MANIFEST.json` binds the extracted frame to the original video payload and actual PTS.

## Source drag controller

The original video at PTS 103.445 shows the newly inserted provider quote with its blue canonical Genesis 1:1 source badge and the original target body below it. The Inspector remains expanded. The failed controller can find the new UITextView but cannot find the underlying badge button. The already-passed quote/Note journey collapses the same native sheet before reading background accessibility. The correction adds that existing real header-collapse gesture before background badge/read assertions. It does not alter insertion, metadata, authorization, or any source/body/order/persistence assertion.

Evidence: `extracted/source-drag-failure-state.png`, SHA-256 `1462b787d115337fa9bb0876ee56da34fbc82ddd799e890501a5501211599ef2`. This establishes a displayed canonical badge in the original run; it does not turn the incomplete failed journey into an acceptance pass.

## Hierarchy drag: observed event and smallest next experiment

The production row is a native Button with a context menu, String drag payload, and native folder drop handler. The handler enforces one payload, exact Space identity, current owner permission, and a known source object before entering the same guarded move path used by the Move sheet. No concrete persistence defect was found in this bounded source review. The test did not observe a successful move.

The original synthesized event (attachment 126, activity 1042 under 1039) gives the exact interaction:

| Step | Offset | Native coordinate |
|---|---:|---|
| Touch down | 0 s | (378, 378) |
| End of stationary press | 1.1 s | (378, 378) |
| End of drag | 1.204 s | (378, 326) |
| Touch up | 1.204 s | (378, 326) |

The destination is only 52 coordinate units above the source. The default velocity is recorded as 500 and the destination hold as zero in the original activity title. The actual move takes 104 ms. The source row is highlighted at video PTS 104.493333; the context-menu preview is already open at PTS 105.503333, and remains open at PTS 167. No error alert or acknowledged move appears in these inspected frames. The original 60-second post-event idle wait reports that the app-animation-complete notification was not received. This identifies a native gesture that ended in the menu; it does not identify a failed guarded storage commit.

The smallest next candidate is to retain the same actual source and folder elements and the original 1.1-second initial press, change only the explicit drag velocity and destination dwell, and keep every original postcondition:

```swift
source.press(forDuration: 1.1, thenDragTo: destination,
             withVelocity: XCUIGestureVelocity(rawValue: 100),
             thenHoldForDuration: 0.6)
```

This is a proposed Apple experiment, not a verified fix. The lower velocity gives the drag interaction more travel time and the hold gives the native folder destination time to accept the drop. Keeping the initial hold avoids changing three timing dimensions at once. Apple documents this exact XCUIElement overload and `XCUIGestureVelocity(rawValue:)`; the custom value is in the native velocity unit documented as pixels per second. The new run must preserve and inspect the synthesized event and actual menu/drop outcome. If a slower held native drag still leaves the context menu, investigate the production row's context-menu/drag interaction; do not substitute the Move menu or label the unchanged native move assertions as covered.

Required unchanged acceptance remains: original root row disappears, library reaches ready, folder contains exactly the same object ID once, native block ID and exact Hebrew body survive, and the same facts survive cold reopen. No controller retry should silently perform a second mutation.

Primary API references checked 2026-11-22:

- https://developer.apple.com/documentation/xcuiautomation/xcuielement/press%28forduration%3Athendragto%3Awithvelocity%3Athenholdforduration%3A%29
- https://developer.apple.com/documentation/xcuiautomation/xcuigesturevelocity

Event provenance: the original encoded payload has SHA-256 `88882a2febb072a24c6e7c41718eff1f7cd00d969e79e1041785d54397db35bf`; decoded bplist `048f20dc377ac7672963acca8f940bfd5a2f6580065a226b69a82b1eba13b428`; derived JSON `9b442d8d65106c4deefee361e49f0006f489e90145505c07cace58d415ea957a`. `extracted/GESTURE_FRAME_MANIFEST.json` binds the two immediate gesture frames to the original video and actual frame PTS; the duplicate requested-104 image is byte-identical to requested-103, not an independent observation.

## Evidence handling

Only the selected post-onboarding PNGs were visually reviewed for publication; they contain disposable fixture object names and no recovery phrase. The full original videos include ordinary account onboarding, so preserve them privately and do not publish them unscreened. Original evidence remains immutable. This report supersedes `PRE_ARTIFACT_REVIEW.md`'s unresolved screenshot-dependent alternatives while retaining its source-bound scope.
