# Native annotation schema registration: original-source audit

## Scope and result

This read-only audit identifies the original registration path for protocol `pinkha.torah.annotation/1`, fixed type key `ot-pinkhatorahannotationv1`, and the 17 string relations declared by `OriginalAnnotationNativeMetadata`. The descriptor is a **provisional uncommitted input**, raw SHA256 `21321e2e69bcb29dc784620dd459f1152528f117caa13695e689b6d024813dc5`, 8,112 CRLF bytes at the recorded metadata worktree. Its decoder does not install native objects or provide registered IDs.

**The original APIs support fixed schema identities, but a Swift search/create loop alone cannot establish complete, recoverable registration.** The native source has a durable empty-root window, generic lookup helpers do not prove uniqueness, and visibility requires separate checks. No native call, schema write, test, build, CI dispatch, production permission, receipt, mapping write or ACK was performed or introduced by this audit.

[SOURCE_INDEX.json](SOURCE_INDEX.json) binds 47 complete files: 20 Heart sources at `d98420b1113536afd08cde6de9a5816f6d27ffff`, 20 Swift/overlay sources at `d02a4972e7f124bc97a577e1c6d448d4797acf22`, and seven any-sync sources at `5d71ccad5db77997df2d2426011ebae4e7600d98`. Heart pins any-sync v0.13.8 in go.mod/go.sum; its public annotated tag was resolved and each retrieved blob independently hashed. This is dependency **source** inspection, not verification of an executed Heart binary or a module ZIP checksum. The dirty Heart checkout was never used as source.

## Actual creation and retrieval APIs

| Purpose | Original path | Required use or limitation |
|---|---|---|
| Fixed relation | `ClientCommands.objectCreateRelation` → `core/create.go` → `objectcreator/relation.go` | Supply exact `relationKey`, nonempty display name and an explicitly present numeric `relationFormat = 0` (`.longtext`). Heart forms `rel-<key>` and a native derived state. |
| Fixed type | `ClientCommands.objectCreateObjectType` → `objectcreator/object_type.go` | Supply exact `uniqueKey = ot-pinkhatorahannotationv1`. Omission generates a BSON key. A missing recommended layout defaults to native basic layout. |
| Candidate discovery | Raw `ObjectSearch` in the selected Space | Query exact relationKey or uniqueKey, request identity/format/state fields, and inspect all candidates. This reads SpaceIndex, not a native absence fence. |
| Fresh verification | Original `ObjectShow` for each discovered/returned ID | Verify one exact root, actual Space, native unique key/layout, relation key and longtext format, and reject malformed/archived/deleted/conflicting state. A display name or API slug is not identity. |
| Attach metadata fields | `ObjectTypePropertyAdd`, nonempty key, `.hidden`, `enableInViews = false` | Uses the existing native type Apply. Verify returned key and propertyID against the independently verified map and read the type back. Its internal resolver currently uses `Limit: 1`. |

Two convenient Swift methods cannot implement this descriptor unchanged. `TypesService.createType` never sends uniqueKey. `PropertiesService.createProperty` uses `PropertyDetails.fields`, which serializes name, format and objectTypes but **omits relationKey** and hidden/read-only flags. Passing a fixed key into PropertyDetails therefore does not send it. The narrow adapter should use the existing original ClientCommands with explicit fields; no replacement engine or public constructor is needed.

The existing `AnytypeTorahNativePropertyProvisioningStore` is for the three bundled derived Torah properties. Its lookup requires `sourceObject == "_br" + key`; its definitions use tag format 11 and attach to the three registered document types. The new 17 custom longtext fields have neither that bundled source marker nor that purpose. Reusing that installer unchanged would misclassify or fail their registration.

The field inventory is retained in [DESCRIPTOR_INPUT.json](DESCRIPTOR_INPUT.json): four protocol/classification/namespace/UUID fields, eight immutable creation fields, and five optional applied-commitment fields. Applied-field absence or presence does not prove a rich body was applied. Schema registration must not turn decoder output into identity/body authority.

## What fixed keys actually guarantee

Heart `NewDocWithUniqueKey` and `objectcreator/smartblock.go` select the native derived-tree path for relation/type objects. `space.GetRelationIdByKey` and `GetTypeIdByKey` call the original `DeriveObjectID`; these derive an address and do **not** prove an initialized object exists. No corresponding direct derivation RPC was established in the audited mobile ClientCommands path.

For a modern non-personal Space, the native derived root incorporates the Space, smartblock type/key and parent. The audited payload contains no random seed or creation timestamp. The same root identity is therefore source-derived for that same native derivation context. This is a source conclusion, not an executed concurrent-creation result.

There is a distinct legacy personal-Space branch: it uses an account-signed root, whose source includes the current ACL head. Do not generalize modern fixed-root stability across personal-Space ACL transitions or account changes. The UI `isLegacyStream` predicate was not proved equivalent to native `space.IsPersonal()`. Neither a client-computed ID codec nor a caller boolean should bridge that gap.

The 17 camel-case relation keys and the type's internal key contain no extra hyphen. Adoption must validate their exact bytes; this audit does not establish every index filter's collation. They fit the existing `rel-` / `ot-` parser. API-object slug collision repair is a separate field and cannot supply schema identity.

## Duplicate and partial-failure boundaries

The decisive native sequence is:

1. `PutSyncTree` calls SpaceStorage.CreateTreeStorage.
2. any-sync `objecttree.CreateStorage` commits the root and head in an original database write transaction.
3. Heart subsequently opens the object and `ObjectFactory.InitObject` applies the initial relation/type state.

Those are separate completion boundaries. **A process loss or error after step 2 and before the initializing Apply can leave an empty fixed-ID root.** On retry, CreateStorageTx maps an existing root document to `treestorage.ErrTreeExists`; ObjectCache returns the PutTree error before creating the smartblock. The original mobile create handlers return UNKNOWN_ERROR without an object ID. An index lookup may consequently remain empty. This is a source-supported failure window, not a native crash reproduction.

The existing smartblock initialization also refuses a nonempty existing document when given a creation state. Recovery must not evade that refusal or overwrite an already populated schema object.

| Observed situation | Safe outcome |
|---|---|
| One candidate with complete fresh exact schema readback | Reuse that actual ID; do not recreate it. |
| Multiple candidates, wrong native key/type/Space/format, or malformed state | Explicit conflict; no first-row selection, renaming, deletion or replacement key. |
| Creation error/timeout plus zero indexed candidates | Unresolved, not absent or successful. Do not convert this into a random-key retry or an annotation delivery reset. |
| Fixed root exists but initial definition is incomplete | Remain unavailable until a reviewed original native recovery path establishes and, if authorized, completes that same root. |
| A subset of the 17 relations/type attachments is complete | Preserve those objects; resume only missing verified work. Registration remains incomplete. |
| Owner/account/Space source retires | Stop new admission and preserve original drain semantics; no current-success publication. |

A minimum original native follow-up is an **internal fixed-schema ensure/readback seam** in the existing objectcreator/objectcache creation path. It should expose the actual native-derived ID and distinguish initialized matching state, conflict and empty-root partial state. If empty-root completion is implemented, it must validate the actual key/Space and proven empty native state under the original object lock and current authority. The first conservative implementation may refuse that repair. Simply swallowing ErrTreeExists is insufficient.

## Type attachment and visibility

`FillRecommendedRelations` replaces recommendedHiddenRelations with default hidden IDs when recommendedRelations is absent/empty. Supplying only the 17 hidden IDs to initial type details does not preserve them. The existing additive ObjectTypePropertyAdd route is the smaller path: nonempty fixed key, hidden section, and existing original Apply.

That route has two limits. Its resolver queries an indexed relation with `Limit: 1`, so successful return is not a duplicate-free schema proof. Its `enableInViews` flag supplies visibility for **new** columns; the audited code does not promise to reset an existing column's visibility. Verify returned IDs, final type lists and the relevant original view state. Never replace all type lists or use an empty key, which would mint another relation. Each field attachment is independent; the 17-field batch has no enclosing native transaction.

Pinkha hierarchy subscriptions and fallback reloads include the folder type plus `registeredDocumentTypes`; their `makeRawItem` also rejects other types. Keeping the dedicated annotation type outside that manifest provides this specific hierarchy boundary. Do not insert it into registeredDocumentTypes or copy the existing Torah installer's three-document-type loop.

General type selection and search have different filters. SearchFiltersBuilder/TypesService use original not-hidden filters; the native type/property subscription caches include broader data and assert on duplicates while still selecting a row. They are not strict registration stores. Hiding a type is not evidence that every annotation instance is hidden in every search: the shown search predicate tests each row's isHidden/isHiddenDiscovery fields. The audited source does not prove automatic inheritance. Define and verify each intended surface separately; UI hiding is not an access-control or immutable-metadata guarantee.

## Minimum implementation sequence after composition

1. **Bind the real destination.** Consume the actual selected account/Space source and original full edit-permission composition. SourceBinding's added restriction alone is not a new-object or selected-Space grant. No qualification account or unrelated document Owner.
2. **Observe strictly.** Use raw original search and fresh ObjectShow to establish one actual matching type/relation per fixed key. Include hidden/deleted state in verification; do not adopt a UI cache or discard conflicting rows.
3. **Register exact definitions.** Only through the reviewed native fixed-key creation/recovery boundary, install missing longtext relations and the dedicated basic-layout type. Never mint replacement keys or erase partial native work.
4. **Attach additively and verify.** Use the existing original type-property API for missing fields, retain unrelated native properties, check returned IDs, and verify all 17 definitions and final type state. Preserve original cancellation and before/after-await checks.
5. **Publish only a schema observation.** A private `OriginalAnnotationNativeSchemaStore` beside the existing Annotations sources can return validated native schema IDs bound to the captured source. It must not expose public creation permission, identity/body receipts, a ledger writer or ACK.

Ordinary annotation `ObjectCreate` remains separate. Heart derives its **type** ID and loads the type's recommended layout from SpaceIndex, then creates an ordinary object using the random/time-based tree path. A detail named uniqueKey does not establish annotation UUID idempotency. Existing durable creation fences, identity-only recovery, body verification and R1/R2 distinctions therefore remain required. Positive type-index readiness is also needed before materialization.

## Open acceptance and audit limits

No live account namespace was enumerated and no registration, retry, partial-crash, multi-client or visibility acceptance ran. Descriptor decoder controls, prior pure policies, Space/Participant controls, SQLite controls and StageB evidence are not transferred to registration. All registration acceptance gates remain open; this audit does not change any other task's status.

The r14 overlay hash is `fb96818eb57bd9e0be8da90a11831bcccc7ca8e72cc0a4e9a065500feb7cc077`. It does not replace the audited fixed type/relation/object-cache creation files. Its relevant details injection adds Torah projection after native identity injection, and its added filter rule is scoped to the existing Torah derived properties. No dirty T2 working-tree bytes or replacement schema were used. Read-only path/transport failures and the bounded go-env timeout are recorded separately in READ_SCOPE.json; none is presented as a product test failure.

The root owns any schema/native implementation and acceptance. This packet changes documentation only and leaves all passed Space/Participant/decoder packets and producer inputs untouched.
