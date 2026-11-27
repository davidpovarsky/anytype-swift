# Native Bin current-read failure

Status: source candidate; compilation, XCTest, Native, mounted UI and visual acceptance have not run.

## Concrete failure and correction

At integrated source `2207b131f45d305ba828c93deb0633e275e59cba`, `AnyLibraryPresentation.refreshBin()` reports a failed current read but leaves the previous `binItems` on screen. The existing native Bin view renders Restore controls from those rows. A cached `canWrite` value can therefore leave a stale action visible after the read has failed. This is a presentation defect; the existing native mutation still checks current authority.

The correction clears `binItems` only inside the existing current lifetime, epoch and Bin request guard. An obsolete read cannot clear or replace a newer read. Loading completion retains the original request guard. A dedicated `binReadFailed` state distinguishes the failed read from a successfully empty Bin. The existing native List presents a localized failure row and a borderless Retry button; the empty label is suppressed during failure. An explicit current read clears that failure state when it starts, a successful current read publishes fresh rows, and owner retirement clears the scoped state. The existing alert still presents the original read error, without clearing a global message that could belong to another operation.

The public refresh method retains the actual typed store read, session lease check, native row validation and schema-derived row mapping byte for byte. It captures the original epoch alongside the store/schema before awaiting a private publication implementation; that implementation checks the captured epoch before reading. The internal typed-read test entry captures its current epoch and delegates to this same implementation. The nonescaping read closure is explicitly `@MainActor`, following the actor contract of the existing Library search seam. The read seam is internal; the view observes only the new read-only failure property. No write, authority grant or product fixture switch is added. Besides the refresh implementation, failure property and its clearing in `revoke`, the complete model is unchanged, including archive/remove, Restore, authorization and search. The view changes only the Bin List's failure/Retry/empty presentation.

## Focused model regressions

Two methods, three cases are appended to the existing package test file, using its unchanged production model/session/lifetime fixture and mutation-rejecting journal:

| Method | Cases | Boundary |
| --- | ---: | --- |
| `AnyLibraryBinPublicationTests.failedCurrentBinReadRetiresRowsAndAnExplicitRetryCanRecover` | 1 | A successful Bin read is followed by a failed current read, then an explicit successful retry. Old rows disappear on failure, the failure clears at retry entry, fresh rows return, and owner retirement clears a later failure. |
| `AnyLibraryBinPublicationTests.olderBinCompletionCannotReplaceOrClearANewerRead` | 2 | An actual suspended older read fails after a newer success, or succeeds after a newer failure. Neither completion changes the current rows, failure flag, message or loading state. |

The asynchronous tests advance at the real read-entry continuation, with a bounded failure deadline and deferred continuation cleanup. They do not sleep to guess completion order. All original search test bodies and helpers are preserved. No test is described as executed in this source tranche.

`source-inverse.json` restores all three original files exactly. `source-inputs.json` and `github-source-verification.json` bind the four current source reads. The unchanged native read statement is SHA-256 `63fcd33e2dddc2b6ad6743f8a4567fed18551a4f1bcfbf9c309c9daa66e4e9cd`.

The first source candidate and the explicit-actor intermediate are retained under `prior-review-input` and `actor-annotation-input`. The two small correction records preserve the independent review findings: spell the intended actor contract explicitly and retain the public boundary's epoch across the inner await. Neither earlier input is described as an observed compiler or runtime failure.

`epoch-preservation-input` and `root-independent-review.initial03bd.json` retain the intermediate review that had not yet accounted for the view's empty-state condition. That record is historical and is not final publication approval. `failure-ui-state-delta.json` records the correction and the focused assertion updates. The added suspension helper now also checks cancellation before registering its read continuation and cancels the owned older task during deferred cleanup; no runtime failure was used to imply that this source review had executed the tests.

## Acceptance retained and still required

The historical Bin restore/cold-reopen PASS remains bound to source `e540cd7e01b497f1b3173ae2e68b43ade0b00b6f`, native prefix `410b441e`, receipt `5454534733ae7b9a76fe03a9b0f171d5470069067dc09eb4eb16d200e167c5b0` and its original 210.791-second execution. It is not relabeled as acceptance of this correction, and it is not automatically replayed. Existing accepted hierarchy drag remains excluded.

The next matching shared App must compile and run the two added model methods. Mounted acceptance requires an owned Bin fixture with a successful list followed by an actual failed current read: retain the native/error evidence, verify old rows and their Restore actions disappear, dismiss the original alert and verify the failure/Retry row remains while the empty label does not appear, then verify an explicit successful read restores current content. Review the real localized error UI visually. No synthetic row, test label or component result establishes native ACL, file upload, archive export/import, device or whole-D acceptance.

No compiler/cache mutation, account process, Native invocation, simulator or Mac operation was performed here. Wave3 owns the shared App source freeze and execution; the existing closed Native23 source/product pins are not changed by this tranche.
