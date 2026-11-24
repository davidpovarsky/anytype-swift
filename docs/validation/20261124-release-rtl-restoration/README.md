# Preserve empty-paragraph direction at the typing-attribute write boundary

## Original actual Apple result

GitHub run 45456314424, source `ee28c1f947f1524f0269e9f71c72f2b493528786`, reused the qualified Release products from 45446055084 without building. All three original Return focus methods passed (3/3, zero failures or skips). The original `prepareRealApplicationState()` method failed with three issues at the existing pre-input typing-direction expectation. Original results and retention are copied here without changing their status.

`original-five-line-boundaries.json` contains only the ten closed direction-boundary log rows, with the original log SHA-256 and location. Before first input, lines 2, 3 and 5 had left-to-right typing direction despite being empty, first responder in the same window, under RTL layout, with right paragraph alignment and no active marked text. Lines 1 and 4 were RTL. After the existing first-input delegate preparation, all five were RTL. Existing focus and did-begin-editing paths already prepared empty typing defaults, so a later UIKit attribute restoration can replace the direction.

## Product change

`TextViewWithPlaceholder` normalizes incoming typing attributes at the setter. The adapter changes only the paragraph alignment and base writing direction of an empty automatic paragraph with a known writing context and no IME composition. It copies the existing paragraph style and dictionary, preserving every other style and typing attribute. Explicit alignment, including an explicit session choice before the next render, and unambiguous center/justify choices are retained.

The getter remains a pure read of UIKit state. The change does not edit text storage, call a document action, move focus/selection or schedule a delayed style replay. The real preparation test and all assertions remain unchanged.

## Validation and required requalification

`syntax-only.json` records Swift 6.4.3 Linux parsing and exact changed-source hashes; no Apple typecheck/build/test has run for this repair. Because the typing-attribute write boundary participates in focus restoration, rerun the original Return3 plus RTL preparation1 after the real Apple build. Use the single coherent Release union build for these four methods and the remaining Release/T5 journeys; do not create a redundant four-only App build or replay the already accepted SDK23/ACK7 scope.

The original failed run included an operator interruption after the completed failed test while automatic sysdiagnose blocked finalization. That original failure remains failed. A separately verified installed Xcode policy (`-collect-test-diagnostics never`) will prevent that post-failure collection in the next controlled run while preserving assertions and explicit XCT keepAlways attachments.
