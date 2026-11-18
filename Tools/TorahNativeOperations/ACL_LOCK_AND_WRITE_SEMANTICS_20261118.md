# Native T2 ACL commit fence and write-authority audit

The current change is based on Anytype `6959300744dce744259092ed6b0d2c8ecf291f73`.
It closes the locally observed ACL check-to-commit gap and preserves the identity
receipt when native storage succeeds but head-update construction later fails.
Source review and real Go formatting are complete; compilation and Native
acceptance require the new source-bound Linux run. They are **NOT_RUN** at the
publication of this change.

## Pinned source

- Heart: `d98420b1113536afd08cde6de9a5816f6d27ffff`.
- AnySync: `v0.13.8`, commit `5d71ccad5db77997df2d2426011ebae4e7600d98`.
- Go: `1.26.5`. The four changed Go files passed the real pinned formatter with
  byte-identical output. No Windows compilation was performed.
- `heart-registration.json`, `rpc/heart-rpc.json` and `account_rpc/fixture.json`
  bind the new source inventory through the existing release-family checks.
  The protobuf schema and generated-byte mapper are unchanged.

## Local append contract

`NativeTreeBuilder` now returns a private ObjectTree wrapper and a private
Storage wrapper. `OpenNativeHostLocked` verifies the storage, ACL and root
binding before projection replay. Each host append issues a private context
token for one synchronous local `AddContentWithValidator` call while holding
its private-tree lock. The token is not an RPC field. An absent, foreign or
already used token cannot authorize a local AddContent call.

Preparation and the historical native validator still perform their existing
checks. Once they release their own ACL locks, the Storage wrapper re-decodes
the exact prepared signed bytes and, immediately before `Storage.AddAll`, takes
`ACL.RLock`. It rechecks the native signer, current locally verified `CanWrite`
and equality of the signed `AclHeadId` with the current ACL head. Cancellation
is checked again before the real write. A changed ACL head requires a fresh
append attempt, even if the signer remains a writer. The existing wire error
mapping conservatively reports permission denial; no success or receipt is
returned for that rejected prepared change.

The ACL read lock remains held through the actual native DB transaction commit,
then is released before SyncTree builds its head update, broadcasts, or commits
the separate projection. It is never an outer lock around the whole
`AddContentWithValidator` call, so native preparation does not recursively
acquire the same read lock while a writer waits.

This contract covers the locally verified ACL. It does not claim awareness of
remote ACL records that an offline client has not received.

## Durable receipt and replay

Pinned `objecttree/storage.go` assigns `AddSeq` in the original change slice and
returns success only after its deferred DB commit succeeds. The guard records
that exact committed change. NativeHost uses this durable witness to preserve
`Created`, ClaimID and ChangeID even when SyncTree subsequently returns an
error from `CreateHeadUpdate`. The original error remains an error. Projection
failure additionally retains `ErrProjectionBehind`; an identical retry can
recover the projection without another signed operation.

The byte mapper already retains identity-only receipt metadata after an error
and suppresses the cached payload resolution. A stored change is therefore not
reported as if it never happened, nor is a partial receipt presented as remote
synchronization acceptance.

Remote `AddRawChanges` and deferred receiving-storage replay retain the existing
historical signature, CID, content and ACL checks. A later membership removal
does not erase an earlier valid signed operation. A local token cannot be used
for the remote replay entry points.

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

There is **no recursive ACL read acquisition** under the open/read guard in these exact pinned paths. A pending ACL writer therefore does not introduce the suspected recursive-reader deadlock. This conclusion is source-bound; a dependency change adding ACL locking to iteration must be reviewed. Projection DB and native tree DB remain separate, as required by `OpenNativeHost`.

## Synchronous storage observer boundary

The pinned native `Storage.AddAll` calls `HeadStorage.UpdateEntry` before DB
commit. `UpdateEntry` invokes its observers synchronously, so these callbacks
were audited as part of the new ACL lock scope. The complete pinned production
registrations contain only AnySync `diffSyncer` for this HeadStorage; Heart's
five production AddObserver calls target Chat/PeerStore services instead.

`diffSyncer.OnUpdate` only enqueues into `headUpdater`. Its `mb/v3 v3.0.3`
queue is created with size zero, has no capacity wait, and releases its mutex
after enqueue/signalling. The worker returns from `WaitOne` without owning
that mutex before calling `DiffManager.UpdateHeads` and the subsequent DB
update. The producer can briefly still hold its mutex when the worker wakes,
but it does not wait for the worker. No nested ACL read lock or target/private
tree acquisition occurs in the synchronous callback. This is a source-bound
lock audit, not a new Native runtime result; changing dependencies or observer
registrations requires reviewing this boundary again.

## Required Native evidence

The existing `t2-native-operations` route runs the complete component package
and the existing registry adapter package set. Its component acceptance gate
now explicitly requires these four new methods and all seven named subcases:

- `TestNativeLocalAppendRequiresCommitGuard`: unguarded AddContent, unguarded
  AddContentWithValidator, a foreign guard, and an unbound constructor.
- `TestNativeACLCommitFence`: signed revocation after preparation, ACL-head
  advance while the author remains a writer, and request cancellation.
- `TestNativeCommitReceiptAfterHeadUpdateFailure`: the real native storage write,
  ACL writer exclusion on both sides of its commit, lock release before head
  update construction, preserved receipt, persisted signed readback and an
  identical retry with no state change.
- `TestNativeCommitGuardKeepsHistoricalReplay`: receiving the earlier valid
  signed operation after its writer was removed locally.

Those are 11 required terminal events, counted separately from the existing
suite. The four existing malformed/plaintext/snapshot/foreign-content cases
receive the legitimate internal one-call token and additionally reject
`ErrNativeCommitGuard` as their failure reason. This preserves their original
purpose: reaching the native content validator instead of passing at an
earlier guard.

These component tests use real native ACL/storage machinery. They do not by
themselves establish a middleware two-client permission race, two iOS clients,
power-loss durability or full T2 acceptance. The earlier accepted runs remain
tied to their original source and are not retroactively acceptance of this fix.

## Still open

Target validation still has its separately tracked lifecycle gap. A target
SmartBlock lock alone cannot serialize with a whole-document deletion intent
that is first written to the Space settings tree. The settings/target/private
lock contract, first-root creation behavior, orphan reads, indexed paging and
the remaining original Tier C/D matrix are not closed by the ACL fence.
App capability remains **OFF**.

The current-write audit at `b815465f096b1786bb41d21c25248e9986db25ee`
correctly documented the previous gap: revocation after native preparation
could finish before the operation's durable write. That historical source
observation is the reason for this change, not the claimed behavior of the new
guard. Runtime results for the new guard must come from its own run and SHA.
