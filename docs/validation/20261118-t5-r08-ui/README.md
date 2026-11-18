# T5 R08 source handoff ? Hebrew, long titles, Light/Dark

Producer base: 6b7655c580266251b9afd32100fed97173fa5bb0.
Kit dependency for root's six coordinated pins: 4e59e909dd22685bb46f9396bc57e5f8c627d773.
Kit changes exactly two lines on the title Text: lineLimit(2) and the full-title accessibility label. The row Button, stable ID, context/date labels and navigation closure are unchanged.

## What this adds

The two English core methods and their 7 + 6 observations remain. The controller saves an independent core-result.json before running one new read-only XCTest method twice: Hebrew/light and Hebrew/dark. It reuses the original r15 App and UI runner on the fresh UI account. No additional App build, account creation or association mutation occurs in R08.

Two long native Hebrew/English titles and one native Hebrew Page paragraph are verified by ObjectShow/query/graph readback during the existing fresh preparation. R08 then verifies all five current-Space rows, full accessible titles, bounded reachable row frames, a real related-row tap to the exact native Page and observed App/SwiftUI/navigation/UIKit RTL, the exact retained unlinked core Note, and return to the unchanged five-row baseline.

Each appearance requires actual before/after simctl appearance and Large content-size readbacks, one named XCTest PASS, four original screenshots with AX snapshots, one consistent App PID and no PID reuse from preparation/core or the other R08 selection. The corresponding original AX must contain full native titles/body IDs and actual direction labels. This does not certify VoiceOver.

## Review and corrections

Independent SDK source review covered the controller, R08 validator and UI test. It found one long-identifier XCTest query risk in containing(.button, identifier:); this was corrected to an exact NSPredicate without shortening the native row ID. The source-chip query also uses its exact full ID in a predicate. The sibling re-read the corrected source and reported no further blocker; it did not run Swift/Apple.

The exact source hashes and Python controller results are retained in controller-validation.json and source-manifest.json. Linux controls: 29 test functions, 135 subtest outcomes, 0 failures/errors/skips. These are synthetic evidence/controller controls only. The added exact totalTestCount gate rejects an inconsistent 999 aggregate despite two named Passed methods; the existing per-method/failure/skip/device gates remain.

## Acceptance boundary

Swift compilation: NOT_RUN.
Native preparation additions: NOT_RUN.
Actual R08 XCTest: NOT_RUN.
Visual review: PENDING.
VoiceOver interaction: NOT_RUN.
Physical iPad: NOT_RUN.
Dynamic type scope: fixed Large only; larger accessibility sizes remain open.
Product lookup flag: OFF.
Discovery coverage: indexedTargetsOnly with its existing incomplete/freshness disclosure.

The complete runnable contract is Tools/PinkhaSimulatorGate/T5_NATIVE_UI_CONTRACT.md. No new CI run was dispatched for this handoff. The existing queued r15 build must produce a verified runtime before the already-owned Apple pairing/UI route can execute.

Original pair/core receipts are immutable across R08 failure/cancellation. New evidence uses the existing full credential scan and allowlist; raw xcresults, App bundles and account secrets remain private.
