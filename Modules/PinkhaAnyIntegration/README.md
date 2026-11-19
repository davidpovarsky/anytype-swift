# PinkhaAnyIntegration

This package connects the **actual PinkhaKit domain** to PinkhaAnyEngine. It is
an additive integration: the application's active Heart document/session
composition remains explicit until all native adapters pass acceptance.

## What the bridge implements

| Existing contract | New-engine behavior |
| --- | --- |
| TorahAssociationRepository | Item CRUD on immutable native Any claims |
| TorahAssociationPayloadCodec | Existing v1 lift/v2 model and metadata representation |
| Context identity | Existing NFC/length-prefixed semantic identity; stable ID retained |
| Source quote identity | Distinct instance IDs remain distinct |
| Document/block targets | Explicit Any workspace, exact object/Space identity, reachable blocks |
| Update/remove | Observed predecessor claims; concurrent variants remain visible as conflicts |
| Migration of association snapshots | Validated source, explicit ID mapping, deterministic operations, readback receipts |

The existing provider registry, Sefaria providers, AnytypeTorahWorkspace source
facade and TorahSourceHierarchy are engine-independent. Use these unchanged
from PinkhaKit; the historical workspace name does not imply Heart storage.

Native target checks use the current member's actual identity, status and
permission, allowed document Type IDs, excluded collections, and block
reachability. Fresh native page records omit empty collections. An orphaned
block row is rejected even when the row still exists.

## Mutation and retry contract

Use prepareMutation to obtain an immutable AnyTorahPreparedMutation, persist
the entire Codable value, then call commitPrepared. This freezes the payload
and observed predecessors before dispatch. Replaying it after another edit
does not silently replace that newer edit; divergent successors are conflicts.

The apply convenience method computes a mutation from current state. Reusing
only its operation ID does **not** provide a durable retry plan across
intervening state changes. Whole-snapshot replacement remains refused.

## Association migration contract

AnyTorahMigrationPlan covers one original canonical association snapshot,
including document and block records. The destination account/Space/object and
every source block mapping are explicit. Internal T5 note links require an
explicit objectIDMap: their canonical key, external ID and note metadata ID
are remapped together. Unmapped/incoherent links and unreadable destination
notes are rejected before writes. The planner keeps the source bytes
and hash, stable item IDs, existing item provenance, and unknown metadata at
envelope, record and item levels. New operation signatures belong to the new
Any account; importing old provenance never pretends that account signed
historical data.

The old domain represents JSON numbers as Double. Planning therefore compares
original and re-encoded numeric tokens using exact decimal normalization.
Numbers that would change value, such as 9007199254740993 or a longer precise
decimal, are refused with numericPrecisionWouldChange. Duplicate JSON object
keys are refused too. These cases require a future durable original-source
archive/import representation; they are never silently rounded into success.

The executor preflights target validity and known operation/item identity
conflicts before writing. It then reports partial progress and re-reads native
claims. A complete receipt means every planned claim was live, readable and
free of relevant logical or semantic conflicts at that final observation.
An acknowledged write followed by deletion or conflict produces an incomplete
receipt. There is no global transaction, automatic conflict overwrite or
automatic resurrection of a subsequently removed import.

Keep the original source snapshot outside the transient plan before migrating
valuable data. This package does not yet supply a durable original-byte archive
or a complete Heart database migration. The plan is non-destructive and never
deletes source data.


## Live changes and ownership

The association observer requires an atomic first snapshot from native SSE.
Each published projection rechecks account/Space/target readability and the
owned stream generation. Disconnect, malformed frames, incomplete windows and
overflow terminate the stream; reconnect opens a fresh snapshot. A consumer
must validate the generation again before committing an already queued frame
to UI state.

## Notes, hierarchy and related-document adapters

These adapters now have source implementations in this package. Their actual
test/probe execution status is recorded separately in evidence receipts.

| Adapter | Reused domain | Native boundary |
| --- | --- | --- |
| AnyTorahNotesService | T5NoteCreationFlow and T5SourceIdentity | One immutable creation plan, the host's journaled object/source-line editing, canonical source and origin links |
| AnyHierarchyRepository | PinkhaHierarchyBuilder and PinkhaHierarchyMutationValidator | Installed native wiki collection, object/property APIs and complete object-query SSE |
| AnyTorahRelatedDocumentsService | T5SpaceRelatedDocumentsQuery | One bounded native canonical projection, current object/ACL reads, exact document-context unlink |

A note's phase IDs and creation time are frozen in AnyTorahNoteCreationPlan.
The host implements AnyTorahNoteDocumentEditing using its single durable
creation/write journal. An uncertain stock API create stays uncertain; it
cannot recover by allocating another page. Each retry runs every T5 phase
against idempotent host/association boundaries. A failed later phase retains
the native note ID through the original flow's recovery outcome. Unlinking
never deletes the note object, unrelated sources or quote content.

Hierarchy uses the existing system:wiki/v1 collection, resolved from the
native bundle and checked against synced property declarations. Parent IDs
are native scalar strings and positions use the exact Go lexid v0.0.6
allocator (CharsAllNoEscape, block size 4, step 100). Forty-one golden vectors
are generated by that actual Go implementation. The old sparse Double rank
is only a derived ordinal for the existing tree view, never native storage.
Unknown native properties are untouched by the narrow property patches.
A declared host allowlist controls document types; unsupported child types
block folder removal rather than silently orphaning them.

Creation delegates to AnyHierarchyObjectCreating and the host's same durable
object journal. A prepared move keeps prior placement, the complete recursively nested native
_ver field-version tree and the exact destination position. Retry accepts
already-applied state without a write; otherwise it requires the captured
version as well as the captured values. This detects A-to-B-to-A changes after
reopening the repository. A field-value comparison alone would miss them. The native property API has no atomic
compare-and-set against another writer: the precondition/readback checks are
observations, not a stronger native transaction.

Safe folder removal reparents and verifies all observed direct children
before moving only the folder into the native bin. A partial error returns
the IDs already moved plus the observed archive state (unknown if readback
fails). A newly observed child prevents completion; if one appears in the
post-archive check, the adapter attempts to restore folder visibility and
returns an incomplete receipt. This does not provide a transaction spanning
all child objects; strict concurrent no-orphan semantics still require a
native multi-tree operation.

Related-document results report boundedCanonicalSnapshot coverage, the
scanned claim/candidate counts and the canonical snapshot hash. Only live,
unconflicted document-context reference associations qualify. Block links,
source quotes and internal note links do not become document Source results.
Current metadata/permission reads follow the canonical snapshot and are not
one cross-document transaction. Document modifiedAt is the native document
timestamp, not a claimed timestamp for edits to the separate claim carrier.

Expanded related targets (blocks and source-quote instances) remain behind
their own verified native capability/version. A generic client scan never
sets that capability. Native computed Source/Topic/Word descriptors, indexes
and readiness are a separate engine extension.

Note classification requires configured native note types or marker
collections; a generic page is not automatically classified as a note.
The host supplies the codec for the client-defined native icon string.

## Bounds and activation gates

- Claims are read as a complete, bounded Space snapshot (10,000 operations),
  not as an unbounded or paginated database query. Exhaustion fails explicitly.
- Block target validation reads a complete object block set, capped at 10,000.
- Hierarchy reads a complete active wiki set, capped at 10,000 rows and 512
  ancestor levels before entering the original recursive tree builder.
- Association target identity currently names the canonical editor_blocks body.
  Dataset-qualified standalone editor snapshots do not imply multi-part
  association identity support; that needs an explicit native ABI migration.
- Target/ACL checks and the claim-carrier write are sequential native requests.
  They are not an atomic transaction across those objects.
- Account binding is explicit. There is no Heart fallback or ID inference from
  a currently displayed Heart document.
- Full application composition, files, all registered custom document kinds,
  durable create/write recovery, native computed properties, expanded related
  targets, complete account migration and iOS UI/device acceptance remain
  separate gates. Source implementations alone do not close those gates.

## Verification

Run swift test --jobs 2 from this package. Tests use real PinkhaKit domain
models and codecs with an explicitly in-memory operation store. They cover
mutation identity, unknown metadata, authority rechecks, immutable retries,
migration precision/conflicts/partial progress, and target reachability.
They do not certify native sync or whole-application parity.

The executable pinkha-any-integration-probe --disposable URL ACCOUNT SPACE
uses the real engine and creates synthetic page/block/association records in
the supplied **disposable** workspace. It exercises the concrete HTTP adapter,
domain CRUD, exact retry, migration, native readback, orphan rejection, native
wiki object persistence/observation and related-document lookup/unlink.
It does not prove restart recovery, two-client convergence, iOS UI or physical
device behavior. Use the recorded execution receipts for actual pass/fail
status; the presence of probe source code is not evidence of a passing run.
