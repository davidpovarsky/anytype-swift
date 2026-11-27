# Imported native definition directory

This Host adapter resolves original Heart Type, Property and Option identities
through the saved migration plan and the actual current native definitions. It
adds an ordinary read path for definitions that were already created by the
qualified migration. It does not replay the saved operations.

## Consumer API

Create `AnyNativeImportedDefinitionDirectory(plan:mappings:)` from the exact
saved `AnyDestinationMigrationPlan` and ordered
`[AnyDestinationMigrationMapping]`. Keep this material with the migration's
existing account/Space binding and receipt; a display name, xKey lookup, or
caller-supplied destination object ID is not an identity substitute.

Create `AnyNativeImportedDefinitionStore(client:workspace:)` for the active
destination account and Space. Read one source identity with
`read(sourceObjectID:directory:lease:)` inside an `AnyApplicationSession` lease.
The returned snapshot contains the current typed value, full native JSON,
original source hashes, native address, engine generation and creation outcome.

| Original definition | Native address | Returned value |
| --- | --- | --- |
| Imported Heart Type | Exact native Type object ID | `AnyNativePropertyOwner` |
| Imported Heart Property | Owner kind, owner ID, property ID | `AnyNativePropertyDefinition` |
| Heart Option | Parent property address and original source Option ID | `AnyNativeImportedChoiceOption` |
| Qualified canonical Property | Existing native Type/property address | `AnyNativePropertyDefinition` |

An option remains an embedded native choice entry. Its original ID is preserved
as the option key. It is not represented as a newly allocated native object and
does not acquire an object endpoint.

The directory excludes the migration's source-archive Type and its property
namespace. They are preservation infrastructure, not original Type objects.
`unresolvedSourceDefinitionIDs` explicitly reports original definitions with no
qualified directory entry. `permitsSourceAdmission` and
`permitsDestinationWrites` remain false.

## Identity and authority

All source identity joins and native scope comparisons use exact UTF-8 bytes.
Unicode-normalized spellings cannot substitute for a saved source ID. The
directory validates mapping order, source keys, kinds, record cardinality,
digest forms, signed-change identifiers and reconstructed intent identity.

Saved destination mappings are routing hints. Before exposing an imported
definition, the store asks the native prepared-definition service for the
selected original intent's current receipt. The existing service binds the
account, Space, store, migration plan and intent specification. The reader then
requires the exact original fingerprint, destination object and record IDs, and
final original signed change ID. A forged mapping cannot authorize reading a
different native definition.

The active Host lease and exact account/Space binding are checked before reads,
after HTTP responses and before delivery. Canonical properties use their
existing validated source binding and exact native descriptor. Selecting a Type
for creation still goes through the existing native document-policy reader;
reading this definition does not grant document creation authority.

Two ordinary reads of the definition must agree byte-for-byte under canonical
JSON encoding. The selected intent's native receipt must also agree before and
after. This bounds one device-local observation. It is not an atomic snapshot
of an entire schema or proof of all-peer delivery.

## Edits and provenance

Ordinary native edits do not invalidate the original definition's identity.
Both `committed` and `committed_modified` complete creation receipts are
accepted, provided their immutable creation identity still matches. The
snapshot reports `matchesOriginalDescriptor` separately. Unknown current native
fields remain in `raw`; unsupported projection fields make the descriptor
comparison false rather than being silently discarded.

The source provenance must remain exact. Imported Types retain the original
source object ID, unique key, snapshot hash, JSON-view hash and definition JSON.
Imported Properties retain their complete `xFormat.pinkhaHeart` provenance.
Options retain their own original metadata and also require the enclosing
property's original provenance on each read. Changing the parent's source
identity therefore refuses both the Property and its Options, even if the
option payload itself is unchanged.

There is no mutation API in this reader. Native Type and Property PATCH routes
remain separate operations with their existing native permission checks. The
validation fixture uses those routes only against an owned exact copy of the
retained account, and records every attempted PATCH before dispatch.

## Validation scope

The focused component suite checks distinct native addresses, exact source
identity, archive/namespace exclusion, mapping refusal and the retained
182-operation plan. The native fixture exercises current reads, ordinary
Type/Property/Option edits, forged mapping refusal, foreign-Space refusal,
parent-provenance refusal, revoked Host leases, an intentional native SIGKILL,
and cold reads before and after restoring the original definition bytes.

Actual run receipts and their source/product manifests determine acceptance.
This contract alone does not claim that a test ran. The original 182-operation,
159-head, 156-snapshot and 332-archive-record preservation evidence remains a
separate accepted scope. Unsupported Type families, source-history semantics,
and whole-source admission remain explicit outstanding work.

Accepted component and native evidence is published in
`docs/validation/20261127-wave1-functional-migration/native-definition-directory/`.
It qualifies 13 entries (one Type, seven imported Properties, four Options and
one canonical Property); 137 other source definitions remain unresolved.
