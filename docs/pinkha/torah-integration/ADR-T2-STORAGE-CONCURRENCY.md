# ADR T2 — Torah Association Storage and Concurrency

Date: 2026-10-15

Status: **BLOCKED — no production backend selected**

Decision scope: T2 storage only. This ADR does not authorize Heart, protobuf,
editor, UI, signing, or distribution changes.

## Context and audited baseline

The audit started from the required clean parent
`40f94396d8ebaff84a3b0d04afe50a81c2e67241` on the isolated branch
`pinkha/torah-integration-t2`. `origin/pinkha/torah-integration-t1-hardening`
resolved to the same commit after `git fetch origin`.

The application is pinned by `Libraryfile` to Anytype Heart
`v0.50.21-nightly.20260824.1`, commit
`7e8f5535add386ff5f7573cde47e095c867ab724`. The following behavior was
verified from the Swift client and that exact Heart source rather than inferred
from the fact that Heart uses CRDTs:

- `PinkhaSpaceManifest` schema v1 maps the document association property to a
  concrete Anytype property ID and key. `PinkhaSchemaRoles` names the existing
  block fields `pinkha.torah.associations.v1` and
  `pinkha.torah.sourceQuote.v1`.
- `PropertiesService.updateProperty` calls `ObjectSetDetails` with one detail.
  There is no expected revision, compare-and-swap token, or set-element
  operation in this interface.
- Heart's `ObjectSetDetails` applies the supplied detail values to the current
  local state under the local smart-block lock. That protects one process, but
  a long-text JSON property remains one scalar CRDT value when independent
  clients synchronize.
- `BlockService.setFields` calls `BlockListSetFields` with one complete
  `google.protobuf.Struct`. In Heart
  `core/block/editor/basic/basic.go`, `SetFields` executes
  `b.Model().Fields = fr.Fields`; it replaces the complete fields struct rather
  than merging individual keys. The corresponding Heart unit test asserts
  replacement. A read/merge/write in Swift therefore cannot protect an
  unrelated concurrent field update from another client.
- `ObjectActionsService.createObject` and `Rpc.Object.Create.Request` expose no
  client-supplied object ID or idempotency key. Common page creation reaches
  `CreateTreeObject` when the internal tree unique key is empty. Supplying a
  `uniqueKey` detail is not a supported deterministic-page-create contract:
  `uniqueKey` is a local/derived detail and ordinary page creation does not map
  it to `State.SetUniqueKeyInternal`.
- Native search and subscription are Space-scoped and can request custom keys,
  but search indexing is eventually consistent. The existing hierarchy code
  already retains pending creations because an immediate search can return a
  stale result. A post-create search cannot prove whether a timed-out create
  committed.
- `ObjectShow` can return exact object details, blocks, and object
  restrictions. It is suitable for target/Space/block validation and
  read-back, but it does not add an atomic association mutation primitive.

Relevant repository entry points:

- `Modules/Services/Sources/Services/Properties/PropertiesService.swift`
- `Modules/Services/Sources/Services/BlockService/BlockService.swift`
- `Modules/Services/Sources/Services/ObjectActions/ObjectActionsService.swift`
- `Modules/Services/Sources/Models/Block/BlockInformation/BlockInformationConverter.swift`
- `Anytype/Sources/Pinkha/Bootstrap/PinkhaSpaceManifestStore.swift`
- `Anytype/Sources/Pinkha/Hierarchy/PinkhaHierarchyRepository.swift`

Relevant pinned Heart evidence:

- `core/details.go`
- `core/block/detailservice/service.go`
- `core/block/editor/basic/details.go`
- `core/block/editor/basic/basic.go` (`SetFields`)
- `core/create.go`
- `core/block/object/objectcreator/creator.go`
- `core/block/object/objectcreator/smartblock.go`
- `core/block/object/objectcreator/util.go`

## Candidate A — one JSON value per target

### Document property

Suppose both clients read document payload `[]`:

1. Client A computes `[A]` and writes it to the long-text property.
2. Client B computes `[B]` from the same old payload and writes it to the same
   property.
3. The property is a single value. Convergence can select one serialized value,
   but it cannot reconstruct the association absent from that value. The result
   is `[A]` or `[B]`, not the required union `[A, B]`.

The same failure occurs for remove/add and stale full-snapshot replacement.
An actor, mutex, serial queue, immediate read-back, or blind retry only
coordinates one process. It does not make the read/modify/write atomic across
offline or independent clients.

### Block field

The failure is stronger for block fields. `BlockListSetFields` replaces the
whole struct. If client A writes a Torah key and client B concurrently writes a
different existing field from the same old struct, one complete struct can
replace the other. Even a single-key Torah update must first read and rewrite
all other keys, which creates a lost-update window.

### Decision on candidate A

Rejected as the sole canonical store. Legacy v1 JSON remains readable, but no
T2 code may rewrite it as though it were a conflict-safe database. Unknown,
malformed, or future-version bytes must be left untouched.

## Candidate B — native record per association or operation

Independent synced objects are a plausible union-preserving representation:
different records A and B do not compete for one scalar JSON value, and native
Space permissions/search can scope them. An append-only operation record with
an operation ID and observed-remove tombstones is stronger than physically
deleting the only copy of an association.

The currently exposed creation API nevertheless leaves two unproved and
material gaps:

1. **At-least-once idempotency.** If create commits but the response is lost,
   the client has no object ID. A retry creates another ordinary object. Search
   may still be stale, and `uniqueKey` on a page is not a supported atomic
   uniqueness constraint.
2. **Delete/add convergence and lifecycle.** Deduplicating random-ID records at
   read time does not make a delete complete: a stale query can miss one retry
   duplicate and later resurrect it. Creating hidden pages without a proven
   isolation, query, retention, and cleanup contract would also violate T2's
   no-ghost-object requirement.

Special schema objects such as relations or relation options can have derived
identities, but using them as arbitrary user association records would pollute
the Space schema and rely on lifecycle semantics intended for schema/options.
That is not accepted as an undocumented storage hack.

### Decision on candidate B

Candidate B remains the preferred design family, but it is **not selected for
production** until a sanctioned native API and a two-client proof establish the
required contract. No Anytype host repository adapter is implemented in this
stage while this gate is blocked.

## Required canonical representation once unblocked

The proposed representation is an Anytype-native, Space-scoped, immutable
association-operation record:

- one atomic record contains `operationID`, association ID, target
  `(spaceId, objectId, blockId?)`, kind, role, provider ID, resolved source
  identity, operation kind, observed operation IDs, payload, and provenance;
- records are hidden from normal navigation by a documented native internal
  record/type mechanism, not merely by an optimistic UI filter;
- `operationID` is supplied before the request and atomically unique or maps to
  a deterministic native object identity, so a timed-out retry is the same
  operation rather than a second record;
- removal is an observed-remove tombstone, not destructive deletion of the
  document, quote block, Note, or only historical association record;
- a Space-scoped subscription/query keyed by target drives materialization;
  local pending state may provide read-your-writes but is never canonical;
- reverse lookup uses indexed provider/kind/canonical identity fields rather
  than a full-library scan.

This can be implemented only after one of these facts is established:

1. an existing supported Anytype API accepts a client-generated deterministic
   identity/idempotency key for a non-schema internal object and documents
   create/retry/delete behavior; or
2. an upstream native atomic set/map or internal-record primitive is exposed.

Changing Heart or protobuf to add that primitive is explicitly outside T2.

## Proposed convergence semantics

These semantics are requirements for the eventual backend, not claims about
the current API:

- **add/add, different association IDs:** union; both remain.
- **same-operation retry:** one logical and physical operation, preserving the
  association ID.
- **add/remove:** observed-remove/add-wins. A remove tombstones only add/update
  operations it observed; a genuinely concurrent unobserved add survives.
- **remove/remove:** idempotent union of tombstones.
- **update/update of one association:** retain both immutable operations and
  select a deterministic winner by backend causal order, then mutation ID as a
  tie-breaker. The losing operation remains recoverable/auditable.
- **offline replay:** union all immutable operations; fold them with the same
  rules, independent of arrival order.
- **distinct quote excerpts:** separate association IDs, never semantic-deduped
  solely because canonical source identity is equal.
- **context-reference retry:** semantic identity is unique within one exact
  target; the original stable association ID is retained.

## Target lookup and Space isolation

The eventual query key must include all of `spaceId`, `objectId`, and optional
`blockId`. A bare block ID is never queried globally. Before mutation:

1. load the manifest for the explicit Space and require complete provisioning;
2. call exact `ObjectShow` with the requested object and Space;
3. verify returned object details contain the same Space ID and are neither
   deleted nor archived;
4. reject `.details`/`.blocks` restrictions as applicable;
5. for a block target, find that exact block in the returned object view;
6. keep the explicit request Space even if the application's active Space
   changes.

Normal listing must use one Space-scoped target subscription/query. Search
results cannot be used as immediate commit confirmation; pending records must
remain until the authoritative stream confirms them.

## Manifest and migration policy

No manifest schema extension is committed while the backend is blocked.
Portable codecs continue to read:

- document associations payload v1;
- source quote payload v1;
- both `role: "source_quote"` and `role: "sourceQuote"`.

New association writes canonically encode `sourceQuote`. Rich source quote
provenance uses payload v2 in the portable codec. A future storage backend must
introduce a manifest schema migration only for fields/types it actually
provisions. Migration must be idempotent and must reject a manifest newer than
the client without overwriting it.

Legacy JSON is read-only compatibility data until a safe operation-record
backend exists. Migration must append equivalent records, verify them, and only
then mark migration state; it must never clear the legacy value first.

## Failure, cancellation, retry, and crash recovery

The eventual creation call must be atomic for the complete immutable operation.
Cancellation is checked before starting and propagated after any native call.
Only a request with a stable idempotency key may be retried. A timeout with an
unknown commit result must be reconciled by that key, not by creating an
unrelated record. There are no detached `Task {}` writes.

If schema/type creation is ever required, it is a separately journaled
manifest migration. Partially provisioned schema remains `.inProgress` and is
repaired idempotently. User content, existing fields, and containing objects
are never rollback targets.

## Adversarial probe and measurements

The portable test `TorahAssociationConcurrencyProbeTests` models the exact
single-value schedule:

- both writers read the same empty payload;
- A writes its complete `[A]` snapshot;
- B writes its complete `[B]` snapshot;
- the final scalar contains one item and has lost the other.

That test is a negative proof about read/modify/write algorithms, not a native
sync test. Source inspection additionally proves that block `fields` is a
replace operation in the pinned Heart implementation.

Environment measurement:

- `apple-doctor --json`: Windows, Swift 6.3.3, portable Swift only,
  `apple_sdk_available: false`;
- no local `Dependencies/Middleware` installation;
- existing `AnytypeTests` use injected fakes/stubs and contain no disposable
  real-Heart two-client fixture;
- no authorized disposable Space/account or two-client device harness was
  supplied.

Accordingly, real middleware reopen, offline replay, permissions, and
two-client sync are **BLOCKED**, not PASS.

## Proof plan required to unblock

Using disposable accounts, Spaces, documents, and blocks only:

1. establish two independent Heart clients with sync enabled;
2. create one sanctioned internal record type and verify it never appears in
   normal navigation;
3. run add A/add B from a shared old state, disconnect/reconnect, reopen both
   clients, and observe A+B;
4. drop a create response after server commit and retry the same operation;
   verify one physical/logical operation and stable ID;
5. interleave observed remove A with concurrent add B and then remove/remove;
6. restart both clients and repeat after offline replay;
7. verify Space/read-only restrictions and target deletion between validation
   and mutation;
8. prove indexed target and reverse queries, including stale-index
   reconciliation;
9. for any block-field mirror, interleave an unrelated field update and prove
   neither key is lost.

Only those observed native results can move this ADR to Accepted and authorize
the host adapter.

## Consequences

- No unsafe JSON repository is shipped.
- No speculative hidden-page adapter or block-field writer is shipped.
- T2 portable identity, legacy codecs, provenance, deterministic serialization,
  and adversarial tests can be completed independently.
- T2 overall status remains `PARTIAL/BLOCKED` until real native persistence and
  concurrency evidence exists.

## Supplement — native BlockCreate journal audit (2026-10-18)

The follow-up audit began from exact T2 head
`813f6b6c8824125f5244ff1d4b7db4a3c81b39cd` on the isolated branch
`pinkha/torah-integration-t2-unblock` and re-audited Heart tag
`v0.50.21-nightly.20260824.1`, commit
`7e8f5535add386ff5f7573cde47e095c867ab724`.

### Candidate C — deterministic-ID immutable operation blocks

The candidate is partly real:

- `RpcBlockCreateRequest` carries a complete block model.
- `simple.New` retains any nonempty caller-supplied block ID.
- local `basic.CreateBlock` rejects an ID already in the current state.
- a complete initial block model can carry content and fields in its
  `ChangeBlockCreate`, avoiding a later whole-fields replacement.

Those facts do not provide cross-device collision safety. Tree reconstruction
calls `ApplyChangeIgnoreErr`; `changeBlockCreate` unlinks an existing ID and
uses `State.Set` without comparing payloads. An exact-tag Tier B probe generated
independent branch creates from the same snapshot and rebuilt snapshots after
both replay orders. Identical duplicate payloads collapsed to one reachable
ID, but differing payloads were silently last-replay-wins: A→B retained B and
B→A retained A. No error or conflict was produced. A create targeting an
anchor already removed was likewise made unreachable while the create error
was ignored.

The ordinary RPC path also has no intrinsic invisibility contract. Text block
payloads feed `State.SearchText`, and normal `BlockCreate` reaches
`smartBlock.Apply` with undo history enabled. A fields-carried payload avoids
that one text-index path but is discarded by the existing Swift
`BlockInformationConverter` and remains unproved for editor, preview, export,
backlink, and undo isolation.

### Host decision

No journal host is accepted. The existing Pinkha manifest is an ordinary
hidden page with a server-returned random ID. When discovery sees duplicate
manifests, it chooses one and asynchronously deletes the others. A journal
attached to a losing manifest can therefore be destroyed. A new random-ID
hidden page would retain the ambiguous-create/duplicate-root problem, while
reusing a user document would mutate its tree, index, history, and exportable
content. No sanctioned deterministic internal journal root was found in the
exposed path.

### Decision

Candidate C is **REJECTED / STILL BLOCKED** on the pinned implementation.
Failures B04, B06, B12, B13, and B16 are safety failures; Tier C persistence
and Tier D two-client sync are additionally unavailable. No production adapter
or migration is authorized. The detailed code evidence, B01–B16 matrix, and
probe are in `T2_UNBLOCK_NATIVE_BLOCK_JOURNAL_AUDIT.md` and
`t2-block-journal-probe/`.
