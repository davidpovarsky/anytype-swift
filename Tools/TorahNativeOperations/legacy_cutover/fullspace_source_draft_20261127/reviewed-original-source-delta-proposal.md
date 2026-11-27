# Heart full-Space Torah index barrier — source delta for review

Status: proposed engine tranche, not implemented or qualified. This is separate
from the published cutover RPC manifest and the pending Swift client qualification.

## Existing authority and storage

The native Space storage owns HeadStorage and its `heads` collection in the same
`AnyStore()` database (`sync/commonspace/spacestorage/spacestorage.go`). The
per-Space object index is a different database. Ordinary `spaceIndexer.indexBatch`
already commits object details, native Torah projection and indexed head hashes
under one root index transaction. The common fulltext queue is a third concern;
neither its counter nor `LastIndex` proves this barrier.

`HeadStorage.IterateEntries` currently omits `Iterator.Err()` and offers separate
live/deleted filters. The new read will open the existing `heads` collection under
one native ReadTx, enumerate every entry with explicit iterator/error/close checks,
and call the original `HeadStorage.GetEntry(tx.Context(), id)` decoder. It creates
no collection, tree or account. The scan includes queued/deleted status, heads,
common snapshot, derived/parent fields and last-add sequence. It stops with an
explicit incomplete/error result at 10,000 entries or a 16 MiB aggregate witness
budget. No successful prefix is returned.

## Proposed files and responsibilities

| Source | Narrow change |
| --- | --- |
| `core/pinkha_torah_space_index.go` (new) | Account-scoped read-only native handler, using the existing `pinkhaTorahScope` owner and current ACL helpers; H1/index/H2 fencing, typed reasons and deterministic generation. No generated RPC edit in this tranche. |
| `space/spacecore/storage/anystorage/pinkha_heads_snapshot.go` (new) | Bounded direct read of the original heads collection, using the original entry decoder; exact native root-header witnesses and error propagation. |
| `pkg/lib/localstore/objectstore/spaceindex/pinkha_torah_snapshot.go` (new) | Additive exported function accepting the existing Store, checking its native implementation, and reading headsState plus object rows in one read transaction. No Store interface/mock expansion. Resolve the existing native Torah index pointer before opening that transaction. |
| `core/pinkha/torahindex/readiness_snapshot.go` (new) | Reuse the original binding resolver, document classifier, projector and cache integrity implementation against that caller-owned read transaction. Recompute into copies and compare derived fields; never invoke Recover/rebuild or write data. |
| `pkg/lib/localstore/objectstore/spaceindex/pinkha_native_admission.go` (new) | Store a versioned metadata-only native root-type witness together with the exact indexed head hash in headsState, under the existing index transaction. No private content or new database. |
| `core/indexer/spaceindexer.go` plus an additive helper | In the existing explicit non-indexable branch, admit only a validated native header for the allowlisted non-document roots. Unknown/missing types retain an incomplete result. The existing batch/root transaction writes the hash and exclusion witness together. |
| `core/block/editor/smartblock/smartblock.go` and `pinkha_torah_operations.go` | Carry a copied immutable native header in DocInfo for the explicit non-document branch; add a metadata-only private-root index hook that uses the existing indexer queue without document initialization/Apply/fulltext. |
| `core/block/editor/torahops/{native_host,cutover_native_host}.go` and `torahopsobject/{object,cutover_object}.go` | Optional production-owned admission callback after successful native replay/projection commit, including initial open, actual SyncTree Update/Rebuild and local append. The registered native object adapter supplies the hook. Native failures retain the original committed receipt; index failure is joined, never reported as zero effect or retried automatically. Independent native host fixtures may omit the callback. |

The admission callback must run only after the projection transaction has ended.
It copies the actual held tree header and heads, then follows the same existing
tree-to-indexer order as ordinary smartblock indexing. The indexer must not load a
tree or acquire an ACL lock while its index transaction is open. Header validation
and immutable witness creation happen before queue admission; the transaction
only persists those already validated bytes. The readiness reader holds neither
a native head iterator nor ACL lock while taking the index transaction.

The adapter captures the original account-run owner, exact Space and concrete
Space index instance when it is registered. A callback never looks up whichever
account or global index happens to be active later. Retired work refuses admission
to that captured index. Queue acceptance is not an index-commit acknowledgement:
the barrier remains incomplete until the matching heads and witness actually
commit together. If the native write has already committed, any callback failure
keeps its exact original durable receipt and propagates the joined failure through
the existing RPC/byte contract; it neither clears the effect nor requests replay.

## Non-document roots and deletion

Original `SmartBlockType.Indexable()` intentionally excludes Date, AccountOld,
Notification, Devices, and the two private Torah StoreState roots. MissingObject
is also non-indexable but is **not** an admissible exclusion. Virtual ID-based
objects with no native tree do not fabricate an authoritative head entry.

An exclusion requires all of: an explicit allowlisted native root kind, original
root-type/Space validation, matching root ID and header digest, a versioned stored
admission, and exact equality between its indexed head hash and H1/H2. A stale
mutable `type` property or empty `CommonSnapshot` grants nothing. The two private
Torah roots additionally use their existing deterministic Space-root validators.
The original ACL/settings trees remain identified by the Space storage's exact
native IDs, never by a display name or inferred missing snapshot.

Deletion uses a versioned admission written in the same original index deletion
transaction as its tombstone. It binds the exact Space/object/root identity and
the authoritative terminal deletion entry, including deletion generation or
sequence, last-add sequence, heads and native deletion status. `isDeleted=true`
with an absent headsState row alone is insufficient: an old tombstone must not
qualify a later incarnation, restored old state, or new native head. Root/header
identity is captured before destructive removal; if the original pipeline has
already discarded it, the barrier remains incomplete until an authoritative
existing deletion receipt can bind the generation. It never fabricates that
proof from missing data.

For a terminal deleted entry the index must contain the exact matching admission
and ID/Space tombstone, no canonical/derived document projection, and no live
indexed-head value. A queued deletion is incomplete until native deletion
finishes. A missing row or old admission is incomplete. Any index transaction
rollback preserves incompleteness; stale-tombstone, rollback, resurrection/new-head
and deletion-sequence ABA cases are explicit negative gates. Native deletion may
be irreversible, but that invariant is not assumed from an index row's absence.

Home/Archive link-derived flags also require the original `lr` reconcile marker
to match the authoritative Home/Archive heads with the original `HashIds`
algorithm. A document's unchanged own heads cannot prove a separately changed
archive tree has been applied. These native reconcile witnesses enter the same
bounded index snapshot and generation; no new duplicate archive index is added.

## Read sequence and proof

1. Bind the current native account/run scope and exact Space/canonical key. Obtain
   the already initialized index instance before a DB read transaction. Check
   current ACL read permission and capture its head token.
2. Read H1, including all live/deleted entries and native root proofs. Close its
   iterator and native transaction before entering the index database.
3. In one index ReadTx, capture bounded headsState and object rows. Every live
   non-protocol entry must first match its indexed head hash, before classification
   can exclude it. Then validate exclusion proof or the current canonical binding
   and projection. Eligible supported empty payloads require the same explicit
   derived readiness/version/cache proof as nonempty payloads. Unsupported,
   malformed, unknown, absent, partial or mismatched data remains incomplete.
4. Close the index transaction, read H2, then recheck current native ACL and account
   owner. H1/H2 must match exactly, including deletion and sequence fields, and ACL
   token/scope must be unchanged. Private witness data is discarded on a failed
   authority fence.
5. Hash a domain/version frame containing exact Space/key/schema binding, current
   native run identity, ACL token, sorted head witnesses, index/exclusion/deletion
   witnesses and derived projection proofs. Reuse the original sorted-head SHA
   algorithm; no timestamp-derived generation. Return only the bounded readiness
   contract, counts and typed reasons.

This proves one current local native snapshot. It does not prove other-peer
convergence or a complete/truncation-free caller query. Wave2 must require matching
complete generations before and after its bounded related query and independently
prove query coverage. No read starts indexing, creates roots or repairs data.

## Required qualification before integration

Use actual signed native objects and the production indexer: ready existing data;
new signed/unindexed object blocks completeness; real index completion restores it
and changes generation; canonical content/type/archive/delete transitions; explicit
empty versus unsupported projection; known non-document admission and unknown-root
refusal; cold process rebuilding with no stale readiness inheritance; current ACL
revocation withholding delivery. Inject iterator failure and transaction rollback
to prove no prefix/partial admission. Exercise local and actual SyncTree remote
updates of private roots, and preserve committed cutover receipts when the index
hook fails. Existing source-qualified evidence remains retained under its original
scope. No Apple build or unrelated app edits are part of this tranche.
