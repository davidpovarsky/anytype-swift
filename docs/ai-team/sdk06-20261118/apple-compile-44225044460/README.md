# SDK06 Apple compiler corrections from run 44225044460

The real Apple Inspector build at `fcdf0cb5e8800cb3b51fe92d29166e43ceae47a2` failed before native fixture execution or UI acceptance. Seven diagnostic lines identify three SDK source issues. `compiler-errors.txt` contains those exact lines from `command-02.log`; `artifact-metadata.json` records the outer artifact and inner member hashes. The full artifact remains in a Windows temporary analysis directory and is not committed or copied to scratch.

## Changes

- `PinkhaHanlinCreatePageContext` explicitly imports `HanlinPlatformContracts`, where `HanlinToolInvocationID` is declared. Verified against canonical Hanlin commit `116cc6be0654a5d11bc56ba00e0310031107ee36`, `Packages/HanlinPlatform/Sources/HanlinPlatformContracts/HanlinIdentifiers.swift`.
- The three journal lock calls use unqualified `flock` under the existing `import Darwin`. This avoids the module-qualified lookup resolving to `struct flock`. The BSD call, integer arguments, `LOCK_EX | LOCK_NB`, `LOCK_UN`, failure handling and file-descriptor ownership are unchanged. No C shim, alternate locking primitive, unsafe ABI declaration or new dependency is introduced. Apple's contract is [flock(2)](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/flock.2.html).
- Mounted-block acknowledgement finds the exact block in the controller's existing accessible diffable data-source snapshot instead of calling its fileprivate convenience method. It still requires native reachability, exact UTF-8 ID, a block item, its current index, a visible mounted cell and intersection with the collection view. No EditorPageController visibility or navigation API is changed.

## Verification and limits

`git diff --check` and Swift 6.3.3 frontend syntax parsing of the three changed files passed. The parser ran on Windows with an iOS simulator target and explicitly warned about the Windows sysroot; this is not Apple type checking, linking or UIKit acceptance. The pin's identifier declaration and the existing editor getter/lookup implementation were inspected directly.

The existing focused SDK suite includes `HanlinHostWriteTests.originalScopeAndExclusiveOwnerCannotBeReplacedByAnotherSceneOrSpace`, which exercises exclusive journal ownership; its Apple execution after this correction is still required. The four-suite SDK controller and its expected case counts are unchanged.

Apple compilation after the fix: **NOT_RUN**. Native fixture/UI acceptance for this source: **NOT_RUN**. The separately published 21-check lifecycle extension remains intact and does not change the meaning of the failed run.
