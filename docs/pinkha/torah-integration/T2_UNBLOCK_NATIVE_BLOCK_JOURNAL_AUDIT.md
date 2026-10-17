# T2-Unblock / Native Block Journal Audit

## 1. Stage

`T2-UNBLOCK / NATIVE BLOCK JOURNAL AUDIT`

## 2. Status

`REJECTED / STILL BLOCKED`

The caller-supplied block-ID path is real, and an initial block model can carry
the immutable payload without a later `BlockSetFields`. It is nevertheless not
a safe association journal on the pinned implementation. Cross-branch replay
does not compare payloads for a duplicate ID: the later replay silently
replaces the earlier block. A create whose positional anchor has disappeared
can also be ignored during tree rebuild. No sanctioned stable invisible host
was found, and using the existing manifest can lose the journal when duplicate
manifests are canonicalized and deleted.

No production adapter, schema migration, editor hook, or user-data write path
was added. T3 was not started.

## 3. Source base

- Verified parent branch: `pinkha/torah-integration-t2`
- Verified parent SHA: `813f6b6c8824125f5244ff1d4b7db4a3c81b39cd`
- Working branch: `pinkha/torah-integration-t2-unblock`
- Pinned Heart tag: `v0.50.21-nightly.20260824.1`
- Pinned Heart SHA: `7e8f5535add386ff5f7573cde47e095c867ab724`
- TorahInspectorKit SHA: `e8aefc626350c8ee0df9daf8d7de7e1dcd0ea418`
- Final branch SHA: recorded in the final task handoff because a commit cannot
  contain its own SHA.

The Heart source was checked out detached at the exact tag/SHA and remained
unmodified. The isolated probe imports the published exact tag instead of
using or patching a working copy.

## 4. What `BlockCreate` really supports

### Request, ID, content, and local duplicate behavior

- `pb.RpcBlockCreateRequest` has `ContextId`, `TargetId`, a complete
  `*model.Block`, and `Position` (`pb/commands.pb.go:51748-51753`). It has no
  expected revision or idempotency token separate from the block ID.
- `Middleware.BlockCreate` calls the block service and returns the ID only on
  success (`core/block.go:26-46`). Every error, including duplicate ID, is
  flattened to `UNKNOWN_ERROR`; there is no duplicate-specific response code.
- The service opens a state for `ContextId` and calls the basic editor
  (`core/block/editor.go:52-58`). The cache path then invokes ordinary
  `smartBlock.Apply` with no `NoHistory` flag
  (`core/block/cache/cache.go:158-179`).
- `basic.CreateBlock` checks object block restrictions, requires non-nil
  content, calls `simple.New(req.Block)`, clears caller-supplied children,
  validates the chosen block kind, calls `State.Add`, and finally inserts the
  ID at the requested target/position
  (`core/block/editor/basic/basic.go:133-160`). `State.Add` returns false for an
  ID already visible in that local state (`state/state.go:271-280`), so a
  same-client duplicate is rejected before commit.
- `simple.New` generates a BSON object ID only when `block.Id == ""`; a
  nonempty caller ID is retained (`core/block/simple/simple.go:68-77`). No
  generic format/length validation was found on this path. Both fallback base
  and text `Validate` return nil (`simple/base/base.go:102-104`,
  `simple/text/text.go:97-100`).
- The initial model is persisted as part of `ChangeBlockCreate`. Base
  `ModelToSave` returns the complete block model, including fields. The Tier B
  probe verifies the supplied ID, text payload, and fields through change
  replay and a snapshot rebuild.
- The existing Swift `BlockService.add` does transmit `information.id`, but
  `BlockInformationConverter.convert(information:)` replaces input fields
  with an empty protobuf struct
  (`BlockInformationConverter.swift:27-40`). Therefore the existing converter
  cannot atomically write a fields payload. A raw request or new dedicated
  adapter would be required, but neither is authorized after the safety
  failures.

### Replay is not collision-safe

Local duplicate rejection does not apply when two disconnected branches each
created the ID while it was absent. During reconstruction:

1. `sourceimpl` iterates tree changes and calls
   `State.ApplyChangeIgnoreErr` (`core/block/source/sourceimpl/source.go:647-685`).
2. `changeBlockCreate` constructs each supplied model, calls
   `unlinkForReplay(id)`, and then calls `State.Set` before positional insertion
   (`state/change.go:342-362`).
3. `State.Set` replaces the map entry; it does not compare the old and new
   models (`state/state.go:283-285`).
4. `ApplyChangeIgnoreErr` deliberately suppresses create/move errors
   (`state/change.go:163-169`).

Consequently, identical duplicates collapse to one reachable ID, but differing
payloads under that same ID are silently accepted. The final payload is the
payload of the later replay. Reversing replay order reverses the winner. This
violates the mandatory collision-detection and order-independence invariants.

### Position, history, and search effects

`InsertTo` mutates the parent's `ChildrenIds` according to the target and
position (`state/position.go:18-88`). Distinct IDs created at the same root
anchor both survive raw replay, although their sibling order follows replay
order. If a non-root target has disappeared, insertion returns
`target block not found`; reconstruction ignores the create error after the
block model has already been set, leaving an unreachable value that
normalization can discard.

The operation is also not intrinsically invisible:

- `State.SearchText` concatenates text from every reachable text block
  (`state/state.go:578-588`), so a text-carried JSON operation becomes native
  full-text content.
- normal `BlockCreate` reaches `smartBlock.Apply` with history enabled, and a
  nonempty undo action is added to the object's undo history
  (`smartblock/smartblock.go:650-700`, `830-845`).
- using non-text fields avoids that exact `SearchText` path but has no proven
  editor/export/backlink invisibility contract, and the current Swift
  converter discards those fields.

## 5. Safe journal host

No safe host was established.

The current Pinkha manifest is an ordinary page created with an `isHidden`
detail and a server-returned random object ID
(`PinkhaSpaceManifestStore.swift:154-171`). Discovery searches the Space by a
nominal `uniqueKey`. When more than one result exists, it selects a canonical
manifest and asynchronously deletes every secondary object
(`PinkhaSpaceManifestStore.swift:25-79`). Blocks attached to a losing manifest
would be deleted with that object. The manifest also stores configuration in a
whole JSON description value and has no demonstrated high-volume, retention,
backup, or bounded-query contract. It is rejected as the journal host.

No exposed Swift/Heart API in the audited path creates a dedicated ordinary
hidden object with a caller-supplied deterministic object ID. Internal
unique-key constructors exist inside Heart for sanctioned smart-block types,
but ordinary page `ObjectCreate` does not expose that as a supported journal
root contract. Reusing an existing document/root would alter its block tree,
search text, undo history, and potentially export/editor output. Creating a
random-ID hidden page reintroduces ambiguous-response duplicate roots and
eventual-search recovery. Neither is accepted.

## 6. B01-B16 result matrix

`Tier B` below means the isolated exact-tag state/change/snapshot probe. It is
not middleware disk persistence and not real sync.

| ID | Result | Tier and evidence |
|---|---|---|
| B01 | PASS | Tier A+B: caller ID, initial text, and initial fields remain in the emitted `ChangeBlockCreate`, survive replay, and survive `NewDocFromSnapshot`. This is state/snapshot read-back only, not Tier C disk persistence. |
| B02 | BLOCKED | Tier A proves a same-client repeat is rejected by `State.Add`; Tier B proves two identical replayed creates collapse to one reachable block across snapshot rebuild. Real middleware close/reopen and retry response handling require Tier C, which is unavailable. |
| B03 | BLOCKED | Tier B surrogate passes: identical same-ID branch changes leave one uncorrupted reachable block in both replay orders. The required two offline synced clients and restart are Tier D and were not available. |
| B04 | FAIL | Tier A+B: differing payloads under one ID return no replay conflict. A→B ends with B, while B→A ends with A. This is silent, order-dependent last-replay-wins replacement. |
| B05 | BLOCKED | Tier B surrogate: distinct IDs A and B both remain reachable in either raw replay order; sibling order follows replay order. Actual sync convergence/order after two independent clients is Tier D and remains blocked. |
| B06 | FAIL | Tier A+B: after the anchor is removed, `changeBlockCreate` sets the new model, `InsertTo` fails, and production-style `ApplyChangeIgnoreErr` suppresses the create error; the operation is not reachable after apply. A design restricted to the immutable root anchor was not proven on a durable safe host. |
| B07 | BLOCKED | Response-loss injection, retry, close, reopen, and one durable record require a disposable Tier C middleware fixture. None exists. |
| B08 | NOT RUN | Native observed-remove/add-wins folding was not implemented or run after the storage primitive failed B04/B06. The documented portable policy is not a native proof. |
| B09 | NOT RUN | Concurrent immutable update materialization was not implemented or run after the storage primitive failed. |
| B10 | BLOCKED | Offline sync in both orders, crash/retry, restart, and equal reopened materialization require Tier D. |
| B11 | BLOCKED | Source paths perform restriction/target checks, but wrong-Space, read-only, removed-object, and permission-race non-interference require disposable Tier C/D environments. |
| B12 | FAIL | Tier A: text payloads enter `SearchText`; normal RPC creation enters undo history. No alternative native block kind was proven invisible across editor, home, search, preview, export, backlinks, and undo. |
| B13 | FAIL | Tier A: manifest discovery asynchronously deletes noncanonical duplicate manifest objects, so a journal on a losing host can be destroyed. No stable sanctioned replacement root was found. |
| B14 | NOT RUN | 1k/10k load, subscription, recovery, backpressure, target index, and reverse-index measurements were not justified after correctness rejection and no safe host. |
| B15 | PASS | Tier A+B: the probe carries the complete immutable content and fields in initial block creation and never calls whole-fields replacement. This does not make the overall backend safe. |
| B16 | FAIL | Tier A: the chosen native text/base block validators accept arbitrary content; Heart has no Pinkha payload/version validation. No middleware guard was installed, and malformed/future operation records were not proven to fail before persistence or replay. |

## 7. Exact concurrency outcomes

### Native Tier B observations

The reproducible probe is in
`docs/pinkha/torah-integration/t2-block-journal-probe` and runs:

```console
go test -mod=readonly -v -count=1 ./...
```

On 2026-10-18 the exact-tag Go 1.26.5 run completed in `-mod=readonly`
mode with all five top-level tests passing (`ok`, final package test time
22.280s; 92.9s final command wall time, after a 358.8s first Windows host
build). The initial-payload test also proves unrelated existing block fields
remain unchanged. A passing test here means the assertions observed the
intended native behavior; the B04 and B06 assertions deliberately confirm
unsafe behavior and therefore remain matrix FAIL results.

Its assertions cover:

- initial deterministic ID plus content/fields through replay and snapshot;
- same ID + identical payload in A→B and B→A: one reachable block;
- same ID + different payload: no error, last replay wins, and the winner
  changes when order changes;
- distinct IDs at the same root anchor: both survive; sibling order follows
  replay order;
- create after removed anchor via `ApplyChangeIgnoreErr`: not reachable.

The exact command output and toolchain are recorded in `PROGRESS.md`.

### Source inference only

- Real object-tree sync should give clients a deterministic tree iteration
  order, but that does not turn a payload mismatch into an observable
  conflict. The state code accepts and replaces it.
- Observed-remove/add-wins and deterministic update folding could be built at
  the application layer only after every immutable operation is durably and
  completely retained. B04/B06 and the missing safe host invalidate that
  premise, so no fold result is claimed.
- No real add/remove two-client result is reported.

## 8. Persistence, recovery, authorization, isolation, and performance

- Tier C: **BLOCKED**. This Windows checkout has no
  `Dependencies/Middleware`, Apple SDK, disposable Space/account fixture, or
  registered workflow that performs mutable real-Heart journal tests.
- Tier D: **BLOCKED**. `gh secret list` exposes only notification secrets, not
  disposable account/Space credentials. The user's personal Space was not
  used.
- Authorization and per-Space isolation: the request has explicit context and
  existing source checks restrictions, but no wrong-Space or permission-race
  run was performed. No PASS is inferred.
- Crash/retry/reopen: no real middleware disk run was performed. Tier B
  snapshot rebuild is narrower and labeled as such.
- Indexing/performance: not measured. Heart exposes object search/indexing,
  not a proven per-operation-block query index. A derived 1k/10k target and
  reverse index was not built after correctness rejection.
- Remaining risks include random/duplicate journal roots, host deletion,
  operation exposure, undo pollution, unsupported size growth, replay drops,
  malformed payload acceptance, and unproved backup/restore behavior.

## 9. Repository changes

Changed only on `pinkha/torah-integration-t2-unblock`:

- this audit report;
- the isolated exact-tag Go state/replay probe and its module lock data;
- an additive supplement to `ADR-T2-STORAGE-CONCURRENCY.md`;
- an additive T2-Unblock entry in `PROGRESS.md`.

No production Swift, protobuf, Heart source, app workflow, schema, UI, or
unrelated branch/repository was changed.

## 10. Next safe action

Keep T2 `PARTIAL/BLOCKED`; do not start T3. Do not implement the block-journal
adapter on this primitive.

To reopen T2, Heart would need an already-supported or separately approved
primitive that provides all of the following together: a sanctioned stable
invisible Space-scoped host; atomic immutable operation creation with a stable
caller identity; explicit identical-retry versus differing-payload conflict
semantics during sync/replay; non-dropping anchor behavior; payload validation;
and bounded indexed queries. Then B01-B16 must be rerun through real middleware
and two independent authorized disposable synced clients, including restart,
offline schedules, permissions, visibility/export/undo, and 1k/10k load. That
future work is a new T2-unblock attempt, not authorization for T3.
