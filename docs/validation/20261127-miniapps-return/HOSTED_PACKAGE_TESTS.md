# Original package regressions in the shared App test host

This change is preparation for the root-owned combined build. No App build,
UIKit execution, package test execution or product acceptance is established by
the source membership change or the Python controls.

## Source and project seam

The existing AnytypeTests target already links PinkhaAnyUI, PinkhaAnyHost,
PinkhaAnyEngine, PinkhaAnyIntegration, PinkhaKit, TorahInspectorCore/UI and shared
Hanlin products. It already compiles the original
Modules/PinkhaAnyNative/Tests/PinkhaAnyNativeTests/NativeDocumentPublicationTests.swift
through an explicit SOURCE_ROOT file reference.

Use the same seam for these original files, without copying or changing their
bodies:

- Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeTextRendererTests.swift
- Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeTorahRelatedIdentityTests.swift
- Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyLibrarySearchPublicationTests.swift

The only Xcode change is one PBXFileReference, PBXBuildFile, group reference and
AnytypeTests Sources-phase membership per file. Sources phase
03C5C53C22DFD90C00DD91DE belongs to target 03C5C53F22DFD90C00DD91DE.
No target, scheme, package pin, resource ownership or production-source membership
is changed.

The root must first integrate the corresponding owner source milestones. The
related-identity file was reviewed at 15b0740c70b32f607c81d60d0b2be6069463e337
(Git blob 5c2f413005d9e2252f97f6a6b3b46f5f7c81d14d); the library-search file
at 03dae6742dec6279b8329991d435a7562918a278
(Git blob 5d3add6d085c85e14dd0bd062db61beb64484c9f).
They are self-contained and do not use a package test Bundle.module resource.
The renderer file at 087b6894b9c78a73c106d6717214c48d21206633 is unchanged
(Git blob c8372f370ff3cba7bc6f9563c4e522f919081662) and has three methods.
The current frozen source manifest must bind every compiled file; these
inspection revisions do not replace that requirement. That same owner milestone
adds AnyTypeTests/Pinkha/AnyNativeEmptyParagraphDirectionTests.swift separately;
its four methods/six cases use existing synchronized AnytypeTests membership
and do not require another external file reference.

## Host and dependency implications

Keep the existing TEST_HOST=$(BUILT_PRODUCTS_DIR)/Anytype.app/Anytype,
BUNDLE_LOADER=$(TEST_HOST), App target dependency and shared Debug testability
settings. Original @testable imports remain unchanged. The three files compile
inside the actual AnytypeTests module and run in its existing App host.
This does not build or certify the standalone PinkhaAnyUITests package runner.

Adding these references before the single combined build avoids a separate
full App build. Native library binaries, SDK materialization and package
resolution remain the inputs of that same original combined build receipt.
Do not add a late source overlay to already accepted Products.

The library-search tests exercise the production presentation with typed
suspended reads and reject accidental journal mutations; they do not perform
HTTP/native search or certify a mounted screen. The related-identity tests
exercise the original presentation against their self-contained protocol
fixtures; they do not establish native synchronization or a UI journey.

## Producer and receipt binding

Add all three exact repository paths to the root admission's
selectedNativeTestSources before executing the d77bc5d2 shared producer.
Its existing native proof already binds each selected source to source-before
bytes and the actual AnytypeTests swiftc invocation and SwiftFileList.

The receipt consumer now permits these three exact paths and the previously
hosted NativeDocumentPublicationTests path, alongside AnyTypeTests/*.swift.
It still requires root-selected source equality, exact source bytes and the
actual AnytypeTests compiler invocation. Other package test paths are rejected.
No standalone package FileList or enumerated package-runner case may substitute.

The original source observations include project.pbxproj and these Swift files.
The combined App/UI product inventory and actual xctestrun must be retained.
Controller source is independent of the compiled App source; use the new exact
controller commit/manifest after review, preserving historical e2e7 receipts.

## Execution and original case accounting

Enumerate the newly built original App xctestrun before selecting these suites.
The expected executed test module is AnytypeTests:

- AnytypeTests/AnyNativeTextRendererTests
- AnytypeTests/AnyNativeTorahRelatedIdentityTests
- AnytypeTests/AnyLibrarySearchPublicationTests

Use the actual enumerated identifiers, including Swift Testing method signatures
and argument cases. The reviewed related-identity source has five methods and seven cases:
matching metadata 1, mismatched display 2, mismatched unlink 2, stale-source row 1,
current read-only metadata 1. The reviewed search source has two methods/cases.
The renderer has three methods/cases. Reconfirm all counts against the admitted
owner revision and actual enumeration.
Require every selected case to execute and pass, with zero failures or skips;
preserve original logs, xcresult, summary, test tree, source hashes and device
identity. Do not count declaration discovery or Python controls as execution.

The unchanged original standalone package path remains documented in
.github/workflows/pinkha-any-engine-port.yml. It is a separate historical route,
not the route claimed for this combined hosted acceptance.
