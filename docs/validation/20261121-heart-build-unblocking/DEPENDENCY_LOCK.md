# Original generated dependency lock, independently retained

Original failed Release build44948101231 and the later resolve-only probe44952889349 generated the SAME exact12595-byte App Package.resolved, SHA256e40f48f7844bdd7c1d2423532934a4016e47dc459d1ba4dcf70eee263fd08df8. All44 prior pin records are unchanged; no dependency was upgraded or removed.

The two added identities are:
- swift-markdown: https://github.com/swiftlang/swift-markdown.git, revision25cb61d3482054b09ae76ca4f281b1bfe7fe5a43.
- swift-cmark: https://github.com/swiftlang/swift-cmark.git, revision08ddb528923cc1a6527e02b7a1aee9e516ca749a, version0.9.0. The build log displays this package's product name as cmark-gfm.

The exact generated originHash is c59182ce32cf2c86a024e31640ca458d5a95aab9f19942b9db9513122cdc00e8. It was retained from Xcode's original artifact, not recomputed or invented.

Probe44952889349 correctly remains FAIL: xcodebuild returned74 because that resolve-only job did not install Lib.xcframework; the initial controller also expected the product label cmark-gfm instead of the actual identity swift-cmark. Despite that stop, it retained exact original and generated lock files. Their comparison and the earlier successful App compilation independently establish the lock bytes. No probe success or test execution is claimed.

Original probe artifact14726133625:8962bytes, ZIP SHA25617efc31e8074f20083f392caf40c9b138e556cfb8c2b5a0ce22633bb8faa0d9c. Its result.json, resolve.log and both locks were inspected. The corrected resolver uses the true package identity and the explicitly supplied verified runtime before any future resolution. The actual T5 route separately resolves the retained lock after installing that same runtime and refuses changes.

No repeat probe is needed just to regenerate these already verified bytes. The next required App build supplies the actual dependency/build proof.
