# Original SpaceView authority prerequisite — source and focused evidence

Base: `b854e7f3f59690134bcabdef88527b61517d5ab5`. Fresh upstream develop: `d857b23ea540be33d6faab4f7a7a1a260ab578c1`; merge-base `d5650321577a209505a3277c8437b7608cff1cb9`. The baseline SpaceViewsStorage source is byte-identical to that upstream file. The isolated branch is `codex/otzaria-original-space-authority-20261122`.

## Concrete gap and approved scope

The original class publishes decoded SpaceViews from the original SubscriptionStorage callback but owns no start/stop identity or revocable permission snapshot. Its public publisher throttles for 50 ms, and per-Space compactMap suppresses disappearance. An adapter consuming that UI stream therefore cannot synchronously retire an earlier capture before the original publication. The original SubscriptionStorage can finish a subscribe after a concurrent stop; its same-data fast path may then retain an earlier callback/state. These are source observations, not executed reproductions.

The root assigned this original file under the standing owner development authorization. The sole product change is an actor-owned lifecycle and an opaque original callback observation in the same file. No Heart/protobuf/schema, Participant implementation, RPC endpoint, public facade, identity receipt, ledger writer or ACK changes occur. Rollback is the exact source-only commit revert, without modifying native data.

## Candidate behavior

- All compound lifecycle and permission mutations run on the SpaceViewsStorage actor. Existing public synchronous getters stay nonisolated and use the existing thread-safe storage; AtomicStorage holds only immutable committed permission snapshots.
- An actual AccountManager generation is captured before one AccountData read. The original callback alone creates observations for the first active native SpaceView per exact target Space, carrying native view ID, account ID, technical Space and actual account source/token.
- A passive account-generation observer retires the view lifetime synchronously before AccountManager publishes a replacement account. Both account and view tokens remain mandatory. Foreign AccountManagerProtocol implementations retain their UI path but cannot mint this prerequisite.
- Native disappearance, inactive status, view replacement, access/status/type/legacy restriction changes and stop retire earlier view captures before the immutable permission snapshot and original UI publication. Unrelated display changes update the original value while retaining the unchanged authority token.
- A passive lifetime on the actual start attempt is retired synchronously by withTaskCancellationHandler. Each view observes and validates that attempt as well as the account, so cancellation during a suspended original start cannot mint or retain a permission, including callbacks delivered by another task. The handler covers the full original start and settlement. Explicit checks inside it precede native subscribe, including cancellation between preflight and handler installation. Stop also retires the attempt before any suspension. The handler performs no RPC or asynchronous actor hop; original subscribe still drains before awaited teardown.
- Source deallocation retires every externally retained view observation through the immutable snapshot; it does not start native cleanup from deinit.
- One starting or active attempt may publish, because SubscriptionStorage awaits its initial callback before returning. The callback explicitly awaits the SpaceViewsStorage actor and rechecks attempt/account there. Stop denies publication before its first suspension, drains any pending start, then performs the one original unsubscribe. Overlapping stop calls join it; failed unsubscribe blocks a new start until an explicit successful stop retry.
- The original UI throttle, first-record lookup and stopped UI cache are preserved. No UI publisher or compactMap result is used as edit authority.

## Boundary that remains open

`OriginalSpaceViewPermission` exposes the original native view plus validate/capture(matching:spaceId:). It is only the SpaceView prerequisite. Full production authority must capture the original Participant prerequisite against the same actual account source/token and apply the unchanged original rule:

`participantCanEdit && (!spaceView.isLegacyStream || isOwner)`

The complete facade/native schema/opaque readback receipt and StageB qualification are still open. These local tokens are not native identity/body receipts and cannot authorize a ledger identity writer.

## Actual execution and exact compiler scope

Source-only commit: `37731bcfdfda320b3a58356b54719e904c399810`. Product SHA-256: `f1570f8cff28d87152ea455ded6bc0bdfeb729e0beb3a70e3a47fb06b4710a57`.

One finite Sentinel execution, `job_0c63ea11d5be`, completed successfully at 2026-11-22 06:20:57 UTC. Full product-file syntax parse passed, the projected complete original actor compiled, and all **22 new controls passed**. No previously passed suite or assertion was executed again.

The compiler was **Swift 6.3.3, targeting Windows x86_64, using `-swift-version 5` and `-strict-concurrency=complete`**. This is Swift 5 language-mode checking by the Swift 6.3.3 toolchain, not Swift 6 language-mode or Apple module acceptance. Compilation took 31.5 seconds; the 22-control executable ran once in 0.359 seconds, PID 31264.

The compiler emitted 22 identical conversion warnings at the fixture's sequential global-function dispatch table (`Controls.swift`); the projected product source emitted no warnings. The table invokes capture-free global test functions serially. The original diagnostics are retained unchanged; the passed input was not edited or replayed merely to suppress fixture annotations.

| New control group | What was actually observed |
| --- | --- |
| Initial source and identity | Initial callback accepted before original start returns; frozen technical Space; exact account/Space matching; foreign manager and byte-case mismatches rejected |
| View changes | Disappearance, native view replacement, legacy/access/status/type changes retire captures before the publication probe; inactive first duplicate cannot grant; display-only update retains token |
| Account changes | Actual AccountManager generation retires the view before account publication; same account text does not revive an older generation; old callback denied |
| Subscription lifecycle | Stop revokes before suspension, waits for pending start, joins duplicate stop, rejects old attempt callbacks, and blocks restart after failed unsubscribe until explicit successful retry |
| Cancellation | Exact pre-handler cancellation at the builder boundary prevents subscribe; canceled pending start rejects callbacks from another uncanceled task; retained capture retires before cancel returns, without an actor hop |
| Source destruction and failure | Retained permission fails after actual weak storage release while account remains current; failed/already-canceled startup leaves no authority |

Twelve canonical Git inputs and seven actual compiled source copies are bound in `controls/INPUTS.json` and `evidence/EXECUTION.json`. The runner verifies product/source inputs before execution and compiled copies/product afterward; retention also rehashes the actual executable and compiler.

- Actual result SHA-256: `17ce9bb5ba8402869aec112c7ad2d9dbe5d6044df47ed0ec6fcb9c6bfce00dee`.
- Actual execution receipt SHA-256: `2a010a4883b50de9b2a6dd54618990512916c2c1fdff00c872dee140c87a46e2`.
- Executed binary SHA-256: `29bdcdcdcb18a71a490f8d79581bdb9c00ef4c473d847d5af07c52a8df626f04`.
- Compiler executable SHA-256: `e1d0a0b20d95a92b22f4906e7ca331a7c8b89be86b2d9a2d215ac24f753e945a`.

## Explicit fixture and acceptance boundaries

The complete changed actor and original lifetime/capture/account declarations are retained without body edits. Only external imports and unchanged protocol convenience extensions are omitted for same-module portable compilation; read-only waiter probes are appended. Native `isActive` and `isLegacyStream` predicate bodies are exact source fragments.

Already-decoded SpaceView field inputs, Factory/Container, publisher, subscription and locking dependencies are explicitly disposable probes. Actual ObjectDetails/protobuf decoding, Combine throttling, original SubscriptionStorage RPC behavior, Apple frameworks, full app/module typechecking and end-to-end native integration are **not exercised**. Raw control observations mentioning a native stop/subscribe describe the instrumented SubscriptionStorageProtocol boundary; actual Heart/native calls are zero. Compiler/toolchain/version/hash and exact substitutions are recorded, not inferred from the full syntax parse.

The original 52 policy controls, SQLite packets and Native/Apple acceptance were not rerun or transferred to this new source. The full Participant + SpaceView admission seam, native annotation schema, opaque owner-checked identity/body receipts, ledger identity writer and delivery ACK remain unavailable/open. No task is closed by this packet.

## Source review corrections (not executed RED tests)

Both initial draft review and SDK peer review identified an omitted deinit retirement and a starting-callback cancellation window before the final Task.isCancelled check. Candidate v2 adds those narrow lifetime closures before any controls. The v1 patch is retained only as source-review provenance; no test or runtime failure is claimed for it.

UI cache publication is not an atomic cross-thread cancellation rollback. The callback rechecks attempt and account immediately before the final cache update, while synchronous revocable captures remain the authority. Root and SDK peer reviewed the complete candidate and approved bounded new actor controls, not native or Apple qualification.

## Independent review

Root read all 22 assertions and actual receipts, then independently verified the 12 immutable Git sources, seven control/compiled copies, complete actor/declaration projections, compiler/executed binary and raw outcome streams. Read-only job_c9b6a36eb757 passed without rerunning tests. The exact receipt and script are retained; receipt SHA-256 c05f364b46a452cc0d578c391f000bf6e4fdfd08d2f64904c6ba0d074fe831f7. This review preserves the same portable fixture and language-mode limits.

## Byte-preserving retention correction

The first evidence-only staged whitespace check stopped before commit/push on original AccountManager whitespace, original Capture/Lifetime EOF bytes and recorded patch context. Its exact failure receipt is retained. Narrow per-file whitespace attributes permit retaining those immutable bytes; source, assertion bodies, compiler copies, runtime receipts and review hashes were not reformatted or replayed. This was an evidence-retention check, not a product or control failure.
