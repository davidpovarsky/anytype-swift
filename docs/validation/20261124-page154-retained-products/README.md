# Page154: exact four-directory fix and retained App/UI continuation

## Observed original failure

Actions run 45432237224 at a7ff33c7128ff706a0ed25bd4a777e7cc62269bb completed one
application build and one UI runner build, both actual build-for-testing exit 0.
No test method ran. The controller then failed with
page_ui_generated_inputs_changed_during_preservation.

All 19 original generated source entries retained their original bytes and modes.
Xcode had added exactly these four empty mode-0777 directories below
PinkhaStage1Acceptance/PinkhaPrebuiltUI.xcodeproj:

- project.xcworkspace
- project.xcworkspace/xcshareddata
- project.xcworkspace/xcshareddata/swiftpm
- project.xcworkspace/xcshareddata/swiftpm/configuration

The original UI post-build inventory and build receipt had not been written.
Their absence remains an explicit admission requirement. The failed workflow and
its incomplete receipts are preserved.

## Narrow correction and continuation

The ordinary build path now predeclares those four empty directories before
freezing generated input inventory. Its existing equality assertions remain in
place. The optional current-page154-retained route uses the existing inline Page
job; it adds no reusable workflow reference.

The retained path admits only the fixed original run, source, artifact, and
thirteen exact uploaded artifact members. It independently verifies the full
731,151,654-byte original ZIP digest and the exact member bytes, including the
two App/UI product archives. It compares all 12 compiled source trees, projected
source origins, and explicitly reviewed helper changes. Product or unrelated
helper changes fail closed.

The original App inventory has 5,006 entries. The UI archive contains 29 product
entries and 23 generated source entries (the unchanged 19 plus the exact four
empty directories). The UI inventory is explicitly labeled as reconstructed from
the original verified uploaded archive. It is not relabeled as the missing
original controller receipt.

Restoration uses new owned directories, verifies exact inventory/modes, original
source receipts, code carriers, signatures, and descriptors, and preserves the
originals. The 46 copied SwiftPM Git alternates are relocated only into the
corresponding copied object stores; all other dependency bytes and actual clean
checkout revisions must match. Native code remains the existing 154-input
producer artifact, checked separately by the unchanged Page controller.

The actual resumed journey still requires one necessary fresh preparation and
the one unresolved UI test on a new owned simulator. Its selectors, assertions,
native observation checks, cleanup, and acceptance rules are unchanged. No
controller or inventory check substitutes for an actual Apple test.

## Verification and accounting

admission-controls.json records eight positive/negative source controls: exact
19+4 admission, original source mutation rejection, unexpected directory/mode
rejection, compiled-source and unreviewed-helper rejection, exact directory
predeclaration, and existing-directory rejection.

The original artifact identity was independently verified on the actual Mac
before this change; the fixed member inventory is included in
page154-retained-inputs.json. Actual restoration qualification passed on the Mac in 83.58 seconds, with
5,006 App entries, 29 UI entries, and 55,819 package inventory entries. Signatures,
code carriers, descriptors, exact archive members, and actual dependencies all
passed. Only the 46 copied Git alternates were relocated; originals remained
unchanged. actual-mac-qualification.json preserves the result. This qualification
ran no build, test, or simulator operation and does not claim Page154 UI acceptance.

The App/UI products remain under:
/Users/m1/builds/_retained-anytype/45432237224-1/build/current-page154-45432237224-1

The original artifact is 14940337147,
SHA256 543a9b4bbed5d4a0a010bb1ad0be46abff17f5d400eeda1cfd6bae5be5d18ff8.
