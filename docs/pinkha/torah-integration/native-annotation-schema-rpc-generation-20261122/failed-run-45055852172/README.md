# Original schema RPC generation: retained baseline and Swift import failure

Run [45055852172](https://github.com/davidpovarsky/anytype-swift/actions/runs/45055852172), attempt 1, executed the frozen source `ca6eb576d0ac105ef260bc2703b7d0dc186a8656` on the original Darwin ARM64 toolchain.

## Actual result

The job failed in command 33, `baseline-typecheck-generated-swift`, after the original baseline generators and Go message build returned successfully. The compiler reported `no such module 'SwiftProtobuf'` with the recorded import search path ending in `.build/release/Modules`. The compiled SwiftProtobuf module directory was not archived, so its actual location is not established by this evidence.

Both private materialized SDK copies passed their source and isolation checks: 1,038 files and 20,082,375 bytes each. The exact-source SwiftProtobuf, original file splitter and custom Gogo generators built successfully. Baseline native generation, baseline Swift generation and `go build ./pb ./pb/service` returned zero. The baseline contains 11 native outputs, 693 Swift outputs and 37 middleware outputs. Its 11 native and 693 Swift outputs equal the original tracked bytes exactly; the same retained baseline bytes are also present in the failure-time snapshot.

Candidate generation was not reached. Candidate files in the failure-time section are original tracked state and confer no generation or compilation result.

## Evidence and lifecycle

The original ZIP is retained unchanged: 11,898,059 bytes, SHA-256 `8d76ee6f186f32985c276dba1f79e2ee82e0db7c1ad9c259ce4c2350b43fc769`, Git blob `e25184bdb2a42773375e85c22558c8e5545a46ab`, Actions artifact 14768420988. All 2,986 indexed payloads, ZIP membership and CRC, each payload SHA-256/Git blob, and the 33 command records were independently read and verified. All 33 owned command groups have an actual terminal drain record; 32 commands returned zero and the Swift typecheck returned one. The owned CI work directory was removed.

The sole finite Sentinel observer, `job_5f514994ea96`, finished successfully at 18:59:51 UTC with `TERMINAL_ARTIFACT_RETAINED`, preserving the generation failure. Its success is evidence-intake completion, not generator acceptance. A separate read-only status snapshot during extraction and the earlier unavailable live-log read remain distinct observations.

The ZIP contains every original command stdout/stderr stream, generated baseline/tracked snapshots, failure-time snapshots, source inventories and actual executable fingerprints. Selected original records are also exposed beside it for convenient inspection; the ZIP remains the complete deliverable. The source-bound verifier remains at `../copy-fix-20261122/verify_copy_generation_artifact.py`.

## Continuation boundary

Reuse the verified baseline output bytes where sufficient. The unretained compiler modules and generator binaries may require rebuilding from their pinned original sources. Query the actual SwiftPM build-product path and observe the owned module files before the next Swift typecheck. Do not infer an actual module path from the failed hardcoded path.

The final after-generation source and tool immutability checks were not reached after the Swift error. This result does not claim those checks passed. No endpoint/Invocation compilation, full SDK typecheck, iOS build, native test, schema/writer/body/ACK acceptance, or production integration occurred. Previously passed native controls remain preserved and were not replayed.
