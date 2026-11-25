# MiniApps operation ownership — shared lifetime and Heart integration

The real Mac Swift 6 run passed all four new ownership controls with zero failures or skips.
This is focused native component qualification; the full Heart/Any app integration and MiniApps UI methods remain required.

## Product change

PinkhaMiniAppsLifetime is one engine-independent owner in PinkhaHanlinCore.
It rejects work submitted after revocation, invalidates already captured leases, and waits for every issued native operation to return.
It deliberately does not cancel a native RPC whose commit outcome is unknown.
Each transition receives a separate UUID hold; finishing an authentication change cannot release the engine switch's hold.
Resumption never makes a prior callback lease valid again.

The Heart coordinator tracks its preparation and result application tasks, the actual account/editor registration, and its owned presentations.
Before authority changes it revokes admission, resolves its own pending confirmation as cancellation, dismisses its own UI, and drains native work.
Capture validates the same lease before native flush and after asynchronous boundaries.
The result applier validates before native writes, after authoritative readback, and before persisting completion and acknowledging the bridge result.
Interrupted operations retain the original replay journal and pending result; no synthetic ACK is issued.

A returned edit that changes the operation the user originally chose requires the same shared UIKit confirmation used by Any.
Rejecting the change or changing account/engine leaves the original result pending.
Native document permission/account/space guards and receipt-before-ACK remain intact.

All eight mutating authentication entry points acquire a MiniApps hold before the native auth call.
Their serialized completion schedules release of only that exact hold, including failure recovery.

## Executed controls

- An issued operation finishes before drain returns; it is not cancelled, and its revoked late acknowledgement is rejected.
- Authentication cannot release an independent engine-switch hold; duplicate or unknown releases do not reopen admission.
- Work revoked before it starts never issues a native write.
- Resuming the current account cannot authorize an old presentation callback.

The original new lifetime source and original four test bodies were compiled unchanged in the focused package.
The fixture's paused operation represents an in-flight asynchronous call for this ownership unit test; it is not claimed as a real engine mutation.
The exact source archive is retained in /mnt/development/projects/evidence/miniapps-lifetime-20261125/source.tar.gz.
SHA256: 8efbd63629f821fc028cf9fda9188ccdcc475842105dc9e036820369a1f40f38.
Mac source/build: /Users/m1/builds/pinkha-miniapps-lifetime-20261125.
Original command/log/result files are adjacent and digest verified.

The shared UIKit confirmation was imported unchanged from e0ca39fb5840a944a625ae334d2532d99ac83e33.
Its actual iOS 27 Swift 6 typecheck passed in the D lane; the combined app and real interaction controls remain pending.
No prior acceptance method or result has been replaced.
