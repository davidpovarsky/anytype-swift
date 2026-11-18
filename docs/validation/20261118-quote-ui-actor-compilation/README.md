# Quote UI compilation correction

The actual Inspector run [44245608599](https://github.com/davidpovarsky/anytype-swift/actions/runs/44245608599), source d325987d1fe721938d8991b2e086cb0de6adcfd3, built the app and AnyTypeTests successfully. Its one selected native preparation passed on iPad Pro 13-inch (M5), iOS 27.0 (24A434), arm64, with no skipped test. The UI-only target then failed to compile; none of the five Inspector UI methods executed.

Swift 6.4 diagnosed four calls from nonisolated XCTest setUpWithError into the main-actor require instance helper, including two non-Sendable autoclosures. The helper now takes an already-evaluated Bool and is explicitly nonisolated. It accesses no instance state and throws the same error for the same failed predicate. All test methods, UI gestures, assertions and actor isolation for UI operations are unchanged. No unchecked Sendable or executor bypass is introduced.

The original artifact and compiler output remain in GitHub and the retained Windows ZIP. Exact hashes and compiler diagnostics are recorded here. This source correction has not yet passed the Apple UI-only compiler or UI acceptance; the failed run is not counted as an Inspector pass.
