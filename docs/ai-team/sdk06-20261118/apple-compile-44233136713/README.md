# SDK06 Debug compile correction - run 44233136713

The exact Apple run on integration source `101d4f4f877c98ee8aca4efb347464c9cdd02e12` failed during Debug-Anytype build-for-testing with exit 65. No selected XCTest/Swift Testing suite executed. Preflight, canonical Hanlin 116 preparation and the verified Heart runtime installation succeeded.

The compiler reported `Notification` ambiguous at line 136 of `PinkhaHanlinNativeAcceptanceDriver.swift`: both Foundation.Notification and Services.Notification are imported. The two following nil-context errors belong to the same event tuple whose type could not be resolved. The source correction qualifies only this type as `Foundation.Notification.Name`. All six real notification names, notification object filters, counters and lifecycle acceptance conditions remain identical.

`compiler-diagnostics.txt` preserves the original compiler context, including both candidate declarations. `execution.raw.json` is the unchanged execution receipt. `artifact-metadata.json` binds the outer GitHub artifact, nested archive, full compiler log and receipt hashes. The original ZIP remains in the Windows task temporary directory; no full log or ZIP was exported to Scratch.

A focused Swift syntax parse is recorded separately. It does not resolve imported Apple symbols or establish Apple build/test acceptance. The next actual Debug-Anytype build must confirm this correction and execute the four selected SDK suites. The separate Release Inspector lane excludes this Debug-only driver. SDK06 and the 21-check native UI acceptance remain OPEN.
