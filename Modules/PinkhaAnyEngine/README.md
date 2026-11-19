# Pinkha Any engine adapter

This package implements the canonical Torah operation contracts over Any's native
HTTP interfaces. Two storage lanes are explicit; there is no silent fallback
between them and no automatic migration of existing user spaces.

## Storage contracts

| API | Native contract | Intended use |
| --- | --- | --- |
| `AnyTorahClaimsRepository` | Generic shared-record bundle on unmodified Any v0.5.0, original source `88fae2e5ae7d0f46d6707567a3123081faa8de9a` | Release-engine interoperability and diagnostics. It cannot supply the guarded native module's final target/authority transaction. |
| `AnyGuardedTorahClaimsRepository` | Versioned `pinkha-torah-native-v1`, bundle `pinkha/torah-native/v1`, canonical dataset `pinkha_torah_claims_v1`, module `pinkha_torah_native` | Native app integration after exact capability and installed-root verification. |

Installation is explicit. Read APIs discover and validate an existing root; they
never install or heal it as a side effect. The guarded module uses dedicated
native snapshot/watch routes and native `modify` writes. Its data must not be
queried through stock query, history or subscription routes.

The generic lane remains useful evidence for the public engine baseline. Its
per-repository serialization and client preflight checks are not a substitute
for the guarded module's server-side invariant enforcement.

## Preserved operation semantics

The canonical binary T2 operation identity matches the pinned native Go golden
vector at original app source `90fcb6033ca4f8aecf8e04d4959cf06fb104adf9`.
Payload is opaque bytes: Hebrew, unknown canonical JSON fields, provider metadata,
licenses, provenance and quote-instance identity are preserved without rewriting.

Distinct payloads under one logical operation ID remain separate immutable
claims. All conflicting variants are quarantined from the live fold, including
variants naming other targets. Observed remove retains unseen adds; concurrent
replacements retain both successors. Referencing a tombstone never resurrects
old content. The fold rejects malformed records, mismatched hashes/creators and
invalid operation shapes rather than guessing a winner.

Native record keys are a reversible 128-hex encoding of logical identity and
content digest. Guarded snapshots require canonical fields, creator equal to the
operation author, and native change/ACL-head provenance. Native provenance fields
are checked as part of the contract; this Swift package does not independently
verify the entire engine's cryptographic DAG from HTTP metadata.

HTTP 200 responses are inspected for top-level and per-page rejections. Writes
are read back before acknowledgement. Guarded exact retry still traverses native
`modify`, so current target and writer checks execute even when the record is
already present. Native `pinkha.ordered_operation_collision` maps to an explicit
collision; concurrent incoming variants remain retained. An uncertain transport
outcome can produce a readback acknowledgement only after exact canonical
reconciliation. It is not proof of permission at a failed dispatch.

## Complete document snapshots

`readObjectSnapshot(objectID:limit:)` uses the native
`/pinkha/objects/:objectId/claims` route and demands the explicit
`object-logical-closure` envelope. The closure contains all claim history for
that object plus every global variant of each seeded logical key. Foreign
collision witnesses are folded before target selection. They cannot be removed
early merely because they name another object.

The response also carries native `reachableClaimBlockIds`, read under the
target/root/type/authority contract. Orphan or removed block history remains
immutable history, but consumers do not present it as current reachable block
content. A foreign witness with an omitted foreign predecessor is harmless only
because the conflicting logical group is quarantined before observed-reference
processing; focused tests cover that ordering.

The object snapshot is explicitly distinct from the complete workspace snapshot.
The global decoder rejects object-scoped envelopes. Migration and diagnostics
may still request the complete bounded workspace; ordinary document reads and
appends use the indexed object closure. An unrelated large Space therefore does
not force every document operation to scan its entire history.

Both native envelopes fail on a partial response, wrong workspace/root/target,
malformed readiness or provenance, and aggregate overflow. Current bounds are
10,000 closure records and 16 MiB of complete encoded response, with 256 variants
per logical operation. These are hard acceptance limits, not pagination that may
silently omit a conflicting variant.

## Live queries and lifetime fences

Generic `watch(session:limit:)` materializes an atomic initial query window and
then applies whole native changes frames. `doc` is authoritative, including a
reread whose version ID is empty. A deleted immutable claim invalidates the view.

Guarded `watch` and `watchObject` consume native complete-state snapshots.
The first event must be a full initial snapshot. Later events replace the
complete state atomically; they are not a promise to deliver every operation.
Existing immutable rows cannot disappear or change. A reused native readiness
generation must describe the same records, provenance and reachability.

`AnyStreamSession` belongs to one managed engine/account lifetime and exposes a
generation fence. Invalidate it before switching the lifetime; this cancels
registered native streams and mapped consumer tasks. Call `requireActive` after
awaited authority checks and at final UI publication, since a queued value may
otherwise arrive after an account switch.

The shared SSE parser handles split UTF-8 and CRLF, rejects malformed/truncated
frames, and bounds both individual events and materialized state. Bounded output
queues terminate on overflow. Native error events, EOF, cancellation, authority
loss or incomplete state require a new connection and full snapshot. No
Last-Event-ID replay, implicit recovery cursor or polling substitute is invented.

The URLSession callback bridge serializes delegate callbacks and protects its
mutable state with a lock. Yield, finish and cancellation execute outside that
lock. Its narrowly scoped `@unchecked Sendable` annotation documents the
Foundation callback boundary; the ordinary redirect delegate is stateless.

## Transport and managed runtime

Only literal loopback HTTP endpoints are accepted and redirects are rejected,
including requests made through an injected URLSession. Query values are encoded
with URLComponents rather than concatenated into paths. Optional opaque
`AnyHTTPAuthorization` installs the managed runtime token on JSON and SSE
requests; descriptions are redacted.

Account pre/post checks detect a changed account but cannot atomically stop an
unrelated process from switching a server during a request. Production callers
must own the embedded runtime and hold the Host application lease, consent and
account fences through native writes. The native managed gateway protects mobile
data routes; an unauthenticated desktop test fixture is not evidence of that
separate mobile boundary.

The dedicated guarded object-create route can fail after a root ID is known.
`AnyObjectCreationUncertain` accepts only the exact versioned native failure
shape, original Space and guarded create route. It carries recovery metadata,
never a success receipt. Host and Hanlin journals decide how to retain that ID
before releasing the original lease.

## Source-bound validation

Receipts retain their original scope and source hashes; a newer source edit does
not retroactively change an older successful test run.

| Receipt | Actual evidence |
| --- | --- |
| `Tools/AnyEngineValidation/evidence/runtime-claims-v4.json` | Generic release-engine two-peer partition/restart matrix: 13 all, 6 live, 1 conflict on both peers after convergence. |
| `Tools/AnyEngineValidation/evidence/runtime-claims-sse-v5.json` | Generic release-engine extension with a real peer SSE update: 14 all, 7 live, 1 conflict. |
| `Evidence/native-object-components-v1.json` | 64 portable XCTest cases and seven real URLSession/SSE transport boundary fixtures, zero failures/skips, source graph stable. |
| `Evidence/native-object-client-runtime-v1.json` | Eight real Swift-client checks against native v4: explicit object closure, unrelated-record exclusion, guarded append/retry, atomic object SSE, observed remove and distinct whole-workspace diagnostics. |

The last row is a warm-runtime client proof, with final target sets of four all
and two live claims. It does not establish cold-restart behavior by itself.
Native Go cold/partition/large-Space proofs are maintained separately by the
native runtime harness. Host, Integration, Hanlin, protected filesystem, actual
iOS UI and whole-workspace migration each have their own acceptance gates.

`PinkhaAnyEngineProbe` requires a disposable account/Space for mutations. Native
object modes are `--lane native --mode object-snapshot` and `object-watch`;
the latter emits a flushed readiness line before awaiting an external mutation.
Generic `--mode watch` and `verify` remain available for the release-engine
harness. Reading/watching never installs a bundle.

Primary implementation references are the pinned Any API sources under
`internal/api`, the versioned native Pinkha handlers/module, the guarded SDK
tree/ACL/storage transaction implementation, and original T2 golden vectors under
`Tools/TorahNativeOperations/overlay/core/block/editor/torahops`. This package
does not itself certify the complete application, file migration or every Apple
presentation flow.
