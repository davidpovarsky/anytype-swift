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

## Accepted native permission contract

The agreed production contract is authentic current-writer admission using the actual retained application, account key and regular Space, followed by accurately reported historical completion. A failed currentness or readback check grants no positive ACK. This is not an atomic promise that no storage insertion can occur after a concurrently arriving revocation.

The real root and content paths have different current/historical admission stages, as shown above. B/C must check the actual current writer before starting and at each closed assignment/create boundary, preserve native Apply permission failures, and recheck currentness before positive readback publication. If revocation arrives after a successful native admission, earlier/later native effects remain historical evidence; cancellation or refusal does not imply rollback. A signed-revocation test must name which admission happened first and inspect actual root/body heads, rather than assume a global transaction.

No new any-sync fence, nested external ACL RLock or rewritten storage engine is proposed. The original implementation remains the owner of its native permission and storage ordering. The source trace is a qualification boundary, not an already reproduced violation. Unknown or partial outcomes recover by their actual mapped identity, never by blind reimport.

## Provenance and actual compiler input identity

Heart's original go.mod declares any-sync v0.13.8 without an any-sync replace. Its go.sum records:

```
github.com/anyproto/any-sync v0.13.8 h1:VVcAX/8VHwIB3D3mEaO0v3ojyixrYvaGI1nwgLja3zc=
github.com/anyproto/any-sync v0.13.8/go.mod h1:d56Pxkt2zaK8K9SAEf8KkhBwJx/a6mEGeRY6h717x0w=
```

Primary GitHub API reads resolve the annotated tag `3e5991d928a2a5ead0fcac5bad1806cad4786070` to commit `5d71ccad5db77997df2d2426011ebae4e7600d98`. The tree is complete (795 rows), and each retained source's size/Git blob/SHA256 is independently checked. Current run 45130249062 now supplies that actual source identity: all seven retained primary source SHA256 values match the actual Apple declared compiler inputs, and the module Sum matches the original go.sum. Evidence commit9357b53ff8230128d1f3340118ec152770feb12a retains ANY_SYNC_ACTUAL_INPUT_MATCH.json (SHA256c5120dc9a5eb05ec68e43dcc2bb01c0e928b39c5d9d05880d5b5b916079b50fe). This binds source identity; it does not claim a new permission-race runtime result or a module ZIP reproduction.
