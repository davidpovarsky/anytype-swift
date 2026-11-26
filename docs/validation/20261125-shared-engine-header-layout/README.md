# Shared engine header layout candidate

The actual 9db accessibility tree places the Any navigation bar at y=32 and its creation action at y=36–72, while the shared engine selector occupies y=44–64.5. Original video also shows document actions visually covered after a cold reopen. The shared root used a safe-area inset around a ZStack containing both engines; the native bar retained window-top coordinates.

This candidate reserves a physical VStack row for the existing shared engine selector and constrains the engine content to the remaining area. The original Heart subtree stays mounted, the Any owner/lifecycle remains unchanged, and no account, source, permission or native mutation guard changes. Header content/actions are unchanged. This is a product layout fix candidate; it is not accepted until actual current App/UI verification.

The isolated Hanlin test separately stopped during its creation preparation. Original attached metadata shows one visible, enabled, hittable new-document action with a finite frame; the fixture never tapped it because its repeated synchronous accessibility attribute reads exhausted the existing readiness budget. The helper now obtains related frame/label/enabled attributes from one public XCUIElement snapshot. It preserves unique query count, existence, hittability, exact labels, positive finite dimensions, two equal frames, all timeouts and every original behavior assertion. No longer timeout, retap, backend fallback or fake acknowledgement is added.

The original failure, screenshot, accessibility tree, private sandbox and full xcresult remain under /Users/m1/builds/pinkha-dual-main-20261125/native-ui-hanlin-9db-isolated1. Only source hashes and non-content geometry are included here; private account material is not published.
