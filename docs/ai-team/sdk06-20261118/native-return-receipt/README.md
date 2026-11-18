# Native return receipt — source handoff

Status: source implemented; Swift component execution and native UIKit acceptance are **NOT_RUN** for this change. The 31 passing Python controls validate the runner and synthetic result gates only.

Producer parent: `f048a33718506763b8097255a98ef742e445cfd3`, which separately fixes the observed SDK consumer build error. The navigation source was prepared against `d79264e007085c8981522e8d4fd42b28cde9334d`. Canonical Hanlin: `116cc6be0654a5d11bc56ba00e0310031107ee36`. This change neither edits Hanlin nor changes its dependency pins.

## Observed missing path and canonical contract

The existing native `targetDidMount` bridge had no actual presentation callback. `open` could enqueue a route while Chat still covered the document, which is insufficient evidence that the document or requested block is visible. Canonical `HanlinHostDispatcher.open` checks session currency both before and after awaiting the host. Keeping that session alive after Chat closes would weaken the existing contract.

The native **Return to document** toolbar action now completes a queued `host.open` while the original presentation is current, consumes a single native handoff, and then uses the existing Close path. Close synchronously revokes the SDK presentation, cancels work, clears transient credentials/messages and unregisters the presentation. The later UIKit dismissal completion attempts a separate, metadata-only native receipt. It is never delivered as an SDK response to the closed session.

The native navigation scope grants no document-read or document-write API, page creation, new Chat presentation, or way to rearm the execution fence. It may reveal the requested block through the existing editor's `revealBlock` method after validating the original native owner; the final receipt still requires the actual visible cell. Ordinary Close remains an ordinary Close and does not mint a handoff.

## Receipt authority

`PinkhaHanlinNavigationLedger` binds the original context, request UUID and exact UTF-8 object/block identifiers. A request can mint only one handoff. The handoff consumes its callback before invoking native validation and caches the terminal result; repeated or reentrant calls cannot publish a second mount. A ten-second monotonic deadline and cancellation task reject missing or late dismissal completions and release retained callbacks.

The deadline is checked both before and after native validation. Independent source review identified that layout/reveal can run synchronously across the deadline, preventing the expiry task from running in the meantime. The post-validation check closes that path. A private implementation clock input defaults to `ContinuousClock.now`; the component test advances it inside the callback without sleeps. The real NativeAccess caller does not override the clock.

`PinkhaHanlinNativeAccess` independently checks the original account, active Space, authorized membership, application state, foreground scene, original editor/document/selection objects, source revision and permissions. A separate one-way navigation fence records account, Space, member, source, selection and scene changes, including scene deactivation. Returning to the previous values cannot rearm it. Chat's own Close revokes the execution fence but does not manufacture a navigation-scope change.

An editor token identifies the exact Chat presentation. Starting another Chat replaces the token. Removing the editor from its parent, rebinding its model, or changing its route owner clears it. No blanket `viewDidDisappear` hook is used, because covering the editor with Chat is the ordinary presentation being tested.

The dismissal completion alone is not accepted. Before recording metadata, the code requires the same actual mounted editor, correct scene and document, visible navigation/tab ownership, and no covering presented controller. A requested block additionally requires live graph reachability, the exact data-source item, visible index path, live cell in the same scene, and visible intersecting bounds. Ownership is checked before and after layout/reveal. A cancelled or stale handoff remains unsuccessful; it does not reopen or navigate to a fallback target.

## Required component execution

Six methods were added to the already selected `HanlinHostAdapterTests` suite:

| Method | Contract exercised |
| --- | --- |
| `nativeReturnReceiptCompletesOnceWithoutRearmingExecution` | One metadata receipt, queue before mount, execution stays revoked |
| `nativeReturnHandoffCannotBeMintedTwiceOrForAnAliasedTarget` | Duplicate identity and UTF-8 alias conflicts |
| `nativeReturnCannotAcknowledgeQueuedOrDifferentMountedTargets` | Queued, foreign context, object and block cannot become a receipt |
| `cancelledOrExpiredNativeReturnNeverRunsMountValidation` | Prior cancellation/expiry prevent callback execution; crossing the deadline inside validation cannot publish a receipt |
| `nativeReturnScopeLossPreservesQueuedReceiptWithoutRetry` | Failed native owner check stays failed and preserves queue metadata |
| `reentrantNativeReturnCancellationCannotPublishMountedReceipt` | Cancellation during the callback cannot be overwritten by late success |

The SDK profile requires all six names explicitly, in addition to reading and hashing every selected tracked suite. Its exact current source inventory is 28 adapter + 12 write + 17 read/write + 6 consumer methods = **63 methods**. The real xcresult gate requires each source method to appear and pass, with no failed/skipped results. Registration or a large aggregate count cannot substitute for a missing method. The separate editor profile is unchanged by this patch.

`controls-linux.log` and `controls-linux.json` preserve the actual 31-control Python run. The two new controls remove each required declaration while retaining the suite count and remove each actual case while retaining a passing aggregate count; both must fail. These controls do not execute Swift or prove native account/UI behavior.

## Native acceptance contract remains open

The existing 21-check native driver, XCTest and root result validator remain unchanged in this handoff. A proposed separate 22nd check, to be coordinated after source review, will use the real **Return to document** button (`pinkha.hanlin.return-to-source`) in the same disposable account fixture, observe the exact original editor after dismissal, and require the native receipt's original request/context/target plus permanent rejection of the closed host. It must never call `acknowledgeMounted` directly from a test or inject a fabricated presentation result.

The existing 21 checks still do not prove an old Allow callback being executed after navigation; they prove prompt dismissal and denial of the old host. The new native return source does not widen those claims. No provider/model call is needed or authorized by this acceptance path.

## Local resource decision

At the recorded Windows preflight, only 477,646,848 bytes of RAM and 6,835,511,296 bytes of disk were free. No compiler was started for this change. The Python controls ran separately on Linux. `resource-preflight.json` preserves that observation; it is not a claim about current host capacity. Actual Swift type checking, component execution and UIKit mount behavior remain Apple gates.
