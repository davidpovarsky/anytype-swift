# IMPLEMENTATION ORDER — Anytype Torah Integration, Stage T1

> **Give this document AND `Anytype_Torah_Integration_MASTER_PLAN_v1.md` to the coding agent.**  
> Status: READY FOR EXECUTION · Version 1.0 · 2026-10-15  
> Your job is to **implement and verify ONLY Stage T1 (including the T0 baseline/docs setup)**, make a commit and push a dedicated branch, then report evidence. **Do not continue to T2–T7.**  
> You have permission to perform the described implementation and run existing GitHub Actions. No signing, deployment, paid infrastructure, deletions or merges are authorized.

## 0. Absolute instructions (read before touching files)

Act as the responsible repository engineer, not an advisor. Inspect real source code first; implement the requested changes; add deterministic tests; verify; commit; push; report. Avoid speculative refactors and unrelated redesign. Do not ask the user to manually edit an Xcode project, download a dependency, or run a local command when you can do it yourself.

**Mission of this stage:** In the Anytype fork, create a compileable, unit-tested **Torah provider/core integration** based on Pinkha's existing Sefaria logic and the **updated** TorahInspectorKit. Deliver reference search/resolution, text retrieval, link/topic data, lexical lookup, source hierarchy and a host-ready `TorahInspectorRepository`, all WITHOUT any UI, Anytype writes, or editor hooks yet.

**Explicit NON-goals of T1** — do not implement or change:

- No `TorahAssociationRepository` storage implementation, object/details/blocks mutations, schema migrations or sync changes (T2).
- No Inspector presentation, SwiftUI views, `EditorPageCoordinatorView`, toolbar, association sheets, block menus, quote insertion, drag/drop or slash triggers (T3–T4).
- No Notes persistence, Knowledge tab or reverse association index (T5).
- No Otzaria integration, auto-detection, `[[...]]`, new Rust/Heart module, new protobuf type or scripting platform (T7).
- No merging/cherry-picking `develop`, `dev`, `main`, `Pinkha` source branch or the `TorahInspectorKit` development branch wholesale.
- No changes to signing, bundle IDs, provision profiles, Cloudflare/Railway, user account or Apple developer settings.

**Do not claim PASS until evidence is shown.** Tests not executed are `NOT RUN`; untestable due to secrets/toolchain are `BLOCKED`; failed tests are `FAIL`.

---

## 1. Pinned repositories and provenance (verify, do not improvise)

| Role | Repository | Ref / pinned HEAD |
|---|---|---|
| Target | `https://github.com/davidpovarsky/anytype-swift` | `pinkha/hierarchy-home-v1` @ `e9ae976ca7882ac0b1fa8efb2f75e20618c82718` |
| Source for provider code | `https://github.com/davidpovarsky/pinkha` | `torah-ux-knowledge-tab` @ `24e074d5557dba632d36dbb71fda8cf9acb8d3ac` |
| Updated shared inspector library | `https://github.com/davidpovarsky/TorahInspectorKit` | `codex/shared-torah-inspector-maktabah` @ `e8aefc626350c8ee0df9daf8d7de7e1dcd0ea418` |

These were checked on 2026-10-15. Anytype `develop` had a separately updated SHA; **DO NOT assume it is a safe linear successor or merge it now**. The source Pinkha repository references the old `TorahInspectorKit` version `0.1.0`; the chosen library SHA is newer than the `0.1.2` tag and exposes updated model APIs.

### Required preflight in the target repository

Run equivalents of the following (use the agent's safe shell/GitHub tools; never force-push):

```bash
git remote -v
git fetch origin --prune
git status --short
git rev-parse origin/pinkha/hierarchy-home-v1
git rev-parse origin/develop
git cat-file -e e9ae976ca7882ac0b1fa8efb2f75e20618c82718^{commit}
```

1. Confirm the `pinkha/hierarchy-home-v1` remote still points to the pinned SHA; if not, record the observed SHA and diff against the pin. **Do not silently switch base** or merge. A changed branch requires an explicit impact note; remain on the pinned commit for T1 unless it makes T1 impossible, in which case report `BLOCKED`.
2. Confirm source repos still contain the pinned commits. Read source at those exact SHAs, not moving branch tips.
3. If the current working tree contains user work, **preserve it**. Make a separate clone/worktree instead of cleaning/resetting existing changes.
4. Make a **new** branch from the pinned Anytype commit, preferably `pinkha/torah-integration-t1`. If it already exists, inspect it and choose a clearly versioned fresh branch; never overwrite an existing branch.
5. Record starting git SHA, branch name and toolchain (`swift --version`, `xcodebuild -version` when macOS is available). Read repository `AGENTS.md`/local instructions if present.

Suggested isolated branch creation when safe:

```bash
git switch -c pinkha/torah-integration-t1 e9ae976ca7882ac0b1fa8efb2f75e20618c82718
```

No `git reset --hard`, `git clean`, `push -f` or upstream branch mutation.

### Read these target files in FULL

- `Modules/PinkhaKit/Package.swift`
- `Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahAssociationModels.swift`
- `Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahAssociationRepository.swift`
- `Modules/PinkhaKit/Sources/PinkhaKit/Domain/PinkhaRuntime.swift`
- `Modules/PinkhaKit/Sources/PinkhaKit/Schema/PinkhaSpaceManifest.swift`
- Existing `Modules/PinkhaKit/Tests/PinkhaKitTests/` tests
- `docs/pinkha/ARCHITECTURE.md`, `DATA_MODEL.md`, `SCHEMA.md`, `PORTED_CODE.md`, `UPSTREAM_HOOKS.md`, `MIGRATION_PLAN.md`
- `.github/workflows/pinkha-tests.yaml`, `.github/workflows/pinkha-validation.yml`, `.github/workflows/ipa.yaml`
- Anytype Xcode package linkage in `Anytype.xcodeproj/project.pbxproj` (inspect only at this stage).

### Read these **exact** source files at the pinned Pinkha commit

```text
app/Packages/PinkhaTorah/Package.swift
app/Packages/PinkhaTorah/Sources/PinkhaTorahCore/Models.swift
app/Packages/PinkhaTorah/Sources/PinkhaTorahCore/ProviderProtocols.swift
app/Packages/PinkhaTorah/Sources/PinkhaTorahCore/SefariaClient.swift
app/Packages/PinkhaTorah/Sources/PinkhaTorahCore/SefariaProviders.swift
app/Packages/PinkhaTorah/Sources/PinkhaTorahCore/SefariaTextRelationships.swift
app/Packages/PinkhaTorah/Sources/PinkhaTorahCore/TorahWorkspace.swift
app/Packages/PinkhaTorah/Sources/PinkhaTorahCore/TorahReferenceUtil.swift
app/Packages/PinkhaTorah/Sources/PinkhaTorahCore/TorahInspectorRepository+Pinkha.swift
app/Packages/PinkhaTorah/Sources/PinkhaTorahCore/Hierarchy/TorahSourceHierarchy.swift
app/Packages/PinkhaTorah/Sources/PinkhaTorahCore/Hierarchy/SefariaHierarchyProvider.swift
app/Packages/PinkhaTorah/Sources/PinkhaTorahCore/FixtureTorahProvider.swift
app/Packages/PinkhaTorah/Tests/PinkhaTorahCoreTests/SefariaProviderTests.swift
app/Packages/PinkhaTorah/Tests/PinkhaTorahCoreTests/TorahInspectorAdapterTests.swift
app/Packages/PinkhaTorah/Tests/PinkhaTorahCoreTests/TorahInspectorRepositoryTests.swift
app/Packages/PinkhaTorah/Tests/PinkhaTorahCoreTests/TorahKnowledgeHierarchyTests.swift
```

Also inspect the updated **TorahInspectorKit** `Package.swift` and the entire public declarations in:

```text
Sources/TorahInspectorCore/Models.swift
Sources/TorahInspectorCore/ProviderProtocols.swift
Sources/TorahInspectorCore/TorahInspectorRepository.swift
Sources/TorahInspectorCore/TorahInspectorCoordinator.swift
Sources/TorahInspectorCore/TorahSourceTransfer.swift
Sources/TorahInspectorUI/TorahInspectorHostActions.swift  # inspect for compatibility; DO NOT import UI in T1
Sources/TorahInspectorUI/TorahInspectorRoute.swift        # inspect scope/entry changes; T3 owns UI
```

Do not copy older public models from Pinkha when their updated equivalents already live in `TorahInspectorCore`. **Never fork/copy `TorahInspectorKit/Sources` into the target.**

---

## 2. Exact deliverables and file boundaries

**Allowed production changes in T1:**

- `Modules/PinkhaKit/Package.swift` (pin Core dependency)
- New or narrowly updated files under `Modules/PinkhaKit/Sources/PinkhaKit/Torah/` (provider/core layer)
- Unit tests under `Modules/PinkhaKit/Tests/PinkhaKitTests/Torah/`
- `docs/pinkha/torah-integration/MASTER_PLAN.md`, `STAGE_01_IMPLEMENTATION.md`, `PROGRESS.md`, source-port ledger
- Narrow factual corrections in `docs/pinkha/PORTED_CODE.md` (do not rewrite unrelated documents).
- If and only if justified by actual package-resolution/build failure: lockfile that is normally committed, or a narrowly necessary Xcode package reference; document why. Prefer no Xcode project modification in T1.
- Do not rewrite existing CI unless a reproducible repo-specific trigger/compatibility defect blocks T1; describe it, make a minimal fix only after inspecting the root cause.

**Proposed file structure** (you may consolidate adjacent files when compilation requires, but responsibilities and tests below MUST exist; record any changed names):

```text
Modules/PinkhaKit/
  Package.swift                                        EDIT
  Sources/PinkhaKit/Torah/
    TorahProviderModels.swift                           NEW
    TorahProviderProtocols.swift                        NEW
    TorahProviderRegistry.swift                         NEW
    AnytypeTorahWorkspace.swift                         NEW
    TorahInspectorRepositoryFactory.swift               NEW
    TorahReferenceUtil.swift                             NEW
    Providers/
      TorahHTTPTransport.swift                          NEW (or combine with SefariaClient)
      SefariaClient.swift                               NEW
      SefariaReferenceProvider.swift                    NEW
      SefariaTextProvider.swift                         NEW
      SefariaRelationshipProvider.swift                 NEW
      SefariaTopicProvider.swift                        NEW
      SefariaLexicalProvider.swift                      NEW
      TorahTopicCache.swift                             NEW, actor-backed in-memory index
    Hierarchy/
      TorahSourceHierarchy.swift                        NEW
      SefariaHierarchyProvider.swift                   NEW
  Tests/PinkhaKitTests/Torah/
    SefariaReferenceProviderTests.swift                 NEW
    SefariaTextProviderTests.swift                      NEW
    SefariaRelationshipProviderTests.swift              NEW
    SefariaTopicLexicalProviderTests.swift              NEW
    SefariaHierarchyTests.swift                         NEW
    TorahInspectorRepositoryBridgeTests.swift          NEW
    TorahHTTPTransportTests.swift                       NEW
    Fixtures/                                           NEW (minimal deterministic fixture data)

docs/pinkha/torah-integration/
  MASTER_PLAN.md                                       COPY exact master plan supplied
  STAGE_01_IMPLEMENTATION.md                           COPY this file, including agent prompt
  PROGRESS.md                                          NEW / update with evidence
  SOURCE_PORT_LEDGER.md                                NEW: origin→target/functionality ledger
```

**Do not overwrite** existing `TorahAssociationModels.swift` or `TorahAssociationRepository.swift`. This stage must leave their public API and serialization stable. The storage repository will be implemented in T2, not now.

---

## 3. Task A — Add TorahInspectorKit Core by exact revision

`TorahInspectorKit` pinned SHA: `e8aefc626350c8ee0df9daf8d7de7e1dcd0ea418`.

In `Modules/PinkhaKit/Package.swift`:

1. Keep existing package platforms (iOS 17, macOS 14) and Swift language mode 6. Keep existing `PinkhaKit` product and test target.
2. Add a **revision-pinned** SPM dependency:

```swift
.package(
    url: "https://github.com/davidpovarsky/TorahInspectorKit.git",
    revision: "e8aefc626350c8ee0df9daf8d7de7e1dcd0ea418"
)
```

3. Add to the **PinkhaKit target only**:

```swift
.product(name: "TorahInspectorCore", package: "TorahInspectorKit")
```

4. Tests that directly import `TorahInspectorCore` may add the same product to test dependencies. Do not link `TorahInspectorUI` in T1; it is owned by T3 and must use the **same pinned commit**.
5. Resolve the package, inspect the actual resolved revision, confirm public declarations match the audited API. Do not switch to `from: "0.1.2"`, `.branch("main")`, another version, or vendor a copy to silence a resolver failure.
6. Do not change minimum iOS deployment target or Swift version just to make this pass. Both manifest files were verified as Swift tools 6.0, iOS 17+, macOS 14+; a toolchain conflict must be diagnosed and reported.

**Expected actual updated Core types (not hand-made approximations):**

- `TorahTextRequest`, `TorahTextVersionMetadata`, `TorahTextSegment`, `TorahTextDocument`
- `TorahLinkedSource` (including `canonicalBookID`, `anchorRefs`, `relationshipKind`, `semanticCategory`, text/version/license metadata)
- `TorahLinkedTopic`, `TorahRelationshipGroups`, `TorahSourceGroup`
- `TorahInspectorSelection` with **explicit `scope`** (section or segment), `TorahInspectorFocus`, `TorahInspectorNote`
- `TorahInspectorRepository` initializer with `textFetcher`, `linksFetcher`, `topicsFetcher` and `notesFetcher`
- `TextProvider`, `RelationshipProvider`, `TorahInspectorProvider`.

Proof: a small unit test should instantiate or compile against the actual updated `TorahInspectorSelection(scope: .section)` and `TorahInspectorRepository(notesFetcher: ...)` API. Avoid deprecated `.segmentRelationships` in new code.

---

## 4. Task B — Port ONLY provider-facing models (do not duplicate Anytype association models)

From Pinkha's `PinkhaTorahCore/Models.swift`, selectively adapt the models that are **not** in updated `TorahInspectorCore` and **not** already in target `TorahAssociationModels.swift`:

- `ReferenceCandidate`, `ResolvedReference` (canonical, Hebrew/English label, provider payload, URL ref, node type, depth, index arrays, first available section, `isEmbeddableSource`).
- `TopicCandidate`, `ResolvedTopic`.
- `WordCandidate`, `ResolvedWord`, `TorahLexicalContext`.

Define them in `TorahProviderModels.swift` with public correct Swift 6 `Sendable` semantics. Keep the original provider-level identifiers and names when possible to minimize port risks. Make their semantics independent of Leaf/SQLite/Anytype BlockService.

**Do not copy the following Pinkha types over existing Anytype types:** `TorahAssociationKind`, `TorahAssociationRole`, `TorahAssociation`, `TorahTarget`, any Leaf ID or SQLite relation. In Anytype they already have alternative names/shapes and are covered by the T2 migration plan. No user-data models should change at T1.

**Normalization requirement:** A display label such as `בראשית א:א` does NOT replace `Genesis 1:1` canonical identity. Preserve provider IDs and raw provider payloads where available; don't generate fake metadata. `ResolvedReference.isEmbeddableSource` must behave like source Pinkha for broad vs precise refs, including section-level versus segment-level differences.

---

## 5. Task C — Port HTTP client, injectable transport, and error behavior

Create/port `TorahHTTPTransport` and `SefariaClient`, based on pinned `SefariaClient.swift`:

```swift
public protocol TorahHTTPTransport: Sendable {
    func data(for request: URLRequest) async throws -> (Data, HTTPURLResponse)
}
```

Implementation requirements:

- production: `URLSessionTorahTransport`, configurable timeout, sensible `Accept: application/json`, **HTTPS** `https://www.sefaria.org` default.
- test: injected deterministic `MockTorahHTTPTransport` which records full request URLs and returns fixture `Data` plus `HTTPURLResponse`. Tests MUST NOT call the live network.
- retain URL path-component percent encoding, including Hebrew and spaces; do not manually concatenate unescaped URLs.
- propagate Task cancellation as cancellation, not as empty results or success. Normalize network errors to existing `TorahError.network` or equivalent, preserving HTTP status in diagnostic failures.
- validate non-2xx API responses in providers; malformed JSON must be reported as decoding failure, not silently dropped into `[]` (empty results are valid only for a legitimate empty response).
- bound timeouts and concurrency, avoid creating a new `URLSession` for every keystroke. A single reusable client per workspace is preferred.
- do not introduce global mutable static clients or `@unchecked Sendable` without documenting a rigorous reason.
- do not add API keys, secrets or authentication tokens.

Required transport unit tests: URL encode exact Hebrew reference; path+query encoding; cancellation; HTTP failure; malformed JSON; non-network deterministic fixtures.

---

## 6. Task D — Port complete Sefaria capabilities without Pinkha SQLite

Implement the following concrete providers; each must expose actual working asynchronous APIs (not TODOs/mocks masquerading as production):

### D1. `SefariaReferenceProvider`

- `suggestReferences(query:limit:)` using Sefaria name API; preserve Hebrew partial search and English search.
- `resolveReference(_:)` via `/api/ref/...` returns canonical ID and Hebrew/English label plus all available reference metadata.
- distinguish no results / invalid reference / malformed server response / network failure.
- prefer exact parsed reference when appropriate; preserve source Pinkha's multiple suggestions and broad source handling. No forced normalization by manually parsing Hebrew numerals when Sefaria can resolve it.
- avoid stale search race when UI eventually uses async requests: cancellation checking is required; UI debounce is a T3 concern.

### D2. `SefariaTextProvider : TorahInspectorCore.TextProvider`

- port `/api/v3/texts/{reference}` with `version`, `fill_in_missing_segments`, `return_format` query and reference metadata `/api/ref/{reference}`.
- preserve original fallback when requested Hebrew version is unavailable (source version fallback); **do not silently relabel fallback text as Hebrew**.
- decode document + ordered segments + section ref + previous/next + version/license/direction.
- preserve chapter/daf ranges and identity; do not fabricate verse 1 from a broad reference.
- do not drop rich provider metadata from the returned Core models.
- test: section, segment, missing segments, no available version, version fallback and empty text.

### D3. `SefariaRelationshipProvider : TorahInspectorCore.RelationshipProvider`

- `/api/links/{reference}?with_text=1`: preserve `sourceRef`, Hebrew ref, type/category, English/Hebrew text, collective titles, `versionTitle`, `license`, raw payload.
- `/api/ref-topic-links/{reference}`: parse topic slug and Hebrew/English titles; deduplicate safely.
- **Updated Kit mapping:** `TorahLinkedSource` has `relationshipKind` (`commentary | link`), `semanticCategory`, `canonicalBookID`, `anchorRefs`. Audit actual API response keys; fill these from genuine source metadata when present, otherwise use Kit's documented inference/fallback; never assign invented anchors.
- test `TorahRelationshipGroups`: deterministic grouping by book; commentary and linked sources separate; no duplicates that represent exactly the same source relationship.

### D4. `SefariaTopicProvider`

The original `SefariaTopicProvider` constructor requires `TorahStore` (SQLite) for full topic-index cache. **Do not port `TorahStore` to the Anytype target as user-data storage.** Adapt via `TorahTopicCache` protocol and a lightweight in-memory actor implementation for T1, with configurable TTL.

- `suggestTopics(query:limit:)`: reuse remote Name API as in source, optionally consult local in-memory index when refreshed.
- `resolveTopic(id:)`: `/api/v2/topics/{slug}` with localized labels and raw payload.
- `refreshTopicIndexIfNeeded()`: explicit lazy refresh of `/api/topics?limit=0&minify=1`; ensure no large eager fetch at application startup or on every keystroke.
- Cache is **non-authoritative external metadata only**, isolated from user associations and safe to discard. Its persistence to disk, if ever required, needs a separate future decision. No table `torah_associations` in stage T1.
- test empty query, cache present/missing/expired, refresh failure and retries, duplicate topic IDs, Hebrew local search.

### D5. `SefariaLexicalProvider`

- `suggestWords(prefix:context:)`, `resolveWord(surface:context:)` using `/api/words/{surface}` as in source.
- preserve `lookup_ref` when `TorahLexicalContext.canonicalReference` exists.
- preserve lexicon/headword/description and stable dictionary discriminator; do not use display headword alone as unique ID.
- no results vs malformed HTTP handling; tests for Hebrew diacritics/variant spelling and empty results.

### D6. `TorahSourceHierarchy` + `SefariaHierarchyProvider`

- port provider-neutral `TorahSourceNode`, `TorahSourceHierarchy`, `TorahSourcePath`, `TorahHierarchyProvider` and source tree parse from Sefaria index/TOC.
- remove/replace **all `TorahStore` dependencies** in the provider. Use a lightweight discardable in-memory TOC cache with bounded TTL (or an injected cache protocol) in T1.
- preserve source Pinkha's canonical book IDs, Hebrew/English titles, category hierarchy, compressed paths, and `filtered(byAssociatedKeys: associationGroups:)` pure filtering logic.
- **Do not query Anytype associations in T1.** Tests should pass fake associated keys and counts to the pure hierarchy filtering function; real reverse-index integration occurs at T5.
- ensure filters match exact books/refs safely. Avoid naive prefix false matches when two titles share leading characters.

**Quality rule for all ports:** preserve functionality, not file-by-file line equivalence; do not bring `PinkhaFFI`, Leaf/ViewModel, `CSQLite`, `TorahStore`, `databasePath` or old `TorahInspectorUI` wrappers into `PinkhaKit`. Comment only where adaptation diverges from source behavior.

---

## 7. Task E — Compose a stable provider registry and host-ready Inspector repository

### E1. Provider protocol/registry

Introduce clear provider-facing protocols, compatible with actual `TorahInspectorCore` interfaces:

- New provider protocols for `ReferenceProvider`, `TopicProvider`, `LexicalProvider` (names may be namespaced to prevent a real clash).
- Use the **existing** Core `TextProvider` and `RelationshipProvider`, rather than shadowing them with a copied duplicate.
- `TorahProviderRegistry` maps providers by ID with an explicit default provider, rejects invalid/nonexistent providers, and does not incorrectly route a `providerID` mismatch to the default.
- Use dictionary storage/Sendable safely under Swift 6.

### E2. `AnytypeTorahWorkspace`

This is a **source-access facade**; despite the host-focused name, it MUST NOT import `Services`, `ProtobufMessages`, `AnytypeCore` or call any Anytype storage operations in T1. Build it as a reusable object injected into future host integration. Minimum operations:

```text
suggestReferences(query, limit) -> [ReferenceCandidate]
resolveReference(input) -> ResolvedReference
suggestTopics(query, limit) -> [TopicCandidate]
resolveTopic(id) -> ResolvedTopic
refreshTopicIndexIfNeeded()
suggestWords(query, context) -> [WordCandidate]
resolveWord(surface, context) -> [ResolvedWord]
fetchText(reference, providerID?, request) -> TorahTextDocument
fetchSectionText(reference, providerID?, request) -> TorahTextDocument
links(for reference, providerID?) -> [TorahLinkedSource]
topics(for reference, providerID?) -> [TorahLinkedTopic]
fetchSourceHierarchy(providerID?) -> TorahSourceHierarchy
```

Implement via a **single shared client + registry**, constructor injection for transport, cache and provider configurations, and an explicit `.sefaria` factory. No `TorahWorkspace.application(databasePath:)` from Pinkha and no ad-hoc fresh workspace per row/search request.

`fetchSectionText` should use a tested canonical section resolver; do not casually delete the last colon for sources whose reference shape is more complex. If ambiguous, preserve exact identity and delegate to provider metadata. Preserve `providerID` on every request.

### E3. `TorahInspectorRepositoryFactory`

Create a small `@MainActor` factory/adapter that instantiates the **actual new** `TorahInspectorRepository` with closures connected to this workspace:

```swift
TorahInspectorRepository(
    textFetcher: { reference, providerID in /* source text */ },
    linksFetcher: { reference, providerID in /* source relationships */ },
    topicsFetcher: { reference, providerID in /* linked topics */ },
    notesFetcher: { _ in [] } // T5 will provide an Anytype-backed implementation
)
```

Use correct Swift 6 isolation/capture patterns. Do not use `try?` and return `[]` for all provider errors. If a provider is not registered, throw `TorahError.missingProvider`. Do not create the repository afresh per user keystroke; creation and owner lifetime are T3 responsibilities, but the adapter should be reusable now.

**Important scope distinction:** Core repository `notesFetcher` here is intentionally empty because native Notes in Anytype is a *T5 integration requirement*, not because the current Kit lacks Notes functionality.

Test: instantiate with injected fixture; document fetch, related sources, topics, wrong provider error, concurrency/cancellation, and explicit no-notes behavior. Do **not** implement `onAddNote` or UI callbacks yet.

---

## 8. Task F — Deterministic tests and migration of relevant source cases

Build the complete T1 tests **before** triggering the large iOS CI build. Prefer Swift Testing if that is the local package convention; do not mix frameworks gratuitously. Mocks must not require live HTTP or Anytype account setup.

### Required T1 acceptance matrix

| ID | Test scenario | Minimum expected observation |
|---|---|---|
| T1-01 | Dependency package resolves | Exact SHA `e8aefc...` appears in resolution; `TorahInspectorCore` types imported |
| T1-02 | Hebrew name suggestions | Valid Hebrew partial input returns expected candidate ID in mocked response |
| T1-03 | English suggestions and exact resolve | canonical/labels preserved; no guessed canonical key |
| T1-04 | Broad source classification | Source of book/tractate scale does not pretend to be embeddable verse |
| T1-05 | Hebrew URL/query encoding | Exact percent-encoded API route and query; no malformed path |
| T1-06 | Text V3 section | ordered segments, section, previous/next and license/version/direction |
| T1-07 | Text segment and source fallback | exact segment identity; language fallback correctly reported |
| T1-08 | Text errors | malformed JSON, invalid/empty text, missing API version distinct |
| T1-09 | Relationships | commentary and links parsed with correct rich data, group identity |
| T1-10 | Topic lookup | Slug, Hebrew/English titles, dedup and cache TTL/retry |
| T1-11 | Lexical context | `lookup_ref` sent only with context, word IDs/definitions preserved |
| T1-12 | TOC hierarchy | category tree, compressed path, filtering by fake associated keys |
| T1-13 | Updated library API | section vs segment scope; new notes-enabled repository initializer |
| T1-14 | Repo routing | wrong providerID throws, not silent default fallback |
| T1-15 | In-flight/cancel/error | cancellation honored; no error silently normalized to valid empty list |
| T1-16 | Regression | all existing `PinkhaKit` hierarchy/bootstrap tests still green |
| T1-17 | No forbidden coupling | no SQLite/Leaf/Heart/protobuf/editor runtime imports in new Core files |
| T1-18 | iOS compile integration | existing app/IPA workflow links updated package without app changes |

Adapt reusable data fixtures from Pinkha `SefariaProviderTests.swift`, `TorahInspectorAdapterTests.swift`, `TorahInspectorRepositoryTests.swift`, `TorahKnowledgeHierarchyTests.swift`; **do not simply paste old tests expecting the old Kit API**. Assert public behavior and JSON semantics. Include fixtures for `Genesis 1:1`, `Genesis 1`, `Rosh Hashanah 16b` and at least one cross-book commentary; do not invent API fields that aren't present in the fixture.

### Mandatory baseline regression

Before finalizing, run:

```bash
swift test --package-path Modules/PinkhaKit
```

Record **actual test totals** and failures. No skipping existing hierarchy/bootstrap suites, no commenting out failing tests, and no `try?` that hides failed assertions.

### Deterministic guardrails

- A mock must verify the exact HTTP path/query; returning a fixture for every unknown request is NOT acceptable.
- Test IDs and expected JSON payloads must be checked against source semantics, not invented solely to satisfy tests.
- Verify that fixture/test code never writes user associations or instantiates SQLite.
- Do not claim device sync, quote insertion, Inspector UI or Note editing has been tested in T1.

---

## 9. Task G — Documentation, code provenance and changelog

Copy the two supplied Markdown documents into the target repository without losing content:

```text
docs/pinkha/torah-integration/MASTER_PLAN.md
docs/pinkha/torah-integration/STAGE_01_IMPLEMENTATION.md
```

Create:

**`docs/pinkha/torah-integration/PROGRESS.md`**

- Master version 1.0 and pinned source SHAs.
- Status `T0 = PASS` when verified; `T1 = IN PROGRESS` until all gates actually pass; `T2–T6 = NOT STARTED`, `T7 = DEFERRED`.
- Current working branch/HEAD and links to CI results.
- Table with each T1-01 ... T1-18 scenario and PASS/FAIL/BLOCKED/NOT RUN plus one-line evidence.
- Decisions and observed incompatibilities; follow-up actions needed in T2.

**`docs/pinkha/torah-integration/SOURCE_PORT_LEDGER.md`**

Each adapted file maps original full GitHub source file & source SHA -> new Anytype path, purpose, changes from source (e.g. topic index cache replaces SQLite), test coverage and caveats. Include **Kit revision** and why Core-only is linked in T1.

**`docs/pinkha/PORTED_CODE.md`**

Correct statements claiming non-existent files are already ported. Keep truthful history: mark old entries as "planned in legacy spec" where necessary; mark only actually compiled T1 files as "implemented". Do not rewrite unrelated historical entries.

Never modify `docs/pinkha/UPSTREAM_HOOKS.md` to invent hooks. If T1 remains fully in `Modules/PinkhaKit`, explicitly record **"No new upstream hooks in T1"** in progress report. If a genuinely unavoidable target file outside allowed paths changes, add precise file/diff/gate/merge risk to `UPSTREAM_HOOKS.md`.

---

## 10. Verification protocol and CI budget

**Do NOT run repeated speculative CI cycles.** Finish audit, tests, package resolution and scoped validation before triggering full Anytype build.

### Validation steps in order

1. `git diff --check`; review `git status` and diff file list; ensure no forbidden paths.
2. Swift package resolution (`swift package --package-path Modules/PinkhaKit resolve` if supported by host toolchain), inspect pinned SHA.
3. `swift test --package-path Modules/PinkhaKit` on macOS/toolchain appropriate to the package. Record exact totals, exit status and any compilation errors.
4. Check no dependency drift in tracked `Package.resolved`; only commit generated lockfile entries if this repository tracks them and they reflect the exact dependency.
5. Verify pure Core target compile and no direct runtime/SwiftUI/Anytype Engine coupling.
6. Use existing `.github/workflows/pinkha-tests.yaml` push/PR trigger on a `pinkha/*` branch; record the run URL and result. This workflow uses **macOS 26 / Xcode 26.1** in the inspected repository — do not silently swap it to a hypothetical Xcode 27 configuration.
7. For *actual full iOS app compatibility* use **one deliberate run** of existing `Pinkha Validation & Build` (`.github/workflows/pinkha-validation.yml`) on the T1 branch, only after steps 1–6 are ready. It runs PinkhaKit unit tests, middleware setup, and unsigned Anytype app build. If macOS runner or `MIDDLEWARE_TOKEN` isn't available, mark `T1-18 BLOCKED`, capture exact error, don't invent a successful iOS build.

You are allowed to use a second CI run **only when a concrete code/configuration failure has been root-caused and fixed**, and report why rerun was unavoidable. Do not set up a new workflow, temporary server, service or expensive infrastructure to make the evidence look green.

### Device/build notes

- Building an unsigned IPA does not require distribution provisioning; do NOT touch Apple Developer signing.
- Do not change any `CODE_SIGNING_*`, entitlements, app IDs or team IDs.
- Unit tests may run in package-only context; if the host is Windows/Linux without Apple frameworks, use existing macOS CI instead of forcing UIKit builds locally.
- Do not modify Anytype `EditorPage`, `BlockService`, or `BlockInformationConverter` during T1. The known block-fields issue is explicitly deferred to T4.

### CI decision table

- Tests + iOS build succeed -> `T1 PASS` with links, proceed to handoff but **not to T2 implementation**.
- Tests succeed but iOS build unavailable -> `T1 PARTIAL/BLOCKED`, never mark all gates pass.
- Tests fail -> `T1 FAIL`, fix the demonstrated cause within T1 scope and re-verify; don't “solve” by disabling old tests.
- Upstream branch unexpectedly changed -> record drift and keep pinned baseline; do not merge anything automatically.

---

## 11. Implementation safeguards — do not repeat known Pinkha/Anytype regressions

These rules come from the project's verified code and known editor history; they're relevant even though T1 itself must not touch the editor:

- **Do not edit `BlockInformationConverter` in T1.** It currently creates an empty protobuf field struct on outbound conversion; this is handled by explicit `setFields` / round-trip tests in T4. Document it as an open risk.
- **Do not implement `.inspector` in T1.** Document-scoped host architecture from Pinkha is already proven and must be adapted in T3; global inspector sessions will be rejected in T3.
- **No autofocus changes:** Generic block insert must retain normal focus, Torah quote insert must not focus a read-only quote; T4 test obligation only.
- **No duplicate JSON source truth**: user associations never stored in the T1 topic cache or `TorahInspectorRepository` LRU.
- **No aggressive eager Sefaria indexing at app startup**; stage T1 serves on-demand queries and intentional refresh only.
- **No destructive effects:** no deletion of upstream branches, old files, user data, or existing app capabilities; no reformatting the entire Xcode project.
- **Do not rewrite the editor UI into SwiftUI or build a Web-based Torah Inspector.** Native UI via updated package comes in T3.
- **Don't conflate source selection scope:** `TorahInspectorSelection.scope` distinguishes `.section` and `.segment`; no synthetically invented `preferredSegmentRef` for broad references.
- **Localization UX** is a T3–T6 task; T1 must preserve Hebrew titles, typed identifiers and accurate JSON data.

---

## 12. End-of-stage acceptance and exact handoff report

Do not stop after creating scaffolding or documenting architecture. The **minimum complete T1 deliverable** is a working, tested Sefaria-backed Torah Core module plus an updated, pinned inspector repository factory, committed and pushed in an isolated branch.

### Before committing, prove all these are true

- [ ] Exact base and source SHAs verified; dedicated branch; source repos unchanged.
- [ ] Master and Stage 1 documents are in `docs/pinkha/torah-integration/`.
- [ ] `PinkhaKit` imports `TorahInspectorCore` at pinned updated SHA, not 0.1.0; no vendored kit copy.
- [ ] Source provider model files compile and do not overwrite Anytype association models.
- [ ] Reference, text, relationships, topic, lexical and hierarchy APIs are implemented and tested.
- [ ] There is no `TorahStore`, `CSQLite`, Leaf, UIKit, SwiftUI or Heart dependency in new provider Core code.
- [ ] `AnytypeTorahWorkspace` and `TorahInspectorRepositoryFactory` are reusable, support injection, and route requested provider IDs accurately.
- [ ] Legacy current `PinkhaKit` tests still pass.
- [ ] New tests cover acceptance matrix T1-01 ... T1-18 (mark any impossible environmental test BLOCKED, never silently skipped).
- [ ] Existing iOS build compatibility verified or accurately labeled BLOCKED with evidence.
- [ ] No UI/editor/storage work from T2–T7 or unrelated functionality was touched.
- [ ] Port ledger, progress table, decisions and known risks accurately updated.
- [ ] `git diff --check` clean; commit and push completed to fresh T1 branch.

### Suggested commit (only when tested)

```bash
git add Modules/PinkhaKit docs/pinkha/torah-integration docs/pinkha/PORTED_CODE.md
git commit -m "feat(pinkha): integrate pinned TorahInspector Core and Sefaria providers"
git push -u origin pinkha/torah-integration-t1
```

Adjust `git add` to exact changed paths, and use the actual branch name. Do not stage unrelated pre-existing changes. No merges, force-pushes, release tags or automatic completion of T2.

### Final answer MUST use this evidence-oriented outline

```text
STAGE: T1 — Torah provider/core integration
STATUS: PASS | PARTIAL/BLOCKED | FAIL
BASE: <SHA> (verified against origin/...)
WORKING BRANCH: <branch>
FINAL HEAD: <SHA>
INSPECTORKIT REVISION: <SHA and proof from resolver>

IMPLEMENTED:
- Exact list of production components and paths

FILES CHANGED:
- <path> — <why>

TESTS:
- Existing PinkhaKit: <N passed, N failed, evidence>
- New T1 tests: <N passed, N failed, evidence>
- Acceptance T1-01 ... T1-18: <status per ID>

CI / BUILD:
- Workflow: <exact workflow file>
- Run URL and conclusion: <link/result>
- iOS device app build: PASS/FAIL/BLOCKED, reason

DEVIATIONS / ADRS:
- <none, or fully justified>

KNOWN RISKS / OPEN ITEMS:
- <T2–T7 deferred issues, environment blockers>

NEXT AUTHORIZED ACTION:
- Await review and a separate T2 implementation order.
```

**If blocked:** identify the **exact** command/API/error and what concrete capability is unavailable. Do not say simply "I couldn't"; do not mark mocks as live validation; do not create arbitrary workarounds unrelated to this stage.

---

## 13. Useful direct source URLs for the agent

**Anytype target:**  
<https://github.com/davidpovarsky/anytype-swift/tree/pinkha/hierarchy-home-v1>  
<https://github.com/davidpovarsky/anytype-swift/blob/pinkha/hierarchy-home-v1/Modules/PinkhaKit/Package.swift>  
<https://github.com/davidpovarsky/anytype-swift/blob/pinkha/hierarchy-home-v1/Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahAssociationRepository.swift>

**Pinkha source:**  
<https://github.com/davidpovarsky/pinkha/blob/torah-ux-knowledge-tab/app/Packages/PinkhaTorah/Sources/PinkhaTorahCore/Models.swift>  
<https://github.com/davidpovarsky/pinkha/blob/torah-ux-knowledge-tab/app/Packages/PinkhaTorah/Sources/PinkhaTorahCore/SefariaProviders.swift>  
<https://github.com/davidpovarsky/pinkha/blob/torah-ux-knowledge-tab/app/Packages/PinkhaTorah/Sources/PinkhaTorahCore/SefariaTextRelationships.swift>  
<https://github.com/davidpovarsky/pinkha/blob/torah-ux-knowledge-tab/app/Packages/PinkhaTorah/Sources/PinkhaTorahCore/Hierarchy/SefariaHierarchyProvider.swift>

**Updated Kit:**  
<https://github.com/davidpovarsky/TorahInspectorKit/tree/codex/shared-torah-inspector-maktabah>  
<https://github.com/davidpovarsky/TorahInspectorKit/blob/codex/shared-torah-inspector-maktabah/Package.swift>  
<https://github.com/davidpovarsky/TorahInspectorKit/blob/codex/shared-torah-inspector-maktabah/Sources/TorahInspectorCore/Models.swift>  
<https://github.com/davidpovarsky/TorahInspectorKit/blob/codex/shared-torah-inspector-maktabah/Sources/TorahInspectorCore/ProviderProtocols.swift>  
<https://github.com/davidpovarsky/TorahInspectorKit/blob/codex/shared-torah-inspector-maktabah/Sources/TorahInspectorCore/TorahInspectorRepository.swift>

**Existing target workflows:**  
<https://github.com/davidpovarsky/anytype-swift/blob/pinkha/hierarchy-home-v1/.github/workflows/pinkha-tests.yaml>  
<https://github.com/davidpovarsky/anytype-swift/blob/pinkha/hierarchy-home-v1/.github/workflows/pinkha-validation.yml>

---

**STOP AT THE END OF T1.** Supply your comprehensive execution report, not another proposed implementation phase. Do not proceed with storage, Inspector UI, quote blocks or Knowledge tab until authorized by a new task.
