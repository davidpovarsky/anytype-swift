# T2 native storage upstream research — 2026-10-18

Status: **RESEARCH COMPLETE; T2 REMAINS PARTIAL / BLOCKED**.

This audit was performed against the exact official Heart tag
`v0.51.7-nightly.20261014.1` at
`d98420b1113536afd08cde6de9a5816f6d27ffff`, with semantic comparison to the
old pinned Heart commit
`7e8f5535add386ff5f7573cde47e095c867ab724`. It proposes a minimal sanctioned
extension; it does not implement Heart, protobuf, Swift adapters or T3 UI.

## Result

No current public/native Heart primitive satisfies all T2 requirements at this
tag. In particular, no existing API combines caller-stable operation identity,
same-ID payload collision detection, immutable Space-scoped persistence,
secure indexed target/source reads, and hidden lifecycle semantics.

The defensible next step is a separately approved Heart/protobuf RFC for a
dedicated immutable Torah-operation record host and API. The existing
`AnytypeTorahAssociationRepository` must not be connected until that extension
passes real native middleware Tier C and independent-client Tier D tests.

## Exact source evidence

### Block journal remains rejected

At the audited tag:

- `core/block/editor/state/change.go` `ApplyChangeIgnoreErr` still suppresses
  create/move errors.
- `changeBlockCreate` still unlinks an existing block with the same ID, calls
  `State.Set`, and then `InsertTo`; it does not compare existing and incoming
  payloads.
- `core/block/editor/state/position.go` still returns a missing-target error for
  an invalid insertion anchor. There is no unconditional create fallback.
- `core/block/editor/basic/basic.go` still replaces the complete `Fields`
  value rather than merging concurrent semantic operations.

Therefore the exact previous B04 and B06 failure modes are unchanged:
different payloads under one block ID can silently select the later replay,
and a create against a removed anchor can remain unreachable. Search/undo
visibility and unsafe host cleanup also remain unresolved. A higher version
number is not evidence that B04/B06/B12/B13/B16 passed.

### StoreState is useful machinery, not a ready T2 contract

`core/block/editor/storestate.Builder.Create(collection, id, doc)` accepts an
explicit document ID. `storestate.state.applyCreate` forces the ID and handler,
fills root order and inserts it into the collection. However, `ErrDocExists` is
mapped to `ErrIgnore`; the implementation does not distinguish an identical
retry from a different-payload collision.

`core/block/editor/storestate/modifier.go` retains a last-writer guard defect:
the new modifier calculates field ordering from the incoming value rather than
the stored value, so it does not establish the required deterministic
update/update rule. The proposed immutable design therefore does not rely on
StoreState `Modify` for canonical operation mutation.

`core/block/source/sourceimpl/store_apply.go` contains the full-initial replay
marker introduced by Heart PR #3207 and applies incrementally afterwards.
`PushStoreChange` writes encrypted object-tree changes transactionally with
any-store and stamps ACL head/creator context. It is an internal source method,
not a generic supported RPC/protobuf surface. Existing product handlers add
their own authorization and semantic rules.

### Existing internal hosts are not reusable generic storage

- Chat/discussion uses `chatobject`. Message identity normally derives from a
  change ID, and create handling ignores an existing ID before comparing the
  new payload. Discussion adds chat-specific tombstones and moderation checked
  at a historical ACL head. Importing these types would couple Torah data to
  unrelated product behavior.
- Personal favorites demonstrates caller-explicit IDs, but is tied to the
  account object, a protected internal collection and dedicated APIs. It is not
  a Space-scoped general record service.
- Other internal source hosts have type-specific handlers, indexes, events and
  lifecycle. Their hidden status is not a generic capability grant.

### Ordinary objects do not provide retry-safe identity

The public ordinary object creation RPC does not accept a supported client
object ID or generic idempotency key. Higher-level `CreateObjectRequest` has an
internal `UniqueKey`, but common page creation does not expose it through the
RPC and ordinary pages are minted with random identities. A lost response can
therefore produce a second physical object on retry.

Attaching an undocumented relation named `uniqueKey` to a random page would not
change object identity, atomicity, authorization or lifecycle and is rejected.

### ImportV2 is recovery precedent, not a public record API

`core/block/importv2/persist/persist.go`, `docs/ImportV2Design.md` and object
cache code demonstrate useful patterns: sanctioned types can receive derived
IDs; the importer retains payloads for replay; a run ledger/write-ahead intent
supports recovery; and `ErrTreeExists` is handled only with ownership proof.
Ordinary imported pages, collections and templates still receive minted IDs.

ImportV2 is a privileged migration pipeline with import-specific lifecycle and
recovery. Its internal deterministic IDs do not establish a supported
Space-level client API for immutable records.

### Visibility, deletion and indexing are explicit requirements

Chat objects are not hidden. Account/personal hosts can be hidden because their
dedicated handler and collection define that behavior. Chat-derived types can
participate in export. Whole-object deletion removes the object tree. A new
host therefore needs an explicit hidden/search/backlink/export/undo contract,
retention rule and garbage-collection authority; invisibility cannot be
inferred from an internal type name.

## Upstream issue and PR status checked 2026-10-18

| Item | Status at audit | Relevance |
|---|---|---|
| [Heart #3195](https://github.com/anyproto/anytype-heart/pull/3195) | OPEN; updated 2026-09-02 | Replay fixes and explicit warning that mixed versions can diverge. |
| [Heart #3194](https://github.com/anyproto/anytype-heart/pull/3194) | MERGED 2026-07-07 | Store-state/replay lineage reviewed; not a complete T2 API. |
| [Heart #3207](https://github.com/anyproto/anytype-heart/pull/3207) | MERGED 2026-07-15 | Full-initial StoreState replay marker; incremental semantics remain. |
| [Heart #3311](https://github.com/anyproto/anytype-heart/pull/3311) | MERGED 2026-10-06 | Layout migration makes downgrade claims fixture-dependent. |
| [Heart #3317](https://github.com/anyproto/anytype-heart/pull/3317) | MERGED 2026-10-09 | Native discovery proxy used by Swift DNS-SD work. |
| [Heart #3322](https://github.com/anyproto/anytype-heart/pull/3322) | OPEN; updated 2026-10-11 | Adjacent upstream follow-up; not part of the exact release tag. |
| [Heart #3324](https://github.com/anyproto/anytype-heart/pull/3324) | MERGED 2026-10-12 | Reviewed adjacent release work; no qualifying generic primitive. |
| [Heart #3327](https://github.com/anyproto/anytype-heart/pull/3327) | MERGED at `d98420b…` | Dependency bumps (`any-sync` 0.13.8, `any-store` 1.0.3); no T2 semantic fix. |
| Issues [#3321](https://github.com/anyproto/anytype-heart/issues/3321), [#3253](https://github.com/anyproto/anytype-heart/issues/3253), [#3212](https://github.com/anyproto/anytype-heart/issues/3212), [#3084](https://github.com/anyproto/anytype-heart/issues/3084), [#3254](https://github.com/anyproto/anytype-heart/issues/3254), [#3169](https://github.com/anyproto/anytype-heart/issues/3169), [#3137](https://github.com/anyproto/anytype-heart/issues/3137) | OPEN | Relevant storage/replay/import/index/lifecycle follow-ups; none supplies a released supported contract. |

The exact tag source, rather than issue intent, controls this decision.

## Candidate ranking

| Candidate | Decision | Reason |
|---|---|---|
| A. Scalar JSON detail/field | **REJECT** | Stale whole-value read/modify/write loses concurrent additions. |
| B. One ordinary hidden page per association | **REJECT** | No public stable object ID, atomic same-ID collision contract or dedicated hidden lifecycle. |
| C. Block journal | **REJECT** | B04/B06/B12/B13/B16 still fail or remain unproved at the exact tag. |
| D. Dedicated StoreState-backed immutable records | **RESEARCH BASIS ONLY** | Internal ingredients exist, but collision, handler, RPC, ACL, visibility, index and lifecycle contracts must be added and proved. |
| E. Existing official atomic set/map or deterministic user-object API | **NOT FOUND** | No qualifying released public primitive was found in the audited code. |
| F. Minimal Heart/protobuf extension | **RECOMMENDED PROPOSAL** | Smallest route that can make identity, collision, security and query behavior explicit without abusing another product type. |

## Proposed minimal RFC

### Data model

Create a dedicated, versioned, internal Space-scoped record type,
`TorahOperationRecord`. Records are immutable after creation.

Required fields:

- `spaceId`: authenticated by the open Space/session, not trusted solely from
  payload;
- `operationId`: client-generated UUIDv7/ULID-size opaque bytes, validated for
  canonical encoding and scoped to the Space;
- `payloadVersion` and `operationKind`;
- `target`: typed document/block target with stable native IDs;
- `sourceIdentity`: provider plus canonical source reference for reverse lookup;
- `canonicalPayload`: deterministic canonical bytes, including provenance;
- `payloadHash`: SHA-256 over domain separator, version, Space ID, operation ID
  and canonical payload;
- `authorIdentity`, signed ACL head and creation metadata supplied/verified by
  Heart rather than accepted from the caller;
- causal metadata required by the chosen CRDT fold.

The record's physical native ID must be derived by a sanctioned Heart function
from the dedicated host/type, Space ID and `operationId`. Clients must never
construct arbitrary internal object IDs. Authentication binds the request to
the active Space and grants; knowledge of an ID is not authorization.

### Write API

```text
CreateTorahOperation(
  spaceId,
  target,
  operationId,
  canonicalPayload,
  payloadHash
) -> Created(record) |
     AlreadyExistsSamePayload(record) |
     CollisionDifferentPayload(existingHash) |
     PermissionDenied |
     TargetInvalid |
     UnsupportedVersion
```

Heart must canonicalize/validate the envelope and recompute the hash. In one
native transaction it must authorize the Space and target, derive the host and
record identity, read any existing record, compare canonical bytes/hash, and
either insert or return a typed result. Mapping every `ErrDocExists` to success
is forbidden. A crash after durable commit and before response must make the
retry return `AlreadyExistsSamePayload`, never create a second record.

The initial implementation should use StoreState creation only behind a
dedicated handler and avoid generic StoreState modification. If the existing
create layer cannot atomically compare an existing record, the extension must
add that transaction/handler primitive rather than emulate it with a preflight
search.

### Read APIs and bounded indexes

```text
ListTorahOperations(
  spaceId,
  target,
  cursor,
  limit <= serverMaximum,
  consistencyWatermark?
) -> records, nextCursor?, indexWatermark

FindTorahOperationsBySource(
  spaceId,
  sourceIdentity,
  cursor,
  limit <= serverMaximum,
  consistencyWatermark?
) -> records, nextCursor?, indexWatermark
```

Both are indexed native queries. Neither may scan the Space/library or retain
an unbounded subscription window. Creation returns a durable sequence/change
watermark. Reads expose index progress so a caller can distinguish “not yet
indexed” from “absent” and perform bounded retry/reconciliation. Reconciliation
must be server-bounded and cancelable.

### Conflict semantics

- Adds are immutable operations. Two different operation IDs survive in either
  arrival order (add/add).
- An identical retry is idempotent. Same ID with different canonical bytes is
  a hard collision and never overwrites.
- Removal is a new immutable operation that names the exact observed add IDs.
  The fold is observed-remove/add-wins: a concurrent unobserved add survives.
- Repeated removes are idempotent. Remove/remove order does not matter.
- An update is a new immutable operation naming its predecessor. Concurrent
  updates are retained, not destroyed. The materialized view uses causal order
  and a documented bytewise `operationId` tie-break for deterministic display,
  while retaining all provenance for conflict/UI policy.
- Replaying, snapshotting and compacting in any valid order yields the same
  logical operation set. Compaction cannot discard records needed by live
  causal/tombstone horizons.

### Target and lifecycle rules

Target validity is checked atomically with create against the authenticated
Space. A target moved within the same Space keeps its stable association. If it
is deleted after validation, operation records remain durably readable by ID
and are marked orphaned in the materialized view; they are not silently
deleted. Cross-Space movement is treated as a new target/authorization domain.

Garbage collection requires an explicit retention policy, proof that all
replicas crossed the tombstone horizon, and a user-visible/export-safe recovery
story. Deleting a duplicate manifest or UI host must never delete the canonical
operation collection by incidental ownership.

### Security and invisibility

- Space membership/grants are checked for every write and read.
- Caller-provided author, ACL head or host ID is not trusted.
- The dedicated host/records are excluded by contract from ordinary search,
  backlinks, object lists, editor blocks, undo, templates and normal export.
- Backup/account export must either include a versioned encrypted logical
  stream or explicitly report unsupported data; it must not silently omit user
  associations.
- No chat, discussion, favorites or arbitrary page type is repurposed.
- Subscriptions are Space/target scoped, paged and bounded.

### Compatibility and migration

Older Heart versions that do not understand the dedicated record type must not
open/mutate it as a generic object. Capability negotiation is required before
the Swift adapter enables writes. New Swift with old Heart returns an explicit
unsupported error. Old Swift ignores the feature without deleting data.

Legacy portable v1 data migrates by deterministic operation IDs derived from a
domain-separated hash of the legacy stable association identity, only after a
dry-run verifies collisions. Migration is append-only, resumable with a durable
ledger, and treats same-ID/different-payload as a reportable blocker. No schema
overwrite is permitted. Downgrade is unsupported until a disposable fixture
proves data preservation and must be communicated as such.

The Heart/protobuf change must ship as one reviewed release family: Heart
handler/model, protobuf commands/results/events, generated Swift wrappers,
Services adapter, middleware artifact and iOS CI packaging. The Swift upstream
pin must not be advanced independently.

## Mandatory adversarial proof plan

Every test records operation order, native IDs, canonical payload hashes,
on-disk readback and the test tier.

1. Concurrent A+B adds from the same old state, both delivery orders.
2. Lost response followed by an identical retry; one physical record and typed
   `AlreadyExistsSamePayload`.
3. Same operation ID with different payload/hash; typed collision and unchanged
   first record.
4. Remove/add and remove/remove in both delivery orders, including unobserved
   concurrent add survival.
5. Concurrent updates, deterministic materialized ordering and retained
   provenance.
6. Invalid v1/v2/future-version, corrupt canonical bytes and hash mismatch.
7. Branch/replay/snapshot/compaction permutations and reopen from disk.
8. Target deletion, move, cross-Space move and create/delete race.
9. Revoked membership, insufficient grant and ACL-head race; no partial write.
10. Offline reconnect through two independent Heart processes and controlled
    interleavings.
11. Crash after native commit and before RPC response.
12. Exact-target and reverse-source query under index lag with watermark-based
    bounded reconciliation.
13. 1,000 and 10,000 operation performance, memory, page size and subscription
    bounds.
14. No appearance in normal search, backlinks, editor, undo or ordinary export;
    backup behavior explicitly verified.
15. Mixed old/new Heart and downgrade using disposable backup/restore fixtures.

Tier A is source inference; Tier B is Go state/change testing; Tier C is real
middleware persist/close/reopen in an authorized disposable Space; Tier D is
two independent syncing clients/processes; Tier E is real iOS/device
acceptance. A mocked two-client service is not Tier D, and compilation is not
Tier C.

## Gate and next decision

Current evidence is **C=BLOCKED, D=BLOCKED** because there is no implemented
sanctioned host/API and no authorized disposable two-client fixture. The RFC
needs separate Heart/architecture approval, implementation in its own task,
then all Tier C+D cases above. Until then:

- keep T2 `PARTIAL / BLOCKED`;
- keep B04 and B06 `FAIL`;
- do not implement/connect `AnytypeTorahAssociationRepository`;
- do not start T3;
- do not test a new Heart on a personal or production Space.
