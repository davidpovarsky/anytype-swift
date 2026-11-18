# Simulator protection metadata ? measured SDK06 journal repair

## Original diagnostic evidence

[Apple run 44269454953](https://github.com/davidpovarsky/anytype-swift/actions/runs/44269454953) completed successfully as a diagnostic at source `e30371162f7ddc41a0aa71dbfc81e5cd61c68636`. Its controller status is `DIAGNOSTIC_COMPLETE_NOT_SDK_ACCEPTANCE`. A standalone, synthetic UIKit application ran as PID 5859 in a fresh owned iPad Pro 13-inch (M5) iOS 27.0 simulator (24A434) under Xcode 27.0 (27A266a), Swift 6.4. The controller checked source, runtime, bundle, nonce, PID and receipt identity, then shut down and deleted only that simulator.

Both measured parents reproduce the initial journal contract: Application Support/Anytype and the temporary-directory parent used by the failing component tests. Directory creation with the requested protection attribute and subsequent backup exclusion succeeded. The first unsatisfied requirement in each location is `root.attributes`: permissions are 448 (0700), but Foundation returns no `protectionKey` value or type. Scope directories have the same result. Namespace files return permissions 384 (0600) and also omit the protection attribute.

Observed limitation: Simulator protection metadata is unsupported/unavailable on this tested runtime. Successful attribute-setting calls are not evidence of physical-device Data Protection. The probe deliberately continues after recording the mismatch to measure independent operations; production code did not continue past the failing guard.

All measured lock/open/fstat, synthetic write, FileHandle synchronization, both F_FULLFSYNC calls and every parent-directory fsync succeeded. POSIX errno values were 0. These observations reproduce a sufficient cause of the journal's initial `.unavailable` on this simulator. They do not prove that every historical write failure has no additional cause, nor do they prove hardware power-loss durability. All original SDK, native-write, physical-device protection and physical-power-loss acceptance flags remain false.

The compiler completed in 208.059 seconds with exit0. The preserved verbose log contains the actual frontend and linker commands plus a sysroot warning. Compilation and actual simulator launch succeeded. This duration does not establish the cause of the earlier 240-second timeout/cancelled workflow.

## Narrow production change

Only `PinkhaHanlinWriteJournal.swift` and `HanlinHostWriteTests.swift` change. An internal readback-policy helper preserves the exact required protection value. A compile-time `targetEnvironment(simulator)` branch permits only an absent key. Wrong present values, unknown strings, NSNull and wrong types remain rejected everywhere. On a physical device, absent metadata still fails.

The three production call sites retain their existing mode, regular-file, size, symlink, ownership and canonical-record guards. Directories still require 0700; namespace and journal records still require 0600 through fstat. Creation and attribute-setting calls remain throwing operations. O_NOFOLLOW, exclusive flock ownership, fsync and F_FULLFSYNC are unchanged. There is no runtime switch that a caller, model, environment variable or test can use to opt a device into the Simulator policy.

The existing file-protection assertion now identifies the Simulator metadata limitation explicitly and also checks 0600. It keeps the strict expected-value assertion for devices.

## Regression contract

Two non-parameterized methods are added to the existing write suite:

- `protectionReadbackRejectsWrongPresentValues` accepts the expected enum/string values and rejects present wrong values/types. Missing metadata is asserted according to the compiled target, without a physical-protection claim.
- `journalReopenRejectsChangedDirectoryAndRecordModes` creates real disposable journal data, releases its owner, changes one of four actual file/directory modes, and requires reopening to fail with the existing error category. It verifies that the wrong mode and original namespace/reservation bytes remain unchanged after rejection.

The write suite becomes 14 methods. The root-owned source/result gate must require SDK 72 methods/73 argument runs and combined 123 methods/142 argument runs, with both new names explicit. The only parameterized SDK method remains the existing two-budget consumer test.

The two files pass Swift6 grammar parsing on the installed Windows Swift 6.3.3 toolchain. That is not Apple typechecking, component execution or native create acceptance. These new regression tests and SDK 72 remain NOT_RUN until the real Apple job. Root and T2 independently reviewed the exact source delta before publication.

## Byte provenance

Artifact 14413162959 is 14,445 bytes with SHA256 `6fde3d01c9c0f7d873bd6e4f64de411d4ab4c21b033936b83868720bd1e2eee3`.

Original platform receipt SHA256: `f85f94871511fc3ae8e3318bf3b7c0597b4198969e6daba35a3ebf2ecb044d25`.
Original execution SHA256: `06a2788f94d996a43c3628c084f9909efe76d64bfe157207b6f24a1bd5b6936d`.
Original compiler log SHA256: `553a2fa90002c4a40d293b18dd3adb8395036d6cc516fee6406eff15797dea93`.

Selected original bytes are retained in `raw/`, mapped by `origin-manifest.json`. Local `-text` attributes preserve hashes across Windows checkouts. `proof-validation.json` is a derived local identity/consistency check; the original receipt remains unchanged. Source and syntax-only evidence are separately identified.
