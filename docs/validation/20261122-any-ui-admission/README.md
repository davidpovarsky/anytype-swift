# Any native UI preflight, 22 November 2026

[Original run45028482383](https://github.com/davidpovarsky/anytype-swift/actions/runs/45028482383), source `b2fc3804426067dd1ec8318d6ea92a4bcb8e9545`.

The actual application and UI runner built successfully. The built application passed its single-scene bundle contract. Reuse validation admitted the prior native artifact and UIKit evidence without executing those tests again.

The following freeze step failed with `compiled_ui_target_identity`. No requested entry, mounted, Files or custom Type UI journey executed. The failure is not product acceptance. The owned provider and simulator cleanup completed.

`original-evidence.zip` preserves the original GitHub artifact bytes, including the build log, xcresult, failed freeze receipt, reuse receipts and cleanup receipts. `failure-audit.json` binds its GitHub ID, digest and all30 original file hashes. It contains no compiled App, UI runner or xctestrun, so those products cannot be reused in a subsequent job.

The corrective work must retain strict target/runtime/product identity and preserve the actual test configuration for diagnosis. Existing passing native and UIKit tests remain reusable; full native-app UI acceptance stays open.
