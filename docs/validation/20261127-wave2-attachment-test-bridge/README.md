# Host the two existing attachment test sources in AnytypeTests

Status: source preparation; **NOT_COMPILED / NOT_RUN**. This tranche changes exactly two source files over `2f9ac20a910d9922e13f8e5d410757604437fcc5`: the existing App project and the original receipt-admission allowlist. It creates no target, package, test, controller, selector profile, or product admission.

## Why the bridge is required

The published attachment suites already live in the existing SwiftPM test directory. `Modules/PinkhaAnyUI/Package.swift` uses normal source discovery, so it needs no modification. The hosted `AnytypeTests` App target, however, includes seven package test files through explicit direct-source references. Neither new attachment test was among those references or the corresponding original-source allowlist.

The exact project preimage `39b5ebb5…` and receipt module preimage `d63b8a04…` are byte-identical at own parent `2f9ac20a…` and primary current integration `919626d8a5a2701c2dfb56277a657fa593700b98`. This correction therefore uses a direct child of the own source parent. It does not import unrelated changes from the current integration.

## Exact changes

For each of the following existing sources, `Anytype.xcodeproj/project.pbxproj` gains one file reference with `sourceTree = SOURCE_ROOT`, one build-file reference, one membership in the existing root group, and one membership in the existing `AnytypeTests` source phase `03C5C53C22DFD90C00DD91DE`:

| Existing original source | Source SHA256 | Original target | Hosted target | Pending methods / cases |
|---|---|---|---|---:|
| `Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeAttachmentIntentStoreTests.swift` | `c0b7afacfaf2803cea214281e104b9a17a790dd2b1523e8f2e675510c6cef809` | `PinkhaAnyUITests` | `AnytypeTests` | 3 / 4 |
| `Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeAttachmentMetadataTests.swift` | `b9d0f1b8c72e503d4e4952b33f519fc93680d54a8384e828f001d498ddd71a91` | `PinkhaAnyUITests` | `AnytypeTests` | 3 / 13 |

The four new PBX object IDs are unique. All seven existing package bridges remain. The original native target, dependencies, frameworks, synchronized groups, App source phase and build settings are unchanged. The already-linked package products cover these sources' imports; the metadata source retains its original `canImport(UIKit) && canImport(HanlinMiniAppsBridge)` condition and still requires actual compiled enumeration.

`Tools/MiniApps/receipt_admission.py` adds only those two exact original paths to `HOSTED_PACKAGE_TEST_SOURCES`, changing that finite set from seven to nine. All 17 function definitions and the rest of the complete module are byte-identical. The full inverse restores both original source files. Adding an allowed origin does not select or execute a suite and does not authorize a different source or product.

## Exact future build handoff

The original producer is unchanged (`wave3_shared_build.py` SHA `47c66dde…`). Its actual helper is `w3_compiler_lists`, correcting one locator label in the retained Editor intake; the original intake and explicit correction both remain preserved.

Wave3 owns the next exact combined source, actual producer controls and resource slot. It must:

1. Bind the new project bytes and receipt-admission module hash in a separately reviewed source/control closure.
2. Retain the exact existing `selectedNativeTestSources` set and add these two original paths with hashes from that same combined source. The actual `nativeCompilationProof.requiredSources` and consumed compiler FileLists must include both.
3. Qualify the actual successful compiler invocation and actual enumeration of both original suites, then use the original result validators for the intended 3/4 and 3/13 cases.

This packet proves a source-input delta of **two**. The current live 57-row selected inventory was reported but not independently resolved in this bounded task, so no new total of 59 is certified here. `qualifiedNextNativeCount` remains null. Stage1 UI inputs are unchanged. The original Core22 lanes do not automatically execute these two suites, and this change does not add a selection route for them.

The actual Apple compiler, installed modules, enumeration, test outcomes and UI acceptance remain pending. No Oracle, Mac, Native, account, simulator, compiler or existing-suite replay is performed by this source tranche.
