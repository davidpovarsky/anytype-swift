# Torah Integration Progress

Master plan: `MASTER_PLAN.md`, v1.0

Base Anytype SHA: `e9ae976ca7882ac0b1fa8efb2f75e20618c82718`

Source Pinkha SHA: `24e074d5557dba632d36dbb71fda8cf9acb8d3ac`

TorahInspectorKit pinned SHA: `e8aefc626350c8ee0df9daf8d7de7e1dcd0ea418`

Working branch: `pinkha/torah-integration-t1-hardening`

T2 pinned baseline: `40f94396d8ebaff84a3b0d04afe50a81c2e67241`

T2 working branch: `pinkha/torah-integration-t2`

T2-Unblock working branch: `pinkha/torah-integration-t2-unblock`

CI-validated implementation HEAD: `b1ed4b561f78d2883ae2f7f0d8383cde41b0c821`

T2 CI-validated implementation HEAD: `0486bb72337a8c95b863ad8c8d9c5a7f11f51669`

Local toolchain: Swift 6.3.3 on Windows; Apple SDK unavailable locally.

| Stage | Status | Working branch | Evidence | Outstanding |
|---|---|---|---|---|
| T0 | PASS | `pinkha/torah-integration-t1` | Origin branch and all three pinned SHAs verified; clean isolated branch created from the pinned Anytype commit; supplied documents copied byte-for-byte. | None. |
| T1 | PASS | `pinkha/torah-integration-t1-hardening` | Initial T1 evidence remains valid. R1-R5 hardening added official-shaped response fixtures, 114/114 macOS package tests, a live bounded canary, and a full unsigned iOS app/IPA build at `b1ed4b561f78d2883ae2f7f0d8383cde41b0c821`. | None; await review. |
| T2 | PARTIAL / BLOCKED | `pinkha/torah-integration-t2-unblock` | Original portable work remains valid. The exact-tag native BlockCreate follow-up proved caller IDs and atomic initial payloads at state level, but also proved silent differing-payload replacement, removed-anchor loss, search/undo exposure, and unsafe manifest-host cleanup. Candidate status: `REJECTED / STILL BLOCKED`. | A different sanctioned stable/invisible native primitive plus real disposable middleware and two-client/offline proof is required. No unsafe adapter was installed. |
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

## T2 acceptance evidence

Unit-test names below identify portable/model evidence only. They are never
reported as real middleware or two-client sync evidence.

| ID | Status | Evidence |
|---|---|---|
| T2-01 | PASS | T2 began from clean exact hardening head `40f94396d8ebaff84a3b0d04afe50a81c2e67241`; origin matched; isolated branch `pinkha/torah-integration-t2` created before edits. |
| T2-02 | BLOCKED | `ADR-T2-STORAGE-CONCURRENCY.md` audits exact Swift/Heart calls and `staleScalarReplacementLosesConcurrentAdd` formally reproduces JSON loss. No candidate meets both native atomic convergence and retry idempotency, so no backend is selected. |
| T2-03 | PASS | Portable files import only Foundation and pinned `TorahInspectorCore`; static scan finds no Services, Heart, protobuf, SQLite, UIKit or SwiftUI dependency. |
| T2-04 | PASS | `roleCompatibility` decodes `source_quote` and `sourceQuote` and asserts canonical `sourceQuote` encoding. |
| T2-05 | PASS | `documentRoundTripIsLossless` retains the stable ID, every supplied field, absent optional label, and unknown item/envelope JSON across reopen. |
| T2-06 | PASS | `legacySourceQuote` covers unchanged V1; `richProvenanceRoundTrip` covers raw provider/reference payloads, original source text, version/license, UTC timestamp and UTF-16 excerpt coordinates. |
| T2-07 | PASS | `safeFailures` rejects future/corrupt data before producing a value; V1 canonical decode/encode/reopen is byte-idempotent and never invents missing provenance. |
| T2-08 | BLOCKED | No approved Anytype-native persistence backend; document reopen behavior cannot be claimed. |
| T2-09 | BLOCKED | No approved Anytype-native persistence backend; block reopen behavior cannot be claimed. |
| T2-10 | BLOCKED | `targetIsolation` proves the portable key separates documents, but independent native persistence/reopen is unproved. |
| T2-11 | BLOCKED | `targetIsolation` proves block IDs are part of the portable key, but independent native persistence/reopen is unproved. |
| T2-12 | PASS | `contextDeduplication` and `quoteInstances` prove stable retry identity, deterministic context dedup and retention of distinct quote excerpts. |
| T2-13 | BLOCKED | Exact scalar add/add loss is proven; no real two-client safe backend exists to retain A+B. |
| T2-14 | BLOCKED | ADR defines proposed observed-remove/add-wins operation semantics, but no native tombstone/operation representation is available for proof. |
| T2-15 | PASS | Deprecated snapshot APIs are non-requirement throwing extensions; `staleSnapshotAPIsThrow` asserts both document and block replacements fail visibly. |
| T2-16 | BLOCKED | Offline native replay requires an authorized disposable two-client environment after the missing primitive is implemented. |
| T2-17 | BLOCKED | Portable identity includes Space and `targetIsolation` proves key separation; actual native Space membership/permission checks require the blocked adapter. |
| T2-18 | BLOCKED | Orphan/target validation policy is documented, but native object/block existence and move races require the blocked adapter. |
| T2-19 | BLOCKED | Permission failure/unchanged canonical data requires a real native backend fixture. |
| T2-20 | BLOCKED | Heart `BlockSetFields` whole-field replacement risk is documented; no safe block-field write was shipped. |
| T2-21 | BLOCKED | No production mutation occurs, but non-interference of a future native association backend remains unproved. |
| T2-22 | BLOCKED | Proposed immutable operation retry/recovery semantics require client-supplied idempotent identity not exposed by current ordinary object creation. |
| T2-23 | BLOCKED | Codec corrupt/future data returns explicit errors rather than empty lists; backend failure and unknown-provider behavior need the blocked adapter. |
| T2-24 | PASS | Repository/identity interface and ADR specify indexed Space/target/source lookup plus reverse-query support without library-wide scans; T5 index/UI is not implemented. |
| T2-25 | PASS | macOS/Xcode run `38805873149` passed 125/125 tests in 15 suites (114 existing plus 11 T2), 0 failures, at `0486bb72337a8c95b863ad8c8d9c5a7f11f51669`. |
| T2-26 | PASS | Registered IPA run `38805908691` repeated 125/125 tests, installed middleware, built the unsigned iOS device app, packaged and uploaded the IPA at the same implementation HEAD. No host adapter files exist because T2-A correctly blocked them. |
| T2-27 | BLOCKED | No authorized disposable real middleware object/Space fixture is available, and no unsafe personal-Space test was attempted. |
| T2-28 | PASS | ADR and this matrix explicitly distinguish formal in-process/model evidence, real middleware persistence, and real two-client/device sync; the latter two are reported BLOCKED, not inferred. |

### T2-Unblock native block-journal audit

The follow-up B01–B16 matrix is recorded in
`T2_UNBLOCK_NATIVE_BLOCK_JOURNAL_AUDIT.md`. Its final status is
`REJECTED / STILL BLOCKED`:

- exact Heart source and Tier B state/snapshot evidence pass caller-supplied ID
  retention and complete initial payload carriage;
- same-ID/different-payload replay silently replaces the earlier model and is
  order-dependent (B04 FAIL);
- a create whose target anchor was removed can be ignored and left unreachable
  during production-style replay (B06 FAIL);
- text payloads enter native search text and normal block creation enters undo
  history; no alternative block kind is proven invisible (B12 FAIL);
- duplicate manifest canonicalization can delete a losing journal host (B13
  FAIL);
- native base/text validation does not validate the Pinkha payload/version
  (B16 FAIL);
- middleware persistence, real two-client sync, permissions, crash/retry, and
  load/index proof remain BLOCKED or NOT RUN and are not inferred from Tier B.

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

### T2 portable domain and concurrency gate, 2026-10-16

- Exact local/origin hardening baseline `40f94396d8ebaff84a3b0d04afe50a81c2e67241`
  and isolated `pinkha/torah-integration-t2` branch — PASS.
- `apple-doctor --json` — Windows Swift 6.3.3 available; Apple SDK unavailable.
- `swiftc -frontend -parse` over all T2 production/tests, isolated Swift 6
  typecheck against the exact pinned `TorahInspectorCore` models, deterministic
  runtime smoke (decode/encode/reopen/unknown fields/identity), portable
  dependency scan and `git diff --check` excluding the byte-exact supplied
  assignment's intentional Markdown hard-break spaces — PASS.
- `swift test --package-path Modules/PinkhaKit` locally — BLOCKED at the unchanged
  pinned dependency because Windows has no `CoreTransferable`; macOS CI is the
  authoritative package run.
- `.github/workflows/pinkha-tests.yaml`, run `38805873149` — PASS at
  `0486bb72337a8c95b863ad8c8d9c5a7f11f51669`; 125 tests in 15 suites passed,
  0 failed: <https://github.com/davidpovarsky/anytype-swift/actions/runs/38805873149>.
- `.github/workflows/ipa.yaml`, run `38805908691` — PASS at the same SHA; 125
  tests, middleware download/setup, unsigned iOS device build, IPA packaging and
  artifact upload all passed:
  <https://github.com/davidpovarsky/anytype-swift/actions/runs/38805908691>.
- IPA artifact ID `12007806245`, `Anytype-Hebrew-Unsigned-Device-IPA`,
  151,160,830 bytes, SHA-256 digest
  `361591a3ca95ee20adbf987dea2ab41763256ce318a4d7ff8ccb5fb14ca25fa4`,
  retention through 2026-10-22.
- Supplied Stage 2 assignment and repository copy both hash to
  `C541491FBC4A3813A253DEE1A6DD95F92817C84B811E55C468C22C80D1C482EE`.
- Real middleware CRUD/reopen and real two-client/offline convergence — BLOCKED;
  no disposable authorized environment or qualifying atomic/idempotent primitive
  exists. These are not represented by the passing unit/build workflows.

### T2-Unblock native BlockCreate audit, 2026-10-18

- Parent/origin `pinkha/torah-integration-t2` both resolved exactly to
  `813f6b6c8824125f5244ff1d4b7db4a3c81b39cd`; clean isolated branch
  `pinkha/torah-integration-t2-unblock` created — PASS.
- `Libraryfile` and Go module resolution both pinned Heart tag
  `v0.50.21-nightly.20260824.1` to
  `7e8f5535add386ff5f7573cde47e095c867ab724` — PASS.
- `apple-doctor --json` — Windows with portable Swift 6.3.3; no Apple SDK.
  This follow-up changes no Swift production code, so no unsupported local iOS
  result is claimed.
- Exact-tag source audit covered middleware error mapping, local create,
  ID generation/validation, state add/set, change replay, positional insertion,
  smart-block apply/history/rebuild, object-tree reconstruction, native search,
  Swift conversion, manifest discovery, and duplicate cleanup — PASS.
- Isolated Go probe command: `go test -mod=readonly -v -count=1 ./...` from
  `docs/pinkha/torah-integration/t2-block-journal-probe`, executed with the
  exact tag's Go 1.26.5 toolchain in `-mod=readonly` mode — PASS. All five
  top-level tests passed (including both duplicate replay orders) in 22.280s:
  initial ID/content/fields survived replay and snapshot; identical duplicates
  collapsed to one reachable ID; differing payloads silently selected the last
  replay; distinct IDs both survived with replay-dependent sibling order; and
  a create against a removed anchor remained unreachable. Unrelated existing
  block fields also remained byte-equivalent. The final command used 92.9s wall
  time; the first host build took 358.8s.
- `Dependencies/Middleware` is absent. Repository secrets visible through
  `gh secret list` are only `NOTIFY_DEVICE_ID` and `NOTIFY_DEVICE_TOKEN`; no
  disposable middleware account/Space or independent two-client fixture is
  configured. Tier C and Tier D — BLOCKED.
- No CI workflow was spent: the safety invariant failed at pinned source/state
  replay, and the registered workflows contain no authorized real two-client
  fixture. The prior T2 macOS/IPA results remain valid for unchanged Swift.

## Decisions / ADRs

- T1 caches only discardable provider metadata in actor-backed memory. No user data or association truth is stored there.
- `fetchSectionText` follows `TorahTextDocument.sectionRef` returned by the provider instead of syntactically dropping the last colon.
- Explicit provider IDs are strict routing keys; an unknown explicit ID throws `TorahError.missingProvider`.
- The Inspector factory wires `notesFetcher` to an explicit empty result until T5.
- No new upstream hooks in T1.
- T2 rejects a single JSON detail/block field as canonical association truth:
  both client paths replace a scalar/whole fields value and lose a concurrent
  stale read/modify/write addition.
- Ordinary native object creation exposes no client-supplied stable identity;
  retry after a lost response can create duplicate hidden records. Search is
  eventual and cannot repair physical idempotency.
- The future proof target is immutable association-operation records with stable
  client operation IDs, observed-remove/add-wins semantics and indexed
  Space/target/source queries. It is a proposal, not an installed schema.
- Until that primitive and disposable two-client proof exist, T2 deliberately
  ships no `AnytypeTorahAssociationRepository` adapter.
- The follow-up deterministic-ID block journal is rejected: replay uses
  unlink-and-`Set` without payload comparison, so differing content under one
  ID is silent last-replay-wins; invalid anchors can drop reachability.
- The manifest is not a journal host. Its duplicate canonicalization deletes
  secondary manifest objects, which would also delete their attached blocks.

## Known risks and blockers

- The existing `BlockInformationConverter` fields behavior remains an open T4 risk and was not changed.
- Sefaria is a live external API and can evolve. T1 decoding is intentionally bounded (8 levels, 512 visited nodes and 4,096 output characters) and retains raw provider JSON for diagnostics.
- T2 native persistence remains blocked. Caller-supplied block IDs exist, but
  their replay collision semantics, anchor behavior, visibility/history, host
  lifecycle, and validation fail the journal gate; a real two-client test
  environment is also absent. Portable codecs/policy remain complete.
- T3 Inspector UI/session work, T4 quote/editor integration, T5 Notes/reverse
  index, T6 device/RTL/accessibility/release validation and T7 extensions remain
  deferred.

## Changes from approved scope

Production changes remain inside `Modules/PinkhaKit`; T2-Unblock changes are
limited to documentation and an isolated exact-tag Go probe under
`docs/pinkha/torah-integration`. T2 adds no host adapter or schema mutation
because its mandatory concurrency gate did not pass. No workflow was created
or edited; the follow-up did not spend CI after native correctness failed.

## Next action required to unblock T2

Do not implement the rejected block journal and do not start T3. Expose or
verify a different sanctioned Heart-native primitive with a stable invisible
Space-scoped host, caller-supplied operation identity, explicit payload
collision detection, non-dropping insertion, validation, and bounded indexed
queries. Then run B01–B16 against real middleware and two independent clients
in an authorized disposable Space, including response loss, reopen, offline
replay, permissions, visibility/export/undo, target deletion, and 1k/10k load.
Only a complete passing result authorizes the Anytype host adapter.
