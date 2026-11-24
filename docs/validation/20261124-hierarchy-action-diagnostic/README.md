# Hierarchy action diagnostic — 24 November 2026

The original native UI method reached folder creation, document creation, content save and its real cold reopen. The first-process LLDB observation recorded both name request setters and both NameSheet initializations. It did not reproduce the earlier name-field readiness failure; debugger timing prevents treating that as a fix or acceptance result.

The same original method then failed at the 45-second original_drag_row_disappearance assertion (NativeLaunchTests.swift:551), 145.318 seconds into the test. LLDB had detached when the first App process terminated during the intended cold reopen, so this trace does not identify which drag handler ran.

The diagnostic controller timed out after the failed test while Xcode collected automatic system diagnostics. The xcresult lacks its final Info.plist and cannot earn acceptance credit. Its original logs remain on the Mac at the exact receipt path. A separately identified simctl diagnose process group carrying both the owned simulator UUID and work path was stopped; readback confirmed no remaining owned processes and no owned device. All 830 retained product entries and signatures stayed unchanged. No App, UI runner or native build occurred.

The follow-up controller70d52f333ac5453d3377f92e9010a69a86f209e6 attaches only to the second App process, after the original cold reopen. Offline LLDB qualification resolved exactly one code location each for the dropDestination callback, List onMove callback and model.move. It uses the installed Xcode never-collect option and preserves the original UI method and assertions. Offline qualification is neither a test execution nor product acceptance. Its actual run remains pending in this receipt.
