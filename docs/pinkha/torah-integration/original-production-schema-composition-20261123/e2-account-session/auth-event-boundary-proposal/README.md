# Frozen original auth presentation and event delivery proposal

Status: proposal only. The seven accepted E2 product afterimages remain frozen. No Auth, native, event, view-constructor or framework facade product source is changed by this packet. The complete source inventory and exact originals are retained for review. The one complete proposed AuthService afterimage is unapplied and uncompiled.

## Why the existing restriction must reach actual admission

OriginalAuthAttempt.startupBinding validates and acquires every capture immediately at the original Invocation permit. A presentation-retirement observer alone is insufficient: retirement marks one lifetime unavailable before invoking its observers, leaving a real interval in which a separately observed child can still admit using only its own captures. The proposed default-empty `restricting` initializer parameter appends the already frozen presentation capture alongside the original parent captures. Its default parent remains OriginalAuthRequestContext.parent. The same original capture acquisition, parent observation, named-RPC binding and actual native completion remain in charge. It creates no account/Space authority and does not change any default caller.

This extra AuthService.swift hunk needs explicit source-scope review. It is the narrowest identified change that lets the existing original native admission atomically observe a closed presentation without discarding existing parent lineage.

## Frozen caller, not a global current-presentation lookup

The existing registered PinkhaHanlinAuthService remains the only AuthService wrapper. An internal, immutable presentation handle is minted by that exact registered actor after deployment setup, with one captured restrictive lifetime. No replacement AuthService instance, Factory override, public token constructor, source-ID authority, DEBUG SPI or disposable credential is introduced. Its forwarding AuthServiceProtocol value always calls that same registered actor with its exact frozen handle. A private task context can transport that already captured handle across the immediate forwarding call; it never chooses an owner or retags an event. The original OriginalAuthRequestContext.parent is preserved independently.

At the wrapper's existing `perform` admission, the actor checks the exact active handle, admits its lifetime, constructs the existing OriginalAuthAttempt with that capture plus the existing parent lineage, and records startup admission under the same actor before it can dispatch. A retired handle cannot be replaced by a later current handle. The original standalone bodies remain the default path.

## Explicit original view construction chain

Five existing view constructor seams are required because their private State models are created during later SwiftUI evaluation. A TaskLocal around the outer View value's construction does not capture those deferred constructions. Proposed immutable constructor forwarding is:

| Existing view | Frozen forwarding |
| --- | --- |
| AuthCoordinatorView | To PrimaryAuthView and LoginCoordinatorView |
| PrimaryAuthView | To PrimaryAuthViewModel's added internal initializer |
| LoginCoordinatorView | To LoginView |
| LoginView | To LoginViewModel's added internal initializer |
| DeletedAccountView | To DeletedAccountViewModel's added internal initializer |

The already approved ApplicationCoordinatorView/Model pass the same handle, including the deleted-account route and persisted-account restore. The old public/default initializer behavior stays exact. Each model retains an immutable optional caller; its original injected service is used unchanged for standalone, and the frozen forwarding service is used for embedded calls. No model obtains a later owner from a singleton. These five view paths are proposed additions, not implemented changes.

## Whole original UI operations and escaped callbacks

Tracking only the Auth RPC is insufficient. Primary createAccount continues through push registration, usecase/workspace writes, seed persistence and onSuccess after the RPC. Login walletRecovery persists the seed before accountRecover. The original body must remain one tracked operation until it actually returns, including its original catches, not merely until cancellation is requested. The minimal wrapper retains a child Task for that original body, admits it through the frozen lifetime, cancels it on retirement, and releases the original lifetime observation only after the child's actual return. It does not replace any original auth or UI logic.

Entry inventory requiring this wrapper: Primary createAccount and app-action subscription; Login keychain action, entropy action, wallet recovery, AccountShow subscription, selectAccount and logout; DeletedAccount restore/logout Tasks; ApplicationCoordinator persisted login/select plus its account/state consumers. The secure-alert continuation and migration onFinish callback can escape an earlier operation and must enter using the same retained model/caller again. The complete original continuation, including seed reads before walletRecovery, needs the entry check. TaskLocal inheritance alone is not evidence of ownership. Synchronous navigation callbacks must also reject the retired embedded handle.

The retained process owner keeps actual consumer tasks through shutdown and joins them; the presentation view disappearing cannot discard their lifetimes. New owner installation remains blocked until those original operations and queued event deliveries have completed. The later onboarding subtree reached by Primary onSuccess still needs its own source inventory before claiming complete account-creation presentation retirement; this packet does not infer that proof from the three Auth models.

## Close states and actual native Stop

Closing synchronously retires the frozen caller, then uses the original wrapper's current/previous attempt and actual startup-admitted fact. It does not infer native startup from accountID or a UI flag. An untouched or ordinary-only presentation drains its admitted ordinary/native and whole UI operations and returns a distinct closed-before-account-start result. It must not call native AccountStop merely to manufacture success; native correctly reports ACCOUNT_IS_NOT_RUNNING for an untouched landing page.

An actual admitted startup uses the original logout(false) ordering: dispatch real original Stop before joining a retired startup. A pending ordinary operation must actually return before the original wrapper can accept Stop. A failed Stop retains the original successfulStopRequired poison and keeps the retired owner installed for an explicit retry; it cannot admit a replacement owner or be reclassified as drain-only. Duplicate close calls share one retained close operation/result. A completed native cancellation request alone is not drain: the original startup/UI operations and queued events still have to finish.

## Two actual event boundaries

AccountEventHandler and FileErrorEventHandler currently call EventBunchSubscribtion.addHandler, which schedules registration in an unretained Task. Awaiting startSubscription therefore does not establish upstream registration, even when the separately accepted downstream Combine demand gate is ready. Existing addHandlerAwaiting performs real actor registration before returning. The proposed embedded registration path adopts that original method, retains/validates its installation through concurrent stop/cancel, and leaves original standalone registration unchanged. It must not return success from a merely created Task or a canceled registration.

The original ServiceMessageHandler native callback only yields Data to an AsyncStream; a single existing consumer later decodes and awaits all original handlers. A late AccountShow from a retired ordinary recovery can therefore still be queued after the RPC returns. Capturing the old Login model protects its own callback but does not prevent a newly subscribed model from receiving that queued global broadcast. A fence must cover this existing FIFO before replacement-owner installation. The proposed fence records a monotonic accepted-chunk frontier under the same synchronous enqueue lock and acknowledges each chunk only after its existing awaited handler returns. Waiting captures the current frontier; completion/cancellation of the consumer fails unresolved waiters. It never sends a synthetic event, reorders data, adds buffering or credits a completed RPC as event delivery.

For AccountRecover, the native owner's read-only trace proves its AccountShow callback is synchronous. The callback enqueues into this original FIFO before the actual RPC returns; after that original operation drains, the FIFO frontier can cover its pending broadcast. This specific proof must not be generalized to unrelated background native producers without their own lifetime proof.

## Required bounded controls after source approval

1. Standalone default source inverse and default-empty parent/capture behavior.
2. Presentation retirement before admission, and immediately before/after actual original named-RPC admission, retaining every original parent capture.
3. Ordinary wallet recovery completion/cancellation, with no false native Stop receipt.
4. Real startup cancellation: original Stop first, then actual startup and UI return; failed Stop blocks replacement and permits retry.
5. Late old-model recovery, AccountShow, secure-alert and migration callbacks after another presentation would otherwise be installed.
6. Old queued native AccountShow delivered through the real FIFO before the replacement subscriber; held handler prevents the fence from completing.
7. Registration stopped/canceled before or during awaiting upstream installation; original downstream positive-demand/cancellation gate remains separate.
8. Duplicate close, canceled UI waiter and actual retained cleanup completion.

Portable lifetime controls cannot qualify Combine, UIKit, Keychain, App Group entitlements, native account bootstrap or the new production ABI. Those remain actual Apple/native gates.

## Existing readiness evidence terminology

The accepted seven-source packet's EXTRACTION.json status FAIL/passed[] is an initial preexecution snapshot. It is preserved byte-for-byte. Final RESULT.json SHA256 6fdf80a3336c1b737c0ef5afd082d015c2713385c822d61915aa5088c31d2178 and its eleven command stream records establish the actual eight PASS controls/79 assertions. No source-control rerun is requested here.
