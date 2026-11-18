# Private T2 native registry adapter — 2026-11-18

## Current status

Source implementation and focused tests are prepared against immutable Heart
`d98420b1113536afd08cde6de9a5816f6d27ffff`. Formatting and patch/hash validation are
available before publication. Native execution of this new source is **NOT_RUN**
until its own Linux receipt exists. The earlier 61-pass writer authority run
44218461051 proves the previous host source only. App capability remains OFF.

## Identity and receiving Space

The owner-approved allocation is fork-local Go type `PinkhaTorahOperations`,
`0x504B0001` (decimal 1347092481). It is deliberately absent from the generated
upstream protobuf enum. A test compares the allocation against the pinned
`model.SmartBlockType_name`; upgrading the pin requires collision review.
No claim of an upstream reserved number is made.

The unique key is `pinkhaTorahOps-v1`. The actual native wire identity is
unchanged from the signed two-process proof:

- ChangeType: `pinkha.torah.operations.v1`.
- ChangePayload: exact bytes `store-change/immutable-claims-v1`.
- Derived encrypted root, exactly one per Space, no page parent, no random seed,
  no personal-Space account-signature variant.
- Operations remain signed/encrypted StoreChange immutable claim creates.

`torahopscontract` owns canonical derivation and complete root comparison.
The receiver supplies its Space independently; CID, raw header bytes and all
root metadata must agree. Enum values in generic `anytype.object` payloads cannot
allocate this private host. Type-cache hits and virtual prefixes cannot bypass
the receiving-Space check. Missing Space and unknown future wire versions fail.
The allocation does not reuse T5 manifest/public/private derived property keys.

## Registry, source and native tree

The dedicated type is valid, store-backed and explicitly nonindexable for all
three existing index-policy outputs. It gets every existing generic object
mutation restriction, including delete, duplicate, publish, type and layout.
Generic random creation and private account-signature derivation are rejected.
Cache derivation accepts only the canonical `v1` root. Direct creation/import
cannot inject private populated history through generic PutTree; imported native
history must enter the receiving private builder and validator.

`BuildTreeOptsForSpace` chooses the private NativeTreeBuilder/NativeTreeValidator
before interpreting history. They retain actual AnySync CID/signature/ACL checks
and validate the operation collection/author/Space/encryption/content contract.
The dedicated source exposes only a local id/Space/hidden metadata State to the
cache. It is not `source.Store`, never installs a competing block listener and
rejects generic PushChange. Generic BuildState rejects private history before
using a block-change decoder. NativeHost exclusively owns the SyncTree listener
and recovers its replayable StoreState projection.

## Factory and locks

Factory InitObject already holds the source tree lock. It invokes the private
base initialization and `OpenNativeHostLocked`; it never re-enters the ordinary
locking constructor. Private initialization only establishes cache/close/state
plumbing. It skips document relation/layout injection, block migrations, generic
Apply and indexing. The factory returns immediately after private init.

AppendTorahOperation and ReadTorahTarget obtain their own host tree lock; callers
must use an object returned by GetObject and must not invoke them inside Space.Do
on that same host. These are internal native methods, not an App RPC. The shared
current locally verified read/write ACL guards stay in NativeHost. ACL/history
semantics remain those in ACL_LOCK_AND_WRITE_SEMANTICS_20261118.md.

The adapter obtains its projection DB from existing
`anystoreprovider.GetCrdtDb(spaceID)`: `<account>/objectstore/<space>/crdt.db`.
Native tree storage is separately owned at `<storage-root>/<space>/store.db`.
Source audit: provider getter and DeleteSpaceData in
`pkg/lib/datastore/anystoreprovider/provider.go`, native storage path in
`space/spacecore/storage/anystorage/storageservice.go`. Existing Space deletion
closes/removes the projection directory and tombstones outstanding getters.
No new global DB owner, cleanup service or account startup creation is added.

## Target lifecycle contract and limits

The adapter resolves targets through its receiving Space's native object lookup.
It requires a Page or Template in that same Space, not marked deleted/uninstalled;
a nonempty block ID must exist in the object's current State. The host's own ID
is rejected before target lookup to avoid reacquiring the same tree lock.

Append is checked at the adapter boundary and again by NativeHost's callback
before a new signed operation. Read validates current target availability before
returning a projection. An unavailable target rejects even a retry at this host
adapter boundary; the already durable receipt remains in native history.

This is a **non-atomic two-tree contract**: a target can be deleted after its
check while the independent operation tree commits. Orphaned claims persist;
there is no automatic journal deletion, target substitution or late destructive
cleanup. Restoring the same stable object/block IDs makes the retained claim
readable again. Full middleware deletion/export/backup/ACL transport and the
public RPC contract must accept this behavior before enabling App capability.

## Focused proof and boundaries

The component suite retains all existing real disk, ACL and two-process native
transport cases. New cases exercise a constructor while the caller holds its
actual native tree lock and receiving validation of actual signed history,
foreign Space, malformed heads and corrupt CID.

The registry suite uses actual canonical roots, the allocation/prefix registries,
source routing, base SmartBlock/factory initialization, signed AnySync native
storage and provider-owned CRDT databases. It checks generic mutation denial,
no initialization changes, separate physical SQLite files, reopen into a fresh
projection, provider cleanup/tombstones, source refusal to decode block history,
foreign/missing/removed targets, block removal and retained orphan history.

The factory fixture uses explicit service-boundary adapters for source lookup
and target lookup; target documents are real Heart State values. The separate
source fixture executes the actual source service and native tree builder.
Neither fixture is a full middleware account or production coordinator test.
A green registry suite cannot claim old-client preservation, full search/export,
production peer authentication, atomic target lifecycle, App/RPC or iOS coverage.

## Reproducible source and dependencies

`heart-registration.json` hashes the exact patch, ten original/patched Heart
files and all 26 Go overlay files. The runner requires exact app/Heart SHAs,
clean tracked inputs, matching baseline hashes, a successful git-apply check,
matching applied hashes, unchanged Go modules and Go1.26.5. It checks formatting
and every suite's required test identities/package results; partial or empty
execution cannot pass. Five controller checks cover false-success rejection.

The component job remains Ubuntu24.04 with Go1.26.5 and no Tantivy dependency.
The separate registry job uses the previously proven musl closure:

- `golang:1.26.5-alpine@sha256:111d79159b2326f7e80c4a4706e1ba166acb0e2611df853955f3621828cd49e8`.
- Existing build_custom_heart.py dependency helper, Tantivy v1.0.6 asset
  `linux-amd64-musl.tar.gz`, SHA-256
  `88b34e006707bfec2d29e8b26405f67cbb975d06fd4ea164da856d0084aaabbc`.
- Temporary Go workspace selects reviewed root genproto
  `v0.0.0-20241021214115-324edc3d5d38`, verifies both module and go.mod h1 sums,
  and leaves the pinned Heart go.mod/go.sum unchanged.
- Static qsort_r compiler probe, musl compiler/unwind runtime, source-bound logs,
  2 CPUs / 6 GiB container limit, serial Go package compilation and bounded tests.

CI uploads each suite's raw JSON test log and receipt for 14 days, including
bootstrap/compile failures. It has read-only repository permission, no release,
no simulator matrix and no access to personal account data. Actual receipts,
not this source document, determine acceptance status.
