# Fresh Files.Open authority qualification

## Current status

Attempt 2 passed both actual SDK methods on 27 November 2026. The complete log records two starts, two passes and no skips. Both owned process groups exited normally and were positively absent. The first attempt's compiler-only failure, original fixture and raw compiler output remain retained.

The already completed signed ACL and lifetime suite remains valid: receipt `68964e6db8802065ba69edad5614ec52cde3603b14f9628d65d808aa76563766` records 35 runs, 35 passes, no skips, and two normally closed owned process groups. Those tests are not repeated by this qualifier.

## Actual successful second attempt

| Item | Observed value |
|---|---|
| Job | `job_3519aefd1e09` |
| Completed | 2026-11-27 13:09:10 UTC |
| Controller duration | 37.5686 seconds |
| Result | `PASS_FRESH_SYNTHETIC_ACTUAL_FILES_OPEN2` |
| Receipt | `4eb696473d3cc199f935f826944a03681e0decd16047039579aba9718fc2ff35` |
| Original log | 82,010 bytes; `591d666b13b749aff81dbca436e87aaef78eb79d6c1535747b5d2cfe71376fa7` |
| Cached reader method | PASS, 0.60 seconds |
| Awaited fetch method | PASS, 0.27 seconds |
| Method starts / passes / skips | 2 / 2 / 0 |
| Owned process groups | 2, exits 0, positively absent, no signals or forced cleanup |
| SDK726 source manifest | `8f572975bb767e6eb573d30061015382a2c4133c0065f84a635e44e276ca8d34` |
| Actual OS denial | Verified in both selected methods before SDK initialization |
| Peak owned output | 146,650,321 bytes |
| Final root / development free | 2,711,810,048 / 34,553,221,120 bytes |
| Retained private inputs, retained account opens, original role mutations | 0 / 0 / 0 |

The immutable receipt is `/mnt/development/projects/evidence/pinkha-w1-fresh-files-open-20261127/attempt2/result.json`. The raw log is its sibling `files-open2/original.log`. Exact public copies are retained as `actual_attempt2_result.json` and `actual_attempt2_original.log` beside this document. The SDK source, qualified signed-unit source and admitted public inputs all remained unchanged through final verification.

The actual compiler was Go 1.27.4 for Linux arm64, using the same exact driver, compiler and linker recorded by the signed35 qualification. Its canonical driver hash is `59c65090beeda377c09007eb8fae1c6aadf0a7b551e65ee13d461092d29e8005`. Shared cache growth of 128 MiB was an allocation estimate; this qualifier enforced the complete owned-output cap and both live filesystem floors.

## Preserved first attempt

| Item | Observed value |
|---|---|
| Job | `job_07be7a678015` |
| Controller duration | 25.198 seconds |
| Result | `FAIL_FRESH_SYNTHETIC_FILES_OPEN2` |
| Receipt | `411fc3533f77073019e348e48c8cb73643c12a765e6d0cfd7a579bd550f71a7b` |
| Compiler log | `61ee7382dc6071dbeb50413b84d921a963e8ad5c84845c8064123c8b42a4d3c1` |
| Selected method starts | 0 |
| Owned process groups | 2, both positively absent; exits 0 and 1 |
| Forced cleanup or signals | None |
| Peak owned output | 75,173,888 bytes |
| Source and public inputs | Unchanged through final verification |
| Retained private inputs or account opens | 0 |

The failure is a fixture API mismatch: `AclList.Records()` returns decoded `AclRecord` values. The fixture attempted to pass that slice to `NewInMemoryStorage`, which accepts original signed `RawRecordWithId` values. No read-authority assertion was reached.

## Narrow fixture correction

The successor uses the original `RecordsAfter(ctx, "")` serving API on the newly created fixture's own ACL. Under the same read lock it captures the ACL root, head and decoded count. After obtaining the original signed bytes, it requires a nonempty chain with the exact count, root and head, then uses the unchanged `BuildAclListWithIdentity` and `recordverifier.NewValidateFull()` path.

The original v0.13.8 implementation reads cloned signed payloads from storage in ascending order; the decoded view deliberately drops raw data. The correction does not reconstruct signatures, substitute an ACL state, read an old account, or export account records. The public source excerpt is retained in `public_sync_rawrecord_api.txt`; its original `list.go` hash is `7a44abd9184d1b05191c1955989c7eb45026ec664acab2811635b230d543cc2c`.

The source delta is `fresh_raw_record_api.review.patch` (`8147c629e62b76a6071ff608e225d8613da25cac6936259e9485e19c7385a622`). The corrected fixture is `b7d91dd885239f0b5c7cad99d22985affd3d20cc554b9f097487ce2be6dfc76b`. The failed fixture `b038b0f3cd1b0d5cae679a2193dcf28a5a79763aa2a618e395507de48b373270` and every prior controller are preserved under `before_fresh2_raw_record_api`.

Only fixture pins and its exclusive physical source location change in the qualifier, native producer and GET-only consumer. Their function and class ASTs remain identical. The 1,745-byte HTTP deadline function remains `b92bf5edfce867716532a89c17880cbc6cafe3afe1b97b8e81647c497103be81`; actual deadline receipt `0a2da3fdb8c1d962a0e6d74e750292dc934ff5c826c0b025bb38702717394db6` is reused without rerunning those controls.

## Actual runtime scope

The successful qualifier ran exactly these two methods against the same SDK725 source qualified by the signed suite, plus the single corrected fixture file:

- `TestFilesOpenFreshCachedReaderStopsAtSignedRemoval`
- `TestFilesOpenFreshAwaitedFetchDiscardsAfterSignedRemoval`

Both methods created new in-memory identities and new encrypted fixture data in exclusive retained test directories. The OS denial helper was active before SDK initialization. The cached-reader case required zero newly delivered plaintext and denied seeking after signed removal; the awaited-fetch case required the original pending fetch to withhold plaintext when removal was observed after the wait. The original complete signature/content and CAR checks remained active.

This result qualifies the SDK boundary. The shared native executable still requires its separate producer receipt, followed by the original removed pair's GET-only HTTP checks. Apple-bound runtime, cloud quota recovery and deletion of plaintext already possessed by a reader are outside this fixture's acceptance. The original HTTP authority failure `ecd4e58378cbb82731926536e82fca655da64ee156057ba411a242c95942c2ab` remains a failure until the corrected product passes those separate checks.
