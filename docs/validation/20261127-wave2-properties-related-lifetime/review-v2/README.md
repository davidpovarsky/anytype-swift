# Properties related-document request ownership

This is a narrow source correction over App `d8a2c67b6dae09a7b769e803a319de3d3080019c`. Apple compilation, component tests, Native calls, simulator UI and visual acceptance are **NOT_RUN**. The candidate does not admit or modify a current App product.

## Problem and scope

The original native Properties action started an unstructured Task before the lookup captured ownership. `showDocuments(with:)` then bound its result only to the mounted document epoch and current modal booleans. Closing and reopening Properties on that same mounted document restored those booleans, so an old success could open its source list in the new presentation. Its unguarded catch could also overwrite later feedback after close, unmount or revoke.

The source audit is retained separately at `../t5-publication-lifetime`. No cross-Space runtime data disclosure is claimed. The existing shared Inspector repository already has an owner/generation barrier and typed authority-failure clearing; it is not changed by this correction.

## Candidate behavior

`AnyNativeSourceDocumentsPresentation` is the actual result state used by `AnyDocumentPresentation` for its existing public rows/title properties. A Related documents tap now enters synchronously, captures the document owner, current Properties presentation UUID and request UUID, and then creates its Task. It also captures the existing mounted owner guard. Both late success and late error must still own all of those boundaries before publication. A prior request cannot clear the newer request's loading state or run its completion callback.

Changing `showsProperties` retires the previous presentation. An actual document unmount/revoke also retires it, clears its rows/title and cancels its task. A subsequent mounted owner or reopened Properties sheet starts fresh. Cancelled tasks join the document's existing `closingObservers` drain; this does not introduce another native session or process manager. Ordinary owned child sheets do not retire Properties merely because they cover it.

The native read remains the original typed index query, current metadata reads, second index/readiness comparison and final account/run lease validation. Its complete 963-byte body is byte-identical, SHA-256 `d87529a209c6942cb1c77ee0e36c956a5c992ea14210238ddc12c46916768f14`. Current read failures still reach the existing localized error path; current incomplete results still display the existing incomplete-index message.

The native Properties view remains in charge of reserving/releasing its existing child presentation. That reservation is now bound to the same observable Properties presentation UUID, including captured dismissal and completion callbacks. Retaining the old view's State no longer blocks a reopened presentation, and an old callback cannot release the new presentation's reservation. The native-child/navigation eligibility policy remains the original policy. Related-sheet dismissal setters also require their captured presentation UUID.

The original public async `showDocuments(with:)` signature is retained. It awaits the exact child task to completion and forwards caller cancellation through `withTaskCancellationHandler`. The actual button uses the distinctly named synchronous `requestSourceDocuments` entry. No native query, schema, engine, account, shared-session, storage or write authorization contract changes.

## Source and validation

`source-inverse.json` records the exact four candidate files and full reverse application of `source.patch` to every original byte. The new result-state source disappears under that inverse. The original existing related-identity test file is an exact 7,010-byte prefix. `source-origin.json` binds the four paths to the downstream PinkhaAnyUI module, absent from both the map baseline and fresh upstream develop. The existing 130-row source refactor map is unchanged; this is not a new source-gate execution result.

The old five methods/seven declared identity cases are preserved. The appended suite adds four methods/nine declared cases:

| Method | Declared cases | Boundary |
|---|---:|---|
| `queuedOldRequestCannotBorrowReopenedSheetAndCurrentFailureCanRetry()` | 1 | Close/reopen occurs before the old Task can start; the old provider is never called. Retained view reservation state is scoped by the actual presentation UUID, old dismissal cannot release a new reservation, and a current failure can retry. |
| `noncooperativeOldCompletionCannotReplaceReopenedRequest(olderFails:changesDocumentOwner:)` | 4 | Old success/error returns while the new request is still suspended, on the same or a replaced document owner. It cannot publish feedback/rows/title or finish the new loading state. |
| `retirementDiscardsRowsAndRejectsANoncooperativeCompletion(fails:)` | 2 | Previously published rows are discarded at retirement; a late success/error and new request on the retired owner cannot restore them. |
| `asyncWaiterJoinsReadAndForwardsCallerCancellation(cancelCaller:)` | 2 | The actual await helper cannot return before the controlled read settles; cancellation reaches the exact child task and suppresses its late result without abandoning its completion. |

The tests exercise the production result model through typed suspended reads which deliberately ignore cancellation after starting. They do not synthesize native permissions, construct a private Note marker, replace engine storage, or establish Native read correctness. Their declaration scope is `PinkhaAnyUITests`. The same original test file also has an existing direct hosted bridge; selecting the new suite there requires the actual future product's compiler-input proof for this changed file and the new product source. No PBX file, package manifest, compiler inventory, result parser or consumer pin is changed here.

Only the local byte inverse has been executed. No Swift syntax parse/typecheck, component method, XCTest, Native request or UI method has run for this candidate. Historical T5 36+9 results and all old failures remain retained.

## Review and integration

The initial candidate and its source-only Interfaces review are retained in `review-v1`. Root identified two concrete source issues in that predecessor: the changed public async contract and an unversioned view reservation. The successor preserves that async contract and versions the reservation as described above. Its full inverse still restores the original App bytes, while a separate revision delta preserves exactly what changed after the first review. Final independent reviews are recorded against the successor's exact hashes; predecessor review is not treated as review of new bytes.

A proposed attachment intent-store accessor is deliberately excluded. It will be a separately identified insertion after its final signatures and root review, preserving this full inverse and source scope.

After independent review, the source packet belongs on a new isolated Wave2 branch. Wave3 owns final integration, actual product source admission and execution. Any existing consumer which pins the earlier test-file bytes must receive a separately reviewed source-bound successor; the current product cannot acquire this behavior from a controller-only pin change.
