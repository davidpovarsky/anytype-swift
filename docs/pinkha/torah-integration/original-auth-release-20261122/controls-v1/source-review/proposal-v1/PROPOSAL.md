# Original account startup: reviewed-source repair proposal

Status: source-only proposal. No production source applied, compile/test/native call, account/database change, or readiness claim. The first bounded candidate is only the existing transition's completion waiter. The subsequent Auth/LoginState/decorator changes require review of the exact proposed implementation. Selected-Space code and StageB runtime remain peer-owned.

## Proven original interleavings

| Boundary | Exact original behavior | Required constraint |
|---|---|---|
| AuthService.createAccount/selectAccount -> LoginState | The original closing lease remains through account-bound subscriptions; AccountManager's setter confirmation cannot open the lifetime while that lease exists. SpaceView/Participant capture once and can retain nil. | Complete actual native release before the first account capture and subscription, then freeze that capture. Never recapture an already-invalid subscription source. |
| Invocation GCD native body | Swift continuation resumes before the defer calls completion.finish(). | A Swift RPC return or synchronous transition.finish() is not actual drain. |
| Transition.State.release | released=true is a once-only claim before closing.cancel() and optional confirmOpened(). | A wait latch must be separate and signal only after both effects, with atomic waiter registration. |
| AuthService actor reentrancy | Another account operation can run across setup, native RPC, logging, or subscription awaits; account-ID equality alone cannot distinguish an old same-account attempt. | Exact original flow ownership and synchronous revocation must guard native admission and later publication. |
| Heart AccountStop(false) | cancelStart can return immediately while the original start still owns its real cleanup and RPC drain. | Preserve prompt native Stop dispatch; no global mutex/queue behind the pending start. Stop return alone cannot reopen or certify cleanup. |
| Original Login Back action | Back is enabled while accountSelectInProgress and invokes logout(false). | An unconditional overlap rejection/queue changes the actual cancellation route. |
| PinkhaHanlinAuthService | changingAccount rejects all overlap; create/select resume bootstrap and accountDidOpen after awaits without exact attempt checks. | Any narrowly allowed Stop overlap also needs stale-start retirement and checks after those actual awaits. Simply deleting the Boolean is unsafe. |
| LoginStateService | Sendable class has compound unowned start/stop awaits and an untracked membership Task. Atomic flags do not serialize this lifecycle. | A stopped old startup must not restart a later service or publish into the next account. Track/drain the owned sequence and membership task, while allowing native Stop independently. |

## First concrete API candidate

File: Anytype/Sources/ServiceLayer/Account/EditorAccountWriteTransition.swift.

Add internal async finishAndWaitForRelease(verifiedAccountIsCurrent:) -> Void. It delegates to existing one-shot finish, then waits for State.releaseCompleted. The completion latch is set after the existing lease cancellation and optional verification/confirmOpened effects. Waiter registration and completion share the existing State lock; continuations resume outside it. Existing synchronous finish, deinit, named RPC allowlist, original operation drain, and committed event behavior are unchanged.

Void is deliberate: it certifies only that this transition's actual release effects completed. Another closing lease, retired flow, failed account identity, cancellation, or unavailable real AccountManager lifetime can still deny the first frozen account capture. It is not helper readiness, subscription readiness, selected-Space authority, or an SDK receipt. A second call cannot replace the first stored verification closure. Cancellation of an awaiting Swift caller does not release a still-running native body or synthesize successful drain.

The original account must be installed under the closing lease, verified against the exact current attempt and returned native account, and only then the finish/wait seam used. After waiting, recheck that same attempt, cancellation and exact account; obtain the first actual AccountManager token and retain it for subscription startup. Never poll availability until a later account becomes eligible.

## Subsequent bounded implementation seams

1. Keep original AuthService ownership. Capture a private attempt before its first suspension, synchronously retire it on cancellation or the narrowly allowed Stop supersession, and identity-check its cleanup so an older defer cannot clear a newer operation. A queued GCD native start must validate that same frozen attempt at the existing transition permit's actual begin boundary; checks only before await are insufficient. This is a restriction on original authentication, not another selector or a public caller-Boolean capability.
2. Preserve original Stop behavior. An allowed logout(false) must be able to issue original AccountStop while a real start is pending. The retired start's closing lease and cleanup remain until actual drain. Starts or unrelated account mutations need explicit bounded busy/currentness outcomes while an earlier cleanup is unresolved; do not make all auth calls wait behind an unbounded start. removeData=true keeps the distinct original native erasure/error path and must never inherit the false-path shortcut.
3. Give the existing LoginState subscription sequence an exact owner/captured account. Check before and after every suspension and keep its tasks owned. Retiring a startup prevents new steps immediately; stop and a later startup must coordinate actual in-flight start completion so stale stop cleanup cannot tear down a fresh account. No await occurs under a thread lock. A method returning without a callback is not opaque Participant/Space permission proof.
4. Keep the Hanlin wrapper thin, but compose the same bounded attempt/Stop rule around its existing close/quiesce/base/resume/open awaits. No stale continuation may resume bootstrap after Stop wins; journal flushing/removal semantics remain unchanged. Root must review the concrete wrapper scope before application.

## New controls proposed only for the first completion seam

- No admitted RPC: first exact verified release completes and a first account token is possible.
- Admitted original operation remains in its native body: waiting cannot finish or open a token before actual completion.
- Interleave a second waiter while the original verification callback is running, after released=true but before confirmOpened: neither waiter returns until the effects finish.
- Another original closing lease remains: this waiter can complete but account token remains unavailable.
- Cancellation while the actual operation is admitted: it does not release the lease or complete drain early.
- First finish without verification cannot later be upgraded by a duplicate finish-and-wait call; existing first-call semantics remain.

These would exercise exact original Lifetime/Operation/Dispatch/Transition code with controlled disposable callbacks, and must be labeled portable control scope. They do not prove actual Heart startup, original Combine/subscription callbacks, native SDK or StageB acceptance. No existing passed policy/SQLite/Native cases are selected.

## Remaining source-derived issue and scope

The original withUncancellableHandler ResumeBox does not retain cancellation before continuation/task installation. This is an unexecuted source interleaving, not a claimed runtime failure. Keep the shared global helper unchanged until its actual call closure and semantics are reviewed; an Auth attempt captured before installing its cancellation handler must nevertheless deny late admission when cancellation has already won.

Native source selection is immutable d98420b1113536afd08cde6de9a5816f6d27ffff; the four retained start/stop files are disjoint from r14. Swift is immutable 37f48119609747c01ee92cf597e4216f63b7bfa4. SOURCE_INPUTS.json binds every cited full source. No mnemonic, live account data, or user database was inspected or logged.
