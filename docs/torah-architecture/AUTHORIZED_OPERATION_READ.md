# Authorized operation read v1

`pinkha-authorized-operation-read-v1` is an additive shared read contract. The
current default Any v9 artifact does not advertise it. Existing append, target
read, canonical operation bytes and full-T2 capability flags remain unchanged.

## Authority and result

The application supplies only the canonical 32-character lowercase operation
ID. An adapter owns its engine, account, Space and session generation. Those
values bind delivery; they do not grant caller-selected permissions.

The native reader acquires verified private history and current native read
authority. It discovers a bounded complete logical operation closure, releases
discovery locks, acquires every distinct target and definition dependency, and
repeats the complete operation query. A changed closure or any unavailable,
denied or ambiguous target refuses the entire result. No partial operation,
source identity, conflict witness, canonical bytes or provenance is released.

| Result | Meaning |
| --- | --- |
| `found` | All current local variants passed the native authority checks. |
| `absentInVerifiedLocalSnapshot` | This verified local private-tree snapshot contains no variant for the ID. This says nothing about other devices or unsynced history. |
| `historyUnavailable` | An existing verified private history cannot be acquired. The reader never creates or installs a private tree to answer a read. |
| `targetStateUnavailable` | At least one target's current eligibility or reachability cannot be established. No payload is returned. |

A found variant preserves its original content-derived claim ID, operation,
author and Space IDs, target, exact canonical bytes and native creator/change/
ACL provenance. Variants are sorted by claim ID and unique. A result with more
than one variant is a conflict closure, not an arbitrarily selected winner.

## Target reachability

- `liveDocument`: an existing eligible native document with current read
  authority; the original operation has no block target.
- `liveBlock`: the operation's block has a structurally valid current path to
  the document root under the same native target snapshot.
- `unreachableBlock`: the document is still live, eligible and authorized, but
  the requested block path is absent or has a native tombstone. This does not
  assert that the block was deleted or ever existed.

A malformed or cyclic requested path fails closed. Unrelated orphan history
need not be scanned. A missing or deleted whole object does not return an
orphan payload: signed tombstone authority and original target eligibility
have not been established by this contract.

## Bounds and snapshot identity

The maximum complete closure is 256 variants. The actual encoded native
response, including framing, duplicated metadata and Base64 expansion, must be
at most 4 MiB. The shared Swift value also imposes a decoded canonical/provenance
budget; that additional check does not replace the transport limit.

The 64-character native snapshot token identifies the acquired local snapshot
and authority. It is not a causal sequence, replica watermark, permission token
or authorization that survives an account switch. The adapter rechecks its
owned session after awaits and prevents an invalidated or cancelled read from
releasing a value.

## Native implementations

Any performs two `NativeReadSnapshot` calls. The final one holds the private
tree, all target trees and native definition dependencies, current Space ACL,
and a single projection transaction. `GuardReadyLocked` and the existing signed
native handler establish projection provenance. The new read validates every
stored canonical identity and emits exact canonical bytes. It uses the existing
`logicalKey` index, not a whole-Space scan. The HTTP handler buffers and bounds
the complete encoded response before writing it.

The Swift decoder negotiates the explicit contract, maximum variants and maximum
bytes. It rejects incomplete capabilities and unsupported runtimes without a
legacy fallback. The retained runtime therefore remains usable for its accepted
capabilities without implying support for this new read.

Heart composes a separate additive native overlay with the existing production
overlay and RPC boundary. Its native reader and generated transport are reviewed
and validated independently; the shared Swift result does not itself claim to
verify native signatures.

## Acceptance scope

Focused tests exercise the new native authority/closure and adapter lifetime
paths. Prior accepted unrelated suites are retained. Completing this slice does
not complete full T2: reverse-source pagination/index readiness, backup/import,
causal ordering, complete two-client acceptance and negotiated iOS runtime
proof retain their independent acceptance requirements.
