# Any compiled UI product admission repair

## Status

Review-ready controller/workflow change based on commit `b2fc3804426067dd1ec8318d6ea92a4bcb8e9545`. No new Apple build or UI execution is claimed. Copy only the three paths in `ANY_XCTESTRUN_FIX_FILES.json`; this scratch directory also contains unchanged dependency files used for review.

## Original evidence and diagnosis

Run `45028482383` built the actual app and UI runner under Xcode 27.0 (27A266a). Its original `native-ui-build.log` ends with successful build-for-testing. The log identifies the app target `PinkhaAnyNativeApp`, test target `PinkhaAnyNativeUITests`, and generated runner identifier `io.pinkha.anynative.uitests.xctrunner`. The original app ownership receipt passed. Admission then failed with `compiled_ui_target_identity`, before any native UI acceptance stage.

The committed `PinkhaAnyNativeApp.xcscheme` has one Testables entry targeting `PinkhaAnyNativeUITests` (blueprint A50000000000000000000002) and no TestPlans. Its SHA-256 is `f208c605b78e849e18defc7c759f3588dc9ab9b3f3bdd7502257c605da9db308`. The Xcode project maps this target to `io.pinkha.anynative.uitests`, product `PinkhaAnyNativeUITests.xctest`, and `TEST_TARGET_NAME = PinkhaAnyNativeApp`.

Apple documents that schemes without Test Plans use xctestrun format 1; Test Plans use format 2. The old gate assumed format 2's nested TestConfigurations regardless of declared version. This establishes a source/documentation-supported schema mismatch. The exact original plist was not retained, so its actual keys cannot be asserted retrospectively.

Primary source: https://developer.apple.com/documentation/xcode-release-notes/xcode-11-release-notes.md — Testing, item 46346053. Apple's xcodebuild.xctestrun manual also describes version dispatch and the TestBundlePath/TestHostPath/UITargetAppPath placeholders; its archived manual text is available at https://keith.github.io/xcode-man-pages/xcodebuild.xctestrun.5.html.

## Change

- Dispatch strictly on xctestrun version 1 or 2; absent metadata denotes documented format 1. Reject unknown or incorrectly typed versions and mixed schemas.
- Require exactly one enabled UI target. In format 1, the exact root dictionary key is the target identity; a present BlueprintName must agree. Format 2 still requires exactly one configuration, one target and exact BlueprintName.
- Bind configured app, runner and test bundle paths to the exact local products, with documented placeholder expansion only. Verify all three bundle/executable identities. Reject destination-artifact substitution, skipped or explicitly non-UI targets, duplicate plist keys, external paths, symlink manifests and multiple matching manifests.
- Retain existing native-artifact source binding, complete product inventories, exact prior-method source protection, same-products freeze and actual named-test/postflight checks. Add the unchanged scheme to frozen source inputs.
- Before admission, preserve original matching xctestrun files and a SHA-256-bound tar containing only those manifests and the two compiled app bundles. The existing always-upload evidence step includes these files even if admission fails. Preservation is explicitly not an admission or execution success.
- Execute only the five new controller controls for the remaining-native-ui CI scope.

## Validation performed

Five new synthetic controller tests passed in 0.033 seconds. These exercise both formats (including implicit version 1), ambiguous/disabled/mixed/unknown configurations, path and bundle substitution, duplicate keys/symlink/multiple manifests, and retained native source binding.

The preservation block was also executed against a temporary synthetic product tree. It retained a deliberately invalid original manifest byte-for-byte before admission, produced a matching archive digest, included only intended products/manifests, and recorded an external symlink without following it. Workflow YAML and all modified Python parsed successfully.

No earlier native or UI test suite was rerun. No actual Apple result is inferred from these synthetic controls.

## Reuse boundary and next evidence

The failed run's original artifacts contain logs, receipts and build xcresult, but no compiled products or xctestrun. These cannot supply executable bytes for test-without-building. Its successful build remains evidence of compilation, not a reusable binary archive. The next run must build once; previously proven native runtime and UIKit evidence can still be reused under their existing exact source bindings. New preservation will retain the resulting build for independent inspection and possible separately qualified future reuse.

The next successful capture must expose the observed formatVersion and bind its original xctestrun SHA-256, three local paths, all product bytes and the original native runtime receipt. UI acceptance remains blocked until the actual named XCTest journeys and postflight checks pass.

## Original UIKit14 reuse review

`reuse_uikit_execution.py` protects the actual UI, Engine and Host source trees, the Kit Editor and RTL directories, the exact three test files, and selected package manifests. The Any repair's controller, new controller tests and workflow are outside that source map. None changes a reviewed before/after Git blob or the fourteen-method inventory. Therefore `uikit14-unexecuted-source-changes-20261122.json` needs no amendment for this patch.

The root's separate addition in `Modules/PinkhaKit/Sources/PinkhaKit/Torah/T5NativeRelatedLookupCapability.swift` is also outside this component source map. Its diff adds lazy constant string identities and one exact comparison under the unchanged enabledByBuild guard. The old UIKit result does not provide native or UI acceptance for this new identity. `UIKIT_REUSE_IMPACT.json` records the precise changed-path intersection and original/current capability hashes. This is not a blanket review of future changes elsewhere in the protected source closure.
