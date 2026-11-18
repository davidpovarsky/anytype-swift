# Native T2 ACL lock and write-authority audit

Source review on 2026-11-18, before App binding. This is a source receipt, not a new runtime PASS.

## Source identity

- Anytype overlay reviewed: `b815465f096b1786bb41d21c25248e9986db25ee`.
- Heart: `d98420b1113536afd08cde6de9a5816f6d27ffff`.
- Heart's pinned AnySync module: `github.com/anyproto/any-sync v0.13.8`.
- Native test toolchain: Go `1.26.5`; no new Windows compilation was started for this audit.
- All paths below are relative to the respective pinned repository/module, not an unspecified latest checkout.

## Open/read lock graph

`OpenNativeHost` and `NativeHost.ReadTarget` acquire **Tree.Lock → ACL.RLock**, check the host key's current `AclState.Permissions`, and retain that ACL read lock through replay and the returned projection. The allowed read roles are Reader, Guest, Writer, Admin and Owner. Historical `HadReadPermissions` is deliberately not authority for a current request.

| Called path | Exact pinned source | ACL locking within the path |
| --- | --- | --- |
| `recoverLocked → SyncTree.IterateRoot` | AnySync `commonspace/object/tree/synctree/synctree.go` | `checkAlive` reads local closed/deleted flags, then delegates. No ACL access. |
| `ObjectTree.IterateRoot → IterateFrom → Tree.IterateSkip` | AnySync `commonspace/object/tree/objecttree/{objecttree.go,tree.go}` | Iterates already verified native history and decrypts using `ot.keys`. No ACL acquisition or validator call. |
| `recoverLocked → SyncTree.IterateAfterAddSeq` | AnySync `commonspace/object/tree/synctree/synctree.go` | Same `checkAlive` and delegation, without ACL access. |
| `ObjectTree.IterateAfterAddSeq → Storage.GetAfterAddSeq → ChangeBuilder.Unmarshall(false)` | AnySync `commonspace/object/tree/objecttree/{objecttree.go,storage.go,changebuilder.go}` | Reads persisted changes and uses `ot.keys` for decryption. Unmarshal decodes native bytes; no ACL access. |
| Conversion/application callbacks | Overlay `native_host.go`, `store.go`, `projection.go`; Heart `core/block/editor/storestate` | Decode/author-binding/immutable StoreState application and any-store transactions. These callbacks do not call ACL APIs. |
| Current ACL update | AnySync `commonspace/object/acl/{list/list.go,syncacl/syncaclhandler.go}` | `AclList` embeds a Go `sync.RWMutex`. Sync handlers take its write lock to apply records. Applying records does not acquire this object tree lock or invoke its replay listener. |

There is **no recursive ACL read acquisition** under the b815 open/read guard in these exact pinned paths. A pending ACL writer therefore does not introduce the suspected recursive-reader deadlock. This conclusion is source-bound; a dependency change adding ACL locking to iteration must be reviewed. Projection DB and native tree DB remain separate, as required by `OpenNativeHost`.

## Write authority and revocation boundary

`NativeHost.Append` holds the tree lock, checks current `CanWrite` under a short ACL read lock, and releases that ACL lock before replay/target validation/native append. It must not wrap the complete `AddContentWithValidator` call in an ACL read lock: that native call acquires ACL read locks itself, which would create a recursive-reader deadlock with a waiting writer.

The authoritative preparation path is AnySync `objecttree.go: prepareBuilderContent`: it takes ACL.RLock, rechecks **current** `Permissions(content.Key.GetPublic()).CanWrite()`, obtains the current encryption key and ACL head, and then releases ACL.RLock. `AddContentWithValidator` builds/signs that captured content. Its separate `validateTree` lock calls `objecttreevalidator.go: validateChange`, which verifies `PermissionsAtRecord(c.AclHeadId, c.Identity)` and the history relationship. Storage persistence follows afterwards.

Consequences:

1. A removal already present before the host preflight rejects both a new append and a retry of acknowledged bytes, with no new tree/projection mutation.
2. A removal applied after host preflight but **before native preparation** is caught by the native current-permission recheck. `TestNativeCurrentWriteAuthority` now exercises this deterministic interleaving with real signed ACL records and key rotation, through the existing target-validation callback.
3. A removal concurrent with the operation **after native preparation has captured an authorized ACL head** may complete before the operation reaches `storage.AddAll`. The pinned native validator uses the captured historical head; this audit does not claim an atomic current-ACL check through durable commit. A stronger cross-log commit-order guarantee is a separate native contract and is not supplied by adding an outer ACL read lock.
4. No client can claim knowledge of an ACL removal that has not yet reached its locally verified log. These tests concern known local state; they do not exercise production ACL transport or coordinator acceptance.

## Runtime evidence boundary

The earlier native transport PASS (18 top-level tests and 36 subtests) is tied to overlay `12bef033a3fd217b67c0e9f2af77e242b487fad6`. The current-read guard and new writer-revocation cases require Linux execution at their exact source SHA. Until that run succeeds, their status is **NOT_RUN**. Full T2, middleware/RPC, hidden lifecycle, block-target deletion races and iOS remain outside these component/protocol proofs.
