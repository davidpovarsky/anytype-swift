# EXECUTION ORDER — Pinkha × Anytype Torah Integration, Stage T2

**Document version:** 1.0 — 2026-10-15  
**Stage:** T2 — Anytype-backed Torah association persistence and concurrency-safe data model  
**Audience:** Autonomous coding agent with access to the local Anytype fork, GitHub and its CI  
**Scope:** Implement *storage, migration, domain codecs and tests only*; no functional UI/editor changes.  
**Status:** Ready for the user to hand to an agent. Merely reading this document does not authorize any code change; the user authorizes T2 by explicitly assigning it.

> **Primary objective:** Build reliable, synced, Space-scoped, object/block-scoped Torah association persistence **on Anytype's own canonical data model**, with no lost concurrent updates. This is **not** a task to replace Heart, invent protobuf block types, or port Pinkha's SQLite database.

---

## 0. Source-of-truth order and absolute prohibitions

Read, in this order:

1. `docs/pinkha/torah-integration/MASTER_PLAN.md` (authoritative scope/gates), `PROGRESS.md`, `SOURCE_PORT_LEDGER.md`, `T1_REVIEW_FINDINGS.md`.
2. `docs/pinkha/ARCHITECTURE.md`, `DATA_MODEL.md`, `SCHEMA.md`, `UPSTREAM_HOOKS.md`.
3. The current source code at the exact SHAs below; **verify rather than assuming** that the repository or API still matches this document.
4. This T2 implementation order. Where a design choice is deliberately unspecified, make an evidence-backed ADR, not an undocumented guess.

**Never:**

- Merge to `develop`, `dev`, `main`, or another product branch, rebase or force-push an established branch, or modify `davidpovarsky/pinkha` / `davidpovarsky/TorahInspectorKit`.
- Modify Heart, its Rust implementation, `anyproto`, protobuf schema/generated protobuf, Anytype's sync engine, or invent an extra database as the canonical data store.
- Store user-authored associations, snippets, notes or quote provenance as the sole truth in SQLite, UserDefaults, a process-local actor/cache, or an in-memory singleton.
- Change the native editor, text input/focus path, Inspector presentation, slash menu, T3/T4 UI, T5 Notes/reverse index, signing, provisioning or distribution behavior.
- Treat an unsigned build or a mock test as proof of real synchronization between two independent Anytype clients.
- Hide errors with `try?`, fake empty arrays, default-space fallbacks, fabricated metadata, or silent retries on unsafe mutations.
- Delete actual user data, clean up other users' objects, or test concurrency against a real personal Space. **Use disposable test Spaces and disposable test objects only.**

Maintain all user-visible operations behind existing Pinkha runtime gating; T2 can add isolated storage code without an editor hook. Avoid unrelated cleanup and large architectural rework.

---

## 1. Immutable baseline and branch discipline

**Repository:** `https://github.com/davidpovarsky/anytype-swift`  
**Verified T1 hardening branch:** `pinkha/torah-integration-t1-hardening`  
**T2 parent commit (must match remote):** `40f94396d8ebaff84a3b0d04afe50a81c2e67241`  
**T1 CI-validated code commit:** `b1ed4b561f78d2883ae2f7f0d8383cde41b0c821`  
**TorahInspectorKit pinned revision:** `e8aefc626350c8ee0df9daf8d7de7e1dcd0ea418`  
**Original Pinkha source commit:** `24e074d5557dba632d36dbb71fda8cf9acb8d3ac`.

Before any edit:

```sh
git status --short
git remote -v
git fetch origin
git rev-parse origin/pinkha/torah-integration-t1-hardening
git show --stat --oneline 40f94396d8ebaff84a3b0d04afe50a81c2e67241
git diff --stat 40f94396d8ebaff84a3b0d04afe50a81c2e67241 origin/pinkha/torah-integration-t1-hardening
```

Do not overwrite a dirty tree. If the remote parent diverges, **STOP and report** instead of silently moving the baseline. With a clean tree, branch **from the pinned commit**, not from `develop`:

```sh
git switch -c pinkha/torah-integration-t2 40f94396d8ebaff84a3b0d04afe50a81c2e67241
```

If that branch already exists, inspect it and continue safely; do not recreate/reset it. Push only `pinkha/torah-integration-t2`. No PR merge or base-branch update.

**Preflight CI provenance:** T1 tests run `38791289901`, IPA run `38791605742`; both succeeded on `b1ed4b56...`; final head's subsequent commit contains documentation only. Preserve all T1 provider code, package pins, fixtures and tests.

---

## 2. Current real architecture — inspect the following files **in full**

### Existing portable domain

- `Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahAssociationModels.swift`
- `Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahAssociationRepository.swift`
- `Modules/PinkhaKit/Sources/PinkhaKit/Schema/PinkhaSchemaRoles.swift`
- `Modules/PinkhaKit/Sources/PinkhaKit/Schema/PinkhaSpaceManifest.swift`
- `Modules/PinkhaKit/Sources/PinkhaKit/Bootstrap/PinkhaSchemaMigrator.swift`
- `Modules/PinkhaKit/Sources/PinkhaKit/Bootstrap/PinkhaSpaceBootstrapEngine.swift`
- `Modules/PinkhaKit/Tests/PinkhaKitTests/` (existing test style and fixtures).

### Already operational Anytype host adapters and schema

- `Anytype/Sources/Pinkha/Bootstrap/PinkhaSpaceBootstrapService.swift`
- `Anytype/Sources/Pinkha/Bootstrap/PinkhaSpaceManifestStore.swift`
- `Anytype/Sources/Pinkha/Bootstrap/PinkhaServiceAdapters.swift`
- `Anytype/Sources/Pinkha/Hierarchy/PinkhaHierarchyMutationService.swift`
- `Anytype/Sources/Pinkha/Hierarchy/PinkhaHierarchyRepository.swift`
- `Anytype/Sources/Pinkha/Hierarchy/PinkhaHierarchySubscriptionConfiguration.swift`
- `Anytype/Sources/Pinkha/Bootstrap/PinkhaRuntime+App.swift`

### Native Services and serialization

- `Modules/Services/Sources/Services/ObjectActions/ObjectActionsServiceProtocol.swift` and `ObjectActionsService.swift`
- `Modules/Services/Sources/Services/Properties/PropertiesServiceProtocol.swift` and `PropertiesService.swift`
- `Modules/Services/Sources/Services/BlockService/BlockServiceProtocol.swift` and `BlockService.swift`
- `Modules/Services/Sources/Models/Block/BlockInformation/BlockInformation.swift`
- `Modules/Services/Sources/Models/Block/BlockInformation/BlockInformationConverter.swift`
- `Modules/Services/Sources/Services/ObjectSubscriptionService/ObjectSubscriptionService.swift`
- Anytype's `ClientCommands.objectShow`, `ClientCommands.objectSetDetails`, `ClientCommands.objectCreate` and `ClientCommands.blockListSetFields` call sites.
- `Anytype.xcodeproj/project.pbxproj` and registered test/IPA workflows (read only by default).

**Verified API entrypoints (not a complete interface):**

- `PropertiesServiceProtocol.updateProperty(objectId:propertyKey:value:)` and `updateProperty(objectId:fields:)` are property writes to a **single** object; there is **no established compare-and-swap transaction** in these interface signatures.
- `ObjectActionsServiceProtocol.createObject(...)`, `updateBundledDetails(contextID:details:)`, `delete(objectIds:)` provide native object creation/update/deletion; prove lifecycle and Space validation before using.
- `BlockServiceProtocol.setFields(objectId:blockId:fields:)` persists fields on an **existing** block. `BlockInformationConverter.convert(information:)` currently creates an empty `Google_Protobuf_Struct()` for new block fields. **Do not rely on metadata set at creation time or modify the editor in T2.**
- `PinkhaSpaceManifest` already maps `documentAssociationsPropertyId`/`Key`. `PinkhaSchemaRoles` defines `pinkha.torahAssociations`, `pinkha.torah.associations.v1`, and `pinkha.torah.sourceQuote.v1`.
- `TorahAssociationRepository` is presently **only a protocol**, with `listDocumentAssociations`, `listBlockAssociations`, `setDocumentAssociations`, `setBlockAssociations`, `removeAssociation`. No host-backed production implementation was present at the T1 baseline.

Review the original Pinkha models at:

- `davidpovarsky/pinkha@24e074d.../app/Packages/PinkhaTorah/Sources/PinkhaTorahCore/Models.swift` — `TorahAssociation`, `TorahSourceQuoteExcerpt`, `TorahSourceQuoteProvenance`, legacy `role: "source_quote"`, provider payload and timestamps.
- `.../TorahStore.swift` — reference for semantic uniqueness and reverse-query behavior **only**, not a storage backend to copy.
- `.../TorahWorkspace.swift` — reference for add/remove semantics and stable source identity; T1 has already adapted its provider-only parts.

### Mandatory audit note

Explain the existing `TorahAssociationRole.sourceQuote` serialized spelling mismatch: current Anytype model uses `"sourceQuote"`, original Pinkha used `"source_quote"`. Preserve decoding of both and use an explicitly chosen canonical spelling on new writes; do not silently drop legacy items.

---

## 3. Mandatory T2-A gate: storage/concurrency investigation **before implementation**

This gate is the most important part of T2. Do not commit a naive JSON-array read-modify-write implementation and announce it as synchronized.

### 3.1 Write a storage ADR before selecting a backend

Create `docs/pinkha/torah-integration/ADR-T2-STORAGE-CONCURRENCY.md` with:

1. Existing manifest/object property and block field conventions, supported Anytype service APIs and their observed semantics.
2. Compare two candidate families:
   - **A.** One versioned JSON document property / per-block JSON field. Analyze *exactly* what happens when two separate clients read the same old JSON and concurrently add different items, remove items or update the same entry. A process-local `actor`, mutex, serial queue, extra read-back, or blind retry is **not** a multi-device lost-update solution.
   - **B.** Native, individually persisted association records/relations/objects (or another **proven** Anytype-native convergent representation). Analyze native visibility, queryability, permissions, deletion/tombstones, concurrent additions and idempotency.
3. State **the chosen canonical representation**, why it avoids lost independent updates, where writes physically live in Anytype, and how legacy v1 document/field data are read without loss.
4. Semantic concurrency model for add/add, add/remove, remove/remove, update/update, and offline replay. Explicitly document add-wins/remove-wins behavior where relevant; don't pretend every conflict is resolvable by one scalar LWW value.
5. How an association record is found efficiently by `(spaceId, objectId, blockId?)`, without cross-Space leaks or relying on a potentially stale search result immediately after mutation.
6. Whether a manifest schema extension is necessary; when and how it is versioned, migrated, and guarded against newer unsupported versions.
7. Failure/retry/cancellation and crash recovery, including partial object creation or half-finished metadata writes.
8. Measurements from a **controlled adversarial probe** using disposable test objects or isolated test clients. Record an exact reproduction of the old JSON lost-update risk if the backend supports it; otherwise formally characterize the API's actual atomic operations.
9. Limitations and a test plan for validating real Heart persistence/sync. A two-actor in-process fake is **not** a two-device sync test.

**Choice guidance:** If a single JSON property or block field cannot demonstrate an atomic/merged concurrent update for distinct associations, it must NOT be the sole canonical conflict-safe store. A native record-per-association approach is a **candidate**, not an assumption: verify that hidden/internal records really sync, can be queried under permissions and can converge correctly, including same-key duplicates and deletions. Do not infer atomicity from filenames or CRDT branding.

### 3.2 Non-negotiable gate

Before implementing an adapter, record the ADR and a compact proof-of-concept test that demonstrates the required concurrent semantics. If the native APIs cannot meet them without changing Heart or forfeiting user data, **do not install an unsafe workaround**. Mark T2 `BLOCKED`, provide the exact missing primitive/evidence and a viable design proposal. It is acceptable to complete pure models/codecs and tests before this blocker; do not claim full T2 PASS.

---

## 4. T2-B portable domain/codec work (`Modules/PinkhaKit`)

Implement/test **pure Swift 6 portable code**. Keep `PinkhaKit` free from `Services`, `Factory`, `SwiftProtobuf`, UIKit/SwiftUI or Heart runtime. Continue using pinned `TorahInspectorCore` only when the provenance model needs its `TorahTextDocument`.

### 4.1 Semantic identity and targets

- Association identity must scope *all* of: `spaceId`, `objectId`, optional `blockId`, kind, role, providerID, and canonicalKey or provider-specific resolved identity. A bare block ID is **never** a globally unique target.
- `labelHe`, `labelEn`, display text and raw query are **not** canonical identifiers.
- Independent notes or deliberately distinct quote excerpts must not be silently collapsed merely because their canonical source is equal. Define whether context references are unique within one target, and which excerpt/source-quote fields distinguish intentional separate instances.
- Two distinct document targets may contain the same source and keep separate association IDs.
- Preserve stable association UUIDs across read, save, load and migration; do not generate new IDs while decoding existing payloads.

### 4.2 Versioned serialization and backward compatibility

- Continue to parse `TorahDocumentAssociationsPayload v1` and `TorahSourceQuotePayload v1` unchanged.
- Decode both `role: "source_quote"` and `role: "sourceQuote"`; encode the selected canonical spelling, and test round trip.
- New schemas may use `v2` only if required by genuinely new data. Give the format an explicit version, upgrade path and reject unsupported future versions *without overwriting them*.
- Preserve `id`, `kind`, `role`, `providerID`, `externalID`, `canonicalKey`, both available localized labels, raw input, original provider payload, creation/update times and unknown legacy metadata as far as the existing source provides them. Do not fabricate provenance fields.
- Support missing legacy optional fields without overwriting valid present values. Reject corrupt JSON clearly; do not confuse malformed data with legitimate zero associations.
- Ensure deterministic serialization for test fixtures (sorted keys and explicit date strategy). No locale-dependent identity comparisons.

### 4.3 Source-quote provenance model (storage only, no insertion UI)

Create or adapt equivalent structures for:

- exact `canonicalRef`, provider identity, raw Sefaria/reference payload;
- `TorahTextDocument` as captured at insertion time, including language, version, license, direction and actual segment/section identities;
- retrieval timestamp and *optional* selected excerpt, segment reference/index, UTF-16 character offset and length where known;
- snapshot text and read-only flag; preserve unknown future fields without destructive truncation where feasible.

Protect snapshot fidelity and provenance: the display normalizer introduced in T1 is **lossy** and must not replace the original captured source text or raw provider response. The actual source-quote *block creation* belongs to T4, not T2.

### 4.4 Repository interface semantics

Preserve compatibility with existing `TorahAssociationRepository` consumers or supply a deliberate, compiling migration. Implement clear, safe operations for **add/upsert, read, update and remove**. The existing `setDocumentAssociations`/`setBlockAssociations` are full-snapshot APIs: do not silently implement them as destructive stale-snapshot overwrites. Either give them proven conflict-safe semantics or make conflicting replacement observable/throwing, while exposing narrowly scoped per-association mutations. Document the replacement-versus-merge policy in the ADR.

Recommended pure source locations (adjust file names to existing repo conventions, not speculative API assumptions):

- `Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahAssociationModels.swift` *(modify narrowly)*.
- `Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahAssociationRepository.swift` *(extend with source-compatible semantics as needed)*.
- `Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahAssociationIdentity.swift` *(new if useful)*.
- `Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahAssociationPayloadCodec.swift` *(new)*.
- `Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahSourceQuoteProvenance.swift` *(new)*.
- `Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahAssociationMergePolicy.swift` *(new only if selected ADR requires it)*.

No copies of `TorahStore.swift`, `CSQLite`, or Pinkha Leaf types.

---

## 5. T2-C Anytype adapter (only after the ADR and adversarial proof)

Host-layer files belong under `Anytype/Sources/Pinkha/Torah/Storage/` or a similarly cohesive `Anytype/Sources/Pinkha/Torah/` subdirectory. Examples of responsibilities:

| Proposed file | Responsibility |
|---|---|
| `AnytypeTorahAssociationRepository.swift` | Implements the portable repository protocol using native Anytype storage |
| `AnytypeTorahAssociationStorage.swift` | Thin, mockable service abstraction over `objectShow`, property details, block fields and/or native record operations actually chosen in ADR |
| `AnytypeTorahAssociationIndex.swift` | Efficient per-Space/per-target lookup and live invalidation if needed; **not** the canonical store |
| `AnytypeTorahAssociationFactory.swift` | Resolves the correct Space manifest and creates a scoped repository; no global mutable current-document pointer |
| `TorahAssociationStorageContractTests.swift` | Tests storage adapter with deterministic fake and, where feasible, a real Anytype middleware test fixture |

These names are **proposals**, not a claim that those files exist. Use accurate project registration. The T2 adapter is part of the **app target** and may use native `Services`, `Factory`, `AnytypeCore`, `ProtobufMessages` and `SwiftProtobuf`; none of those may leak into `Modules/PinkhaKit`.

### Core behavior

1. Resolve a `PinkhaSpaceManifest` for the supplied **explicit** `spaceId`, require it to be fully provisioned and verify the object's actual membership/permission in that Space before any write. Never silently redirect to the active Space.
2. `listDocumentAssociations(objectId:spaceId:)`: return only whole-object associations from authoritative Anytype data, with stable IDs and deterministic order.
3. `listBlockAssociations(objectId:blockId:spaceId:)`: confirm the block exists within that document; return only that block's associations. A deleted/moved block is not a valid old-document target.
4. Individual add/upsert/delete operations: idempotent on retry; unrelated entries never disappear during concurrently interleaved mutations on two clients. No accidental duplicate from at-least-once requests.
5. A delete of an association must **not** delete the containing Anytype document, its source-quote text, or a user-authored Note. Distinguish unlink, delete record, and delete entire document.
6. Persist and load source quote metadata on a pre-existing block via a safe `setFields`-style path and a read-back. **Do not create a quote or modify BlockInformationConverter in T2.** Preserve existing *other* fields when modifying one logical Torah field; never replace the whole fields struct with only the new custom key without verifying native merge semantics.
7. For valid source quotes, enforce permissions and target identity; for unreadable/deleted objects, fail explicitly and leave no unrelated data mutated.
8. Avoid repeated global scans during normal listing. Prove the selected native query/subscription/index supports the expected target lookups and eventual-indexing races; a cache/optimistic pending list may improve read-your-writes but **cannot become canonical**.
9. Ensure `Task` cancellation, error categorization, bounded retries for safe operations, and no hidden `Task {}` fire-and-forget writes to user data.
10. Never create user-visible ghost pages, duplicate schema objects, or hidden objects with unknown lifecycle. If internal record objects are chosen, document how they are isolated from normal navigation, synchronized, recovered, and cleaned up without deleting unrelated content.

### Native API mapping to verify rather than invent

- Document details update: `PropertiesServiceProtocol.updateProperty(...)` or `ObjectActionsServiceProtocol.updateBundledDetails(...)`; pass the **manifest's concrete property key** rather than `PinkhaSchemaRoles.documentAssociationsProperty` as a hardcoded object-details key.
- Exact document/block read: `ClientCommands.objectShow(.with { contextID, objectID, spaceID })`, then inspect `objectView.details` **and** `objectView.blocks` for the relevant requested IDs. Validate returned `spaceId` and lifecycle.
- Pre-existing block mutation: `BlockServiceProtocol.setFields(objectId:blockId:fields:)`; verify `BlockFields` typing and whether the backend merges or replaces keys.
- Native internal record approach, if chosen: investigate `ObjectActionsServiceProtocol.createObject` / `ClientCommands.objectCreate`, actual metadata fields, internal visibility, search/subscriptions and `ObjectActionsServiceProtocol.delete`. Do not assume `uniqueKey` enforces atomic uniqueness across simultaneous offline creates.
- For subscriptions follow existing `PinkhaHierarchyRepository` patterns: listener registration before start, Search/SubscriptionStorage authoritative flow, local pending reconciliation and explicit cancellation; don't call a search reload immediately after creation and discard pending data on its stale result.

**Failure semantics:** On partial failure, either rollback safely **without damaging preexisting data**, or surface an explicit recoverable state and allow deterministic idempotent repair. Do not claim rollback where Anytype has not exposed transactions.

---

## 6. T2-D exact acceptance matrix (must report each ID)

A test listed below is NOT satisfied merely because a function is present. Provide specific assertion evidence, including exact test names and the category of test (unit / mocked adapter / real middleware / two-client sync / device).

| ID | Required invariant |
|---|---|
| T2-01 | T2 starts at the exact pinned hardening HEAD, isolated branch and clean initial diff |
| T2-02 | Storage ADR tests actual native API semantics; rejecting naive JSON lost-update, with proof and selected safe strategy |
| T2-03 | Portable `PinkhaKit` remains Services/Heart/protobuf/SQLite/UI independent |
| T2-04 | Legacy `source_quote` and current `sourceQuote` both decode; canonical encoding is stable |
| T2-05 | Document payload v1 decodes, re-encodes and retains all items/IDs without inventing fields |
| T2-06 | Source quote payload v1 decodes; new provenance codec round-trips raw provider data, source text/version/license/timestamp and excerpt offsets |
| T2-07 | Unknown newer schema/payload version fails safely and is never overwritten; migrations idempotent |
| T2-08 | Per-Space document association add/list/upsert/remove persists after reopen/new repository instance |
| T2-09 | Block-scoped add/list/upsert/remove persists and survives a new repository instance |
| T2-10 | Two different documents with same canonical source keep separate independent associations |
| T2-11 | Same document: two block associations with same canonical source keep distinct targets |
| T2-12 | Semantic dedup is defined and deterministic; same-operation retries create no duplicates; distinct quote excerpts are not silently collapsed |
| T2-13 | **Two independent clients**, both starting from the same old state, concurrently add A and B: eventual persisted result contains **both** |
| T2-14 | Concurrent delete/add and delete/delete semantics converge as described in ADR; no unintended resurrection |
| T2-15 | Stale full-snapshot `setDocumentAssociations` and `setBlockAssociations` cannot silently erase unrelated concurrently inserted entries |
| T2-16 | Offline mutation and reconnection/replay converge, or are explicitly BLOCKED pending a real two-device environment |
| T2-17 | Cross-Space isolation: same object/block-looking IDs cannot cross-read or cross-write; actual Space membership verified |
| T2-18 | Missing/deleted/moved object/block is rejected or handled per explicit orphan policy; never mutates unrelated target |
| T2-19 | Read-only/permission-denied write returns error and leaves canonical data unchanged |
| T2-20 | Existing block metadata fields survive writing/removing Torah fields; persisted fields read-back matches expected values |
| T2-21 | Existing normal Anytype document content, parent/order/navigation metadata and editor blocks remain unchanged by association updates |
| T2-22 | Injected write failure/crash between multi-step operations is recoverable and idempotent; no unexplained orphan data |
| T2-23 | No false-success empty lists on malformed data, backend failure, unknown provider or unsupported migration |
| T2-24 | Reverse lookup requirements of T5 can be supported efficiently and securely without full-library scans on every keystroke (interface/ADR evidence; do not implement UI or full index yet) |
| T2-25 | All existing hierarchy/bootstrap + T1 provider tests remain green |
| T2-26 | Full unsigned device app build / IPA CI succeeds with all new host adapter files included in the target |
| T2-27 | A **real Anytype middleware** read/write/read-after-reopen integration test passes on disposable objects; distinguish from pure mocks |
| T2-28 | Two-actor mock and a real two-client/two-device synced-storage proof are explicitly distinguished in the handoff; report actual results, not assumed equivalence |

**Gate:** T2 PASS requires defensible evidence for the storage guarantees in the master plan, **including actual Anytype persistence and concurrency behavior**. If the available environment cannot prove actual multi-client sync, report `T2 PARTIAL/BLOCKED` and retain proof-ready tests and clear manual test steps; do not downgrade requirements silently. Do not use an individual's live Space for this test.

### Required adversarial scenarios (interleave steps deliberately)

- **A+B:** Client 1 reads empty, Client 2 reads empty, Client 1 adds source A, Client 2 adds source B (both document and same block); reload through fresh clients; expect A+B.
- **Idempotency:** Repeat an add after a simulated request timeout whose server side may already have committed; expect one logical association and preserved ID.
- **A− / B+:** Client 1 removes A while Client 2 adds B; final state reflects documented concurrency rule and retains B.
- **Distinct excerpts:** Same source with two different captured passages within one document; neither excerpt is silently discarded.
- **Target deleted:** A block/document is removed between validation and mutation; no attachment to an unrelated object.
- **Space switch:** A request initiated for Space A completes after app's active Space changes to Space B; still updates A or rejects safely, never B.
- **Legacy migration:** Read v1 `source_quote`/current v1 records, upgrade once, reopen, rerun migrator and verify no duplicate or loss.
- **Malformed/newer:** Corrupt and future-version payloads should produce a distinct actionable error and must remain byte-for-byte unchanged in canonical storage.

---

## 7. T2-E consolidated test and CI procedure

**Do not burn CI credits by discovering missing test coverage one job at a time.** Audit tests and project target membership first, implement a deliberate comprehensive acceptance suite, then run local/static checks before macOS CI.

1. `git diff --check`, targeted lint/parse, validate JSON fixtures and existing `PinkhaKit` tests where toolchain supports them.
2. Check static architectural boundaries: no new `CSQLite`, Leaf/Rust/Heart user-store, no unapproved app editor/UIKit hook, no accidental `try?` on writes.
3. Test the portable codec, semantic key construction, migration, replay/merge policy with deterministic fixtures and mock storage in `Modules/PinkhaKit/Tests/PinkhaKitTests/Torah/Storage/` (or project convention).
4. Add host adapter contract tests using injected native-service abstractions. Existing `AnytypeTests` target is at `AnytypeTests/`; if real host tests cannot be registered reliably, document exactly how the target was inspected and use a minimal reproducible integration harness.
5. Ensure any added Swift files are actually compiled by `Anytype.xcodeproj` (folder-based membership is **not** an assumption). Prove the new adapter's code is referenced by tests or app and is not dead uncompiled source.
6. Run the existing `.github/workflows/pinkha-tests.yaml` on the T2 branch; capture test count/log/run URL/HEAD.
7. After source and test audit, run **one deliberate full build** via registered `.github/workflows/ipa.yaml`, which already tests, sets up middleware, performs unsigned iOS build and uploads an IPA. Avoid the previous 404 issue with `.github/workflows/pinkha-validation.yml` (not registered on the default branch).
8. If any failure occurs, fix the **identified** issue without unrelated rewrites or force-push. Rerun only necessary validation and report all attempts honestly.
9. For real Heart integration/2-device tests, use only authorized disposable test Space infrastructure. If two clients cannot be instantiated, state exactly which gate is BLOCKED and what environment will establish it; never count an all-green Swift unit suite as verified cross-device sync.

CI env may require `MIDDLEWARE_TOKEN` and macOS/Xcode. Do not modify those secrets, signing or workflows merely to bypass environment limitations.

---

## 8. Required source-change ledger and documentation

Create/update:

- `docs/pinkha/torah-integration/ADR-T2-STORAGE-CONCURRENCY.md` — concrete backend choice, proof and conflict semantics.
- `docs/pinkha/torah-integration/STAGE_02_IMPLEMENTATION.md` — copy **this exact assignment** to the repository (verify SHA-256 against supplied local file). If a previous revision exists, preserve it under version control and explain changes.
- `docs/pinkha/torah-integration/SOURCE_PORT_LEDGER.md` — mapped original `TorahAssociation`, excerpt/provenance and `TorahStore` behaviors to new Anytype-native abstractions; explicitly mark SQLite code **not ported**.
- `docs/pinkha/torah-integration/PROGRESS.md` — T2 acceptance matrix/evidence, next stage status, exact SHA and blockers.
- `docs/pinkha/SCHEMA.md` and `DATA_MODEL.md` only to reflect **actual implemented** schema, versioning and storage semantics (never speculative claims).
- `docs/pinkha/UPSTREAM_HOOKS.md` only if any absolutely unavoidable native upstream file was changed; include precise scope and runtime gating.

Use real code, lines and API method signatures in the ADR. Include failed or blocked proof attempts. Do not erase T1 history. If schema migration is required, document a safe rollback/compatibility policy and never overwrite an unknown newer manifest.

---

## 9. T2 completion checklist

- [ ] Exact parent SHA and Kit pin preserved; target branch isolated.
- [ ] Code-level audit, native API concurrency probe and ADR completed **before** adapter implementation.
- [ ] Canonical association data is Anytype-native and persists, not SQLite/local cache.
- [ ] No unproven read-modify-write JSON overwrite path can erase an unrelated source attachment.
- [ ] Object and block scope each have a complete tested CRUD contract.
- [ ] All compatibility/codec/provenance cases retain user data.
- [ ] Space, object, block, permission and deletion policies verified.
- [ ] Two-client adversarial add/add, add/remove and offline/retry results documented with the type of evidence.
- [ ] Real storage read-back/new-session and native sync validation evidenced or clearly BLOCKED.
- [ ] Tests green, iOS unsigned build green, and all added code compiled/registered.
- [ ] Only T2 storage/domain files were changed; no unrelated UI, editor, Heart or Kit edits.
- [ ] `PROGRESS.md`, ledger, schema docs and new ADR updated; no misleading PASS labels.
- [ ] Working branch pushed; no merge to any other branch; clean worktree.

**Do not implement T3.** Document a proposed next action only. If T2 is blocked, do not substitute UI work for missing storage proof.

---

## 10. Exact final handoff report format

Use this structure and provide actual URLs/hashes:

```text
STAGE: T2 — Anytype-backed Torah association storage
STATUS: PASS | PARTIAL/BLOCKED | FAIL
BASE: 40f94396d8ebaff84a3b0d04afe50a81c2e67241
BRANCH: pinkha/torah-integration-t2
FINAL HEAD: <full SHA>
CI-VALIDATED IMPLEMENTATION HEAD: <full SHA>
KIT REVISION: e8aefc626350c8ee0df9daf8d7de7e1dcd0ea418

ADR: <path, summary, chosen backend, why alternate was rejected>
CONCURRENCY PROOF: <two-client schedule, storage backend, exact observed outcomes>
REAL MIDDLEWARE/DEVICE EVIDENCE: <what ran vs what was mocked or BLOCKED>
SCHEMA/MIGRATION: <versions, fields/objects, old-value preservation, backward compatibility>
FILES ADDED/MODIFIED: <paths grouped by domain, host, tests, docs>
ACCEPTANCE: T2-01..T2-28, individual PASS/FAIL/BLOCKED and evidence for each
TESTS: <count, suites, 0 failures?, exact command, environment>
CI: <workflow IDs/URLs, HEAD, build outcome, IPA artifact ID if generated>
CONFLICT/FAILURE RESULTS: <concurrent add/remove, crash, offline, permissions>
DEVIATIONS: <all departures from this assignment>
KNOWN RISKS: <remaining problems and scope>
NEXT AUTHORIZED ACTION: Stop. Await review; no T3 implementation without separate order.
```

**Final status rules:** A `PASS` from CI means that exact CI step passed; it is not automatically a T2-wide PASS. `BLOCKED` means a necessary proof could not be obtained; do not reclassify it as success. `NOT RUN` means it was not executed. A compile-success does not establish data consistency, even when Heart is called a CRDT engine.

---

## 11. Direct source references

- Target hardening branch: <https://github.com/davidpovarsky/anytype-swift/tree/pinkha/torah-integration-t1-hardening>
- Parent commit: <https://github.com/davidpovarsky/anytype-swift/commit/40f94396d8ebaff84a3b0d04afe50a81c2e67241>
- T1 tests: <https://github.com/davidpovarsky/anytype-swift/actions/runs/38791289901>
- T1 IPA: <https://github.com/davidpovarsky/anytype-swift/actions/runs/38791605742>
- Original Pinkha source: <https://github.com/davidpovarsky/pinkha/tree/24e074d5557dba632d36dbb71fda8cf9acb8d3ac>
- Pinned InspectorKit: <https://github.com/davidpovarsky/TorahInspectorKit/tree/e8aefc626350c8ee0df9daf8d7de7e1dcd0ea418>

**END — T2 EXECUTION ORDER v1.0.**
