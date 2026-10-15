# Torah Integration Progress

Master plan: `MASTER_PLAN.md`, v1.0

Base Anytype SHA: `e9ae976ca7882ac0b1fa8efb2f75e20618c82718`

Source Pinkha SHA: `24e074d5557dba632d36dbb71fda8cf9acb8d3ac`

TorahInspectorKit pinned SHA: `e8aefc626350c8ee0df9daf8d7de7e1dcd0ea418`

Working branch: `pinkha/torah-integration-t1-hardening`

CI-validated implementation HEAD: `b1ed4b561f78d2883ae2f7f0d8383cde41b0c821`

Local toolchain: Swift 6.3.3 on Windows; Apple SDK unavailable locally.

| Stage | Status | Working branch | Evidence | Outstanding |
|---|---|---|---|---|
| T0 | PASS | `pinkha/torah-integration-t1` | Origin branch and all three pinned SHAs verified; clean isolated branch created from the pinned Anytype commit; supplied documents copied byte-for-byte. | None. |
| T1 | PASS | `pinkha/torah-integration-t1-hardening` | Initial T1 evidence remains valid. R1-R5 hardening added official-shaped response fixtures, 114/114 macOS package tests, a live bounded canary, and a full unsigned iOS app/IPA build at `b1ed4b561f78d2883ae2f7f0d8383cde41b0c821`. | None; await review. |
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
| T1-02 | PASS | macOS CI passed deterministic Hebrew suggestion coverage against the mocked Sefaria name response. |
| T1-03 | PASS | macOS CI passed English suggestion/exact-resolution coverage with canonical keys and labels preserved. |
| T1-04 | PASS | macOS CI passed broad book/tractate/section classification coverage. |
| T1-05 | PASS | macOS CI passed exact Hebrew path, query and contextual `lookup_ref` encoding assertions. |
| T1-06 | PASS | macOS CI passed Texts V3 ordered-section, documented 1-based ordinals, same-section ranges with gaps, navigation, version, license and direction coverage. |
| T1-07 | PASS | macOS CI passed exact segment identity, refusal to fabricate cross-section identities and actual-language fallback coverage. |
| T1-08 | PASS | macOS CI passed distinct malformed JSON, empty text/version and HTTP error coverage. |
| T1-09 | PASS | macOS CI passed `anchorRefExpanded`, nested Hebrew/English text, HTML normalization, raw-payload preservation and deterministic Core grouping coverage. |
| T1-10 | PASS | macOS CI passed Name API `key`/`title` identity, response-language handling, Topic v2 bilingual titles, deduplication, cache TTL, expiry and retry coverage. |
| T1-11 | PASS | macOS CI passed diacritics, stable lexical identity, recursive `content.senses` definitions, flat legacy definitions and contextual `lookup_ref` coverage. |
| T1-12 | PASS | macOS CI passed TOC parsing, cache, compressed path and exact numeric/Roman-prefixed book filtering coverage. |
| T1-13 | PASS | CI and portable typechecks compiled explicit `.section`/`.segment` selection and the notes-enabled repository initializer against the exact Kit revision. |
| T1-14 | PASS | macOS CI passed strict provider registry and wrong-provider repository routing coverage. |
| T1-15 | PASS | macOS CI passed cancellation and non-silent transport/provider error coverage. |
| T1-16 | PASS | Both hardening macOS workflows passed all 114 tests in 12 suites (72 pre-existing, 37 original T1 and 5 R1-R5 hardening tests), with 0 failures. |
| T1-17 | PASS | Static scan of new production files found no SQLite, Leaf, Heart, protobuf, Services, UIKit or SwiftUI coupling. |
| T1-18 | PASS | Existing registered `.github/workflows/ipa.yaml` built the unsigned Anytype device app at the hardening SHA, packaged the IPA and uploaded `Anytype-Hebrew-Unsigned-Device-IPA` successfully. |

## Verification log

- `swift package --package-path Modules/PinkhaKit resolve --verbose` — PASS; exact Kit revision reported by resolver.
- `swiftc -frontend -parse` over all new Torah production and test sources — PASS.
- Portable Swift 6 typecheck of all `PinkhaKit` production sources against the exact Kit Core declarations — PASS.
- Portable Swift 6 typecheck of all existing and new `PinkhaKitTests` sources — PASS.
- Initial local `swift test` attempt — NOT RUN to completion: an earlier timed-out process left `.build/build.db` locked; a clean scratch-path retry timed out after 300 seconds without output. This host has no Apple SDK and is not treated as authoritative.

- `.github/workflows/pinkha-tests.yaml`, run `38751030425` — PASS at `fa5a9bdf86724f9162a98173a4a00c9fbdf3ee95`; 109 tests in 12 suites passed, 0 failed: <https://github.com/davidpovarsky/anytype-swift/actions/runs/38751030425>.
- `.github/workflows/ipa.yaml`, run `38751578677` — PASS at the same SHA; 109 tests passed, middleware setup succeeded, unsigned iOS device build succeeded, 145 MB IPA packaged, and artifact `Anytype-Hebrew-Unsigned-Device-IPA` uploaded: <https://github.com/davidpovarsky/anytype-swift/actions/runs/38751578677>.
- IPA artifact ID `11983111694`, 151,100,326 bytes, SHA-256 digest `bc0a2ac524ac0e2fbc956c049de149d4b224b444670b230f0524701d4eec8ff9`; retention through 2026-10-22.

### T1 review remediation (R1-R5), 2026-10-15

- `swift package --package-path Modules/PinkhaKit resolve` — PASS; Kit remained pinned at `e8aefc626350c8ee0df9daf8d7de7e1dcd0ea418`.
- `apple-doctor --json` — Windows portable Swift 6.3.3 available; Apple SDK unavailable.
- `swiftc -frontend -parse` over every edited Swift source/test, Foundation-only typecheck of the new bounded JSON normalizer and reference helper, JSON parsing of all fixtures, static unsafe-pattern scan and `git diff --check` — PASS.
- Local `swift test --package-path Modules/PinkhaKit` — BLOCKED at the unchanged pinned dependency because Windows has no `CoreTransferable` module. macOS CI is authoritative.
- Bounded read-only live canary — PASS for `/api/ref/Genesis 1:7`, Texts v3, Links, Name API, Topic v2 and `/api/words/שלום`; observed 1-based `[1,7]`, `anchorRefExpanded`, HTML-bearing relationship text, Name `key`/`title`, bilingual topic titles and recursive lexical `content.senses`.
- Initial hardening CI run `38790869245` compiled all production/tests and executed 114 tests; one test-only raw-JSON escaping assertion failed (`</b>` versus the valid serialized `<\/b>` form). The assertion was corrected without production changes.
- `.github/workflows/pinkha-tests.yaml`, run `38791289901` — PASS at `b1ed4b561f78d2883ae2f7f0d8383cde41b0c821`; 114 tests in 12 suites passed, 0 failed: <https://github.com/davidpovarsky/anytype-swift/actions/runs/38791289901>.
- `.github/workflows/ipa.yaml`, run `38791605742` — PASS at the same SHA; tests, middleware setup, unsigned device build, IPA packaging and artifact upload all passed: <https://github.com/davidpovarsky/anytype-swift/actions/runs/38791605742>.
- IPA artifact ID `12001423107`, `Anytype-Hebrew-Unsigned-Device-IPA`, 151,105,287 bytes, unexpired at verification time, retention through 2026-10-22.
- Detailed response-contract and fixture provenance: `T1_REVIEW_FINDINGS.md`.

## Decisions / ADRs

- T1 caches only discardable provider metadata in actor-backed memory. No user data or association truth is stored there.
- `fetchSectionText` follows `TorahTextDocument.sectionRef` returned by the provider instead of syntactically dropping the last colon.
- Explicit provider IDs are strict routing keys; an unknown explicit ID throws `TorahError.missingProvider`.
- The Inspector factory wires `notesFetcher` to an explicit empty result until T5.
- No new upstream hooks in T1.

## Known risks and blockers

- The existing `BlockInformationConverter` fields behavior remains an open T4 risk and was not changed.
- Sefaria is a live external API and can evolve. T1 decoding is intentionally bounded (8 levels, 512 visited nodes and 4,096 output characters) and retains raw provider JSON for diagnostics.
- T2 storage/conflict policy, T3 Inspector UI/session work, T4 quote/editor integration, T5 Notes/reverse index, T6 device/RTL/accessibility/release validation and T7 extensions remain deferred and untested by T1.

## Changes from approved scope

Production changes remain inside `Modules/PinkhaKit`; documentation changes remain under `docs/pinkha`. The requested `.github/workflows/pinkha-validation.yml` could not be dispatched because GitHub returned HTTP 404 and the workflow is not registered on the default branch. No workflow was created or edited; the one deliberate full-build slot used the already registered `.github/workflows/ipa.yaml`, which performs the required PinkhaKit tests, middleware setup, unsigned device build, IPA packaging and artifact upload.

## Next authorized action

Await review and a separate T2 implementation order. Do not start T2.
