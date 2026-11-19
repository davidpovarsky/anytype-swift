# Remaining native boundaries and reviewable handoff

This describes concrete next adapters; it does not claim they are activated.
The preserved application base is 586c98bcc17dee425664224e508fc0e8df277678.
Any API references below are from the inspected v0.5.0 source
88fae2e5ae7d0f46d6707567a3123081faa8de9a.

## Implementation checkpoint (2026-11-19)

The additive Integration package now contains the native association observer,
immutable T5 note plans/flow adapter, native wiki schema/lexid/tree mutation
adapter and document-related lookup/unlink adapter. These are concrete source
implementations, not activation claims. The previously executed 41-test suite
and native integration probe v2 passed; the new 71-test suite and extended
native hierarchy/related probe are being validated separately.

The wiki decision below is now resolved: use system:wiki/v1, scalar parent and
native lexid strings, retaining original tree and cycle-validation behavior.
The parent Host module owns the single durable object/source-line journal.
No new shadow canonical store or undeletable derived note/folder is introduced.
Expanded T5 and computed native property activation remain independent gates.
See Modules/PinkhaAnyIntegration/README.md for the exact scope and bounds.

## Persisted hierarchy (HIER-01, HIER-02, HIER-03)

The old host binds three portable pieces to Heart:

| Old host binding | Existing domain behavior to retain | Native Any binding |
| --- | --- | --- |
| PinkhaHierarchyRepository.start / reload | Complete eligible object set; declared folder/document types; manifest/book exclusions | ObjectsAPI query/subscribe on the installed hierarchy collection, excluding bin/template |
| PinkhaHierarchyReconciler | Pending creates survive stale frames; rename/move/order optimistic state reconciles to native state | Feed atomic object-query snapshots with an account/session generation; keep optimistic state as presentation only |
| PinkhaHierarchyMutationService.createFolder / createWritingDocument | Exact declared type/template, title, parent and append order; immediate native object identity | POST /v1/spaces/:spaceId/objects with type/collections/initialProperties; verify native object readback |
| move / updateOrder / rebalanceSiblings | Cycle prevention, sibling ordering, root move, stable object IDs | One PropertiesAPI.Set patch under the hierarchy collection owner for parent and position |
| deleteFolderSafely | Reparent every direct child before removing the folder; no silent orphaning | Reparent and verify each child, then attach bin collection to the folder; journal partial progress and verify the final tree |

The current native wiki is already an object collection with parentId, pos
and folder properties. Its roots/actual property IDs must be resolved from
the installed bundle and declarations. Docs/28-well-known-bundles.md explains
the binding; docs/03-api.md describes PropertiesAPI.Set and the wiki tree.
A create is an ordinary object filed under the wiki collection. The wiki root
is the collection definition and is not itself a page in the tree.

This port now reuses the native system:wiki/v1 collection. Do not copy Heart's list-valued
parent property workaround into a native single parent reference. Native
lexical position strings may replace sparse Double ranks, but ordering must
remain deterministic, ties must be stable, and source sibling order must be
preserved during migration. The existing PinkhaHierarchyBuilder and mutation
validator can remain the domain layer; a native-position adapter must replace
only rank storage/order calculations that depend on Doubles.

The old scalar-parent compatibility decoder is a **source migration rule**.
It is not a requirement for newly written Any data. Preserve legacy meaning
while producing one unambiguous new parent link.

Required acceptance:

- All registered document kinds, folders and books survive the explicit ID map.
- Root moves, cycle rejection, duplicate ranks/positions and safe deletion work.
- A stale native frame cannot hide a just-created item.
- Partial reparent failure leaves the folder present and produces a recoverable
  receipt; deletion is not declared complete on request dispatch alone.
- Disconnection, permissions and account switch fence both snapshots and writes.

## T5 notes and related documents (T5-01, T5-02, T5-03)

The old AnytypeTorahNotesService composes T5NoteCreationFlow with four actions:
create a native note object, associate its source, add the source line to the
editor, and attach the internal note link to the origin. The reusable flow
already reports an object ID plus a recovery error after a partial write; its
pending-note map is session memory, not a durable cross-process journal.

The new adapter should bind those actions to:

1. ObjectsAPI.Create / POST /v1/spaces/:spaceId/objects with the registered
   note/document type, not a guessed old Heart type ID.
2. AnyTorahAssociationRepository on that new object in the same workspace.
3. POST /v1/spaces/:spaceId/objects/:objectId/editor/:dataset/blocks using the
   declared editor part/storage dataset, followed by native readback.
4. AnyTorahAssociationRepository on the new origin object, retaining the
   existing typed source-selection and internal-link conventions.

Internal origin links carry the note ID in canonicalKey (anytype-note:ID),
externalID and customMetadata.anytypeNoteObjectId. These three values must
map together. The association migration planner now requires an explicit
objectIDMap and checks destination note readability. Unmapped or inconsistent
references fail before writing; item IDs, source selection IDs and unrelated
metadata remain stable.

An ambiguous create timeout must not trigger a new native page with a fresh ID.
Use a durable creation plan/receipt and a native identity that can be probed,
then resume later phases. Likewise, a source-line write needs exact retry
identity or readback; the legacy attempted flag alone is not proof of a
successful native block write.

For related documents, retain T5SourceIdentity, T5SpaceRelatedDocumentsQuery,
T5ExpandedRelatedDocumentsQuery and T5BlockReachability. The old host searches
verified native source indexes, then loads canonical content, exact object
identity, readiness and restrictions before accepting a candidate.

The new candidate adapter can read native claim indexes for provider/source
and target IDs, but it must apply the canonical conflict projection first.
A raw provider/source index hit is not proof that a claim is live: observed
removes, concurrent replacements and logical collisions matter. Check each
candidate's current Space, type, bin/template state, member authority and
block reachability. Deduplicate the same target while preserving association
and quote instance identities; return explicit coverage/truncation.

The existing expanded T5 feature is gated off unless its native version/hash
contract is proved. A new query implementation must earn its own capability;
do not reuse the old macro or report a verified expanded index from a
client-only scan. Unlink removes only selected association claims; it must
never delete the related document or source quotation content.

Required acceptance includes note create/resume without duplicate pages or
source lines, cross-document related lookup, source/provider identity, orphan
and deleted block exclusion, quote-instance targeting, exact unlink scope,
pagination progress, stale candidates and permission changes.

## Native computed Source/Topic/Word properties (PROP-01..PROP-04)

The preserved implementation is native, not merely three display chips.
Modules/PinkhaHeart/torah.Project builds source/topic/word identity arrays,
labels and a canonical SHA. Binding resolution and readiness epochs guard
the index, while the existing property catalog and host tests enforce native
descriptor identity, picker behavior and Type retention.

Keep these semantics:

- Only document-level context associations enter document source properties.
- Block links, source-quote instances and internal anytype-note links are not
  silently promoted into document Source/Topic/Word values.
- Deleted, archived/in-bin, template and unsupported objects are ineligible.
- Canonical bytes/operations are authoritative; derived arrays, labels, hashes
  and readiness can be rebuilt and cannot become a second canonical store.
- A malformed, future-version, conflicted or incomplete projection is
  unavailable/stale, never a verified empty result.
- Derived descriptors, hidden/attach policy, universal property picker and
  retention across compatible Type changes require native acceptance.

The inspected user-dataset API permits declared fields, native indexes and
immutable-record policies, but does not expose arbitrary user computed-field
hooks. SDK docs/user-datasets.md explicitly lists computed fields as outside
that surface. API scope "derived" refers to handler-computed values; it is
not an expression language that can run Pinkha's projection.

Therefore there are two separate next pieces:

- A registered native Any handler/projection extension must consume the
  canonical association operation dataset, materialize deterministic
  read-only source/topic/word output and maintain rebuild/readiness state.
  Existing pure Go identity/projection logic is reusable only after its input
  adapter consumes the new canonical operation projection correctly.
- The Swift host must discover/verify that extension's capability, schema and
  version, then bind its native property descriptors to the existing UI.

A Swift computation can be useful for preview and verification, but it does
not satisfy the native searchable-property capability. A writable property
mirror is also insufficient. Until native read-only derivation, indexing,
rebuild, import/export boundaries and Type-change retention are proved,
PROP-01..PROP-04 stay open.

Relevant native calls are declaration reads under types/collections/parts,
GET /v1/spaces/:spaceId/properties/:objectId, native objects/query and
query/subscribe, plus the engine extension's eventual readiness contract.
The contract must be specified by implemented backend code; do not invent an
HTTP readiness endpoint or set a local success flag as proof.

## Current evidence and known gap

Native target membership/object/block/orphan contracts were exercised on
synthetic local data; see evidence/20261119/native-target-contracts.json.
This is separate from the compiled Swift observer and bridge execution.

Native search testing found that exact Hebrew, phrases, prefixes, English and
pointed literal queries work on the fixture, while unpointed "שלום" did not
match stored "שָׁלוֹם". See
Tools/AnyEngineValidation/evidence/search-native-v1.json. The old Heart
equivalent has not been verified, so this is a new-engine search gap, not an
established regression. Provider candidate diacritic normalization does not
prove old full-text behavior. Any future folded search index must retain the
original canonical text unchanged.

## Host composition still required

TorahEditorSession currently constructs the Heart association repository and
Heart note/related services. The hierarchy, editor document, selection/quote
writes, native properties, Hanlin read/write host, account ownership, binary
lifecycle and UI observers must all select the same backend session.
Installing only the association adapter in a Heart document is forbidden
mixed-store composition. Full application and physical-device acceptance stay
open until this ownership transition and all capability groups are proved.
