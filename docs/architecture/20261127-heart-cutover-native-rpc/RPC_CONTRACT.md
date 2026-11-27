# Heart cutover RPC v1 — native consumer contract

This is the engine contract for the additive native cutover capability. Its protobuf source is `overlay/pb/protos/pinkha_torah_cutover.proto`; the five dispatch entries are appended to the original `ClientCommands` service. The retained App15/native8ac product does not yet contain these newly generated methods. Consumers must use a newly qualified coherent native generation and its exact manifest before enabling the capability.

## Entry points

| Method | Request | Response | Native responsibility |
| --- | --- | --- | --- |
| `PinkhaTorahCutoverSourceRead` | `PinkhaTorahCutover.Scope` | `SourceReadResponse` | Read the exact current native property and target heads under account, space, target and current ACL authority; never create roots. |
| `PinkhaTorahCutoverRead` | `Scope` | `ReadResponse` | Read complete locally available signed metadata and v1 histories, verify referenced receipts, and project cutover status without writing. |
| `PinkhaTorahCutoverAppend` | `RecordRequest` | `AppendResponse` | Explicitly append signed Begin, Import witness, or Seal metadata in the separate versioned native tree. |
| `PinkhaTorahCutoverImport` | `OperationRequest` | `OperationResponse` | Import exactly one admitted source fact through the existing v1 association tree and its native signer/ACL/target validation. |
| `PinkhaTorahCutoverAssociationAppend` | `OperationRequest` | `OperationResponse` | Apply an ordinary association add/remove/replace only through the current cutover policy, preserving the original v1 wire and receipts. |

Every scope supplies `protocolVersion = 1`, space ID, object ID and exact property key. Requests do not accept an account key, effective author, native root, or permission decision. Native code derives these from the loaded account and actual target. Referenced native changes are independently verified against immutable signed history; their presence in a request is not authority.

The Go gRPC methods and gomobile byte wrappers come from the repository's original Anyproto gogo generator. Existing generated function bodies remain exact, apart from the five explicit dispatch cases added to `CommandAsync`. A small separate Go alias file accommodates that generator's historical nested response-error naming while the new schema shares one error type. No generated output is hand-edited.

## Lossless source and identity

`SourceValue` contains the property key, a presence bit, and original bytes. Missing, present-empty, and differently formatted JSON are distinct. The source property remains retained after Seal and unlink. The shared Swift `TorahLegacyAssociationCutoverPlan` regenerates complete canonical facts from these bytes. It preserves unknown fields, original record IDs, exact locations, semantic anchor metadata, and integers beyond floating-point precision.

Plan and fact identities use the existing versioned byte framing and standard SHA-256. A fact's identity binds space, object, block, provider, canonical reference and full canonical payload. The native import operation identity binds the plan, fact and actual native author. Consumers must freeze these bytes and identifiers across ambiguous outcomes and retries.

The native source-coverage guard verifies the complete source-to-fact correspondence. A consumer cannot approve a partial list by providing its own digest. A source change after admission is a visible divergence, even if the caller retries an already committed operation.

The initial request bounds remain those of the admitted contract: 1 MiB retained legacy property, 1,024 source facts, 64 KiB per fact payload, and 4 MiB complete framed plan. The RPC mapper checks its own bounded wire size and rejects whole oversized replies; it never reports a truncated history as complete.

## Explicit durable phases

1. Read source and construct the shared lossless plan. No read performs migration, recovery writes, import, repair, or deletion.
2. Append Begin with frozen record ID, plan, plan ID and observed source heads.
3. For each fact, append the deterministic v1 import. Keep its original claim ID and signed native receipt.
4. Read the actual native receipt, then append the separate Import witness naming the fact and exact physical claim, change, creator and ACL head.
5. After all source facts have actual witnessed coverage, append Seal naming complete bindings and observed Import metadata identities.
6. Ordinary v1 association actions continue through the cutover-aware association method. Unlinking imported content does not erase its original history or undo the Seal.

The two native trees are not one atomic transaction. A v1 import can commit before its metadata witness. A crash or lost acknowledgment at that point leaves visible unfinished work. Resume reads current authority/history, retries the original frozen import identity, verifies the existing receipt, and explicitly finishes the missing metadata. No new operation ID may be minted merely to conceal an ambiguous prior result.

A completed idempotent result is not current authority. Before returning a previous receipt, native code rechecks current account, ACL, target and exact retained source, and refuses divergent/conflicting source state. A valid Seal following an unchanged import does not invalidate that import's exact frozen retry.

## Read semantics and errors

`Snapshot.completeLocal` means the returned native snapshot is locally complete under the current bounded read. It is not a peer acknowledgment or a statement that disconnected writers have no unseen changes. Metadata and v1 claims retain their native authors and signed receipt identities; conflicts are never collapsed into a last-writer result.

Statuses are `LEGACY`, `PENDING`, `SEALED`, `DIVERGED`, and `CONFLICTED`. A normal read before native roots/history are locally available can return `HISTORY_UNAVAILABLE`; this must not be presented as an empty or completed migration. Missing history, invalid coverage and changed source are distinct conditions.

Every native response carries `protocolVersion` and a typed `Error`. Codes are:

| Code | Meaning |
| --- | --- |
| 0 | Success |
| 1 | Native failure not otherwise classified |
| 2 | Invalid request |
| 3 | Unsupported protocol version |
| 4 | Native permission denied |
| 5 | No loaded native account |
| 6 | Account lifetime changed during the call |
| 7 | Native target state unavailable |
| 8 | Local signed history unavailable |
| 9 | Native projection requires recovery |
| 10 | Explicit read/wire bound exceeded |
| 11 | Call cancelled |
| 12 | Deadline exceeded |
| 13 | Immutable identity or cutover conflict |
| 14 | Required cutover history/coverage incomplete |
| 15 | Exact retained legacy source changed |
| 16 | New mutation disallowed after Seal |

`issues` preserves every classified cause from joined native errors, in a deterministic priority order. Descriptions use fixed labels rather than arbitrary native error text that might contain private account details. Account change and permission refusal take priority over later state errors.

Failed reads release no snapshot. Failed writes release no private history or resolution. If a write was already committed before a postflight failure, its validated bare claim/change identity and disposition may remain so that the consumer can report an ambiguous durable result and later reconcile it. Such a receipt is not success and does not authorize publication.

Malformed byte payloads fail in the original generated decoder before native dispatch. Protobuf versions 0 and future unsupported values fail closed.

## Shared infrastructure and isolation

The capability uses the existing account application, space service, native account-lifetime fence, current/historical ACL checks, native tree manager, encrypted signed SyncTree, StoreState and SQLite projection. The new metadata host is separate because the original v1 validator intentionally accepts only its original Create/association wire. No duplicate account, file store, network stack, or parallel ACL database is introduced.

Root IDs and all authority are derived in native code. Scope changes between accounts or spaces are refused by the same existing account/target lease boundaries. Consumers of Hanlin, MiniApps and Otsaria should depend on the scoped contract and immutable result identities, not internal roots or platform UI state.

## Qualification and integration

The accepted typed-core milestone is commit `05c2f6d4f391a5b9d3dab7efa2987afd887a5f65`. Its real registry/signed history/reopen evidence is in `docs/architecture/20261127-heart-cutover-native-core`.

The generated RPC source has its own frozen manifest, canonical generator receipt, source-retention audit, and executed qualification controller. Compilation alone is not RPC acceptance. The controller requires actual generated gRPC dispatch through all five methods, strict malformed/version/error/bounds coverage, and real SIGKILL recovery in three distinct processes. Recovery runs in isolated OS network namespaces containing only loopback for the local RPC connection. Focused native-host and actual gomobile byte-wrapper regressions are separately counted.

Wave3 owns native product composition and the integration branch. Before activation it must combine this manifest with other reviewed native changes, regenerate the corresponding Swift protobuf/bridge output from the same source, and provide the exact resulting product identity. Wave2 owns UI, gestures and mounted acceptance. Existing application artifacts are not silently relabeled as containing this capability.

See the actual retained receipts for which gates have executed; the contract itself does not declare peer synchronization, Apple framework acceptance, UI completion, or engine-switch parity.
## Additive Go package boundary

The new generated Go message package is pb/cutoverpb. It imports the original
top-level pb definitions for v1 operations. Service registration imports both;
the original pb package does not import the dependent cutover package. Its
original files remain byte-for-byte unchanged.

The isolated-package canonical descriptor comparison permits only go_package
metadata to differ from the original candidate. Protobuf full names, message and
field numbers, and the Swift wire contract remain identical. Go vet remains
enabled. An overlay-only new package needs an empty physical directory for vet's
working directory; the preparation receipt records that topology addition and
verifies all retained source-file bytes unchanged.

## Typed Swift ownership boundary

PinkhaHeartCutoverClient.swift uses the existing production
PinkhaNativeReadLifetime observer and leases. It cannot manufacture activation.
Before dispatch it checks the exact opened-space owner and the complete native
runtime version supplied in PinkhaHeartCutoverProfile. The expected runtime must
contain the full lowercase source-manifest SHA-256. An ordinary App version or a
different runtime cannot enable this boundary.

Reads validate ownership again before releasing a snapshot. All three mutation
methods freeze request bytes and use an owned acknowledgement task after
dispatch. Caller cancellation cannot silently discard a committed result or
trigger an automatic retry. If the owner retires after a durable native write,
the failure retains the validated disposition/claim/ChangeID and all native
joined-error issues, while withholding private resolution data. Undecodable or
oversized replies never invent a durable identity; transport failure remains
uncertain.

PinkhaHeartCutoverNative.swift directly calls the five generated Lib.Service
byte functions without request/response body logging. Its factory requires both
PINKHA_NATIVE_T2_AUTHORIZED_READ_V1 and PINKHA_NATIVE_TORAH_CUTOVER_V1 at build
time, plus the exact runtime profile at invocation. Wave3 supplies the coherent
product identity and enables the build seam together with the matching bridge.

Canonical Swift generation uses original SwiftProtobuf 1.32.0 commit
c6fe6442e6a64250495669325044052e113e990c and the repository's original filesplit
parser. Only additive production protocol files are installed. A historical test
fixture never substitutes for production protobuf definitions.

The focused Linux qualification uses exact production lifetime/client sources,
canonical generated protocol types, and exact excerpts of the original Sourcery
response conformances. Ten ownership/error methods cover the five methods,
retired and replacement owners, cancellation, frozen requests, committed error
receipts, response bounds, and exactly one dispatch. One interop method replays
eight byte-exact frames captured from actual native generated-gRPC execution.
This proves Swift encoding/decoding and boundary behavior within that scope;
it does not replace actual native-account, Apple bridge, peer transport or UI
acceptance. The corresponding original receipts determine whether these
prepared tests have executed successfully.
