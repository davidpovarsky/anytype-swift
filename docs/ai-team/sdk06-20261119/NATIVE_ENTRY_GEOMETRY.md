# Native entry geometry — 2026-11-19

## Authenticated failed source

Run 44469001681 at 80bc4989bc2ac198bd7688f7960151996c1f486a built the real application and passed the single disposable native preparation case. The original iPad UI case failed after 38.221 seconds at its unchanged 20-second AWAIT_READ_CONSENT deadline. It did not reach logout or any of the 22 native acceptance checks.

Artifact 14505103219 is 31,793,362 bytes; full ZIP SHA256 e328dbb91d5df4d77c0dc8d7625b72bee65c9465ee4c906ae12203ae827a9e84. All outer and inner ZIP CRCs were verified. Nested evidence ZIP SHA256 6133ee06f2e5723100f8214ebe8db40b4fd79b7093f680afc1f19c6b67b1eb93. The complete evidence is retained; no successful result is inferred from the previous source.

## Native evidence and narrow correction

The native XCTest session log records the actual button frame (333.5,1308,48,48), AX visible/activation point (338.3,1312.8), and one actual 50ms touch at that point in application PID 52544. Native interruption detection found no interrupting element. That point is 27.1529 points from the circular control's center, outside its 24-point radius. The actual recording remains on the source editor after the event. No native acceptance status label or driver receipt exists on this attempt. Existing evidence does not distinguish an uninvoked callback from every possible launcher guard failure; the inaccurate activation geometry itself is directly observed.

The existing downstream Pinkha button now places the unchanged controlHeight frame inside its label and gives that label a circular hit region. Its accessibility activation point is the normalized center of the same actual control. No fixed screen coordinate, retry, programmatic test launch, new presentation owner, credential, authorization or source selection is introduced. The existing launcher, native Button.tap, consent controls, all 22 checks and deadlines remain unchanged. On a phase timeout only, XCTest now retains its actual app AX tree and screenshot before the same original assertion, rather than leaving only missing-element query text.

Both changed Swift files pass grammar parsing locally. This is not Apple typechecking or native UI acceptance. The original UI22 native case is the affected acceptance gate. SDK06 component tests already running at 80bc remain attributed to80bc; this UI-only correction does not change their inputs.

## Primary API reference

Apple documents contentShape as the view's hit-testing shape and accessibilityActivationPoint(UnitPoint) as the assistive gesture origin:
- https://developer.apple.com/documentation/swiftui/view/contentshape(_:eofill:)
- https://developer.apple.com/documentation/swiftui/view/accessibilityactivationpoint(_:)-9l0w0

## Scope and open acceptance

Changed application file: Anytype/Sources/Pinkha/AI/PinkhaHanlinLaunchButton.swift, originally introduced by downstream commit ad278c0583a07baefe29763d9c176af0f8a9ca3d.
Changed test file: PinkhaStage1Acceptance/Tests/HanlinNativeAcceptanceUITests.swift, failure evidence only.
Upstream observed develop d857b23ea540be33d6faab4f7a7a1a260ab578c1. Heart, middleware/protobuf, original source authority, SDK 116cc6be0654a5d11bc56ba00e0310031107ee36 and workflow/pins are unchanged.

Logout teardown, actual final auth controls, absence of the prior banner and stale homepage sheets still require the complete native journey on the corrected source. No claim of UI22 acceptance or full SDK06 completion is made.
