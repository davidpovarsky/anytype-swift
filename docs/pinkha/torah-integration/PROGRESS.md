# Torah Integration Progress

Master plan: `MASTER_PLAN.md`, v1.0

Base Anytype SHA: `e9ae976ca7882ac0b1fa8efb2f75e20618c82718`

Source Pinkha SHA: `24e074d5557dba632d36dbb71fda8cf9acb8d3ac`

TorahInspectorKit pinned SHA: `e8aefc626350c8ee0df9daf8d7de7e1dcd0ea418`

Working branch: `pinkha/torah-integration-t1`

Current HEAD before T1 commit: `e9ae976ca7882ac0b1fa8efb2f75e20618c82718`

Local toolchain: Swift 6.3.3 on Windows; Apple SDK unavailable locally.

| Stage | Status | Working branch | Evidence | Outstanding |
|---|---|---|---|---|
| T0 | PASS | `pinkha/torah-integration-t1` | Origin branch and all three pinned SHAs verified; clean isolated branch created from the pinned Anytype commit; supplied documents copied byte-for-byte. | None. |
| T1 | IN PROGRESS | `pinkha/torah-integration-t1` | Exact SPM resolution and portable Swift 6 production/test typechecks passed. | macOS package tests, push workflow and iOS validation build. |
| T2 | NOT STARTED | | | Storage and conflict-policy ADR remain separately authorized work. |
| T3 | NOT STARTED | | | Inspector UI and document session are deferred. |
| T4 | NOT STARTED | | | Quote/editor integration is deferred. |
| T5 | NOT STARTED | | | Native Notes and reverse index are deferred. |
| T6 | NOT STARTED | | | Device, RTL, accessibility and release validation are deferred. |
| T7 | DEFERRED | | | Otzaria and other extensions are outside the approved core path. |

## T1 acceptance evidence

| ID | Status | Evidence |
|---|---|---|
| T1-01 | PASS | `swift package resolve` resolved `TorahInspectorKit` exactly at `e8aefc626350c8ee0df9daf8d7de7e1dcd0ea418`; actual updated Core declarations typechecked. |
| T1-02 | NOT RUN | Deterministic Hebrew suggestion test authored and typechecked; awaiting macOS test run. |
| T1-03 | NOT RUN | English suggestion/resolution behavior test authored and typechecked. |
| T1-04 | NOT RUN | Book, tractate and section classification test authored and typechecked. |
| T1-05 | NOT RUN | Exact Hebrew path and contextual query encoding tests authored and typechecked. |
| T1-06 | NOT RUN | Texts V3 section ordering/navigation/version test authored and typechecked. |
| T1-07 | NOT RUN | Exact segment and source-language fallback tests authored and typechecked. |
| T1-08 | NOT RUN | Malformed JSON, empty version and HTTP error tests authored and typechecked. |
| T1-09 | NOT RUN | Rich relationship mapping and deterministic Core grouping tests authored and typechecked. |
| T1-10 | NOT RUN | Topic cache hit/expiry/retry/dedup/Hebrew search tests authored and typechecked. |
| T1-11 | NOT RUN | Diacritics, stable lexical identity and `lookup_ref` tests authored and typechecked. |
| T1-12 | NOT RUN | TOC parsing/cache/compression/exact-book filtering tests authored and typechecked. |
| T1-13 | PASS | Portable typecheck compiled explicit `.section`/`.segment` selection and notes-enabled repository initializer against the exact Kit source declarations. |
| T1-14 | NOT RUN | Registry and repository wrong-provider tests authored and typechecked. |
| T1-15 | NOT RUN | Transport cancellation and non-silent error tests authored and typechecked. |
| T1-16 | NOT RUN | Baseline `swift test` did not complete on the Windows host; macOS workflow is pending. |
| T1-17 | PASS | Static scan of new production files found no SQLite, Leaf, Heart, protobuf, Services, UIKit or SwiftUI coupling. |
| T1-18 | NOT RUN | Existing `pinkha-validation.yml` has not yet been dispatched. |

## Verification log

- `swift package --package-path Modules/PinkhaKit resolve --verbose` — PASS; exact Kit revision reported by resolver.
- `swiftc -frontend -parse` over all new Torah production and test sources — PASS.
- Portable Swift 6 typecheck of all `PinkhaKit` production sources against the exact Kit Core declarations — PASS.
- Portable Swift 6 typecheck of all existing and new `PinkhaKitTests` sources — PASS.
- Initial local `swift test` attempt — NOT RUN to completion: an earlier timed-out process left `.build/build.db` locked; a clean scratch-path retry timed out after 300 seconds without output. This host has no Apple SDK and is not treated as authoritative.

## Decisions / ADRs

- T1 caches only discardable provider metadata in actor-backed memory. No user data or association truth is stored there.
- `fetchSectionText` follows `TorahTextDocument.sectionRef` returned by the provider instead of syntactically dropping the last colon.
- Explicit provider IDs are strict routing keys; an unknown explicit ID throws `TorahError.missingProvider`.
- The Inspector factory wires `notesFetcher` to an explicit empty result until T5.
- No new upstream hooks in T1.

## Known risks and blockers

- The existing `BlockInformationConverter` fields behavior remains an open T4 risk and was not changed.
- macOS/Xcode package tests and the unsigned iOS app build are required before T1 can be marked PASS.

## Changes from approved scope

None. Production changes remain inside `Modules/PinkhaKit`; documentation changes remain under `docs/pinkha`.

## Next authorized action

Complete T1 verification, commit and push the dedicated branch, run the two existing workflows, then await review. Do not start T2.
