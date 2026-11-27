# Sharing presentation authority — Wave 2, 2026-11-27

## Source tranche

The current sharing view model silently returned when a completed snapshot belonged to a different engine, account or Space. On a refresh or mutation readback that left the previous snapshot, invitation and grant controls visible. The new code first checks the active presentation generation, then treats a wrong-scope result as `PinkhaSharingError.invalidResponse`. The existing error path clears the snapshot and shows the existing localized refresh or uncertain-action message.

The public SwiftUI views, mutation authorization, native service calls, account owner and native contracts are unchanged. The internal Foundation/Observation view model is compiled independently of SwiftUI so the actual model can be tested on Linux. The SwiftUI views remain inside the original platform condition. Reversing the import boundary and two guard changes restores every original source byte from a089ff29.

## Actual focused evidence

The exact five new `SharingPresentationTests` methods ran with the real Swift compiler and XCTest on Oracle/Linux. Their controlled sharing service deliberately supplies wrong-scope responses; these are presentation-model tests, not native ACL or Apple UI acceptance.

| Run | Passed methods | Failed methods | Command exit | Source unchanged |
| --- | ---: | ---: | ---: | --- |
| Original scope-return behavior, portable imports only | 2 | 3 | 1 | Yes |
| Corrected current-generation scope handling | 5 | 0 | 0 | Yes |

The original regression produced 18 assertion failures across its three failed methods. The full logs, source inventories, command receipts and Swift version are retained here. Both owned process groups were positively absent after completion. No historical T5 calls, native engine calls or Apple build ran in this tranche.

Coverage includes foreign engine/account/Space responses for both Heart and Any (six combinations inside one XCTest method), mutation and invitation readback, suppression of a second write from stale UI state, valid role readback and an old generation completing after the sharing screen is reopened. Interfaces provided an independent source review with no blocker.

## Integration and limits

`result.json` binds exact code/test hashes and actual logs. The prospective source-retention tree overlays only the two source/test files on Wave 3 commit91368faea4873ee118e73626b2aa0ff7fb841007. All121 existing mappings are retained, with zero unreviewed baseline changes or inventory errors. This downstream module did not exist in baseline586c98, so the existing map requires no extra row. The first verifier attempt failed to write its output into a root-private directory; that failure is preserved separately and is not a source-verification result.

Cherry-pick this source tranche independently of the earlier App16 preparation commits. Shared Apple compilation, owner-sharing UI, real joined-member role/approval journeys and visual error presentation remain pending on Wave 3's integrated product. The original sharing title/disk-floor failures remain failures. This tranche does not close T2 or the Wave 2 core acceptance gate.
