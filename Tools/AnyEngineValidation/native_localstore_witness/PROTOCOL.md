# Native local-store witness candidate

Status: SOURCE_FROZEN_FOR_REVIEW. Compilation and all six new methods are NOT_RUN.

## Exact scope

This candidate captures every decoded document returned by every registered collection
in ONE already initialized native SpaceStorage's AnyStore database, through one
native ReadTx.Context. This is registered collection/decoded-row coverage, not
original SQLite pages/BLOB bytes, every SQLite internal table, semantic object/block
identity census, full Space export, replica completeness, file payload completeness,
production authorization, or migration admission.

The new package is core/pinkha/localstorewitness. Its current native composition is
Heart d98420b1113536afd08cde6de9a5816f6d27ffff plus four additive package files. It does
not import other Heart packages and does not rebuild the existing Heart154 candidate.
The unchanged go.mod/go.sum are byte-equal to that candidate's module pins.

## Capability and current ownership

Capture accepts a package-sealed Capability/Lease, never a path or a caller-selected
database. Both interfaces require package-private marker methods. There is NO public
issuer and NO production issuer. The sole issuer is in the build-tagged native fixture.

That issuer owns a freshly initialized real SpaceStorage, a random private owner nonce,
and a live generation. It issues a lease only for its current owner. Capture checks
current ownership before transaction acquisition, after inventory, during scans, and
after transaction completion; the exact binding cannot change. It matches the actual
storage.Id and the captured state row's Space ID, retains the actual header digest,
and checks the captured ACL/settings root rows and head-row presence.

These checks establish fixture-owned scope only. They do not stand in for account
authorization or lifetime integration in an application. The only accepted authority
is owned-fixture-only-v1. Production authority requests are rejected.

Zero or unqualified Witness values cannot return a complete Receipt or WritePrivate.
The completed flag is set only after iterator, transaction, current-lease and lease-close
checks succeed. Any failure returns nil witness. A completed receipt describes the
capture checkpoint, not perpetual authority after that checkpoint.

## Codec guarantee

Native Doc exposes decoded anyenc.Value, whose lifetime ends at iterator advance.
There is no original raw row-byte API in this interface.

Representation: anyenc-v1.0.3-decoded-value-roundtrip-v1.
For each row and typed row ID:
1. Validate depth/node/output-byte limits before allocating detached encoding.
2. MarshalTo(nil) copies a native decoded-value re-encoding before Next.
3. Parse the detached encoding with a fresh native parser.
4. Compare exact exposed types, string/binary bytes, float64 bits, array order, and
   every ordered object entry including duplicate entries.
5. Reject unsupported or non-round-trippable values. Required top-level id/state
   binding fields must occur exactly once.

Binary versus string, signed zero/NaN bits as exposed by Value, raw UTF-8 spellings,
and entry order are preserved or the row is rejected. No JSON conversion occurs.
Native MarshalTo cannot faithfully encode some constructed values (for example NUL
inside a string); strict round-trip comparison rejects them.

This proves lossless preservation of the values EXPOSED by the pinned native decoder.
It does not prove identity to original storage serialization: that decoder has already
interpreted the SQLite BLOB, including its empty-key sentinel and number format.

The driver decodes a whole row before this package sees it. Candidate limits therefore
bound accepted/detached output, not maximum memory consumed by native decoding.

## Inventory and read-only boundary

Exactly one GetCollectionNames call and one native ReadTx; its exact Context is passed
to every OpenCollection, unfiltered Count and Iter operation. Count and iteration use
the same native snapshot. Every row ID and detached value is retained, duplicate typed
row IDs and ambiguous identity fields rejected, and terminal iterator/Close errors
propagated. Every collection is included. Unknown collection names are captured with
unresolved coverage, including empty collections; none is silently treated as semantic
admission. Known names only classify containers.

Capture does not create/open-creating collections, obtain a write transaction, call
ObjectListExport/ReadDoc, rebuild an index, fetch a file, or access a DB path. It uses
OpenCollection on the existing initialized store only.

Limits: <=64 collections, <=10,000 rows, <=1 MiB re-encoded row, <=16 MiB total row
encoding, depth <=64, <=100,000 value nodes per row, collection-name bytes <=4096.
Limits may be lowered only. Exceeding a limit returns no witness. Encoding additionally
retains typed IDs and framing, so private container size is larger than row-byte count.

## Private and public evidence

WritePrivate emits a deterministic length-framed container including owner nonce,
Space ID, collection names, typed IDs and detached values. Store it only under the
explicit mode-0700 private fixture root, with mode-0600 files. Never publish its bytes,
database contents, keys, native identities, or raw native logs.

Receipt exposes only authority kind, generation, safe counts, SHA-256 values and scope.
Its collection identities are hashes. Native snapshot/identity proof requirements are
always true; hasNativeSourceAdmission and permitsDestinationWrites are always false.

## New execution protocol

Build tag: pinkha_localstore_witness.
Toolchain profile: explicit new Go1.27.4/linux-arm64/glibc, CGO_ENABLED=1,
GOMAXPROCS=1, go -p=1, warm existing module/build caches, GOPROXY=off.
No old test selectors are admitted.

Selected top-level methods:
- TestLocalStoreWitnessNativeConcurrentTransaction
- TestLocalStoreWitnessOwnershipAndCancellation
- TestLocalStoreWitnessLimitsAndNativeBinding
- TestLocalStoreWitnessIteratorAndTransactionFailures
- TestLocalStoreWitnessDecodedEncodingRoundTrip
- TestLocalStoreWitnessUnqualifiedAndPrivateOutput

The main method creates a real native SpaceStorage from actual any-sync account/space
payload APIs in a private disposable store. A read adapter delegates the FIRST
collection inventory to the actual native database, then signals an independent owned
writer goroutine. That writer uses an actual native WriteTx to update StateStorage,
update/insert probe rows, and create one additional collection, then commits before
capture resumes.

The first witness must retain the old state, old rows and old collection inventory.
A direct native StateStorage read must observe the committed new state. A second
capture in a later transaction must observe the new state/rows/collection. The adapter
records exactly one read transaction/inventory and exact native context on all reads.
This is a real native transaction interleaving, not repeated-head/JSON inference.
Both private witnesses are retained; only safe receipts/counters are logged.

Five additional top-level boundary methods contain 15 scoped subcases for current
ownership, cancellation, limits, native binding, iterator/close failures, plus codec
and output checks. Error injections wrap real native reads and are explicitly adapter
controls; they are not counted as additional real concurrency proofs.

Native fixture databases/private witness files are retained after close for audit.
The owned writer is awaited; no process/device/network/account beyond this fresh local
fixture is opened. Default package tests are unaffected without the opt-in build tag.

## Retained exclusions

nativeSnapshotProofRequired=true
nativeIdentityCensusRequired=true
hasNativeSourceAdmission=false
permitsDestinationWrites=false
productionAccountAuthorization=NOT_IMPLEMENTED
fullHeartSemanticMigration=NOT_RUN
filePayloadCensus=NOT_RUN
AppleOrMountedAcceptance=NOT_RUN

Existing Heart154, old staged Any/SDK candidates, original proof bundles, application
fixtures, mounted source pins, shared writer and Asana were not changed.

## Pre-execution source review

Original uncompiled native source 862e98d16b6ae55207a41b53a036d8b7660a189a is retained.
Root found an initializer field-name mismatch and missing explicit InventoryScope.
Commit 74b5f2c844ac3879125888c538d5990af3db3cb8 corrects that single initializer line. Neither version
has been compiled or executed at this checkpoint. Test source is unchanged.
