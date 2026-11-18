# Actual PinkhaKit package tests
Run https://github.com/davidpovarsky/anytype-swift/actions/runs/44241658214 passed on the exact application source in verification.json.

The original Swift Testing terminal line reports 214 tests in 28 suites passing. All 28 suite completion lines are retained verbatim in selected-log-lines.txt, alongside the terminal line and observed tool metadata. The separate XCTest wrapper reports zero tests; it is not the Swift Testing result. The full 177,280-byte original job log remains on GitHub and on the connected host, identified by SHA-256.

The tested Modules/PinkhaKit Git tree is byte-identical to the tree at the later integrated commit recorded in verification.json. No package source changed for this proof. This is actual macOS package execution with the observed Xcode26.4.1 SDK root, not iOS27 application/UI, physical-device, Native sync or release acceptance. No new build or test was inferred from the source-tree equality.
