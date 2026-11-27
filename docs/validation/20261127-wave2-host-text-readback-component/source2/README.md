# Host2 source2: exact private SwiftPM alias and fresh namespace

This is a source-only successor to the published `d9d0c3e6cad2868bd18a5a2826ef7ea401716f5e` preparation. Its 35 inputs occupy 448,981 bytes. Actual source2 execution has not occurred and requires a separately coordinated slot.

## Retained actual attempt1

The original `swift test` CLI started once. The controller failed while its resource sampler encountered the actual private alias `xdg-config/swiftpm/cache` pointing to the same owned root's `xdg-cache/org.swift.swiftpm`. The controller's original receipt `2287f915…` remains **FAIL**, with `safeToReleaseRuntimeSlot=false`; both compiler logs are empty, no XCTest case or HTTP fixture ran, and no compiler execution is qualified. Empty logs do not establish that no compiler child or compiler work began.

The original owned-process helper terminated its newly owned group and recorded positive absence. Root's separate read-only audit `ac83d091…` subsequently verified unchanged source/dependency custody, the single exact alias, zero current audit children and resource retention, then released the slot. That retention result does not change the original failure or provide product acceptance. All supplied original receipts, logs, start/upload/preflight records and the separate release record are retained under `actual-attempt1/`.

## Minimal correction

Only `allocated_bytes` changes behavior: it admits that exact alias path only when both its raw absolute target and resolved target equal the one expected private path. Every other alias retains the original policy. `os.walk(followlinks=False)`, `lstat` allocation counting, the build-tree link rule, resource floors and caps remain unchanged.

The next attempt uses the absent owned namespace `/mnt/development/projects/evidence/pinkha-wave2-host-text-readback-source2-20261127`. The only other input changes are the controller's root literal, its derived Package hash, and the Package's 34 owned-root path literals. Complete inverses restore `cb854…` and `fdfcac…`. All 27 production files, the full Host test file, Python fixture, process helper, Crypto closure, compiler-witness validator and method selections remain exact. No attempt1 directory is reused or overwritten.

Root review `da00695b…` and peer review `c4469c3d…` accept the corrected source tuple. One local isolated guard control accepted the exact alias and rejected a foreign target and an unlisted alias. Its first harness setup stop is retained separately. These controls did not import/run the controller or execute Swift, XCTest, HTTP, Native or Apple work.

Future scope remains two selected XCTest methods/cases with four looped controlled HTTP flows. Original Host/uploader/T5 tests are not replayed. The exact input packet is `3a23e8da…`; controller `fc6dba3c…`; Package `f66f3701…`; source inverse `7abd783b…`. The source2 materializer and compressed envelope will be pinned separately after this source commit exists.
