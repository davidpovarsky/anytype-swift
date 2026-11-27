# Wave 1 engine and consumer boundary — 2026-11-27

## Integration scope

This handoff is based on application commit `a089ff29a5c0a7e415aac800844505f099a5561d`.
Wave 1 owns the engine boundary and its focused tests. Wave 3 owns consumer
integration, the final integration branch and the shared Apple build. Wave 2
owns UI, gestures and editor presentation. No consumer application was edited
to produce this handoff.

## Shared ownership and isolation

| Boundary | Concrete implementation | Required consumer behavior |
| --- | --- | --- |
| Native Any lifetime | `PinkhaAnyHost/AnyApplicationSession.swift` and `AnyHostLease` | Bind account, Space, generation UUID and native `startedAt`. Use `perform`; revoke and drain before replacing the native runtime. |
| Native Heart operation reads | `PinkhaHeartEngine/HeartAuthorizedOperationSession.swift` | Create a new session generation on reopen, synchronously invalidate before account/Space replacement, and call `publishIfCurrent` on the main actor immediately before publication. |
| Shared Hanlin ownership | `PinkhaAnyHanlin/PinkhaHanlinCore/PinkhaHanlinAccountOwner.swift` | Use the common owner and journal. In the dual runtime, Heart uses `anytype` and Any uses `anytype-any`; account key bytes and namespace are both significant. Closing one engine must not close the other's metadata. |
| Shared MiniApps lifetime | `PinkhaAnyHanlin/PinkhaHanlinCore/PinkhaMiniAppsLifetime.swift` | Revoke admission, invalidate generation, await outstanding native work, then release only the caller's own hold token. An authentication return must not release an engine-switch hold. |
| Shared sharing lifetime | `PinkhaSharing/PinkhaSharingAccountOwner.swift` | Open and close the owner per engine/account. Drain before sign-out, selection or runtime stop; native ACL checks are still required. |
| Application facade | `PinkhaEngineHost/PinkhaEngineHost.swift` | The facade forwards to the existing Any runtime/presentation owner. It does not create a second storage or authorization implementation. |

Paths in the table are relative to `Modules`; symbols, source ownership and
call sites were inspected at the stated base. They establish implementation
contracts, not new Apple runtime acceptance. The retained SDK06 evidence
(23 methods/32 cases, ACK7 and the separate Hanlin UI continuation) keeps its
original scope and source pins.

Persisted identity must include the engine namespace, original account and
Space. Never normalize an opaque native identifier, borrow a lease from a new
session, or treat matching public account/Space IDs as proof that a reopened
session is the old session. A cached snapshot is not an ACL grant.

## HTTP dispatch and response authorization

`AnyHTTPClient.requestJSON` and `requestJSONResponse` add an optional
`validateResponse` callback before the existing final `authorize` parameter.
Existing labeled and trailing `authorize` call sites remain source-compatible.

- `authorize` admits dispatch. A mutation callback may consume a one-shot
  approval; the client invokes that callback once.
- After a successful response, the client rechecks its native account.
- A supplied `validateResponse` runs after that account check. It must check
  the original consumer lifetime without consuming another approval.
- With no explicit response callback, GET rechecks `authorize` before returning
  its body. A GET callback therefore represents a repeatable read check.
- A GET response-fence failure returns the underlying failure and does not
  deliver the payload.
- A mutation response-fence failure is uncertain: the native operation may
  already have committed. It is never automatically retried. The dedicated
  object-create route retains only validated recovery identity in its original
  Space through `AnyObjectCreationUncertain`.
- Cancellation is checked before dispatch and before response delivery.

Example with a separate mutation response check:

```swift
let response = try await client.requestJSONResponse(
    method: "POST",
    path: ["v1", "spaces", "join"],
    body: request,
    validateResponse: { try await lease.validate() },
    authorize: {
        try await lease.validate()
        try await approval.consumeOnce()
    }
)
```

The consumer must distinguish pending HTTP 202 from created HTTP 201.
A successful HTTP status also does not override a native per-item rejection.

### Native receipt journals

`AnyNativeBlockCreator` has an intentional one-shot `beginDispatch` fence.
It must receive and journal a returned block ID under the original operation
before performing the final consumer publication check. Do not blindly add
`validateResponse` to this call site: suppressing its response before the
journal records the ID could lose the information required to reconcile a
committed operation. Existing creator/journal adapters retain their ownership
of that order.

For operations that can carry all required recovery metadata through the
transport error, an explicit pure response validator is appropriate.
For journal-first operations, retain the original native receipt first,
then validate before exposing it to a consumer. In either case, a lost
confirmation is not permission to dispatch the mutation again.

## Storage, sharing and FilesV2 contract

The native engine owns ACL, CRDT state, signed changes, encryption, file
custody and sync. Consumer lifetime checks are additional fences; they do not
replace native authorization.

The inspected SDK FilesV2 model distinguishes registration from durability:
inline payloads are durable by construction; larger files remain inflight
until a fleet-signed receipt has been verified. A storage-limit refusal is
`limited`, not an empty successful file. A retry must retain the original
file and operation identity. File metadata, thumbnails and original content
must remain in the same account/Space authorization scope.

The retained private network has only file-v1 nodes. Its missing fileV2
broker/fleet key is a deployment gap, not evidence that a LAN transfer proves
cloud durability. Cloud receipt, quota, range/resume and peer/offline outcomes
must be reported separately by the FilesV2 acceptance owner.

The original 182-operation/159-head/156-snapshot/332-archive preservation proof
remains retained. The independent original156 audit at
`/var/lib/pinkha-w1-engine-contracts-20261127/original156-coherence-audit/result.json`
verifies 313 manifest-referenced source files and unchanged capture coherence.
It does not promote the source's false semantic, history or admission flags.

## Wave 3 consumer integration

| Consumer | Handoff |
| --- | --- |
| Hanlin | Keep common account/journal ownership, per-engine namespaces, original-scope recovery and native ACL. Review each new response validator against the journal-before-publication rule. |
| MiniApps | Keep separate revoke holds and generation checks on asynchronous returns. Native write completion must be drained before changing engines. |
| Otzaria | Apply the same storage/permission/sync contracts in its actual adapter and qualify that adapter in Wave 3. Its application code and runtime were not inspected or changed by this patch. |
| Shared Apple build | Integrate the engine commit and test the consumers against the resulting exact source/native pins. No additional App/native Apple build was performed here. |

## Evidence and limits

Focused HTTP evidence is in
`docs/validation/20261127-wave1-http-authorization`.
The original GET regression failed before the change; seven new boundary
methods and six existing affected response/recovery methods pass after it.
These tests use real loopback HTTP with a controlled server and an unchanged
account identity. They prove the client response/lifetime contract, not
native ACL, peer convergence, cloud durability or whole-product acceptance.

Two earlier build attempts are retained as non-acceptance evidence: disabling
the index store produced no XCTest execution; switching that existing build
to indexing failed before tests because its index was absent. The regression
and final execution use the fresh, indexed build and actual XCTest results.

The exact native8ac `commands.proto` still lacks upstream Account.Select
Error114/requiredSpace. Do not combine the newer generated Select type with
that older native schema. Local free-space handling and cloud storage quota
are separate integration requirements.
