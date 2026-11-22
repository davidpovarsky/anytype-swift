# Focused native-history component qualification

**PASS: 16 distinct methods, 16 passes, zero failures or skips.** Sentinel job `job_82914797a4fc` completed with exit code 0 on Swift 6.3.3 for `x86_64-unknown-windows-msvc`. The original log records nine `NativeHistoryReaderTests` XCTest methods and seven `AnyNativeHistoryPresentationTests` Swift Testing methods, each with exactly one start and one successful terminal. The checks did not select any previously passed project suite.

The reader controls cover native order and opaque values, reader authority, denial before/after transport, document generation changes, cursor scope binding, duplicate/stalled pagination, unavailable/truncated/oversized states, bounds, and revocation during a transport that ignores cancellation. Publication controls cover superseded preview results, page failure, refresh, owner retirement, typed version failures, the 20-page limit, and a listed truncated version that must not trigger a full read.

## Original evidence and reproducibility

`portable-originals/attempt-4/swift-test.log` is the original 27,077-byte stream, SHA-256 `68aa337fe3ffcf434a7847e0577d90d14252a1939c910b6d27c0376fe8b27055`. Its original 3,352-byte receipt is SHA-256 `dbf2f9282e54e5bcabb6e62b6229ea7aada07436d93a4c373b34ab9aaec9c7e7`. The 36,339-byte source snapshot is SHA-256 `783327b13240972ce59df81d53899ce06825a78569e7d9e3fafbde22fe52f711`. All decoded transfer sizes and hashes were checked before admission. An initial overlarge prior-attempt transfer was rejected because SentinelX inserted a truncation marker; only complete bounded transfers were retained.

The package uses 233 exact Git-tracked baseline files from app `bf5b2fb4e0b446f8e13c04c8f9d8c16a44b41345`, plus the six owned history files, with no source changes during the successful attempt. The package wiring selects the actual Host, Engine, Integration, and Kit modules. Dependencies were clean and pinned to swift-crypto `e8d6eba1fef23ae5b359c46b03f7d94be2f41fed`, swift-asn1 `917b472dbe53ba699cbb0495f9a95a084bc6364d`, and TorahInspectorKit `511454e49450cb2581ddf77f644146ff3e30dbef`. These are actual dependency sources, not test stubs. The original package manifest, resolved pins, and before/after source observations are retained.

Three earlier attempts timed out while building dependencies or source, before any test method executed. Their original receipts and raw logs remain under `portable-originals/attempt-1` through `attempt-3`; they have not been relabeled as passes. The final attempt reused its already staged exact sources and completed the compiler work. Only its observed method terminals contribute to the 16-pass count.

Run `python validation/qualify_portable_history.py` from the slice directory to recheck all retained original-file hashes, six owned source hashes, native test names and terminals, dependency identity, and receipt consistency. The checker reads evidence only; it does not rerun Swift or native tests. Its result is preserved as `PORTABLE_HISTORY_AUDIT.json`.

## Limits retained

These are portable component controls using scripted HTTP and authority observations. They do not execute the Any history HTTP server or a native ACL transition. Conditional UIKit and SwiftUI view bodies are excluded on Windows. Apple product typechecking, mounted history acceptance, and physical-device checks remain **NOT_RUN**. The separate new mounted XCTest source has only a grammar parse, also retained separately. APP-01 remains open, with no claim of whole-app parity, network transport, mixed-version behavior, migration, or semantic-anchor completion.
