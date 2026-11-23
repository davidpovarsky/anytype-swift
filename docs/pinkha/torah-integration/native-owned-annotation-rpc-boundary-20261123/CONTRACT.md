# Proposed original annotation import RPC boundary

## Decision proposed for review

Prefer one blocking original annotation import command plus one narrowly scoped cancel command for the first production composition. Keep preparation, Start, Done, Result and release as application-owned operations. Do not publish four new public methods merely because those four lifecycle concepts exist.

This recommendation is a source design, not an implemented endpoint. The B1/C product at 62e5f1c9d62c99cc00debfe7e1975557eeec32fa is running its separate nine-leaf qualification at run45159946802, source1ec511b046fff1c46aaeb8425b98932a19400ad2. This packet does not edit that source, add a generator run, activate a production caller, or claim the pending native result.

The two-command asynchronous alternative remains explicit below. It is preferable only if the closed SDK cannot preserve the blocking command's genuine response/drain while delivering cancellation for the same captured attempt. No serial-RPC premise is used: the actual Invocation uses DispatchQueue.global and withUncancellableHandler.

## Existing owners and exact source facts

SOURCE_INPUTS.json binds the immutable sources, including the independent 25-input downstream map and the additional original registry, lifecycle and progress sources.

- The actual Service owns the application pointer, wallet/account lease and ownedImports registry. The private annotation bridge uses the original TryRLock, checks the actual app/wallet/usable lease and registers the real operation before Start.
- ownedImportRegistry.operations already retains the real ownedAccountImport. pruneDrainedLocked removes entries only after the actual operation's Done closes. No caller completion flag or channel is admitted.
- OwnedImportOperation.Start uses its original sync.Once. Even cancellation before Start enters the actual original Execute; its real return, file outcomes, mapping, export/readback and stage cleanup precede Done.
- Result returns a copied historical outcome only after Done. A copied readback can coexist with an error or a stage earlier than BodyMatched; it is not a currentness or acknowledgement grant.
- Original process.NewNoOp().Id() is empty, Cancel does nothing, and Done is nil. The existing ProcessCancel command routes through the real process registry by ID. It cannot stand in for the owned annotation operation's cancel/Done pair, and no process ID should be manufactured.
- The actual original Swift Invocation calls the native wrapper on the global queue, observes its concrete response before completion.finish, preserves original native errors, and checks Task cancellation after the response path. The existing schema-specific history wrapper shows how to retain raw native response bytes without making a public receipt constructor.
- The current Host local save has zero outbox destinations. The existing outbox-only native-creation fence cannot be reused by inventing a delivery. Root owns that separate durable saved-row/attempt design.

## Comparison

| Choice | Native execution and result ownership | New retained state | Cancellation race | Suitability |
| --- | --- | --- | --- | --- |
| Blocking Import + concrete Cancel | One admitted original operation; Import waits for its actual Done, copies Result, then returns through the real generated wrapper | An immutable cancellation binding on the existing ownedAccountImport only while the original call is in flight; no terminal result cache or public Release | A Cancel arriving before native registration is unobserved, not drained; the closed SDK must keep the real import invocation/attempt and can reissue only cancellation for that same attempt | Preferred minimal first patch, subject to concrete SDK cancellation-owner review |
| Start + one operation-control command | Start registers then starts the same real operation; Control performs bounded cancel/result/release actions | A bounded index must retain the same real operation/result beyond the Start response and registry pruning until actual copied-result transfer/release | Native operation context must outlive Start's transport context through an explicit joined handoff; lost Start response must never cause a fresh automatic import | Valid fallback if the blocking route cannot preserve the actual Invocation owner |
| Existing ObjectImport or ProcessCancel alone | Existing ObjectImport can return before the desired owned completion; NoProgress has no usable process identity | Does not establish the required owner | Swift Task cancellation is not native cancellation | Insufficient; do not relabel it |
| Four independent new Start/Cancel/Observe/Release endpoints | Same required semantics as Start plus one control | Same retention obligations with more generated surfaces | Does not solve ownership by naming more methods | Not proposed |

The proposed names in PROPOSED_WIRE_FIELDS.json are review placeholders. Genuine generated names, native Lib symbols and Swift ClientCommands must come from the original generator and framework build.

## Preferred native application surface

The public application entry should accept only bounded source data and comparisons: protocol, original expected account, source root/Space, target Space, untouched archive bytes and their digest, plus a cancellation secret from the closed original SDK attempt. It must obtain the actual app internally and re-enter the existing private annotation bridge. It must not accept a caller app pointer, filesystem path, ImportRequest, executor, callback, update-existing mode, mapping or completion boolean.

The only new cancellation binding is an immutable record attached to the already-existing ownedAccountImport:

    secret [32]byte
    sourceDigest [32]byte
    sourceRootID string
    sourceSpaceID string

The existing record already has the actual app, accountID, target spaceID and the real operation pointer. The binding is created only by the concrete annotation entry; generic owned imports keep it absent. It has no writable completed/canceled/succeeded state. No second importer, operation executor, account source, persistence database or terminal-result registry is introduced.

The secret must be unpredictable 32-byte data created only inside the closed original SDK operation owner after capturing the real account/selection/source. The public SDK must have no constructor accepting caller strings or bytes to fabricate that owner. On the wire the secret is correlation data, not an account or Space permission: native application/wallet/lease admission and actual current-writer checks remain mandatory. Cancel uses it only to resolve an already-admitted operation with the exact account, target Space and source digest/root/Space comparisons. A zero or wrong-length secret is rejected, and an in-flight duplicate secret is refused rather than starting another execution. It is never logged or used as a progress ID.

The proposed token check covers only currently retained in-flight entries. It is not a durable idempotency key, a cross-process replay barrier, or a guarantee after a Done entry has been pruned. The closed single-use original SDK invocation and the real Host dispatch/uncertainty fence must prohibit a second import of an uncertain saved attempt. This proposal does not silently add native tombstones or an unbounded result cache.

The native ownership sequence is:

1. Validate the concrete protocol and bounded request data. Capture the actual application through the original Service without holding its read lock across a nested admitted call. A replacement between capture and private preparation must be refused by the original pointer check.
2. Use the unchanged original app/wallet/lease and registry ordering. Preserve the old private helper as the nil-binding route; the new bound helper adds only the immutable cancellation comparison and duplicate check before the same real registry insertion.
3. Release Service/registry locks before Start, waits, RequestCancel or any external/native callback.
4. Invoke the real operation.Start exactly once and wait for its actual Done. The original request context remains valid for the lifetime of this blocking native command. Context cancellation requests cancellation; it cannot return a fake drained response while native work or cleanup still runs.
5. Call the actual Result, copy complete bounded native history into an independent response, and only then return. Registry pruning/release may remove only a genuinely Done entry. The local outcome copy remains historical even if AccountStop subsequently retires the app.
6. Do not make a new native import after an unknown transport result. The original SDK single-use invocation and the Host's real durable attempt fence, which is still to be implemented, own that prohibition.

No native context handoff is needed for the blocking route. The source and its request context remain owned until original completion. This is one reason to prefer it over an asynchronous Start response.

## Concrete cancellation behavior

The application cancel entry locks only the existing registry to find the already-owned operation. It matches the immutable secret and frozen account/source/target comparisons, copies the actual operation pointer, releases the registry lock, and invokes only RequestCancel. It does not call AccountStop, remove a stage, delete a registry entry, close Done, mutate Result, create an import or select a replacement account.

The cancel response has three distinct observations:

- REQUESTED: RequestCancel was actually invoked for the matching original operation. It does not claim cancellation has drained or that there were no writes.
- DONE_OBSERVED: the matching actual Done was already observed closed. The SDK still joins the original import Invocation response/drain before releasing its own source lifetime.
- NOT_OBSERVED: there is no matching retained operation at this lookup. This covers a call that has not registered, a mismatched attempt, or a genuinely completed/pruned operation. It cannot prove which occurred and cannot authorize release, retry or acknowledgement.

No fresh selected-Space write permission is required to cancel an already-owned historical attempt. The exact old owner/token still binds the request. No permission is minted by that exception, and ordinary/new write admission remains unchanged.

Cancellation before native registration is the main qualification obligation for this option. The SDK must retain the same original in-flight Invocation and raw-response owner when Cancel says NOT_OBSERVED. It may make bounded, rate-limited cancellation-only rechecks for that same attempt; it must never treat a lookup miss or the end of a wait budget as completion. If a bounded cancellation observation window ends, the attempt remains unresolved and blocks replacement/ACK until the actual original invocation drains or the same owner rejoins it. The protocol must not silently assume that Swift cancellation reached Go, nor invent a cancel-before-start native generation bit.

The exact SDK observation cadence and rejoin implementation belong to the SDK source review. If it cannot meet that obligation while preserving original Invocation admissions, use the Start-plus-control alternative with an explicitly reviewed native ownership handoff. That implementation choice is unresolved by a source diagram.

## Lossless bounded outcome

PROPOSED_WIRE_FIELDS.json specifies the proposed concrete request/history fields. They copy native facts only after actual Done. Native error and body-copy error remain separate; a nil native error alone does not mean the wire body was copied or that the Host is current.

A positive native-history response requires:

- actual operation registration and Done observed;
- actual Result available and no owning native error;
- the actual mapping observation, source-to-native rows and trace, with original empty NoProgress ID preserved;
- actual readback Stage == BodyMatched, exact source digest, actual account/target/root and full native ZIP/report;
- a complete bounded copy with no dropped mapping/file rows, truncation or re-encoding of archive/body content.

Every actual mapping row uses the source archive digest plus its original member path, source identity, converter identity and returned native identity. The private absolute staging ArchivePath is not an external authority or useful SDK identifier; native B1/C already checks it against its owned stage. The wire projection must explicitly document this removal and preserve the source-digest/member binding. All other mapping categories, aliases, per-file outcomes and incomplete/error histories remain distinguishable.

The existing accepted payload policy is unchanged: raw archive <=1,048,576; 512 members; expanded <=8MiB; depth64; 262,144 fields. Proposed additional wire-copy limit is 2,097,152 encoded protobuf bytes for this concrete result, checked before final serialization/allocation. This is a new transport proposal, not a silent change to the Host JSON bound or ActionWireCodec. Exact partial-metadata/resource limits must be checked against the actual nine-leaf result inventory before implementation approval. If a complete result exceeds the approved copy budget, return an explicit COPY_REFUSED history with actual Done and error/category facts; do not truncate and do not claim successful body transfer. Native effects can already exist, so Host uncertainty remains retained.

The native and Swift logging paths must mask the archive bytes, full result archive and cancellation secret for these exact commands using the existing per-invocation masks. No generic logging or existing command behavior should change.

## Alternative: Start plus one control command

If selected after SDK review, expose two concrete generated commands, not four generic public owner APIs:

- Start takes the same exact archive/source/account/Space/attempt data, registers the original operation and calls real Start before returning an opaque native-issued handle.
- Control takes only that exact native handle/attempt binding and a finite action: request cancellation, observe a nonblocking actual Result, or release only after actual Done and copied-result ownership. It cannot change a target, source, archive or owner.

This option must keep a bounded lookup pointing to the same real owned operation when the original lifecycle registry prunes Done. That lookup stores no alternate execution state. Releasing a pending operation is refused; cancellation is never release. Terminal results remain historical after account/source retirement.

The asynchronous transport context must not cancel the newly-owned operation merely because Start returned. Conversely, a canceled preparation must join actual preparation/stage cleanup before it is called refused. No raw context.Background substitution or unchecked context.WithoutCancel should be accepted as proof of that handoff.

Lost Start responses and process restarts remain uncertain effects. A new call or new token cannot silently retry the import. A terminal cache expiry cannot create permission to reimport. The concrete retention bound and recovery/transfer behavior require review; this packet deliberately does not create that registry.

## Proposed native edit boundary and qualification

PROPOSED_PATHS.json lists the smallest candidate native paths. No path is edited in this packet. Existing application/registry/operation/AccountStop remain the owners; the importer and twelve B1/C body/graph files stay exact unless the actual nine-leaf result identifies a concrete defect.

The eventual native RPC qualification should add only genuinely new boundary cases: complete generated import response and real raw-response copy, exact cancel of its owned operation, cancellation lookup before registration remaining unobserved, wrong token/account/Space/digest refusing to cancel another operation, retained error/partial history, and actual Done before response/release. Reuse the historical archive/lifetime/schema evidence at its original scope instead of replaying old standalone selectors. Necessary new disposable source production is input setup, never retroactive credit for old tests.

After native source review, use the original generator once for the actual candidate IDL, retain all generated deltas and compile the real endpoint/Lib symbols. Original Swift concrete Invocation, the closed E2 account/selected-Space owner and the Host saved-row/attempt join remain separately owned integration steps. No hand-written generated method or empty successful response is acceptable.

## Source and publication status

This packet is documentation only on a new sparse branch from exact1ec511. The active native qualification and its sole observer are unchanged. All source citations are actual revision:path byte identities in SOURCE_INPUTS.json. The copied REMAINING_BINDINGS files are unchanged peer artifacts. No test, new producer, RPC, API mutation or production activation is performed by this proposal.
