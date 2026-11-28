# Prepared native definitions

The optional `space.PreparedDefinitionService` on `Space.Objects()` creates custom type, collection, property and atomic type-part definitions with durable identities. Its contract is `pinkha-native-prepared-definitions-v1`. The ordinary prepared object route still rejects metatypes and template copies. Definition capabilities are separate; network delivery is not asserted.

## Native contract

`PrepareMigrationDefinition` accepts an immutable `MigrationInput` and one `MigrationDefinitionSpec`. The only current kinds are:

| Kind | Seed | Result identity |
| --- | --- | --- |
| typeDefinition | TypeCreateParams | ObjectID, the actual native type root |
| collectionDefinition | CollectionCreateParams | ObjectID, the actual native collection root |
| propertyDefinition | Existing custom OwnerObjectID plus PropertyDraft | RecordIDs[0], derived from the original signed change |
| partDefinition | Existing custom type OwnerObjectID plus PartDraft | Ordered RecordIDs for the part, dataset heads, fields and indexes in one original signed change |

All input bytes, source identity, plan digest, actual destination account/Space and durable store generation are fingerprinted. The shared unique intent binding refuses collisions across ordinary objects, blocks, files and definitions. Display names and xKey never act as identity adoption keys.

Type and collection creation proceeds one durable stage per request: definition-root-prepared, definition-root-committed, definition-bootstrap-prepared, then complete. Property creation has definition-property-prepared then complete. Atomic part creation has definition-part-prepared then complete; its batch contains between 1 and 2048 unique records, with an encoded native payload bounded to 256 KiB. Part/head IDs are generated only once before durable reservation; field/index IDs are derived from that same original signed native change. Query status or retry the same preparation/commit after an interrupted reply. Never allocate a substitute intent merely because a request timed out. An obsolete envelope requires explicit reconciliation; a modified or deleted committed row never permits recreation.

A native signed root or encrypted change is durably checkpointed in a private immutable ledger before append. Native dependency heads, current signing account and current ACL authority fence both preparation and append. The special definition policy accepts only the closed seed shape and an actual type/collection native root; built-in and registered owners refuse mutation. Original IDs and signed bytes survive SDK reopen and abrupt process termination.

The source mapping coordinator must persist source ID to ObjectID/RecordIDs after reconciliation. It must establish source enumeration, source checkpoint authority and original source payload completeness independently; these destination receipts cannot prove those source properties.

## HTTP

- GET /v1/spaces/:spaceId/pinkha/migration/definition/capabilities
- PUT /v1/spaces/:spaceId/pinkha/migration/intents/:intentId/definition/prepare
- POST /v1/spaces/:spaceId/pinkha/migration/intents/:intentId/definition/commit
- GET /v1/spaces/:spaceId/pinkha/migration/intents/:intentId/definition

Prepare uses the existing MigrationPrepareRequest envelope with the definition contract. specBase64 contains exact bounded JSON with one kind and one type, collection, property or part seed. HTTP seeds use the ordinary Any TypesCreateRequest, CollectionsCreateRequest, AddPropertyRequest and PartDraftRequest shapes and validators, including xKey, layout and descriptor validation. The source SHA binds the original decoded bytes. Duplicate keys, case aliases, unknown fields and lossy JSON numbers refuse before native admission. Existing intent retries bypass handle preflights only to reach the native ledger's full immutable binding check.

The atomic part wire shape is `{ "kind": "partDefinition", "ownerObjectId": "<mapped custom type ID>", "part": { ... } }`. The part seed uses the ordinary key, name, icon, pos, hidden, ui, uses and datasets fields. Dataset drafts preserve their nested fields and indexes. The native lock rechecks the compiled custom owner, installed modules, reserved-module policy, dataset collisions and every declared use. Unknown uses are refused instead of being silently filtered. Status and commit preserve all original ordered record IDs. Modification or deletion of any batch row is terminal and never recreates the batch.

## Qualified scope

The focused production SDK controls exercised:

- Actual signed type and collection root/bootstrap reservations across five SDK reopens, property reservations and four concurrent commit callers, and an ordinary object that uses both migrated custom property definitions.
- Static owner, destination scope, same-source intent, cross-kind intent, changed-head and ordinary metatype refusals.
- Committed modification and deletion without replacement.
- Actual child-process kill without SDK.Close; reopen retains the original signed type bootstrap and property identities.
- Native type/collection root acceptance plus wrong-kind, ordinary-object-route, foreign-space, revoked-writer, advanced-ACL and cancellation refusals.
- Production HTTP type and property creation/status/retry, plus duplicate/case/unknown/numeric/scope refusal.
- One existing ordinary object/block restart regression after the shared prepared internal changes.
- An actual six-record atomic part/dataset/field/index reservation across two SDK reopens, followed by an actual prepared editor paragraph on the migrated custom type.
- Current-head, static/collection owner, missing-use, duplicate-dataset, unknown-module and registered private-module refusals, plus terminal part modification/deletion without replacement.
- An actual abrupt child-process kill before atomic part append; all six original IDs survive recovery and commit exactly once.
- The production HTTP part route, preserving the signed batch identity, plus duplicate/alias/unknown-field rejection inside nested typed arrays and shape maps. The previous definition HTTP method passed after extending nested field admission.

Recursive property children and required declarations are explicitly refused by this version because the pinned ordinary constructor does not write them. Atomic type parts and their initial datasets are qualified by the focused controls above. Source-side extraction, complete source-to-destination mappings, native history replay, network delivery and whole-Space acceptance remain separate work. The frozen prepared-file Apple artifact candidate is unchanged by these definitions.

The atomic native implementation is pinned to any-sync-sdk `ef63bcaed93064c8de24ed656842f3e56ed34008`. This continuation adds four top-level control methods and reruns one affected definition HTTP regression; helper subprocess entrypoints and nested refusal cases are not counted as additional methods.
