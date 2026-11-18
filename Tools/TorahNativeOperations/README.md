# T2 native immutable operations and signed-tree transport

This is an isolated **native storage and signed-tree host candidate**, built against Heart
`d98420b1113536afd08cde6de9a5816f6d27ffff`, any-store `v1.0.3`, and Go `1.26.5`.
It implements real StoreState handlers, native write transactions and SQLite
queries. The new host also uses real AnySync encrypted, signed history and
TreeSync replication. It does not replace the existing Swift association repository or enable
a new application capability.

The November 18 contract decision explicitly accepts a claim set for AB03:
offline clients cannot promise a global first writer. Two different immutable
payloads under one logical operation ID are both retained, reported as a conflict,
and never silently resolved by arrival order. A locally ordered mismatching write
is rejected before inserting either a claim or provenance receipt.

## Files and execution

`overlay/core/block/editor/torahops` provides the native operation host. The
source-bound `heart-registration.patch` now adds the approved private type,
receiving-Space checks, source selection, factory dispatch, restrictions and
canonical cache derivation and a private generic-import guard to exactly eleven
pinned Heart files. Additional Go
files implement and test the private adapter. Generic StoreState, fulltext/index,
T5, account/wallet and public RPC sources remain unchanged. The replay handler hooks into
`Handler.BeforeCreate`, inside the existing StoreState/any-store write transaction,
before generic StoreState would ignore `ErrDocExists`.

The runner refuses an unexpected app/Heart SHA or modified tracked source,
records every overlay file hash and the upstream dependency hashes, then runs:

```sh
go test -p 1 -count=1 -timeout=240s -json ./core/block/editor/torahops
```

Use a fresh checkout of the pinned Heart and the exact Go toolchain on PATH:

```sh
python3 Tools/TorahNativeOperations/run_native_operations.py \
  --heart-source build/Heart-T2-Operations \
  --evidence build/t2-native-operations-evidence \
  --expected-app-sha "$(git rev-parse HEAD)"
```

`.github/workflows/pinkha-t2-native-operations.yml` is a reusable Ubuntu 24.04
workflow. It accepts an optional immutable `source_sha`, preserves the GitHub run
ID/attempt/workflow ref, and uploads the raw Go event log and receipt for 14 days.
It has only repository read permission and no release, simulator or user-account
steps. The `component` suite tests this package and its isolated loopback
protocol without Tantivy. A separate `native-registry` job uses the same pinned
Go1.26.5 Alpine image, Tantivy archive and temporary genproto resolution already
used by the T5 Linux proof. It executes focused registry/source/factory tests.
Dependency or compile failure is never counted as native acceptance. See
[REGISTRY_BINDING_20261118.md](REGISTRY_BINDING_20261118.md) for the exact adapter
contract and the narrower boundary-fixture scope.

## Exact identity and encoding

An operation has these typed fields in this order:

1. `version`: unsigned 32-bit integer, currently 1.
2. `spaceId`, `operationId`, `authorId`, `kind`.
3. `target.objectId`, `target.blockId` (empty means object-level target).
4. `source.providerId`, `source.canonicalRef`.
5. `payload`: opaque bytes.
6. `observed`: a set of physical claim IDs.

`operationId` is exactly 16 opaque bytes encoded as 32 lowercase hexadecimal
characters. This component does not invent a timestamp or infer causality from
the ID. The future native RPC must allocate/preserve stable operation IDs.

The content hash input is the ASCII domain `pinkha-t2-operation` followed by one
NUL byte, a big-endian unsigned 32-bit version, then each string above in order,
then the payload, then a big-endian unsigned 32-bit observed count followed by
each observed claim ID. Every string/payload/reference is encoded as a big-endian
unsigned 32-bit byte length followed by the bytes. Text is valid UTF-8, without
NUL. No trimming, case folding or Unicode normalization occurs. Observed IDs are
sorted bytewise and deduplicated before encoding. Payload bytes are not parsed
as JSON, normalized, or trusted to satisfy a provider-specific schema.

The logical key is SHA-256 of ASCII `pinkha-t2-operation-key-v1`, NUL, then the
same length-prefixed space ID and operation ID. The physical claim ID is
`lowerhex(logical-key) + "/" + lowerhex(content-hash)`. Thus identical bytes have
one physical record, while conflicting bytes have separate physical records
under the same logical key. A matching hash/ID with mismatching canonical bytes
fails as a critical error instead of overwriting.

Wire JSON is the exact typed `encoding/json.Marshal` representation of
`{"operation": <Operation>, "digest": <lowercase hash>}`: fields follow the Go
struct order above; there are no omitted fields or whitespace; strings use Go's
standard JSON escaping (including HTML escapes for `<`, `>` and `&`); the payload
uses standard padded base64; empty payload is `""`; empty observed is `[]`.
The decoder re-encodes and compares the entire byte string. Unknown/duplicate
fields, trailing data, alternate key order, noncanonical base64 and whitespace
variants are rejected. No JSON number contributes to identity except the typed
integer version.

The golden vector in `TestCanonicalEncodingGoldenVector` was independently
calculated with Python big-endian length prefixes and SHA-256. It covers Hebrew,
HTML-sensitive characters and a trailing newline. See the code for the exact
188-byte input fields and expected 129-character physical ID.

Bounds: payload 64 KiB; at most 256 submitted observed IDs; space/author/object/
block IDs 1,024 bytes each; provider ID 256 bytes; canonical reference 4,096
bytes; wire JSON 256 KiB. Required identifiers are nonempty. Add and replace
require a provider/ref and nonempty payload. Remove requires observed IDs, empty
payload and empty source. Unknown versions/kinds fail closed.

## Write, replay and provenance semantics

`AppendLocal` obtains a native write transaction before lookup, comparison and
insert. It returns `created`, `already_exists_same_payload`, or
`collision_different_payload`. A repeated existing claim returns the same ID
without adding another physical record or receipt. If a remote conflict already
exists, an identical retry is still successful and its returned `Resolution`
explicitly has `Conflict=true` and includes every stored variant.
Before a new local remove/replacement is inserted, every observed predecessor
must already exist in that same transaction and name the same target. Unknown
or cross-target predecessors are rejected without a write. Native signed-history
causality and permission verification remain host responsibilities.

`Replay` accepts a change that the eventual native host must already have
authorized. It stores every valid variant. Different replay orders converge to
the same sorted immutable claim set and conflict result. Duplicate replay is
idempotent. Both helpers use `ApplyChangeSetReturnAllErrors` and roll back the
whole transaction on an error; a partially applied batch must never be committed.

Each operation's author must equal the native change creator. Native change ID,
creator and ACL head must be nonempty and bounded. Replay receipts are immutable
and keyed by a domain-separated hash of physical claim ID + native change ID.
They preserve each replay's creator and ACL head without making a retry's newer
ACL head change content identity. Reusing the same native change ID with a
different receipt is a critical error. The receipt collection has no generic
StoreState handler, so it cannot be mutated via a client StoreChange.

**Author equality and receipt persistence alone are not ACL verification.**
The original projection component cannot decide whether a signer has native
write permission or whether a target exists. `NativeHost` below adds native
signed-tree authority. The projection helpers remain unsuitable as raw
client-controlled RPCs.

## Removal, replacement and conflicts

An add creates an immutable value. A remove creates an immutable tombstone that
names only physical claims the author observed. A replacement creates a new
immutable value and names its observed predecessor claims. Repeated delivery
does not duplicate a tombstone. A tombstone may arrive before the referenced
claim: the reference remains pending and suppresses that exact claim when it
arrives. An unobserved concurrent add survives.

Concurrent replacements keep both successors and suppress their shared observed
predecessor. There is no display winner. `ReadTarget` sorts surviving physical
IDs bytewise. Removing/replacing a tombstone does not erase its historical effect
or resurrect older content. Restoration requires a fresh add ID. No physical
deletion, tombstone garbage collection or compaction is implemented.

Every logical operation with more than one variant is quarantined from the live
fold: none of its add/remove/replace effects is silently selected. Its complete
sorted variant set is returned in `Conflicts`. This rule can change a previously
displayed projection when a conflict is later discovered; the caller must expose
that conflict rather than treat it as ordinary success. A variant naming another
target still makes the operation conflicted: a target-index lookup rechecks the
whole logical operation in the same read snapshot. No arrival-order winner can
hide behind a narrower target query.

## Reads and limits

Operation and target indexes are actual any-store indexes. All target reads use
one native read snapshot. Results are bounded, and exceeding a bound returns
`ErrReadLimit` with no partial result. `ReadOperation`/receipts are limited to 256
variants/receipts; `ReadTarget` takes an explicit limit from 1 to 10,000. Replay
does not discard extra valid claims because of read bounds. There is no RPC
cursor or performance acceptance claim. The native host adds a local applied
sequence and verified tree-head snapshot, neither of which is an RPC cursor.

The collection namespace binds the space and is intended for an already
account-scoped DB. Tests use only fresh temporary databases. An isolated namespace
does not establish product invisibility, account-switch cleanup or security.

## Original component evidence

The tests use the actual pinned Heart StoreState, real any-store SQLite files,
native transactions and reopen. They cover independent disk projections plus
explicit replay; committed subprocess exit without cleanup/response; identical
retry; ordered mismatch; opposite-order offline conflicts; native receipt
immutability; concurrent local writers; observed remove; concurrent replacement;
late delivery; tombstone retention; raw generic-builder attacks; batch rollback;
cross-space namespaces; native index selection; cancellation and bounded reads.

The original two-store case manually delivers operations to each native projection. It is
**not** a network transport, middleware, two-device or full AB01–08 proof. The
subprocess-exit test is a real process exit after commit, not a power-loss/fsync
guarantee. These are useful native component tests (Tier B plus on-disk/process
durability evidence), not Tier C/D/E product acceptance.

## Signed native host and actual two-process protocol fixture

`native_host.go` derives one AnySync tree per Space with ChangeType
`pinkha.torah.operations.v1` and exact UTF-8 ChangePayload
`store-change/immutable-claims-v1`. The root includes the Space ID and has no
parent page. It is a separate experimental namespace: no existing SmartBlock
numeric type, chat, account object, favorites object or T5 manifest is reused.
The root is deterministic; all operation changes after it are encrypted and
signed by the actual account key. This is not yet an application object-type
registration or a claim of hidden-object lifecycle support.

The canonical durable source is the native tree. Each operation is one real
Heart `pb.StoreChange` containing one create into the immutable claims collection.
The wire uses Heart's existing protobuf/Snappy format (`DataType="1/s"`, compressed
above 64 bytes). Decoding is bounded before decompression. `NativeTreeBuilder`
retains upstream CID/signature/historical-ACL verification and adds content
validation before changes are persisted: no plaintext operations, snapshots,
foreign Space, mismatched author, generic modify/delete, unrelated collection,
unknown format or malformed canonical claim. Tree encryption uses AnySync's
derived tree key, not a new encryption scheme.

`NativeHost.Append` locks the native tree, catches the projection up, opens a real
StoreState transaction, checks logical operation identity/observed predecessors,
and invokes the required native target-validator dependency. It appends through
`SyncTree.AddContentWithValidator`. Creator and captured ACL head are decoded
from the newly signed bytes; neither comes from untrusted RPC metadata. The
native tree checks current write permissions and historical ACL authority. A
successful identical retry does not create another signed change. Different
offline changes remain separate signed records and merge into the same conflict
set on every client.

Native tree and projection use separate native databases, as Heart's existing
store-backed source does. Native storage commits before projection commit. A
projection commit error must return `ErrProjectionBehind`, preserving the native
change ID; it must never be overwritten by a subsequent successful lookup.
Reopening/catching up uses native tree iteration, actual signed author/ACL
metadata and StoreState's `MarkFullyReplayed`/`AddSeq` machinery. The first replay
walks complete genesis history; incremental reads follow the real local add
sequence only after that replay. `Update`/`Rebuild` are actual SyncTree listeners.
The transport tests never call the component `Replay` helper to exchange changes.

`ReadTarget` returns the projection, sorted verified tree heads and local applied
sequence under the tree lock. The sequence is local to one peer and must not be
compared between peers or advertised as a global version. There is no partial
success when projection catch-up fails.

Opening the host and reading a target also require the supplied internal host
key to have **current locally verified ACL read permission**. Reader, Guest,
Writer, Admin and Owner are allowed; missing, removed and unknown permissions
are denied. Both operations hold the ACL read lock from authorization through
the complete projection open/read, in tree-then-ACL lock order. Historical
`HadReadPermissions` and possession of old decryption keys are not authorization.
This closes a review finding in source `12bef033`: that source's preserved
54-pass transport proof did not test the current-read guard. The added regression
cases apply actual signed account-add/remove ACL records and retain a populated
projection: current readers/guests can read but cannot write; a foreign key and
a member whose removal is already known locally cannot open or return a cached
snapshot. This is not a claim that an offline client knows remote revocations.

`native_transport_test.go` launches two OS processes with separate peer keys,
native SQLite stores, projection stores and loopback TCP listeners. They are two
devices of the same disposable account, with a real signed owner ACL root. It
uses generated `SpaceSync.ObjectSyncRequestStream` DRPC messages, the upstream
TreeSync request factory/response producer/collector, real verified SyncTrees
and native update listeners. The fixture suppresses background head broadcasts
to schedule an offline partition explicitly, then performs actual full-sync
requests in both directions. It does not transport operation JSON over a custom
mock channel. Standard input is only test control, never peer replication.

Focused checks cover disconnected union, duplicate native delivery, both process
restarts; offline operation-ID conflicts and later ordered rejection; observed
remove with an unseen add; concurrent replacements; process exit after commit
before replying, retry on both devices and one native provenance receipt;
corrupted native wire rejection; and rebuilding a new projection DB from signed
history. Additional native host cases reject wrong author/Space, absent target,
unbound block, canceled request, an unauthorized signing key, plaintext,
snapshot and unrelated collection writes. The logs record process IDs and real
DRPC request/response/byte/change counts. Disposable private keys are written only
inside the test temporary directories and are never part of evidence artifacts.

These are AB01–05 **native protocol subsets**, not completion of those acceptance
rows. The fixture does not run Heart middleware, a coordinator, production peer
authentication, ACL invitation/revocation transport, an actual editor block
graph, ordinary hidden/search/export/undo behavior or iOS. Target validation
checks real disposable native object roots; cross-object deletion races and
block authorization remain an explicit App binding dependency. Unknown-format
rejection must be included in the eventual mixed-version capability contract.

Receipt schema 3 separates `PASS_NATIVE_COMPONENT_AND_LOOPBACK_TRANSPORT`
from `PASS_PRIVATE_NATIVE_REGISTRY_ADAPTER`; full T2 acceptance remains `NOT_RUN`.
Each suite requires its exact test identities and every package result. Missing
or skipped required execution cannot pass. Historical schema-1/schema-2 evidence
remains byte-preserved with its original scope.

## Remaining acceptance before app binding

T2 stays open. The private fork-local SmartBlock allocation and source/factory
adapter are implemented in this isolated overlay, with source-bound tests ready
for Linux execution. Their current acceptance state is recorded only by the
corresponding actual registry receipt. The previous 61-pass Linux writer proof
predates this registry change and cannot accept it.

Still required: actual older-client preservation, ordinary search/export/undo
and account/Space removal behavior through full middleware, production peer/ACL
transport, public RPC/capability contract and indexed bounded pagination,
concurrent target lifecycle acceptance, encrypted backup/retention, performance
and Swift binding. The adapter checks current native target lookup but has no
cross-tree atomic transaction. It preserves orphaned claims and does not silently
retarget or erase them. The existing scalar association path remains unchanged.

App capability stays OFF and the private host is not created during startup.
No user data migration or release is requested by this native proof.
