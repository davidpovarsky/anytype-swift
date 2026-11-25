# Restore Any's original mobile token gateway in the unified runtime

The actual original D drag test entered the single app, switched through the real
engine menu, created an account, acknowledged its backup and created a native
Space. Original native HTTP logs show POST /v1/spaces returned 201, then membership
and capability reads returned 200. The app correctly refused to open that Space:
the combined producer used gomobile but omitted the independent mobile build tag.

The original Any code enables its managed-token gateway under mobile. Without it,
its desktop variant accurately reports mobileManagedTokenGateway=0. The Swift
activation requirement remains unchanged. No capability or acknowledgement is
fabricated.

The corrected manifest includes both tags. A reviewed source-constraint inventory
found only Any's existing token-gateway, process-lock and OpenAPI mobile variants;
Heart, SDK and any-sync have no mobile-tag alternatives in this source closure.
The new simulator producer must execute the original three native methods:
TestPinkhaMobileManagedGateway, TestPinkhaMobileGatewayPreservesStandalone and
TestAcquirePIDLock_MobileNoOp. Exact pass counts and zero skips are required.
The private working fixture copies the unchanged original local nodeconf into
the test's documented staging.yml location outside the source tree. No test
source/assertion changes are made.

The device producer may reuse only that same-manifest original proof and log.
Both Apple slices and the actual app must subsequently pass. This checkpoint
does not claim that the new native checks or Apple producer have run yet.
All original D results and the generic UI error remain retained.

## Original bounded host phase and resource stop

The actual 70f0 gateway host compiler was launched once on 25 November at
10:13:23 UTC. Exact source and the complete native module graph were verified.
The compile was stopped by its owned process-group disk guard after 25.163 s
(exit -15, minimum free 2,122,731,520 bytes), before a test binary or test-execution
command existed. All three methods remain NOT_RUN; the original first receipt
conservatively contains a null count, not a successful or completed test result.

The original failure, all commands and logs are retained under
`/Users/m1/builds/pinkha-dual-native-v1-70f0b2a66286-gateway/evidence` and copied with
exact hashes to Oracle `evidence/dual-engine-native-binding-20261125/gateway-first-disk-stop`.
Only the interrupted, inactive private Go compiler directory was retired after
all owned groups were absent, lsof reported no handles and all 4,855 source files
and original evidence matched. The shared Go caches were retained. Its complete
2,201-entry inventory and receipt remain alongside the original evidence.

A constrained resume accepts only this pre-execution disk stop with unchanged
source, archive, workspace, original fixture and failure logs, no active group,
no existing test binary and an empty private compiler temporary directory. It
retains a separate `evidence-resume-1` result and updates the measured phase
allowance from the original global peak drop plus the remaining host link output.
It does not reinterpret the original failure or permit replay of a completed test.
