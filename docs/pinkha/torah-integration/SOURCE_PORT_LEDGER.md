# Torah Integration T1 — Source Port Ledger

Stage T1 was adapted from `davidpovarsky/pinkha` at
`24e074d5557dba632d36dbb71fda8cf9acb8d3ac`. The target baseline is
`davidpovarsky/anytype-swift` at
`e9ae976ca7882ac0b1fa8efb2f75e20618c82718`.

`TorahInspectorCore` is linked as an SPM product from
`davidpovarsky/TorahInspectorKit` at the exact revision
`e8aefc626350c8ee0df9daf8d7de7e1dcd0ea418`. Only Core is linked in T1;
`TorahInspectorUI` belongs to T3. Kit source is not copied or vendored.

| Pinned source | T1 target | Purpose and adaptation | Tests / caveats |
|---|---|---|---|
| `app/Packages/PinkhaTorah/Sources/PinkhaTorahCore/Models.swift` | `Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahProviderModels.swift` | Ports only provider-facing reference/topic/word models. Existing Anytype association models and serialization remain unchanged. | Reference classification, canonical identity and lexical identity tests. |
| `.../ProviderProtocols.swift` | `.../Torah/TorahProviderProtocols.swift`, `TorahProviderRegistry.swift` | Reuses Kit `TextProvider` and `RelationshipProvider`; adds checked routing for references, topics, lexical data and hierarchy. Explicit unknown IDs throw instead of falling back. | Registry validation and wrong-provider bridge tests. |
| `.../SefariaClient.swift` | `.../Torah/Providers/TorahHTTPTransport.swift`, `SefariaClient.swift` | Reusable injected transport, bounded ephemeral session, exact path/query encoding, cancellation preservation and status diagnostics. | Exact Hebrew URL, query, cancellation, malformed JSON and HTTP status tests. |
| `.../SefariaProviders.swift` | `.../Providers/SefariaReferenceProvider.swift` | Preserves exact parsed suggestions, provider keys, canonical resolution metadata and broad-source classification. | Hebrew/English suggestions, resolve, invalid/malformed and broad refs. |
| `.../SefariaProviders.swift` | `.../Providers/SefariaTopicProvider.swift`, `TorahTopicCache.swift` | Replaces `TorahStore` topic index with a discardable actor-backed in-memory cache and explicit TTL refresh. No eager startup fetch. | Cache hit/expiry, failure/retry, dedup, Hebrew local search and remote resolution. |
| `.../SefariaProviders.swift` | `.../Providers/SefariaLexicalProvider.swift` | Removes SQLite coupling; preserves `lookup_ref`, raw entries, lexicon/headword and a stable dictionary discriminator. | Diacritics, contextual URL, ambiguity, stable IDs and empty results. |
| `.../SefariaTextRelationships.swift` | `.../Providers/SefariaTextProvider.swift` | Adapts Texts V3 and reference metadata to the current Kit models, including language fallback without relabeling. | Section, segment, missing entries, fallback, empty version, malformed and HTTP errors. |
| `.../SefariaTextRelationships.swift` | `.../Providers/SefariaRelationshipProvider.swift` | Maps genuine index/anchor fields to current `TorahLinkedSource`; preserves text/version/license/raw payload and topic dedup. | Rich relationships, commentary/link groups, cross-book link and topic tests. |
| `.../TorahReferenceUtil.swift` | `.../Torah/TorahReferenceUtil.swift` | Keeps conservative book/section helpers. Production section loading uses provider-returned `sectionRef` rather than blindly removing a colon. | Book-prefix false-match and workspace section-resolution tests. |
| `.../TorahWorkspace.swift` | `.../Torah/AnytypeTorahWorkspace.swift` | Rewritten as immutable source-access composition with one shared client and injected caches. All SQLite, Leaf, association writes and reverse-index operations are omitted for T1. | Full registry routing and Inspector bridge tests. |
| `.../TorahInspectorRepository+Pinkha.swift` | `.../Torah/TorahInspectorRepositoryFactory.swift` | Uses the current notes-enabled repository initializer. `notesFetcher` intentionally returns `[]` until T5. | Actual `.section`/`.segment` API, document/links/topics, single-flight and no-notes tests. |
| `.../Hierarchy/TorahSourceHierarchy.swift` | `.../Torah/Hierarchy/TorahSourceHierarchy.swift` | Provider-neutral nodes, paths, compression and pure association filtering. Anytype lookup is intentionally absent. | Compression, fake associated counts and exact book matching. |
| `.../Hierarchy/SefariaHierarchyProvider.swift` | `.../Torah/Hierarchy/SefariaHierarchyProvider.swift` | Replaces `TorahStore` TOC persistence with bounded actor-backed in-memory data. | TOC parse/cache, Genesis and Rosh Hashanah filtering, malformed payload. |
| `.../FixtureTorahProvider.swift` and source test fixtures | `Modules/PinkhaKit/Tests/PinkhaKitTests/Torah/` | Behavior and representative data were adapted into deterministic injected-provider and HTTP fixtures. Production fixture providers were not ported. | No live network and no SQLite. |

## Intentional exclusions

- `TorahStore`, `CSQLite`, Leaf identifiers and all user-association persistence.
- `TorahInspectorUI`, host actions, editor hooks, quote insertion and Notes writes.
- Anytype Services, protobuf, Heart, object or block mutations.
- Otzaria, automatic reference detection and reverse-index persistence.

## T1 review remediation ledger (R1-R5)

Review baseline: `c8d326f637d63318b42d8ab17b7fbd3672142d1b`.
CI-validated hardening implementation: `b1ed4b561f78d2883ae2f7f0d8383cde41b0c821`.

| Review item | Target | Contract-preserving adaptation | Deterministic evidence |
|---|---|---|---|
| R1 — Ref ordinals/ranges | `SefariaTextProvider.swift` | Treats Ref API `start_indexes`/`end_indexes` as 1-based, preserves an exact segment ref, maps same-section ranges from the documented start ordinal and rejects cross-section ranges whose flattened items cannot be assigned honest refs. | `reference-resolved.json`; first-segment, exact-segment, gapped same-section range and cross-section refusal tests. |
| R2 — Links | `SefariaRelationshipProvider.swift`, `SefariaJSONText.swift` | Prefers `anchorRefExpanded`; accepts string or nested-array `he`/`text`; produces bounded plain-text previews while retaining raw JSON, version and license fields. | `links.json`; expanded anchors, nested text order, HTML removal, empty array, raw HTML preservation and grouping/dedup tests. |
| R3 — Lexicon | `SefariaLexicalProvider.swift`, `SefariaJSONText.swift` | Recursively walks `content.senses` with strict depth/node/length limits, strips markup/decodes entities and keeps flat legacy `definition`/`description` compatibility. | `lexicon.json`; nested/deeper senses, entity, flat legacy entry, stable IDs and raw `alt_headwords` tests. |
| R4 — Topics | `SefariaTopicProvider.swift`, `TorahProviderModels.swift` | Uses Name API `key` as identity and `title` as the response-language display value without inventing the other locale; Topic v2 combines `primaryTitle` with primary entries in `titles`. | `topic-name-en.json`, `topic-name-he.json`, `topic-resolved.json`; English/Hebrew locale separation and bilingual resolve tests. |
| R5 — Numbered titles | `TorahReferenceUtil.swift` | Recognizes numeric `1`-`4` and Roman `I`-`IV` first-token book prefixes without weakening exact hierarchy matching. | Extended `toc.json`; direct parsing and exact filtering for `1 Samuel`, `2 Kings`, `II Kings` and `4 Maccabees`. |

Fixtures are minimal, sanitized, official-shaped contract cases maintained in the test bundle. They are not production snapshots and contain no user data. Their field shapes were cross-checked on 2026-10-15 against Sefaria's official Ref, Texts v3, Links, Lexicon, Name and Topic v2 documentation and a bounded read-only live canary. Full provenance and endpoint outcomes are recorded in `T1_REVIEW_FINDINGS.md`.

## T2 association/provenance adaptation ledger

T2 starts at the exact T1 hardening head
`40f94396d8ebaff84a3b0d04afe50a81c2e67241` and refers to Pinkha source
`24e074d5557dba632d36dbb71fda8cf9acb8d3ac` for behavior only.

| Pinned Pinkha source | T2 target | Adaptation | Status / evidence |
|---|---|---|---|
| `PinkhaTorahCore/Models.swift` — `TorahAssociation` | `TorahAssociationModels.swift`, `TorahAssociationIdentity.swift` | Retains stable IDs, kind/role/provider/source keys, available labels, raw input/provider payload, optional timestamps and unknown legacy metadata. Accepts legacy `source_quote` but emits canonical `sourceQuote`. Identity is explicitly Space- and object/block-scoped; context semantic duplicates preserve the old ID, while distinct quote IDs remain distinct. | Portable typecheck and deterministic unit tests. |
| `PinkhaTorahCore/Models.swift` — `TorahSourceQuoteExcerpt` / `TorahSourceQuoteProvenance` | `TorahAssociationModels.swift`, `TorahAssociationPayloadCodec.swift` | Adapts capture time, canonical/provider identity, raw reference response, full pinned-Core `TorahTextDocument`, original provider JSON/text/version/license, and UTF-16 excerpt coordinates. No display normalization replaces captured text. | V1 compatibility and V2 lossless round-trip tests. |
| `PinkhaTorahCore/TorahStore.swift` association uniqueness and CRUD behavior | `TorahAssociationRepository.swift`, `TorahAssociationIdentity.swift` | Translates behavior into per-association add/upsert/update/remove contracts and deterministic pure collection policy. Stale full-snapshot setters are source-compatible throwing extensions. | Unit policy and adversarial stale-scalar probe only; not a native persistence claim. |
| `PinkhaTorahCore/TorahStore.swift` reverse association queries | `ADR-T2-STORAGE-CONCURRENCY.md` | Captures the required indexed Space/target/source query shape for T5 without shipping a scan or speculative index. | Design evidence only; adapter blocked. |
| `PinkhaTorahCore/TorahStore.swift`, `CSQLite`, migrations/tables | **Not ported** | SQLite is neither canonical storage nor a shadow source of truth. No local actor/cache/database stores user associations. | Required exclusion. |
| Anytype native details/block fields/create APIs and Heart `v0.50.21-nightly.20260824.1` | `ADR-T2-STORAGE-CONCURRENCY.md`, `TorahAssociationConcurrencyProbeTests` | Audits exact replacement/create semantics, reproduces stale JSON add/add loss, and records the missing atomic/idempotent primitive plus disposable two-client proof plan. | Gate result: `BLOCKED`; no unsafe host adapter created. |

## T2-L single-writer proof ledger — 2026-10-19

| Audited source/contract | T2-L target | Adaptation | Final status / evidence |
|---|---|---|---|
| Legacy `TorahStore` per-association behavior only | `TorahCanonicalAssociations.swift`, `TorahAssociationPayloadCodec.swift` | Encodes versioned document/block records with explicit Space/object/block locations, stable IDs, provider/provenance data and unknown fields. No SQLite code or tables were ported. | Portable/focused tests pass; canonical representation remains limited to one active writer. |
| Existing `TorahAssociationRepository` operation API | `AnytypeTorahAssociationRepository.swift`, `TorahAssociationMutationCoordinator.swift` | Implements individual add/upsert/update/remove through one process-wide per-document queue, authoritative native read/write/readback and stable-ID uncertain-ack reconciliation. Deprecated snapshot replacement remains unavailable. | Repository tests 5/5 PASS in final native run `39306273085`; not registered for production use after gate failure. |
| Native `ObjectShow`, `ObjectSetDetails`, restrictions and block identities | `TorahAssociationNativeStore.swift` | Validates exact Space/object/block identity and uses the hidden Space-scoped property; block fields are read for preservation evidence but never canonical association storage. | Native Phase 1 1/1 PASS; unrelated serialized blocks retained byte-for-byte. |
| Native account/wallet/Space lifecycle | `TorahAssociationNativeMiddlewareProbeTests.swift`, `pinkha_t2l_native_probe.yml` | Disposable local-only wallet/account/Spaces, overlapping mutations, lost acknowledgement, close/reopen, lifecycle switch, all-Space preload, real force termination and separate cold-relaunch readback. | **BLOCKED / FAIL:** final Phase 2 times out inside `AccountSelect` with `space storage missing`; run `39306273085`, artifact `12218585026`. |
| Full multi-client stale scalar behavior | Existing negative stale-client test and this ADR | Retains the known JSON add/add loss as explicit negative evidence rather than redefining it as single-writer success. | Full T2 remains `PARTIAL / BLOCKED`. |

## iPad trial integration ledger — 2026-10-20

| Source contract | Trial target | Adaptation | Status / caveat |
|---|---|---|---|
| `TorahInspectorKit` candidate `01f58803d1a41c9cb51183ec3cc486155a6c90cb` and native demo `55a5035aa50d6b76d7bb29bacc2b76f30d917236` | Kit `TorahInspectorSheetPresenter.swift` at `f78897cfd418844235f0cd358289daa064225db6` | Uses the actual Kit reader and host actions in a system sheet; ports only the native placement/detent presentation pattern. It does not copy a fake reader or overlay panel. | Package tests passed in run `39333954262`; iPadOS 27 UI evidence rerun is `39337576270`. |
| Existing `AnytypeTorahWorkspace` provider facade | `TorahEditorSession.swift`, `TorahSourcesSearchView.swift` | Debounced source/topic/word suggestion and exact provider resolution. Only resolved references become `TorahInspectorSelection`; topic and word identities remain associations. | Production path has no fixture provider. Network/error/empty/loading states remain visible. |
| Existing T2-L native repository and coordinator | Trial document/block association actions | Reconnects only through the per-document experimental session after explicit disposable destination opt-in. Reads are available while writes remain off. | Single active writer only; old run `39306273085` remains FAIL and full T2 remains blocked. |
| Existing Anytype editor block services | `EditorPageViewModel` source insertion and `EditorPageController+DragNDrop` | One quote-block pipeline for button and UTType drop, real fetched text/citation, `setFocus: false`, block-scoped provenance association. Internal block drag remains unchanged. | Quote editing is not strictly locked; physical drag, Undo/Redo and two-window behavior are `USER TEST PENDING`. |
| Existing Anytype object/block services | `AnytypeTorahNotesService.swift` | Creates an actual `.note` object and source line, links it to the selection, opens it through `PageNavigation`, and removes only the association on unlink. | Underlying note deletion is intentionally absent. |
| Existing scalar detail decoding | `TorahAssociationNativePropertyValue` | Distinguishes an absent property from a present non-string protobuf value and fails closed before decode/write. | Focused deterministic test added; original value is never rewritten by this failure path. |

No Pinkha fixture UI, SQLite store, hidden-page journal, production sandbox copy,
mnemonic, credential or wallet bootstrap was ported.
