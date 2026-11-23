# Original root storage and ACL trace

This is a source finding, not an executed permission-race result. All rows are bound in `SOURCE_BINDINGS.json`; primary any-sync blobs are retained under `primary-any-sync-v0.13.8/`.

## Original path

| Order | Exact source | Observed behavior |
| --- | --- | --- |
| 1 | Heart d98420, `core/block/import/common/objectid/treeobject.go:GetIDAndPayload` | After existing-object lookup, requests the original Space's CreateTreePayload. |
| 2 | Heart d98420, `core/block/object/objectcache/tree.go:CreateTreePayload` | Signs the original root payload with the actual account SignKey and calls TreeBuilder.CreateTree. |
| 3 | any-sync 5d71ccad, `commonspace/objecttreebuilder/treebuilder.go:CreateTree` and `objecttree/objecttreefactory.go:CreateObjectTreeRoot` | Checks Space closed state, reads ACL Head under RLock, creates a signed root. The shown factory does not check current CanWrite. This prepares a payload; it does not insert storage. |
| 4 | Heart d98420, `objectcache/tree.go:CreateTreeObjectWithPayload` | Calls TreeBuilder.PutTree, closes the returned tree, then GetObject with the original create/init option. |
| 5 | any-sync 5d71ccad, `commonspace/objecttreebuilder/treebuilder.go:PutTree` → `object/tree/synctree/synctree.go:PutSyncTree` | Checks Space closed/deleted state, calls SpaceStorage.CreateTreeStorage, then buildSyncTree. |
| 6 | any-sync 5d71ccad, `commonspace/spacestorage/spacestorage.go:CreateTreeStorage` | Calls the original objecttree.CreateStorage for the root, sets AddSeq, and returns it. The shown call is before tree rebuild/ACL validation. |
| 7 | any-sync 5d71ccad, `objecttree/objecttree.go:validateTree` and `objecttreevalidator.go:validateChange` | Validation holds the ACL read lock, but checks PermissionsAtRecord(change.AclHeadId, change.Identity). A derived change returns before that permission check. A root returns after its historical permission check. |
| 8 | Heart d98420, `smartblock/smartblock.go` PushChange path | Original Apply propagates a real PushChange permission error unless the caller explicitly opted into IgnoreNoPermissions. The closed route must not request that opt-out. |
| 9 | any-sync 5d71ccad, `objecttree/objecttree.go:AddContentWithValidator` / `prepareBuilderContent` | Content preparation checks current Permissions(content.Key.GetPublic()).CanWrite under ACL RLock. That lock is released before Build, historical validation and storage.AddAll. These are distinct phases. |

## Consequence for the proposed import

A provider payload, native root existence, or successful historical root validation does not by itself prove current write permission at the point root storage was inserted. Likewise a later body Apply denial does not prove the root left no earlier side effect. The first production gate must retain both root/storage and body/head observations around a real signed ACL change.

The intended proof must name a real linearization point: either a precisely scoped current-writer admission that owns the storage insertion, or an explicitly narrower native permission contract accepted by the owners. It must bind the actual account key/Space and immutable payload; wire account strings, caller booleans and token freshness inferred from UI are insufficient.

Do not wrap the full existing tree creation with an external ACL RLock. The original rebuild/validate path reacquires that lock, and original object initialization may reenter other owners. A pending ACL writer can make nested read locking unsafe. A prospective hook must live within the original native owner and define the lock order, cancellation boundary, collision semantics and behavior after a partial native failure. This checkpoint does not add that hook or change any-sync.

The content path also separates current permission observation from storage commit. That is recorded as a concrete source boundary requiring an exact accepted policy and focused native qualification; it is not asserted to be an already reproduced runtime violation.

## Provenance limit

Heart's original go.mod declares any-sync v0.13.8 without an any-sync replace. Its go.sum records:

```
github.com/anyproto/any-sync v0.13.8 h1:VVcAX/8VHwIB3D3mEaO0v3ojyixrYvaGI1nwgLja3zc=
github.com/anyproto/any-sync v0.13.8/go.mod h1:d56Pxkt2zaK8K9SAEf8KkhBwJx/a6mEGeRY6h717x0w=
```

Primary GitHub API reads resolve the annotated tag `3e5991d928a2a5ead0fcac5bad1806cad4786070` to commit `5d71ccad5db77997df2d2426011ebae4e7600d98`. The tree is complete (795 rows), and each retained source's size/Git blob/SHA256 is independently checked. No module ZIP checksum or earlier runner module-cache source equality is claimed by these reads. The next native gate must bind the actual dependency files it compiles before using this trace as an execution-source admission.
