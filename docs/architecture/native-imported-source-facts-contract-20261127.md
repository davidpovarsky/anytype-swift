# Read original source facts from native immutable Records

## Status and boundary

This is a prepared, unqualified engine adapter. Swift compilation and native
execution are pending. It reads the two existing `heart_source_facts` records
from the already qualified destination migration; it never replays the original
182 operations or constructs replacement records.

The adapter exposes original Heart metadata, block IDs, hierarchy, object types,
relation links and exact source bytes through an ordinary read of the current
native immutable row. These original values remain distinct from current edited
destination content and the destination's signed import event. It cannot
reconstruct the original Heart history tree or supply a missing source account
credential.

## API

`AnyNativeImportedSourceFactsDirectory(plan:mappings:)` validates the saved
plan-to-mapping joins, selects only the explicit `heart_source_facts` part,
requires its owned immutable Records declaration, and validates each embedded
source view against the exact manifest member. Directory entries expose the
original source object ID and the native object, owner Type, dataset and record
addresses. Native mappings remain routing hints until the store verifies them.

`AnyNativeImportedSourceFactsStore(client:workspace:)` provides
`read(sourceObjectID:directory:lease:)`. A successful snapshot carries:

- Original source account, Space, object, witness and manifest identities.
- The complete `AnyHeartNativeSnapshotView`, including original protobuf/JSON
  bytes, all details and unknown fields, block records and hierarchy.
- Original derived values with their source relation key and corresponding
  native property name, without rewriting the values.
- A separately typed destination creation: signed change ID, destination
  author, and destination author-clock seconds.
- Current host generation and engine-start identity, plus the original raw
  native row.

The directory explicitly refuses source admission. Its entries and the
returned snapshot expose no destination-write authority.
`originalHistoryReconstructed` is always false.

## Existing native data contract

| Field | Scope | Meaning |
| --- | --- | --- |
| `sourceObject` | Immutable synced | Exact original Heart object ID |
| `sourceSnapshotBase64` | Immutable synced | Exact captured native protobuf |
| `sourceViewJSON` | Immutable synced | Exact captured JSON projection |
| `sourceSnapshotSHA256` | Immutable synced | Hash of the original protobuf |
| `sourceViewSHA256` | Immutable synced | Hash of the original JSON bytes |
| `sourceDerivedBindingsJSON` | Immutable synced | Original derived values and explicit provenance separation |
| `importedBy` | Native derived | Destination creation signer |
| `importedAt` | Native derived | Destination creation clock |

The reader requires exactly the six ordinary fields and the two existing native
stamps in the schema. The established schema constructor already rejects
non-string or duplicate required entries, mutable fields, forged stamp scope,
and an open additional-properties contract.

Historical bindings must contain exactly the recognized derived keys actually
present in the captured details: `creator`, `createdDate`, `lastModifiedDate`,
and `lastModifiedBy`. Missing, repeated, remapped or changed values are refused.
The original whole view remains available even when it contains other metadata.

## Read sequence and authority

1. Match account and Space byte-for-byte and validate the current host lease.
2. Require current native read membership, then open the original immutable
   migration capability and fetch its native-owned schema.
3. Reconstruct the original intent specification from the plan, schema and
   exact values. The native status response must match its account, Space,
   store, plan, source key and specification digest.
4. Require complete/current commitment, the original mapping fingerprint,
   object, sole record ID and sole signed creation ID.
5. Read the current row through the native read-only query endpoint. Require
   the complete one-record dataset census and exact record identity.
6. Locate the exact uncoalesced native signed creation and its record snapshot.
   Reuse the existing immutable authority and projection validators to bind
   signer, clock and all original source values to that creation.
7. Require a second identical current row and an unchanged current intent
   receipt, then recheck membership and lease before returning.

Every identifier is an individually encoded native path component. A query
POST is a read operation and uses a repeatable lease callback. The adapter
exposes no prepare, commit, PATCH, restore or reauthorization operation.

These checks describe a bounded local observation. They do not claim an atomic
whole-object or whole-Space snapshot, a cross-peer delivery barrier, revocation
of data already copied by a caller, or original Heart source-history authority.

## Planned focused evidence

Three new component methods cover exact retained original bytes/structure,
complete derived-value lists (including each omission), and changed evidence
or invalid mapping refusal. Synthetic parser envelopes are explicitly separate
from native source authority.

One new native method will execute in two fresh OS-offline processes against an
owned exact copy of the retained destination account. It will compare both
current native rows to their signed creation and original capture, refuse a
forged saved fingerprint, refuse a foreign Space and revoked lease, and require
exact cold-process equality. The already qualified 182-operation migration,
original accounts and unique evidence will remain unchanged.

No PASS is asserted here until the actual receipts exist.
