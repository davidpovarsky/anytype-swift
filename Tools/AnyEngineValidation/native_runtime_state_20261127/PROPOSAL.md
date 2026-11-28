# Native runtime observations: limits, access, and sync

Status: source proposal; no production source edit, compiler, native process,
account inspection, or new runtime qualification has occurred for this tranche.
Root owns the Swift providers and C owns Bookmark/native13. N owns only this
isolated SDK/Any source overlay after the wire contract is agreed.

## Concrete original-source gaps

`anysyncx.App.SpaceStatuses` calls the original coordinator `StatusCheckMany`
and returns one status per requested Space. The generated v0.13.8
`SpaceStatusPayload` includes `Limits *SpaceLimits` and `IsShared bool`;
`SpaceLimits` contains uint32 `ReadMembers` and `WriteMembers`. SDK
`spaceimpl.reconcileDeletions` checks response length and passes each status to
`reconcileOne`, which uses deletion/ownership state but discards those limit and
shareability observations. A missing `Limits` pointer is distinguishable from
a present object whose two numbers are zero. Account.Limits is a different,
already delivered account/network-scoped API; it must remain unchanged.

Heart's `SpaceView.SetAclInfo` records `!AclState.IsEmpty()`. Its
`updateAccessType` preserves an explicit Personal classification first, then
chooses Shared when that ACL predicate or coordinator shareability is true,
otherwise Private. The exact standalone SDK v0.13.8 `aclstate.go` is
byte-identical to the separately retained Heart Sync file for this one file;
this does not equate the two dependency closures. The native `IsEmpty()`
predicate includes ACL invites and pending requests as well as accounts with
permissions. Reconstructing it from a visible member count or the caller's role
would change the meaning.

The SDK's `SpaceInfo.Derived` is a native account-owned derivation marker, not a
Personal designation. The current Any HTTP derived-space registry has only
`bao`; it does not name a Personal space. Neither a derived flag, arbitrary
SpaceType string, caller hint, owner role, nor member count supplies the missing
original Personal provenance.

For sync, original `Tracker.Object` returns its per-object hook row or an
inherited responsible-peer full-space round for an object stored locally.
`Service.Status` separately folds peer presence and protocol incompatibility
into the space rollup. These are different observations. `LastSyncAt` is a
heads-apply/full-space confirmation time. Heart's `syncDate` is the time its
details updater writes a sync projection, so those timestamps are not
interchangeable. The existing SDK hooks contain no equivalent Heart file-object
creator/queued/oversized projection.

## Additive public surface

Add an optional `space.RuntimeStateProvider` interface implemented by regular
`spaceImpl`. Do not add required methods to `space.Space`, change SpaceInfo,
modify Account.Limits, or change existing sync-status endpoints. A server using
an SDK without the optional interface returns an explicit unsupported error.

Proposed methods:

```go
RuntimeState(ctx context.Context) (RuntimeState, error)
RuntimeObjectState(ctx context.Context, objectID string) (RuntimeObjectState, error)
```

Proposed read-only routes:

- `GET /v1/spaces/:spaceId/runtime-state`
- `GET /v1/spaces/:spaceId/objects/:objectId/runtime-state`

Both carry contract version, account/network/Space identity, actual current ACL
identity and signed head, and a capture timestamp. Object results also carry the
exact requested object ID. They are scoped runtime reads, not account-list
mirrors, grants, or translated historical relation values.

### Space response

The exact proposed field names and null behavior are in `WIRE_CONTRACT.json`.
Its compact shape is:

```json
{
  "contract": "pinkha-space-runtime-state-v1",
  "scope": {
    "accountId": "...", "networkId": "...", "spaceId": "...",
    "authorityIdentity": "...", "aclHeadId": "..."
  },
  "capturedAt": "...",
  "coordinator": null,
  "access": {
    "aclIsEmpty": true,
    "personalSpaceId": null,
    "value": null,
    "reason": "personal_provenance_unavailable"
  }
}
```

When a coordinator response exists, `coordinator` is an object containing
`fetchedAt`, the original `status` enum name, `isShared`, and nullable `limits`.
A present limits object always has numeric `readersLimit` and `writersLimit`,
including a genuine zero. No successful response means `coordinator: null`.
A response with no limits means `limits: null`. An offline cached answer retains
its original fetchedAt; neither a read nor a failed refresh advances it.

Access evidence always reports the current signed ACL's native `IsEmpty()`
result. `personalSpaceId` may only come from positive original native provenance
bound to the same account/network. It is not accepted from an HTTP request,
generic derived flag, user settings, or an unverified imported value. With a
known personal ID: the matching Space is Personal1; another Space is Shared2 if
the ACL is nonempty or the coordinator positively says shareable; it is Private0
only when the ACL is empty and a coordinator observation explicitly says not
shareable. Without coordinator evidence the latter classification is unknown.
Without the original Personal designation, the complete original access
classification is unavailable, including cases where a sharing observation is
available. The sharing observation is still returned as its own evidence.

The current Any implementation has no positive original Personal provider, so
the first source implementation must report that precise unsupported state.
This is an explicit unresolved producer boundary, not a false Private default.
A later positive native Personal source can fill this slot without changing
the numeric domain or accepting caller-supplied authority.

### Object sync response

Use the same scope envelope with `objectId` and contract
`pinkha-object-runtime-state-v1`. Include:

- `objectSync.state`: the original SDK string (`unknown`, `offline`, `syncing`,
  `synced`, `error`), without casting its ordinal into Heart's enum.
- `objectSync.basis`: `per_object_hooks`, `responsible_space_round`, or
  `unobserved`, derived from the existing tracker lookup.
- `objectSync.lastSyncAt`: nullable actual heads-apply or inherited
  responsible-space-round time.
- `spaceSync`: the original space rollup and counts, plus an explicit
  `networkProtocolIncompatible` observation from the existing source callback.
- `capturedAt`: when this new response was sampled. This field is not Heart's
  syncDate, not proof of a successful sync, and not a recovered historical date.

Unknown stays unknown. Offline is a space connectivity observation, not
automatically Heart queued3. An old object confirmation remains distinct from a
currently offline/error space. No queued/limited/oversized file-object override
is invented from ordinary FilesV2 attachments. Root's relation provider must
report unavailable when the original Heart value cannot be supported by these
facts. A request samples related native observations; it does not claim a
single atomic consensus instant across tracker and network presence.

## Current-authority delivery boundary

Reuse the qualified `readguard.Value` mechanism with the existing loaded-space
ACL/lifetime loader. Current read authority is checked before work and before
returning a privately assembled result. Account App token, concrete loaded
Space token, ACL identity and signed head must remain the same. Guest identity
is handled through its actual loaded ACL, not by assuming that the account's
main public identity is the ACL identity. Both identities are explicit in the
scope envelope.

Network waits, device-KV I/O, tracker/database lookups and external callbacks
must run outside ACL and lifetime locks. The final protected operation is only
assignment of the fully materialized value. Cancellation, removal, a changed
signed head, App retirement, Space unload/reload or a close-in-progress wait
must withhold the value. The already qualified cancellation/quiescence helpers
are reused; no new callback subscription or public callback-under-lock behavior
is introduced.

## Shared coordinator cache

Keep a Service-owned cache keyed by the exact network/account/Space tuple. Use
the same device-local KV facility already used by Account.Limits; do not place
quota/shareability observations in replicated domain objects or the tech-space
CRDT. Version the stored record and bind the full key, source and fetchedAt.

The existing deletion reconciler feeds successful validated responses into this
cache after its existing exact length check. Its deletion/offload decisions,
cadence, retry policy and input rows remain unchanged. A response captured for
one requested ID must never be assigned to another ID; no partial positional
response is admitted. Nil payloads and missing limits are recorded as absence,
not converted to zero. A failed RPC does not erase a prior successful answer.

The runtime GET may start one bounded, coalesced refresh per Space and wait up
to the existing Account.Limits-style short wait, bounded also by caller
cancellation. The last valid answer remains usable offline with its original
timestamp. The Service owns and cancels/drains refresh workers through its
existing close context/worker lifetime. Close cannot publish a late answer into
a new account or new Service. Raw network observations may remain in the local
cache after membership changes, but every API delivery is reauthorized against
the current signed ACL; this is not an erasure guarantee.

## Exact source ownership proposed

All paths below are relative to native1616. No active retained source tree or
C13 input is edited. The isolated draft lives under this directory's `overlay/`.

| Path | Change |
|---|---|
| `.runtime-artifacts/sdk-source/space/runtime_state.go` | New optional interface and closed typed observations. |
| `.runtime-artifacts/sdk-source/internal/spaceimpl/runtime_state.go` | New current-authority read/projection methods. |
| `.runtime-artifacts/sdk-source/internal/spaceimpl/runtime_cache.go` | New scoped coordinator cache and bounded refresh. |
| `.runtime-artifacts/sdk-source/internal/spaceimpl/service.go` | Service-owned cache field and existing lifecycle integration only. |
| `.runtime-artifacts/sdk-source/internal/spaceimpl/deletioncontroller.go` | Feed valid successful status observations; unchanged deletion decisions. |
| `.runtime-artifacts/sdk-source/internal/syncstatus/runtime_observation.go` | New read projection over existing tracker lookup, rollup and incompatibility hooks; no old tracker state-machine change. |
| `internal/api/runtime_state.go` | New response DTOs. |
| `internal/server/handlers_runtime_state.go` | New GET handlers, typed unsupported/errors and exact mapping. |
| `internal/server/handlers_spaces.go` | One registration hook for the two additive routes. |

New narrowly selected tests will accompany the affected packages. The existing
candidate C13 source map was independently compared: its copies of
spaceimpl/service.go, deletioncontroller.go, syncstatus/service.go,
handlers_spaces.go and api/spaces.go are still byte-identical to native1616.
This does not authorize editing C's source; it establishes the intended disjoint
composition before a later combined producer. Account.Limits, C13, Apps,
readguard production helpers and old Files/transport tests remain unchanged.

## Finite new qualification obligations

Test missing response versus missing limits versus genuine zero; exact
account/network/Space separation; malformed/short positional response refusal;
cached offline timestamp retention; concurrent refresh coalescing and close
drain; cancellation/revocation/head change/reload before delivery; native
IsEmpty semantics with invites/pending requests; Personal-unavailable refusal;
and the exact optional wire shape. For sync, test original per-object evidence,
inherited responsible-round evidence, unknown IDs, and old confirmation beside
current offline/protocol error without inventing Heart values.

Use only fresh synthetic identities/data for any new SDK integration fixture.
No retained private-store copies or exports. No old35/Fresh2/content14/
metadata18/network12/ACL2/P2P2 replay. Source and selected tests receive peer
review before any compiler/native slot. A future producer must join the new
overlay to the exact current Native source and compile once; no source-only
success is a runtime or Apple qualification.

## Source receipts

`public_inputs/source-readback-{0,1,2,3}.json` retain sixteen exact native1616
public source files. The initial oversized retrieval was truncated by the
connector and was not admitted; the bounded complete packets are the inputs.
`public_inputs/v0138-source-readback.json` retains the exact standalone ACL
source identity; packet3 also pins the original coordinator protobuf and
extracts its relevant type declarations. `SOURCE_BASE.json` records all hashes,
the unchanged C13 overlap observations, and original Heart source references.
