# Any engine port: preservation and acceptance plan

Status: implementation in progress. No whole-app parity assertion.

Source authority: 586c98bcc17dee425664224e508fc0e8df277678 on codex/chatgpt-wave15-hanlin-consumer-20261119.

## Architectural boundaries

Keep PinkhaKit portable models/codecs, hierarchy and Sefaria providers. Replace engine adapters instead of transplanting Heart registration patches and protobuf hooks.

Preserve NFC identity, context dedup, separate quote instances and unknown fields at envelope/record/item levels. Source provenance must not be invented.

At the pinned baseline, association storage was explicitly single-active-writer and the T2 immutable candidate was capability-OFF. The isolated native port uses a separately versioned guarded claim contract; its completed and pending gates are recorded in CAPABILITY_STATUS.md. Expanded T5 has a build flag and exact runtime gate. Native Source/Topic/Word properties already exist, with read-only canonical derivation and native filtering; generic backlinks do not replace them.

## Whole-session ownership

TorahEditorSession constructs the Heart repository directly while notes, hierarchy, editor, properties and Hanlin use Heart services. Switching only association persistence splits one document across engines. Use an explicit Any workspace with owned account/Space/object mappings; port all writes together. No automatic Heart fallback after a partial Any write. Preserve original user data.

## Stages

1. Pin sources/dependencies/artifacts and preserve existing work.
2. Verify build and released Any runtime with disposable data; record blockers.
3. Implement isolated Any client and immutable operation repository.
4. Bridge actual PinkhaKit types and non-destructive migration with original fixtures.
5. Port whole host composition: bootstrap, hierarchy, editor, notes, quotes, properties and Hanlin.
6. Real runtime persistence, reopen, two-client/offline/ACL and uncertain-write tests.
7. Source-bound iOS build, simulator acceptance, physical iPad and migration rehearsal.
8. Update Asana after each stage; close only accepted requirements.

## Capability matrix

| ID | Capability | Baseline | Adaptation |
|---|---|---|---|
| BOOT-01 | Space-local schema and role manifest | SOURCE_PRESENT_ACCEPTANCE_NOT_REVALIDATED | Use a pinned Any bundle and explicit per-Space binding instead of Heart property/type/template RPC; retain version validation. |
| BOOT-02 | Bootstrap cancellation and account lifecycle | SOURCE_PRESENT_ACCEPTANCE_NOT_REVALIDATED | Keep app lifetime ownership and drain bootstrap before logout; independent Any account state. |
| HIER-01 | Folders, books, documents and explicit hierarchy | SOURCE_PRESENT_ACCEPTANCE_NOT_REVALIDATED | Reuse hierarchy model; query explicit Any parent relation, not backlinks. |
| HIER-02 | Ordering, cycle prevention and safe folder deletion | SOURCE_PRESENT_ACCEPTANCE_NOT_REVALIDATED | Retain rank/rebalance/reparent plans, translate persistence. |
| HIER-03 | Optimistic reconciliation and live hierarchy | SOURCE_PRESENT_ACCEPTANCE_NOT_REVALIDATED | Use Any atomic snapshot/subscription plus optimistic acknowledgements. |
| ASSOC-01 | Document/block canonical item CRUD | SOURCE_PRESENT_ACCEPTANCE_NOT_REVALIDATED | Use actual domain models and immutable Any operations, keeping item-level repository API. |
| ASSOC-02 | Semantic identity and separate quote instances | SOURCE_PRESENT_ACCEPTANCE_NOT_REVALIDATED | Reuse NFC/UTF8 length-prefixed identity; context dedup and distinct stable quote IDs. |
| ASSOC-03 | Lossless codecs, unknown fields and provenance | SOURCE_PRESENT_ACCEPTANCE_NOT_REVALIDATED | Preserve original bytes and envelope/record/item unknown fields in migration; never invent metadata. |
| ASSOC-04 | Authorization, readback and uncertain writes | ACTIVE_SINGLE_WRITER_MULTI_CLIENT_UNPROVEN | Replace single scalar JSON storage while retaining post-await authorization, stable identities and explicit uncertain/conflict states. |
| T2-01 | Immutable operations and retry/collision retention | CANDIDATE_APP_CAPABILITY_OFF | Translate semantics into Any records; Heart registration patches are obsolete. |
| T2-02 | Observed remove and concurrent replacements | CANDIDATE_APP_CAPABILITY_OFF | Immutable observed claim IDs and multiple live successors; no scalar LWW replacement. |
| T2-03 | Native signer/ACL and commit fence | CANDIDATE_APP_CAPABILITY_OFF | Verify Any native creator/ACL and target authority; caller-provided author not proof. |
| T2-04 | Real two-client offline, reopen and crash proof | NOT_PORTED_NOT_RUN | Port adversarial scenarios to native Any sync processes; reducer/mock tests cannot prove sync. |
| T2-05 | Cancellation during target loading | CANDIDATE_APP_CAPABILITY_OFF | Carry deadline/cancellation into Any target validation. |
| PROP-01 | Native Source/Topic/Word indexed properties | NATIVE_DERIVED_PRESENT_DEVICE_QA_OPEN | Derive only document context links; exclude blocks, sourceQuote, internal notes, templates/deleted/archived. Use real indexed Any records where custom property secondary indexes absent. |
| PROP-02 | Rebuildable projection and stale cache detection | NATIVE_DERIVED_PRESENT_DEVICE_QA_OPEN | Rebuild from claims, pin generation/hash; do not sync local cache as source. |
| PROP-03 | Universal property picker, hide/attach and Type retention | SOURCE_PRESENT_ACCEPTANCE_NOT_REVALIDATED | Retain ordinary Note/Page/custom Type behavior and read-only fields; explicitly translate Any type/collection rules. |
| PROP-04 | Import/export canonical versus local fields | SOURCE_PRESENT_ACCEPTANCE_NOT_REVALIDATED | Explicit migration filtering, no database copying; keep canonical metadata. |
| PROVIDER-01 | Sefaria canonical references and hierarchy | SOURCE_PRESENT_ACCEPTANCE_NOT_REVALIDATED | Reuse providers; Any URI is not canonical Torah normalization. |
| PROVIDER-02 | Texts, commentaries and source metadata | SOURCE_PRESENT_ACCEPTANCE_NOT_REVALIDATED | Keep provider and version/license/raw payload behavior. |
| PROVIDER-03 | Topics, words and registry | SOURCE_PRESENT_ACCEPTANCE_NOT_REVALIDATED | Keep provider registry and locale-specific caches. |
| PROVIDER-04 | HTTP retry/cancellation and metrics | SOURCE_PRESENT_ACCEPTANCE_NOT_REVALIDATED | Preserve bounded retry, Retry-After cap and cancellation. |
| INSPECT-01 | Native Inspector, search and request fencing | SOURCE_PRESENT_BROAD_DEVICE_QA_OPEN | Retain Kit native UI; use one Any-owned session for all editor actions. |
| QUOTE-01 | Quote/drop insertion, focus and provenance | SOURCE_PRESENT_BROAD_DEVICE_QA_OPEN | Translate editor record insertion while preserving quote data; Markdown append alone is insufficient. |
| EDITOR-01 | Editor selection, focus and native ownership | SOURCE_PRESENT_ACCEPTANCE_OPEN | Preserve UIKit/SwiftUI behavior and translate whole editor service/undo transactions. |
| EDITOR-02 | Captured offsets versus durable semantic anchors | DURABLE_TEXT_ANCHORS_NOT_IMPLEMENTED | Preserve UTF16 offsets and excerpt; never call them edit-stable anchors. |
| RTL-01 | Direction and explicit alignment persistence | SOURCE_PRESENT_ACCEPTANCE_NOT_REVALIDATED | Reuse direction policy; Any marker write must preserve unrelated fields. |
| RTL-02 | Navigation direction and leading markers | SOURCE_PRESENT_ACCEPTANCE_NOT_REVALIDATED | Keep native gestures/markers independent from engine. |
| T5-01 | Native note creation and recovery | SOURCE_PRESENT_CRASH_IDEMPOTENCY_LIMITED | Replace every create/link/block callback with Any; retain recovery and add durable receipt for crash-safe retries. |
| T5-02 | Space-wide related documents | SOURCE_PRESENT_ACCEPTANCE_NOT_REVALIDATED | Query indexed canonical records; generic capped backlinks insufficient. |
| T5-03 | Expanded block/quote lookup with capability gate | DEFAULT_BUILD_CAPABILITY_UNAVAILABLE | Any version/schema capability gate and indexed target validation. |
| AI-01 | Canonical Hanlin SDK and presentation | SOURCE_PRESENT_ACCEPTANCE_NOT_REVALIDATED | Keep canonical Hanlin packages; Any storage does not replace Hanlin. |
| AI-02 | Consent for document/selected-text reads | SOURCE_PRESENT_ACCEPTANCE_NOT_REVALIDATED | Any-native snapshot reads retain consent, coverage and limits. |
| AI-03 | Revocation, account and navigation receipts | SOURCE_PRESENT_ACCEPTANCE_NOT_REVALIDATED | Retain all authority invalidation; localhost API alone is not caller authorization. |
| AI-04 | Create-page preflight, durable journal and receipts | SOURCE_PRESENT_ACCEPTANCE_NOT_REVALIDATED | Port native create adapter only with exact reconciliation semantics; retain protected metadata and explicit uncertain state. |
| MIG-01 | Non-destructive identity map and migration | NOT_IMPLEMENTED | Explicit dry-run, complete Space/object/block mapping and receipts. Any v0.4-to-v0.5 upgrade is not Heart migration. |
| APP-01 | Complete original application parity | WHOLE_APP_PORT_NOT_IMPLEMENTED | Port account/Spaces/objects/editor/templates/sets/search/files/history/sync composition together; repository adapter alone insufficient. |
| OPS-01 | Source-bound validation and evidence | PORT_VALIDATION_NOT_RUN | Separate Any module/integration/runtime/whole-app lanes with exact tested SHA. |

CAPABILITY_INVENTORY.json contains exact source blob hashes, invariants and tests. SOURCE_INVENTORY.json records scoped file provenance.

## Offshoot review

The latest T2 target cancellation files are identical to baseline. SDK06 simulator protection changes are retained with newer safe journal reopen guards. Do not overwrite the integration with either older worktree.
