# Original property modal — source handoff

## Scope and provenance

This isolated draft extends the existing original Anytype `.object` property-modal path. It does not establish Apple compilation or Native acceptance.

- Exact fork preimage: `fc03fcd713e2c449ad97c5d1e604a9433c2a309b`.
- Upstream `develop` observed by root for this task: `d857b23ea540be33d6faab4f7a7a1a260ab578c1`.
- Root claimed the work in Asana story `1220765745991426` and authorized the original-source increment under the user's standing authorization.
- Thirteen changed existing Swift files; no target-membership/configuration, generated source, Heart, Owner, Factory, Invocation or source-binding changes.
- Patch: `original-property-modal-owner.patch`, SHA-256 `377ef209aa567db9f95728f54be101726befea96b2e2cc36b28d0ca3a8bb729d`.
- Full base/output hashes: `CANDIDATE_INPUTS.json`. The initial 22 files and 19 further original reference records were checked against their exact Git blobs; the two additional editable preimages are separately recorded.

## Original call chain and authority

| Entry or operation | Draft behavior and original authority |
| --- | --- |
| Slash `.newRealtion` | The spelling and original callback remain unchanged. The callback still invokes the existing `actionHandler.scheduleMutationTask` before it creates its block mutation Task. No alternate slash handler is introduced. |
| `EditorRouter.showAddPropertyInfoView` | A configured router requires its actual `EditorPageCoordinatorViewModel`, the identical prepared Owner, and the identical owned document. An arbitrary output cannot drop the external source binding. |
| `EditorPageCoordinatorViewModel` | Creates one `OriginalEditorPropertyScope` from its retained prepared session and actual document. A pending/failed qualified preparation cannot fall back to nil. |
| `PropertiesSearchData` → `PropertyInfoData` | Carries the same scope reference. Added initializer parameters default to nil, preserving existing callers. The historical `objectId` may be a type ID; it is never treated as the prepared parent target. |
| Prepared property search | Uses the original final `SearchService.searchRelations` under the actual parent Owner's `ObjectSearch` read. Rechecks current source and search request identity after awaiting; uses returned original `PropertyDetails`. It never enters the implicit Pinkha policy/bootstrap/native catalog path. |
| Internal property identity | Uses the existing shared final `PinkhaSpaceManifestStore` via the added strict read entry. That entry admits the original `SearchMiddleService` and calls the unchanged `loadManifest` body. Only `ObjectSearch` and `ObjectShow` are permitted by the parent's read lease. There is no cache authority, bootstrap, migration, save or write fallback. |
| Identity result | Requires the exact returned Space, current schema, complete manifest, native-discovered manifest object ID and complete nonempty canonical/order IDs and keys. Raw identity bytes must match the existing parsed identity helper. The immutable result is scoped to this operation and issuing scope, with post-await source/account validation. |
| New property | Parent list permission is reserved before Task creation. The original `PropertiesService.createProperty` runs through existing `Owner.performMutation(spaceId:)`, with the original `ObjectCreateRelation` request/response. Input has no supplied existing ID/key/source object. Returned real ID/key/Space and protected-property rules are checked before original `addProperties`/`ObjectRelationAdd` on the actual parent. |
| Existing property selection | Revalidates the actual published selection, reads current canonical identities, and acquires the actual selected property document through unchanged `PreparedEditorChildPreparation`. The child must be an exact same-Space original `.relation` document. The named child action validates metadata; parent add runs in parent lineage; then child-only `lastUsedDate` runs on the property ID. Parent callback/publication runs only after the child operation returns. |
| Definition update | Acquires the actual property child with `.editDetails`, uses original `PropertiesService.updateProperty`, and reads the actual retained document after awaited native event delivery. Key/format and unchanged object-type restrictions are preserved; the returned display metadata comes from that document. |
| Archive | The prepared `AsyncButton.prepareAction` reserves the existing parent action before SwiftUI starts the Task. Actual archive uses original `ObjectActionsService.setArchive` inside the selected property child's `.archive` action. No parent context is relabeled as the property. |
| Completion | The prepared Save path dismisses only from a current original completion callback. The existing nil path retains its original immediate Save/dismiss behavior. An uncertain creation is not automatically retried. Original native records are not deleted or represented as rolled back. |
| Adjacent property values | The shared `requireOriginalPropertyValue(propertyId:key:identity:)` only applies current internal/native exclusion. It adds no schema-only readonly/hidden restriction and grants no mutation. The native agent's separate value-entry patch consumes this same helper; its two files are not included here. |

## Preservation evidence

`SOURCE_APPLICATION_RECEIPT.json` records a real `git -c core.autocrlf=false apply --check --whitespace=error-all` and application to all thirteen exact local preimages. Every output matches the candidate bytes; no extra files were created in that application tree.

`SOURCE_PRESERVATION_RECEIPT.json` records 24 bounded source-preservation checks. They compare the unchanged original manifest discovery/load/save and native search bodies, original nil-route bodies, the whole preexisting scope/value configuration and protected file boundaries. The extractor's initial protocol-versus-implementation selection error was corrected in the audit only and is retained in `SOURCE_PRESERVATION_AUDIT_CORRECTION.json`. These checks are not Swift tests, runtime tests or Native evidence.

The native agent independently read the complete frozen thirteen-file candidate. Two source blockers discovered during implementation were corrected: stale Space-only cache provenance and re-entry into a passive parent lease during a child operation. The final source review reported no remaining concrete blocker. Root review is still the integration gate.

## Explicit unqualified or unavailable routes

1. A Pinkha-enabled Space without a unique, complete, current canonical manifest/identity remains unavailable. This code does not bootstrap or repair it under a document Owner. Pinkha-disabled handling retains the existing disabled-policy interpretation and still excludes fixed reserved native keys.
2. Prepared `.type`, `.dataview` and `.library` targets are rejected. They need their own real prepared target/child semantics; no foreign type/property ID is authorized as the parent.
3. The legacy object-type restriction picker has its own unqualified subscription/task graph. It is disabled on this prepared route. Existing restriction IDs can only be retained unchanged after actual child verification; no new foreign type schema is authorized.
4. Cached/already-open selected documents remain subject to the existing fresh source-bound open rejection. This patch neither adopts them nor resets/closes another owner’s document.
5. The slash route preserves its original behavior: an existing row attaches that property, while a format opens creation. It does not add a new Edit menu. Other existing `.edit` callers need to supply an actual supported scope before these bound handlers can be exercised; the foreign TypeProperties schema path is not activated here.
6. Root/native agent separately own the adjacent ObjectProperties/PropertiesList value-entry and mount boundaries. Those fixes must be combined explicitly; this packet makes no claim that an unchanged prepared mount's policy/bootstrap calls are already qualified.
7. Real creation can precede a later validation/attachment failure. Such a failure is a partial/uncertain outcome, not rollback; the original record remains and the model prevents an automatic repeat. Recovery/cleanup is not invented here.

## Remaining execution gates

- One syntax parse of the changed files, then actual Apple semantic/module compilation against the frozen shared SDK graph.
- Original object-property Native journeys: search/select, create/attach, actual slash block callback, definition update, archive and readonly rejection.
- Account/source/permission retirement during canonical read and child open; cancellation while the actual RPC remains active; stale selection/Space/identity rejection; unknown or ambiguous manifest.
- Fresh/cached selected-document behavior, real UI dismissal and actual native event/readback timing.
- The full existing Host/consumer/package/Native gates, with their exact source and artifact pins. No previous passed Owner/dispatcher/Factory suites were rerun for this source-only draft.

No Windows worktree/ref, repository, Asana or CI was mutated for this increment. Publication and integration remain root-owned.
