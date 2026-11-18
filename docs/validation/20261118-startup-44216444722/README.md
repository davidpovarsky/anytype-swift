# Actual iPad startup and document route proof

Run [44216444722](https://github.com/davidpovarsky/anytype-swift/actions/runs/44216444722) completed successfully on 2026-11-18. Source is the focused startup branch at 997807b79c664568edf9f1973875f7e9148b77b6, with TorahInspectorKit c3fbb6c8173858b26fc5b4ce8496ee09fef2b9f9 and the verified r14 runtime from run 44203168617.

## Actual acceptance in this run

- Xcode 27 built the app and executed one native fixture preparation: 1 passed, 0 failed, 0 skipped.
- The actual XCTest UI method AnytypeComprehensiveAcceptanceUITests/testDocumentSourceSearchPresentation passed on iPad Pro 13-inch (M5), iOS Simulator 27.0, arm64: 1 passed, 0 failed, 0 skipped.
- Home was observed after 1.166 seconds of the test readiness wait. The exact Space/object editor marker in the final accessibility hierarchy matches the native fixture.
- Both original screenshot attachments were inspected. The source document and Document links sheet are visible, search is focused, and Sources/Topics/Words and Genesis 1:1 are visible. This focused method does not establish actual provider search-result correctness.
- PID 69621 and its process start identity remained unchanged across this ordinary UI method. Installed executable/carrier checks passed. This does not establish every relaunch or resource-byte equivalence.

The previous run failed in XCTest's 128-character direct identifier lookup after reaching Home. This run uses the full exact identifier predicate. The later integration source is not substituted for the actual tested branch.

## Source and artifact verification

The GitHub artifact ZIP digest was verified before extraction. Every declared candidate input identity was independently recomputed from the exact Git tree. These identities hash Git mode plus blob object ID, as specified by source_inputs(); they are not raw-file SHA256 values. Raw evidence byte hashes are separately recorded in manifest.json. Both screenshot attachments contain the same exported image bytes.

## Bounds

This clears the observed Home-to-document startup blocker for this tested candidate. Current integration, new Hanlin code, r15, quote/drop changes, iPhone, Hebrew, other UI suites, the full matrix and release acceptance remain unproven by this run.
