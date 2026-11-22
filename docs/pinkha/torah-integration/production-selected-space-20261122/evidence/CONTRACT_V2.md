# Original selected-Space prerequisite — source proposal

Base: 37f48119609747c01ee92cf597e4216f63b7bfa4. This is a prepared candidate for independent review. No product source has been applied, and no new control, parse, framework build, native call, account selection, schema write, receipt, mapping or ACK has run for it.

## Bounded contract

The proposed product paths are Anytype/Sources/ServiceLayer/ActiveSpaceManager/ActiveSpaceManager.swift and Modules/Services/Sources/Services/Workspace/WorkspaceService.swift. Existing concrete callers and the protocol remain unchanged. Two passive internal types and the manager's original lifecycle live in that file. No new dispatcher or document Owner is created.

An original non-nil setActiveSpace request synchronously freezes:
- the exact requested Space;
- the actual AccountManager's existing opened lifetime token before the one AccountData read, followed by token validation;
- a new passive source lifetime belonging to that exact manager request;
- when already available, the original SpaceViewsStorage callback-produced permission, matched to that exact account source/token and Space.

There is no later account or view recapture. Missing original SpaceView authority is retained as missing for the whole request. The ordinary UI can still receive the native AccountInfo, but currentOriginalActiveSpaceSelection remains unavailable for that request. A protocol replacement or caller DTO cannot mint the opaque result.

A new request retires the previous source before any suspension. It captures the previous manager task and waits for its result before entering the next request's direct service sequence. A superseded continuation cannot publish manager info, clear the new request's manager state, invoke later direct stages or return a current opaque selection. The currently running manager task is deliberately not cancelled as a substitute for drain: original native Invocation cancellation may return before its dispatched native call has finished. Cancellation of a caller awaiting a shared manager selection does not silently deselect the global manager; the caller checks cancellation before requesting and after waiting. Replacement, stop, account retirement and captured view retirement are the selection authority boundaries.

The manager's WorkspaceOpen uses the existing SourceBinding and original Invocation with the exact RPC name WorkspaceOpen. The new non-requirement WorkspaceServiceProtocol extension first casts to the original internal final WorkspaceService and rejects every replacement conformer. Through that statically dispatched extension, it calls the unchanged original workspaceOpen method, which must issue the original ClientCommands.workspaceOpen and decode that native response using the unchanged original AccountInfo.asModel implementation. It cannot qualify a replacement service merely returning a matching DTO; no caller-supplied boolean or response receipt is accepted. This closes the source-only defect found in frozen candidate b19, whose plain protocol call could return without any named native dispatch. It is a mutation scope, preserving original withChat:true; it is not called a read. A document/read task-local dispatch capability is refused as a global selection entry. The new binding has nil parent and no document Owner. MainActor construction validates the frozen captures before and after construction and checks each newly constructed binding capture for exact source identity and original token. A changed or reopened account cannot substitute a new token during the actor hop.

The original selection lifetime's admitted operations are awaited after WorkspaceOpen return and on the failure path. This is only original per-RPC WorkspaceOpen admission/drain. A prepared but not admitted late native dispatch sees the closed original operation lease. An already admitted native call may complete after source retirement; its outcome is never described as rolled back. No current successful opaque selection is published from that retired request.

Native AccountInfo must retain exact requested accountSpaceId and a nonempty spaceViewId. When a view was captured before opening, the returned spaceViewId must equal that original view ID and the original targetSpaceId must equal the request. The opaque OriginalActiveSpaceSelection is minted only in this latter case. Its initializer is file-scoped; it retains the request and validates the actual account, selected generation and view generation. capture(matching:spaceId:) compares the real account source/token and exact Space and returns the source capture whose lifetime is synchronously retired by the retained view/account observers. It is a selected target prerequisite, not canEdit or authority to create objects.

Stop revokes selection and UI state synchronously, fences new starts/selections, and joins the same previous manager task before performing the original shared clear sequence. Duplicate stops join the same task. Start has an exact subscription object; a queued callback from a retired subscription cannot operate on the replacement manager subscription. Original public UI storage and stream remain caches, and no atomic cross-thread UI rollback is claimed.

## Explicit unresolved dependencies

1. Widgets.prepare spawns an independent task; clear cancels/discards it and releases document references. waitForReady completes a captured task but swallows errors and lacks current-attempt verification. BaseDocument open/close drain was not established by this audit. This candidate does not claim widget readiness or original native close drain.
2. MultispaceOneActiveSubscriptionHelper swallows subscribe/unsubscribe errors, accepts late captured-space callbacks, and writes a prepareData result after its await without an account/attempt fence. ObjectTypeProvider/PropertyDetailsStorage Void return is not proof of successful subscription or teardown. The candidate serializes only manager-owned selection/stop calls; prepareSpaceForPreview and independent helper callers retain their original behavior. Their native readiness, late cache publication and account teardown require separate original lifecycle repairs.
3. AuthService holds EditorAccountWriteTransition's closing lease through LoginStateService.startSubscriptions, and only confirms the account in its deferred finish. The first original Participant/SpaceView attempt can therefore retain nil account authority. No delayed capture in this proposal repairs or conceals that ordering. A separate smallest original auth/subscription ordering repair must preserve actual native transition drain and original subscription stop behavior.
4. Account retirement immediately invalidates opaque selection, but existing independent helper callbacks/UI caches are not transformed into authority or globally drained by this patch.
5. This candidate adds no caller, production SDK factory, document mount, application transport, native annotation schema registration, identity receipt, body proof, SQLite writer, ACK, release/device distribution or account bootstrap.

## New controls proposed after review

Use genuine serialized Swift Testing against the complete proposed manager/attempt/selection bytes, complete original AccountManager, Capture, Lifetime, Operation, SourceBinding/Owner and InvocationDispatchBinding, with explicit original decoded-model/DI/publisher/provider/native-dispatch probes. Positive native-observation boundary controls must compile the actual final WorkspaceService method and its new closed extension; only its native dispatch dependency may be an explicitly labelled probe. No replacement WorkspaceServiceProtocol returning a DTO may be used as a positive qualified-selection witness. Existing opaque SpaceView permissions must be produced through the actual SpaceViewsStorage actor callback, not DTO constructors or booleans. No previously passing Participant, Space, composition, metadata, SQLite or producer semantic suite is replayed.

The focused groups will separately observe:
1. Exact original account/request/native Info/view identity and positive opaque capture; wrong native Space or captured view ID rejects.
2. Missing original SpaceView capture remains unavailable throughout a request even if a newer callback later supplies permission; no delayed recapture.
3. A→B and A→B→A suspended WorkspaceOpen schedules retire old captures and publish only the current request.
4. Original account retirement before dispatch rejects native admission; admitted WorkspaceOpen retains its original drain until native completion even if manager retirement wins later.
5. Stale failure and late success cannot clear or publish B, including after helper awaits.
6. Stop/start overlap and duplicate stop join the exact pending manager task; stopped-subscription callbacks are rejected.
7. Actual account replacement or exact captured view retirement invalidates selection synchronously; reopening/restoring does not revive the old source.
8. Caller cancellation/shared same-Space waiting remains distinct from global manager selection retirement; original caller behavior and new authority limits are explicit.
9. Manager deallocation retires a retained selection where no operation still legitimately retains the original manager.
10. Existing task-local original read/document capability cannot be promoted into WorkspaceOpen; no named-RPC or account/source restriction is weakened.

These are proposed controls, not pass claims. Actual Swift compile may require a narrower original dependency projection; all such probes and source bytes must be frozen and independently reviewed before execution. Full Apple, real Combine/native RPC/UI and production account startup acceptance remain separate.
