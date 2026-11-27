# Properties related-document lifetime: actual component acceptance

The corrected test suite passed **5 methods and 11 cases** using the exact production publication model in an isolated Swift 6.4.3 Linux component. The original compilation failure is retained. This commit changes one existing test file and adds evidence; it changes no production code, package declaration, PBX membership, shared consumer or runtime admission.

## What changed

The original `#require(owner.model.load(...))` expression failed compilation because the macro forwarded five actor-isolated callbacks through parameters that lost `@Sendable`. The repair first evaluates the unchanged call into `Task<Void, Never>?`, then applies `#require` to that local. Every callback body, method, argument case and assertion remains exact. The original 7,010-byte identity-suite prefix also remains exact.

The changed full source is `Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeTorahRelatedIdentityTests.swift`: `f334ce278537413df7ef7b508db8bd250135f002f3b6dfa65a306459e4b807c6` → `629b751244d0b87020ffa3a21e27c2123274b2c26e39aed3aae3bbdade36f2aa`. The two-replacement inverse is retained in `source2-preparation/source-inverse.json`.

## Actual outcomes

| Attempt | Exact receipt SHA256 | Observed result |
|---|---|---|
| Original | `8fbaf3c6dd6b57bc577d7f91ba54403f2ee57ee350d37a0280da74d17c405ceb` | Compiler exit 1; zero test events. Original logs, inputs, source/probe-free cleanup evidence and three compiler FileLists retained. |
| Source2 | `05971770c170562bc9ab8d01efff29ad459c440f6901f19ca84c116f07d543b4` | Exit 0; all 5 methods and 11 cases passed. Actual job ran once from 13:23:17 to 13:23:37 UTC on 27 November 2026. |

The source2 stdout contains ten parameterized case-start/pass pairs and the parameterless method pass. The five-method summary alone was not used to infer eleven cases. The original five-method/seven-case identity suite was excluded from this component and was not replayed.

| Exact method in `AnyNativeSourceDocumentsPublicationTests` | Actual cases passed |
|---|---:|
| `queuedOldRequestCannotBorrowReopenedSheetAndCurrentFailureCanRetry()` | 1 |
| `noncooperativeOldCompletionCannotReplaceReopenedRequest(olderFails:changesDocumentOwner:)` | 4 |
| `retirementDiscardsRowsAndRejectsANoncooperativeCompletion(fails:)` | 2 |
| `asyncWaiterJoinsReadAndForwardsCallerCancellation(cancelCaller:)` | 2 |
| `temporarilyInactiveOwnerFinishesItsRequestAndCanRetry(fails:)` | 2 |

## Exact component boundary

The isolated package contains the unchanged production `AnyNativeSourceDocumentsPresentation.swift` from commit `21d63bef8950f8b927f0d8d3b4b052758bc98fcb` (SHA256 `1cf8d0790e949b7592d4298dff0e788982ad3b0959c838350fe587d2c80e48c1`), the complete original `TorahInspectorCore/Models.swift` from Kit `9058b489e9acc271b4f8ef69e2ed24648f93b4ed` (SHA256 `59a0c8639c8c778c67ff9c60db4b979e3ba7a39dff4c3fb669a54ae23dc113a0`), and exactly 88 import bytes plus the corrected 13,865-byte new-suite suffix. This is an explicit test-file projection; it is not compilation of the full App module or the complete original test file.

The three hand-authored Swift inputs and two generated Swift inputs are bound through four actual compiler FileLists and the actual `swiftc` invocations that consumed them. Raw generated `test_anchor.swift` and `test_entry_point.swift` are retained. Inputs before and after match SHA256 `7902ca3123030725dd98041627bf56dcdd0ca540a6bd1e444db725dd5b538571`. The actual outer SwiftPM setting was `--jobs 1`; the emitted inner SwiftDriver command used `-j2`.

The original process/resource framework, 300-second owned deadline and existing admission/live floors were preserved. Twenty actual resource samples remained above the live floors. The actual cleanup receipt records a positive process-group absence observation; publication and qualification did not probe the historical group again.

Independent qualification is `component/source2/independent-qualification.json` (SHA256 `d462aedee6a311882af12019d851af03d80ff4afdbdbe7eaf206e6a108f41561`). Root's distinct full compiler/result review is `component/source2/root-review.json` (SHA256 `4d4aaa998116af4ea4a31ba0ad9714a3dd4f56bc195632314f0fe2cd9ad9673d`). Both bind the raw logs and exact compiler sources.

## Publication and future App intake

This is an isolated direct child of `2f9ac20a910d9922e13f8e5d410757604437fcc5`. The actual source2 receipt truthfully records `UNPUBLISHED_TEST_ONLY_SUCCESSOR` and a null published test commit because the test was not published when it ran. Those original bytes remain unchanged. The later publication receipt binds the already executed `629b…` full test to the new commit.

The related-identity test already has the original hosted source bridge. A future shared build must bind the new full-file hash, the exact integrated source, actual compiler FileList/command evidence, compiled enumeration and matching test results. This packet does not repin a consumer, open a product gate, add a test path or claim Apple acceptance. Wave3 owns that shared integration.

All original source/control/package/workflow siblings are preserved by the complete bounded Merkle comparison; only this test leaf and this new evidence subtree differ. The source-retention gate was not rerun for unchanged production source. The publication uses an own GitHub branch and performs no Oracle staging, compiler, test replay, Native operation or final-branch write.

## Retained evidence

`component/attempt1/` contains the original failure; `component/retained-original/` preserves original inputs, wrappers, reviews and source-only preparations. `source2-preparation/` contains the minimal test inverse, exact source2 runner/input packet, wrapper inverse and independent source reviews. `component/source2/` contains the actual successful raw attempt, raw tool readbacks, compiler sources/lists and both acceptance reviews. `handoff.json` gives finite source/target/count requirements; `packet-manifest.json` inventories the payload. The separately added Merkle proof binds that payload without a circular self-hash.

The unchanged `language-audit/` packet is retained under its original manifest `6693ada7bfe94d0e1774f2d2f4ea6071f2c00a3eb7a5cd9efb0d2955101cae2e`: 32 files, 524,453 bytes. It contains source evidence and primary documentation locators. It found no proven language-selection defect in the audited path; it does not claim either mixed App/OS language UI lane passed. Both directions retain their separate actual UI acceptance obligations.

Full App/SwiftUI caller compilation, Apple/simulator/device tests, Native persistence, RTL/VoiceOver and final release acceptance remain open. The actual component result is limited to the exact publication model and the eleven documented controlled lifecycle cases.
