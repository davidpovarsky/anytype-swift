# CI43 Linux host controls: 74 actual passes

The same unchanged 74 Python host controls passed on Linux at **2026-11-20 14:25:31 UTC**, with **0 failures, 0 errors and 0 skips**. Both original POSIX process-group controls executed successfully. No Apple, XCTest, Native UI, embedded editor or live-write result is claimed.

## Exact execution and retained failures

- CI source: 48a64236b209b4121d93e2e688caa74a43280eed.
- Documentation checkout used for the run: fe580295ed3c323195cb1d4a6927e21ec5fad9e0.
- Application source: 0a3e80ce2b286ffe2caa7537bf12e3d1d423b25e.
- Runtime: Linux 6.18.57 x86_64/glibc 2.41, Python 3.12.14.
- Original Windows result remains **72 passed / 2 original POSIX skips** in the preceding CI43 report.
- Linux attempt 1 remains **73 passed / 1 error / 0 skips**. Its error was an omitted indirect dependency in the export, not a product or test change.
- Linux attempt 2 is **74 passed / 0 errors / 0 skips**, exit 0. The same 74 method identifiers and original unittest command were used.

The omitted dependency was the genuine Tools/PinkhaNativeDerived/build_native_ipa.py, read by the unchanged cancellation-wrapper test. The original test's fallback path caused the final missing-file message to name Tools/Hanlin/build_native_ipa.py; no case alias or replacement file was invented. The authentic Git blob cb509ecc637ffb669569bfafd7471ba924a5c851 was materialized at its actual tracked path. Its 20,302 canonical bytes have SHA256 c9e35a228779ae761d36cef204a32148ffdd3a338c9ede11dde6df4ebee21055.

All **26 final source inputs** were checked against their exact canonical Git blobs before execution and had identical hashes afterward. The original real Git HEAD, full directory-tree objects and complete index were retained; no Git shim, synthetic commit or remote source fallback was used. The complete 1,286,810-byte index is SHA256 379405d4be269ec6e1fbcb3cf30dd7380ab1f2a1a2cbfec61e0141870b049251. Unselected application blobs were not materialized: this is an exact bounded host-control closure, not a full application checkout or compilation.

## Durable evidence

- RESULT.json: compact source-bound results and both outcomes.
- CANONICAL_INPUTS.json: all 26 exact source paths, blob IDs, SHA256 and lengths.
- RAW_FILES.json: 140 logical original Linux files mapped to 46 lossless gzip objects inside LINUX_EVIDENCE.zip. Identical streams share an object without losing their original logical paths.
- LINUX_EVIDENCE.zip: the original immutable 494,486-byte bundle, SHA256 58107fd0d771a59b0dc0f61249554b4c903e5a8c6557a8033f7774fbb15ec8ba. It retains both complete per-case outputs, both actual runner scripts, command receipts, source inventories and transfer receipts.
- CANONICAL_SOURCE_EXPORT.zip: the original verified 893,317-byte export, SHA256 2906c17e029e4a2d7dedee5215e8b6e7649853d681007375d06ed8077d6c3e8c. It contains the original 25-file canonical export, real Git objects and full index; the authentic supplemental 26th blob is retained in the Linux evidence.
- WINDOWS_EXPORT_RECEIPTS.json: unmodified observed tool responses for the first rejected CRLF git-archive attempt and the successful canonical export.
- RETURN_TRANSFER_RECEIPT.json: one acknowledged Windows return chunk, three unknown completions and the explicit agent_offline responses. No unknown write was repeated and no service was restarted.
- MANIFEST.json: exact SHA256 and lengths of every published file except itself.

The first Windows export archive/diagnosis remain at the owned Windows build path and are not presented here as newly retrieved raw files: Sentinel went offline before final packaging. The inner Linux bundle README was written before that disconnection and describes the planned export/ packaging; this outer receipt and its MANIFEST define the actual delivered set. Its first-attempt source/transfer/runtime facts remain unchanged.

The initial single-use transfer returned HTTP403 without source content. The same owned canonical ZIP then arrived through 28 bounded MCP reads with individual and whole-file hash checks. The Linux result did not depend on the later failed return transfer.

## Publication boundary

This supplementary documentation is published through the GitHub connector on the existing authoring branch, with an expected-head lease at fe580295. No application, writer, test, CI profile, runtime, Heart/SDK pin or frozen Apple branch changes. Apple43 remains a separate actual source-bound gate. The 74 Linux controls establish host-controller behavior on Linux, including the real owned-process cancellation path; they do not transfer a platform-specific Apple result.
