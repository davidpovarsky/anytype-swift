# Original editor framework — attempt 1 failure

Run [44781744925](https://github.com/davidpovarsky/anytype-swift/actions/runs/44781744925), attempt 1, used immutable source `dc3ac07cec63692c8b84877a56e3e3fd60a4c667`. The job completed with failure at **2026-11-20 17:25:33 UTC**. The driver failed while waiting for the owned iPad simulator to boot, before the framework build command.

The actual `simctl boot` command returned 0. The next `simctl bootstatus … -b` command exceeded its unchanged 180-second bound, was terminated and reaped with return code -15, and produced empty stdout and stderr. The original preflight created two owned simulators; it did not boot multiple devices. Its pre-create inventory recorded 40 shutdown devices and no active device. Cleanup subsequently deleted both owned simulators successfully. These observations do not establish the underlying host-load or CoreSimulator cause.

## Executed scope and exclusions

The actual macOS source/authority controls passed **44/44**. The before/after source receipts are byte-identical and bind 22 execution inputs and the original 2,237 Swift source paths. Swift 6.4 and simulator SDK 27.0 identity were observed, but only the compiler version command ran. **Framework compilation, exported-symbol validation, external-consumer compilation, resource execution, and editor UI tests did not run.** No distribution artifact was uploaded. This is zero verified Native/editor execution, not a compiler failure or an import/link failure.

The driver started at 17:17:52.302265 and recorded failure at 17:24:21.427912. The enclosing execution step ended at 17:24:59; the job ended at 17:25:33. These distinct timestamps are retained rather than substituting observation time for execution time.

## Raw evidence

The original 70,669-byte outer artifact is retained unchanged with its API digest. Both its one ZIP member and all 28 members of the nested evidence ZIP pass CRC verification. Every nested member is also preserved losslessly as a deterministic gzip payload. The decoded job log and Root-fetched terminal run/job/artifact API receipts are preserved separately. Temporary signed download URLs are not published. `RAW_INDEX.json` binds raw bytes, gzip bytes and Git blobs; `PACKET_INDEX.json` binds the complete publication.

## Unchanged retry admission

The frozen guard accepts a positive run attempt, including attempt 2, while still requiring the exact repository, push event, workflow path, branch, immutable head, and matching fresh preflight. Work-directory and artifact names include both run ID and attempt. The exact three relevant frozen source files are included and matched to the actual before/after source receipt. No source, timeout, selection, or oracle was changed for this evidence packet, and this packet does not trigger a retry.

Original run 44750790626 booted the same iPad device type and iOS 27 runtime in **80.415913 seconds**. Its original command receipts and boot log are retained as comparison evidence. That successful earlier operation supports testing the unchanged route again; it does not prove why attempt 1 exceeded its bound. Root owns any one-off unchanged-source attempt 2. Attempt 1 remains a failure irrespective of later results.

Run `python3 VERIFY_PACKET.py` from this directory to verify the packet, original ZIPs, all compressed raw bytes, source identity and explicit non-execution gates. This verification does not run Swift, Simulator or CI.
