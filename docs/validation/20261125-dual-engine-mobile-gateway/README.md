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
