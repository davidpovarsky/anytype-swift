# UI4 dedicated hierarchy drag handle — separate product candidate

## Observed failure and causal limit

The actual run45196775684/4 HierarchyDrag method failed after its unchanged1.1s press, velocity100 and0.6s destination hold. Before and after, the source and folder rows were unique, enabled and hittable; the source remained after the45s disappearance wait. The original product places its draggable String modifier on a label nested inside the row-opening Button with a contextMenu. The evidence does not establish a backend failure or prove which recognizer consumed that gesture.

This candidate separates the drag source from that Button. It is a product hypothesis pending a new App build and real mounted execution, not a retrospective explanation or PASS.

## Product change

The outer row is an HStack containing:
- The original opening Button with the original label, identifier and context-menu actions. Plain button styling prevents List's automatic row-wide Button activation from claiming the sibling handle.
- A44x44 Image handle with an explicit rectangular hit area, separate accessibility element/identifier, and Hebrew/English drag label and hint. It is shown only while model.canWrite.
- An accessibility container that retains its children separately, rather than combining or ignoring the handle.

The native payload is still exactly pinkha-any-node|<currentSpaceID>|<objectID>. The complete existing String drop validator and asynchronous model.move body remain byte-exact, now attached to the outer row. No service call is added to the source gesture or test. No repository/native/schema/transport dependency changes.

Apple's existing draggable modifier supplies native drag/drop gestures; this source does not implement a manual gesture or a direct mutation shortcut. References: https://developer.apple.com/documentation/swiftui/making-a-view-into-a-drag-source and https://developer.apple.com/documentation/swiftui/view-accessibility . These documents support API usage, not the inferred cause of the original failure.

## Affected existing real UI method

Only testHierarchyDragIntoFolderPersistsAfterColdReopen is adapted to select the handle by its exact object-derived identifier. It retains the source and destination row identities, same native gesture parameters,45s row disappearance, acknowledged-library-ready guard, exact body/block identity and final cold readback assertions.

The existing20s source-readiness allowance becomes one monotonic handle-admission deadline, including uniqueness, enabled/hittable checks, localized label and the existing private observation. The destination's original20s readiness wait remains. A missing/ambiguous/changed/late handle fails before the gesture. No coordinate fallback, retap, service fixture or timeout increase is introduced.

SourceDrag's actual PASS remains retained without replay; its method and shared helpers are unchanged. The original22 methods remain excluded. HierarchyMove's complete method and useful diagnostics are unchanged. Its original two60.04s/60.03s animation-idle waits and6min overall failure are preserved; no source-only success is claimed. The changed row composition is relevant to its later mounted evaluation, but does not prove that timeout is repaired.

## Separate App origin and proposed future scope

Parent5de44874e34e6647fe6f58f5cee5d915e797fc9a holds Scope A (safe Hanlin diagnostics/Files Image target) and original audit provenance. This separate product scope modifies AnyNativeLibraryView and the failed drag method. It MUST use a newly built current AnyNative App and newly built UI runner. The old immutable4b App and previously compiled E4 runner cannot establish this product source and are not admitted by this draft. Existing retained-product manifests/routes remain untouched.

Future failed-scope inventory, subject to root's frozen execution/profile review:
- HierarchyDragIntoFolderPersistsAfterColdReopen
- HierarchyMoveAndPropertyVisibilityRetainNativeBodyAndType
- HanlinSelectedContextAndSeparateCreateConsentSurviveColdReopen
- CanonicalArchiveFilesRoundtripPreservesMappingAndBodies

That inventory expressly excludes SourceDrag and all prior22. Actual App/UI builds, enumeration, UIKit/Swift compilation, host/product tests and CI dispatches are NOT_RUN. No synthetic UI test was created. Exact full-file inverses, source identities and unchanged native callback/body sections are recorded before execution.

## Source-only resource and ownership profile

This writer is separate so Scope A's physical files stay immutable during peer review. Root admitted >=1GiB free and <=10MiB aggregate transient source-only allocation for A+B+one B index.lock. This does not change any native/build/test resource gate. Both prior source-freeze capacity/transport refusals remain preserved in Scope A.
