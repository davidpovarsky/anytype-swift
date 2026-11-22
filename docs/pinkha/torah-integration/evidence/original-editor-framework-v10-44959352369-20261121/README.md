# Original v10 Native result: component passes, public graph timeout

This is evidence for the unchanged historical original-framework source at `c89d6726c3b2ad6e418296c5ed0f7d705fb88433`, not acceptance of the later editable-Host draft.

Run: https://github.com/davidpovarsky/anytype-swift/actions/runs/44959352369 (attempt 1; job 137014499364; completed failure at 2026-11-21 23:45:13 UTC).

The original mandatory gate executed all 193 exact expected cases, with identical expected/discovered/started/passed sets and zero duplicates, skips, errors or failures. The actual original framework build returned 0 after 1159.257231 seconds. The seven exact constrained generated-package seal transformations passed, followed by all fifteen actual `codesign --verify --strict` commands returning 0. Source observations before and after execution are byte-identical. These facts are supported by the original receipts in the attached ZIP and the bounded review manifest.

The standalone original-target public symbol extraction then reached its unchanged 120-second deadline (120.159671 seconds observed, return -15). Both captured streams were empty and no symbol graph file was emitted. The reviewed producer Swift 5/import/Clang context was present, so the prior invocation-context hypothesis did not resolve the native stall. The full public-surface verifier, external consumer build, external resource runtime and editable Native UI did not run. The qualified distribution was not created or uploaded. This failed run is retained unchanged.

The original artifact is 14730840277, 11,014,466 bytes, SHA-256 4456a2ebf940b8730525cfee46e703c05aa9409011d997204150d64af7c6232a. Its nested evidence ZIP SHA-256 is 333ec9892721ce583f39cd14e5d850e7f8d40e38fca635420c41e91d8538a625. All 528 nested members passed CRC validation. The original build-log digest is 82b4195a2fb965363f6c27d7c69d987fb0286396dbb03f3a94c4d81c2c0ac163.

The selected-receipts ZIP preserves raw original receipt bytes and is source-bound in COLLECTION.json. The full original artifact remains available at the run and in the owner's verified local cache. It does not contain the framework executable/distribution; receipts alone cannot establish transferable binary equality or permit a receipt-only continuation. A new editable-source build is independently required by the new source tree. No existing passing tests were repeated for this evidence commit.
