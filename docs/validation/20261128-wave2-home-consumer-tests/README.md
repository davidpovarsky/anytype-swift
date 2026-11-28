# Wave 2 — Home consumer component tests

**Source reviewed; Apple execution NOT_RUN.** This is a separate test-only delivery over personal-navigation tip `9a4fcf22949385771bb98faac9e4a05c9be65066`. It adds one Swift Testing method with two declared role cases to the existing Library search/Bin test file. It changes no production code, package definition, PBX target, controller or execution gate.

## What this test covers

`AnyLibraryHomeReadinessTests.homeSetOpenAndUnsetAfterRealReadinessUsesCurrentReadAuthority(isReader:)` runs with `false` (Owner) and `true` (Reader). Each case creates its own bounded loopback HTTP transport, connects the real public application session, decodes the real account/run-binding contract and calls the original `AnyLibraryPresentation.open()`. Controlled installed wiki/Note declarations, catalog, hierarchy and initial SSE frames pass through the actual parsers and public readiness path.

The method then exercises set Home → open Home → unset Home → open absent Home. It checks the exact two bound settings dispatches, their readbacks, one exact object-ID/nil-block callback, and no second callback after unset. Reader `canWrite` remains false. This checks the consumer's personal-preference READ policy; the fixture is not an independent Native ACL implementation or proof of actual backend persistence.

The complete final test is 45,691 bytes, SHA256 `e9945ab99ae82ff16e6f3e74e085ce694f38dae4eb7a1d15b129f539d417cd38`. Its original 13,860-byte prefix, four methods and five cases are exact. The original cases are not selected for replay.

## Review findings and correction

Two source findings were retained and corrected before publication:

- **HOME-READINESS-PUBLICATION-01:** receiving the second document query proves the initial hierarchy observation reached the consumer, but precedes postflight and model publication. The existing bounded wait now also requires the expected published `allDocuments` IDs. These are separate facts; the test does not claim the second query necessarily supplied that row when the first already did.
- **HOME-TEST-MODEL-RETENTION-01:** lifetime callbacks hold the model weakly, so the test now retains the actual model outside the `do` scope and uses `withExtendedLifetime` after the awaited presentation drain.

Four unique literal changes reconstruct the whole corrected file from the retained v1 candidate and reverse exactly. The entire HTTP fixture, route contracts, bounds, old prefix and case count remain unchanged. These were source-review findings, not observed runtime failures.

The independent Interfaces and Editor final reviews and Root review are included. The original blocked Editor review remains in `home-test-candidate-v1`.

## Reusable dependency and execution selection

The production dependency is the already-published navigation source commit `0735b9820d2ca4d479e8b964f81b2602a9758cf6` and evidence tip `9a4fcf22949385771bb98faac9e4a05c9be65066`, over W1 `f372f5e243427822df27bf8bd2ba51bf8206c644`. The required Library source is SHA256 `e6111e18c38b582437651cf80f420e5282d8ec473da69cf56ae67c4ef18645d4`.

The existing package target is `PinkhaAnyUITests`, guarded by SwiftUI and Network availability. `test-selection.json` names the source suite/method and two arguments. W3 must enumerate the actual identifier in its admitted Apple test product before selecting it; no installed runner prefix, test discovery or execution is inferred from the source names. The method has the existing one-minute suite time limit. This controlled component uses no Native process and does not itself need a new native backend product. The actual application consumers still need their separately qualified bound-start/HTTP native product.

Transport caps remain 1,024 cumulative requests/connections, 16 tracked connections, 16 KiB per header/body/response, 32 KiB combined request and 16 retained failures. Startup, close and progress waits are five seconds; fixture lifetime is 45 seconds. These are source bounds, not an observed runtime/resource-fit result.

## Evidence layout and custody

- `home-test-candidate-v1` preserves all six complete original author objects and the blocked review. The manifest's original candidate locator is stored here as `full-candidate.swift.txt`; its bytes and Git blob are unchanged.
- `home-test-candidate-v2` preserves the exact successor metadata, correction literals, findings, fixture derivation and final peer reviews. Its full candidate is the actual test file at `Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyLibrarySearchPublicationTests.swift`.
- `root-source-review.json` adds the complete Root prefix/inverse checks and actual lifetime/recovery/package inspections.
- `FILES.json` binds each delivered body except itself. The subsequent `SOURCE_PUBLICATION_VERIFICATION.json` records the actual source commit/tree readback and is added in a separate evidence-only child.

Author manifests, README files and findings are immutable historical snapshots from their review stages. Their then-pending review/publication fields are preserved; the final review files and this top-level status describe the delivery state.

All source custody and publication use V8 plus GitHub objects. No Oracle source directory, build, listener, test process or Mac operation was created for this packet. The branch is Wave 2 owned; W3 alone controls final integration and shared application builds.

## Acceptance still open

Compilation, actual selection and both new cases remain **NOT_RUN**. This packet supplies no mounted Home-button interaction, screenshot, cold-reopen result, actual Native settings persistence, account/Space transition, mixed app/OS language result or imported Home/migration acceptance. Last Opened has its own separate published renderer test packet. Existing accepted cohorts retain their original scopes and are not replayed by this delivery.
