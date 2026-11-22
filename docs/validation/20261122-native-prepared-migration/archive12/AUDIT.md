# Twelve focused Heart archive inspection controls

The exact two new parent-owned Swift files compiled and executed on Swift 6.3.3 for `x86_64-unknown-windows-msvc`. Sentinel job `job_c10bb1a728d7` produced exactly **12 named XCTest starts and 12 passing terminals, zero failures and zero skips**. The raw log is 7845 bytes, SHA-256 `0975ec7ed4a5edbc535f853d2f1ee3ada9b48ee32a342bd9fd40a2b82e21a967`; the original receipt is 5938 bytes, SHA-256 `f34f51fb66a4ee2e186c43ebf047909fb0940a4e6265d4120ea86714cd0691b0`.

The selected suite is `HeartSpaceArchiveInspectionTests`. It exercises byte preservation, exact large integers, duplicate-key rejection, portable path safety, required AnyBlock versions and native identities, flat preorder hierarchy, property legends, file manifests including remote-only recovery boundaries, deterministic source binding, opaque metadata reporting, and refusal to treat retained sidecars as full snapshot proof. `permitsDestinationWrites` remains unconditionally false. This is inspection/preflight foundation, not a complete importer.

The source identities are preserved in `AUDIT.json`. The exact production source is SHA-256 `6a6535670cc9128704f6aabab1c5afd694ac695d4310f59c5e9b5b3acb15292e`; its test source is `c8dd4dbf6fe3eefc1ed1fadb7a56de1829f661c34ad021780e7e90cbb0134638`. Both were unchanged after execution. All 233 original shared tracked files, six history files, two prepared-client files, and 41 copied Integration baseline files remained unchanged. Only the isolated harness rewired package dependency paths; no dependency source was stubbed.

The stage reused the now-idle compiler cache with `--disable-build-manifest-caching`. It did not rerun the prior history16 or client18 suites. Exact clean dependency pins were TorahInspectorKit `511454e49450cb2581ddf77f644146ff3e30dbef`, swift-crypto 3.12.3 `e8d6eba1fef23ae5b359c46b03f7d94be2f41fed`, and swift-asn1 1.7.4 `917b472dbe53ba699cbb0495f9a95a084bc6364d`.

`original/` holds the six original log, receipt, package/pins, and source-map files. `ORIGINALS_MANIFEST.json` binds their exact lengths and SHA-256. `qualify_archive.py --source-root <migration-work-or-repository>` verifies those originals, expected new source hashes, exact named terminal set, receipt, dependency pins, and no-write boundary without executing tests.

Native archive export/import execution, native HTTP, Apple execution, and physical-device acceptance were not run in this scope. Whole-Space migration remains **NOT_PROVEN**.
