# T2 native immutable operation component

This is a new, isolated **native storage component**, built against Heart
`d98420b1113536afd08cde6de9a5816f6d27ffff`, any-store `v1.0.3`, and Go `1.26.5`.
It implements real StoreState handlers, native write transactions and SQLite
queries. It does not replace the existing Swift association repository or enable
a new application capability.

The November 18 contract decision explicitly accepts a claim set for AB03:
offline clients cannot promise a global first writer. Two different immutable
payloads under one logical operation ID are both retained, reported as a conflict,
and never silently resolved by arrival order. A locally ordered mismatching write
is rejected before inserting either a claim or provenance receipt.

## Files and execution

`overlay/core/block/editor/torahops` is a new package added to an otherwise
unchanged upstream Heart checkout. No generic StoreState, fulltext/index, T5,
application or RPC source is modified. The replay handler hooks into
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
steps. Only the component package is tested. No Tantivy artifact is required by
the component source; a transitive dependency failure must be reported as such.

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

**Author equality and receipt persistence are not ACL verification.** This
component cannot decide whether a signer currently has write permission or
whether a target exists. The future signed host must supply and validate native
metadata, bind the active account/space and perform target/permission checks in
the appropriate native transaction. The current helper must not become a raw
client-controlled RPC.

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
does not discard extra valid claims because of read bounds. There is no cursor,
native synchronization watermark or performance acceptance claim yet.

The collection namespace binds the space and is intended for an already
account-scoped DB. Tests use only fresh temporary databases. An isolated namespace
does not establish product invisibility, account-switch cleanup or security.

## What the tests prove

The tests use the actual pinned Heart StoreState, real any-store SQLite files,
native transactions and reopen. They cover independent disk projections plus
explicit replay; committed subprocess exit without cleanup/response; identical
retry; ordered mismatch; opposite-order offline conflicts; native receipt
immutability; concurrent local writers; observed remove; concurrent replacement;
late delivery; tombstone retention; raw generic-builder attacks; batch rollback;
cross-space namespaces; native index selection; cancellation and bounded reads.

The two-store case manually delivers operations to each native projection. It is
**not** a network transport, middleware, two-device or full AB01–08 proof. The
subprocess-exit test is a real process exit after commit, not a power-loss/fsync
guarantee. These are useful native component tests (Tier B plus on-disk/process
durability evidence), not Tier C/D/E product acceptance.

## Remaining acceptance before app binding

T2 stays open. The dedicated native hidden object type/Space host and signed
change-tree append are not implemented. Neither are the atomic native ACL/target
checks, public RPC/capability contract, bounded indexed RPC pagination/watermarks,
true two-process same-Space transport harness, hidden lifecycle/cleanup and
ordinary search/export/undo behavior, encrypted backup/retention, mixed-version
migration, or Swift binding. The existing scalar association path is not made
concurrency-safe by this standalone component.

The next integration step must register the sanctioned host and bind append/read
to native authority and signed history, then execute AB01–08 using two independent
Heart processes and stores in a disposable synced Space. No existing user data
should be migrated until that evidence and the version/capability contract exist.
