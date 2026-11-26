# Editor focus after collection layout

## Observed failure

App15 source 379ca3568f247d2fc218ed63df24796d461713c0 passed all 21 focus lifecycle methods / 32 parameter cases. Its original real-editor preparation still failed before the four UI journeys: the distinct empty row retained one owned request, delivered one scheduled callback, and recorded waitingPresentation once. At the failure observation the actual input was attached, visible, active, editable and in the key window; no native focus attempt had occurred.

Original proof is retained under /Users/m1/development/anytype-root-active-20261125/app15-editor-ipad-he-light-01. Lane result: bc05c9c4ff18b2a20d3c27ee73125a7068846a570235d8f9ce9b5aefb3f2006c. Native result: 2e58d0c4bd276a2709f59c5fcd12a0faeb3c7af9076973be1467be8a38c941ce. These failures are not relabelled.

## Change

Actual row and collection layout events queue the row's existing unattempted request. Final input visibility is checked at its queued delivery, after nested UIKit layout can complete. Ownership, lifetime, lock/editability, current window/scene and input geometry checks remain. Layout never invents a request, directly calls the native responder, or repeats a native refusal. No timer or self-scheduled retry loop is added.

An additional two-case actual collection regression changes ancestor presentation and requests normal UIKit collection layout, without directly calling row layout or the focus/presentation helper. It checks both acquisition by the current request and cancellation after a newer cursor owner. Removing this one 42-line addition restores the original 21-method source byte-for-byte to 74f09e8baa94bc8ab33668ceb72b9f59790d5a1b5e5a6d624b286844651190b3.

Independent native_d_sdk source review found no blocking issue in the three exact changed files. Review is not runtime acceptance.

## Required next gate

Build the consolidated reviewed source once; run the full affected focus suite (22 methods / 34 parameter cases), then the unchanged original real-editor preparation and four UI journeys. App15's previous focus PASS does not qualify this new implementation. No Release, signing, device or TestFlight claim is made here.
