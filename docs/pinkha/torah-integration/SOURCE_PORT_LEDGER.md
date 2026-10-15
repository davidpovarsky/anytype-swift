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
