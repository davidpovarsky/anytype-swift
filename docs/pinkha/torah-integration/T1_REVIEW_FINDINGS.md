# Torah Integration T1 Review Remediation Findings

Date: 2026-10-15

Repository: `davidpovarsky/anytype-swift`

Working branch: `pinkha/torah-integration-t1-hardening`

Original inspected T1 HEAD: `c8d326f637d63318b42d8ab17b7fbd3672142d1b`

CI-validated implementation HEAD: `b1ed4b561f78d2883ae2f7f0d8383cde41b0c821`

This pass is limited to T1 review findings R1-R5. It does not implement T2 storage/conflict policy, UI/editor work, Notes, device UX or later stages.

## Outcome

| Finding | Status | Remediation |
|---|---|---|
| R1 — 1-based ordinals and ranges | PASS | Removed the zero-based adjustment, used both `start_indexes` and `end_indexes`, preserved exact refs, covered same-section gaps and rejected cross-section identity fabrication. |
| R2 — relationship anchors/text | PASS | `anchorRefExpanded` is authoritative when present; nested arrays are flattened in order; HTML is normalized only for display previews while raw JSON is retained. |
| R3 — lexical definitions | PASS | `content.senses` and nested `senses` are recursively decoded under strict limits, with flat legacy definitions retained. |
| R4 — topic identity/localization | PASS | Name API `key`/`title` is decoded without inventing a second locale; Topic v2 `primaryTitle` and primary `titles` supply bilingual resolution. |
| R5 — numbered book titles | PASS | Numeric and Roman ordinal prefixes are recognized and exact hierarchy filtering prevents cross-book matches. |

## Upstream response contracts and implemented decoding

Official sources reviewed:

- Ref: <https://developers.sefaria.org/reference/get-ref>
- Texts v3: <https://developers.sefaria.org/reference/get-v3-texts>
- Links: <https://developers.sefaria.org/reference/get-links>
- Lexicon: <https://developers.sefaria.org/reference/get-words>
- Name: <https://developers.sefaria.org/reference/get-name>
- Topic v2: <https://developers.sefaria.org/reference/get-v2-topics>

The Ref endpoint exposes `normalized`, `depth`, `start_indexes`, `end_indexes`, labels, address types and navigation metadata. A live `Genesis 1:7` response returned `start_indexes: [1, 7]` and `end_indexes: [1, 7]`; the implementation now consumes those values as already 1-based. Texts v3 supplies canonical `ref`/`sectionRef` plus a version text string or nested arrays. Empty entries remain positional gaps before filtering. A cross-section range is rejected when exact per-item refs cannot be derived honestly.

Links responses expose `anchorRefExpanded`, `anchorRef`, `index_title`, `sourceRef`, `he`, `text`, version and license fields. The live canary returned `anchorRefExpanded` and HTML-bearing text. The decoder prefers expanded anchors, supports strings or nested arrays within fixed depth/node/length budgets, strips tags and decodes common/numeric entities for the Core preview, and preserves the untouched serialized row as `rawProviderPayload`.

Lexicon responses expose entries keyed by `headword`, `parent_lexicon`, `rid` and structured `content.senses`; senses may contain further `senses`. The live `/api/words/שלום` canary returned 14 entries and seven top-level senses in its first entry. The decoder recursively collects definitions with maximum depth 8, maximum 512 visited nodes and maximum 4,096 output characters. Flat `definition` and `description` remain compatible.

Name autocomplete returns `completion_objects`; the live Topic query returned `key`, `title`, `type`, `is_primary`, `order` and `topic_pools`, plus root `lang: en`. The decoder uses `key` as stable identity and `title` as `displayTitle`, assigning it only to the evidenced response language (or script when language is absent). Topic v2 returned bilingual `primaryTitle` and localized `titles`; resolution combines both without fabricating translations.

Numbered titles are a local canonical parsing concern. The helper now treats only a first-token numeric `1`-`4` or Roman `I`-`IV` as part of the book title; later numeric tokens still start the section portion.

## Fixture provenance

All added or revised fixtures are minimal sanitized contract cases, not verbatim production snapshots and not user data:

- `reference-resolved.json` mirrors the official Ref field names and 1-based Genesis 1:1 indexes.
- `links.json` models expanded anchors, string/nested text alternatives, empty text, HTML, version/license data and a deliberate duplicate for identity/dedup coverage.
- `lexicon.json` models recursive `content.senses`, HTML/entities, `alt_headwords` and a flat legacy definition.
- `topic-name-en.json` and `topic-name-he.json` model Name `key`/`title` results with explicit response languages.
- `topic-resolved.json` models Topic v2 `primaryTitle` plus primary and alternate entries in `titles`.
- `toc.json` adds minimal numeric/Roman book-title cases.

The field shapes were checked against the official documentation above and a read-only live canary on 2026-10-15. Tests use only injected transports and bundled fixtures; no deterministic test calls the network.

## Verification evidence

- Dependency resolution: PASS; `TorahInspectorKit` remained exactly pinned at `e8aefc626350c8ee0df9daf8d7de7e1dcd0ea418`.
- Portable verification: PASS for Swift parsing of all edited files, Foundation-only typechecking of the new normalizer/reference helper, all fixture JSON, unsafe-pattern scan and `git diff --check`.
- Local package test: BLOCKED by the host, not the code. Windows lacks the pinned dependency's Apple-only `CoreTransferable` module; `apple-doctor` confirmed no Apple SDK.
- Live canary: PASS for Ref, Texts v3, Links, Name, Topic v2 and Lexicon. One initial Links request returned HTTP 504; a bounded retry using `Genesis 1:7` succeeded. Two context-specific word probes returned valid empty arrays; `/api/words/שלום` then supplied the nested lexical shape.
- First hardening CI run: <https://github.com/davidpovarsky/anytype-swift/actions/runs/38790869245> compiled all code and ran 114 tests, with one test-only raw-JSON escaping assertion failure. JSON serialization validly escaped `</b>` as `<\/b>`; the assertion was made serialization-independent without changing production code.
- Authoritative test rerun: <https://github.com/davidpovarsky/anytype-swift/actions/runs/38791289901> — PASS at `b1ed4b561f78d2883ae2f7f0d8383cde41b0c821`; 114 tests in 12 suites, 0 failed. This includes all 109 original tests plus five new hardening tests.
- Registered IPA workflow: <https://github.com/davidpovarsky/anytype-swift/actions/runs/38791605742> — PASS at the same SHA. Unit tests, middleware setup, unsigned iOS device build, packaging and upload all passed.
- Artifact: `Anytype-Hebrew-Unsigned-Device-IPA`, ID `12001423107`, 151,105,287 bytes, retention through 2026-10-22.

## Deviations and residual risks

- The local Windows toolchain cannot authoritatively compile Apple-only dependencies; both macOS/Xcode 26.1 workflows supply that evidence.
- Live Sefaria data is mutable. The canary is supporting evidence only; deterministic fixtures and CI are the regression gate.
- Plain-text normalization is deliberately bounded and lossy for display. Original JSON remains available for diagnostics and future richer rendering.
- No app/UI/editor, `BlockInformationConverter`, project file, dependency pin, workflow, signing, storage or T2-T7 implementation was changed.

## Next authorized action

Await review. Start T2 only under a separate explicit implementation order.
