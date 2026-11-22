# Explicitly owned original import route

Status: source design after the immutable d984 lifetime audit. No native route is enabled, no existing importer or lifecycle source has changed, and no new native execution is claimed. The frozen origin observation packet at `20cb8998` and active compatible compile-only gate at `32adc5c7` remain separate.

## Findings that determine the design

The original importer shares its mutable protobuf converter and native ID provider across calls. `Import(IsSync:false)` launches unjoined work using its component context; `Close` only cancels that context. Original `readResults` joins a worker batch only through normal result-channel exhaustion. Cancellation and ALL_OR_NOTHING error branches call Stop and return while a worker may still be executing. The passed 50 controls already demonstrate that distinction and will not be replayed.

`FileSyncer.Sync` calls `UploadBlockFile(nil, ..., false)`. This nil is an event `session.Context`, not `context.Context`. The original file editor discards the channel returned by `UploadAsync`, and that uploader deliberately uses its service context instead of the argument. Therefore even a successfully drained importer batch excludes later file upload/reference updates. The relation and icon syncers call synchronous `UploadFile(context.Background(), ...)`, so cancelling an importer context does not cancel those uploads. The actual URL reader creates its HTTP request with the supplied context and uses `http.DefaultClient`; no timeout is installed in that function.

The original uploader completes its file-object creation and block-update attempt before returning its UploadResult, but `updateBlock` only logs an error applying the final block update. A completed upload channel proves that attempt finished; it does not prove the resulting block reference or full body was saved. Native semantic readback remains necessary.

The application closes components in reverse registration order. Importer is registered after fileuploader, so importer Close runs first. Adding an importer Close wait cannot depend on later fileuploader Close to unblock it. The pre-close StateChange pass stops indexing/gateway work and marks recovery/FT state; it does not cancel importer or fileuploader contexts.

There is no direct application.GetApp reference in the bounded retained importer/block/file/Space source search. That is insufficient to permit a join under the application writer lock: the original CallbackSender synchronously calls a supplied function, and the mobile bridge synchronously calls MessageHandler.Handle. That callback could reenter a native read or lifecycle call. The design therefore puts neither an operation join nor a long RLock around async import work.

## Smallest internal hook set

### 1. Native upload completion with an operation context

In `core/files/fileuploader/uploader.go`, extract the existing UploadAsync body into a private `uploadAsync(ctx)` helper. Legacy UploadAsync continues to pass `u.serviceCtx`, preserving its current behavior and result channel. Add an internal owned entry point that accepts only the original concrete uploader, passes the owned operation context, and retains the real returned completion channel. No existing interface or generated mock needs a new method.

The owned completion is a closed type with no public field constructor or deserializer. It records scalar native result fields, including the actual destination file ID, only after the original upload channel has closed. Mutable details and encryption-key maps are not exposed; archive/request binding belongs to the later operation envelope. Cancellation requests call the owned cancel function; they never close the completion signal. A closed channel without its one expected native result is an error. The owned route rejects shared preload handles because waiting on an unrelated preload is not owned cancellation.

In `core/block/editor/file/file.go`, factor only uploader preparation so legacy `upload` keeps its existing order and default context. Add a package function that constructs the original sfile around the same held SmartBlock and starts the owned upload. In a new `core/block/owned_file_upload.go`, use the original `cache.DoContext` and the actual file editor; return the started completion even if initial Apply fails. The operation tracker registers that completion before releasing admission. Never wait for it while holding the object lock.

The first version may retain final block-update failure as an explicit unproven effect rather than change legacy updateBlock semantics. No successful result of this route is called applied-body equality. The native archive comparator must verify the final body/reference state after all completions drain.

### 2. Per-operation original import dependencies and complete drain

Add `core/block/import/owned_import.go`. Build a fresh protobuf converter and ID provider for each owned operation from the same retained original components. Do not reuse the legacy component's mutable converter/provider or place a mutex around a long legacy Import call. Construct the original object creator with a scoped BlockService adapter: synchronous UploadFile and object lookups use the owned context; asynchronous block uploads go through the new completion hook and are registered in the operation's file tracker. No global service context is cancelled.

The owned processor uses a separate result-drain policy. On cancellation or first error it stops accepting work, requests cancellation, and continues consuming the original worker result channel until its actual WaitGroup closes it. The legacy readResults behavior stays unchanged. After all admitted object workers stop producing new file operations, seal the file tracker and join every registered native completion. Only then may the owned Done close. Errors retain partial mapping/file observations and never publish a complete success receipt.

Keep the two source identity stages and file-reference domains separate. Generated collections, filtered snapshots, kept IDs, alias keys, uploaded file object IDs and archive members must not be collapsed into one dictionary. The existing diagnostic observation remains historical; an owned operation envelope adds actual account/Space/attempt and exact archived-input binding before any future authority can be offered.

The scoped adapter also exposes a concrete limitation: bookmark sync can launch separate async work. Until that path has an owned completion, the owned archive preflight must explicitly reject a bookmark that requires a fetch. Existing bookmark objects with no fetch and supported static body data must be classified from actual parsed source. This restriction cannot be reported as successful full-archive support.

### 3. Short account admission and nonblocking lifecycle retirement

Add a private owned-operation registry to `application.Service`, with a separate mutex. Admission acquires the existing Service RLock briefly, validates the exact current app pointer and actual wallet identity, checks that no lifecycle retirement is reserved, and registers the owned operation before releasing the RLock. The work uses retained components directly. The registry does not accept arbitrary caller completion functions or caller-manufactured drained flags.

Lifecycle retirement must occur before the existing writer lock, before publishing a new start attempt, and before changing/releasing any account lease. The exact original lifecycle entry points are Service.Stop, AccountCreate, RecoverFromLegacy, AccountMove, AccountSelect, AccountStop, and AccountChangeNetworkConfigAndRestart. WalletCreate/WalletRecover and SetEventSender/SetClientVersion do not close the active app and are not automatically broadened into import cancellation sites.

The retirement helper blocks new owned admission and requests cancellation of every operation admitted to the actual active app. If any actual Done is still open, it returns an explicit `owned import drain pending` error immediately, without entering the lifecycle writer lock, closing components, clearing the app pointer, deleting files, changing wallets, or releasing the account lease. This avoids both a writer-lock/GetApp cycle and a synchronous event callback joining its own import. Pending is not successful Stop or completed cancellation.

When every registered Done has closed, a retry reserves an empty-registry retirement token, then performs the existing lifecycle method under its existing lock. New owned admission remains blocked until that method releases its token. With an empty registry, existing lifecycle ordering and component Close behavior remain unchanged. The existing AccountStop fast cancellation of an already pending AccountSelect is preserved; owned import cannot be admitted while that start's retirement token is active.

Do not implement the guard only inside closeApp. Current stop, restart, account move/removal, and same-account switch error paths can release the account lease even after closeApp fails, and cancelled start cleanup ignores stop errors. The pre-lifecycle admission guard is required to keep the original account alive while owned operations drain.

### 4. Closed consumer integration

The SDK-owned import path keeps the original invocation admitted until the native operation and its file completions actually drain. On owner retirement it requests cancellation through its owned token. It may await the actual completion outside native event callbacks, then retry lifecycle; it must never treat the first cancellation acknowledgement or an ObjectImport immediate response as completed work. A failed Stop continues to block new startup under the already corrected Auth policy.

The native route initially stays internal, with no RPC/product callsite or ACK. Before enabling it, bind the source archive bytes/member inventory, original account and Space, attempt, selected snapshot coverage, actual map and file choices, and a final original semantic export comparison. A fresh same-ID export remains historical and non-atomic; remapped graph proof requires genuine mapping authority and complete file/reference comparison.

## Review and meaningful new controls

The first bounded source diff should contain the uploader/context/completion hook and its original editor bridge, followed by the operation-local dependency/drain implementation and account admission integration. Review those changes independently from the frozen observation packet and running compile gate.

New controls should exercise only these changed boundaries: operation cancellation reaches a blocked synchronous native upload; async completion remains pending after cancel acknowledgement; completion is registered even if initial block Apply fails; a worker failure cannot release an operation before all original workers and file channels finish; two owned imports use separate converters/providers; one operation's cancellation does not cancel another; a reentrant event callback can read GetApp and receives pending from Stop without a self-join; account Stop/Select/Move/remove cannot release the lease while pending; retry after actual drain closes the same original account; and all empty-registry lifecycle paths retain their original order. Actual original-module/native compilation and a genuine native import fixture remain separate required gates. None of these controls may be substituted by synthetic whole-body or ACK claims.

## Additional original service boundary

The immutable d984 `filesync.service` holds a component-wide import-event queue. `SendImportEvents` broadcasts that queue while holding its mutex; `ClearImportEvents` clears the whole queue. The remote backup workers can append later file-limit notifications, independently of local object/file upload completion. No owned import result may claim that this queue or the remote backup service drained. The source-only owned route must preserve legacy default behavior and keep local completion, notifications, and eventual remote synchronization distinct.

The current import-layer draft reserves a file slot before calling native object-lock/upload admission, so even a started upload whose initial Apply fails is retained. Sealing waits for each initial call to return before its actual upload completion can be consumed. The bookmark guard checks the actual live block supplied by the original creator and rejects an unjoined fetch at that point, rather than relying only on an earlier archive inspection.
