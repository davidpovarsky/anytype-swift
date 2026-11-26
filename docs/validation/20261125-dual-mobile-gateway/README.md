# Original mobile gateway qualification — 25 November 2026

## Result and scope

All three unchanged original Any gateway methods executed and passed on the actual Apple Silicon host with Go 1.27.4. There were zero failures or skips. The exact unified source manifest is 70f0b2a66286ae87afdc5a8d5becb267fd1aa5c5110e54381a3b0384afd69a72; all 4,855 native source files remained unchanged.

| Original method | Actual result | Scope |
| --- | --- | --- |
| TestAcquirePIDLock_MobileNoOp | PASS | The original mobile PID-lock implementation is selected. |
| TestPinkhaMobileManagedGateway | PASS | Missing/wrong managed tokens are rejected on the original protected routes, authorized requests work, and an empty managed token fails closed. |
| TestPinkhaMobileGatewayPreservesStandalone | PASS | The original standalone gateway behavior remains available. |

The test-binary compilation took 19.096 seconds; actual original JSON execution took 3.028 seconds. Original execution log SHA256: d52264ac1f71a33fe1c1939cf58678bd61388d28ce6f9480631c3bf25c1e29a4. These are native component controls, not Apple application, peer synchronization, full D acceptance, Release, signing, or TestFlight acceptance. The local network fixture emitted expected unavailable-peer connection messages; no network synchronization success is inferred.

## Why this change was necessary

The actual combined-app hierarchy test reached real Any account/space creation, then the original Swift capability guard rejected the space because mobileManagedTokenGateway was zero. The previous unified binding used gomobile but omitted Any's distinct original mobile tag. The corrected native manifest selects both tags. The Swift capability guard and all original test assertions remain unchanged.

The source also includes C's separately qualified compiled-definition/capture checkpoint delta through Heart donor 5e8f9ce4ec789c1cd775b148a6cc49d4a28f56b5. That source milestone is not a claim that whole-space semantic migration admission is complete.

## Original failures retained

The first gateway attempt stopped its owned compiler process at the actual 2 GiB emergency floor. Its command list proves that the test execution command was never issued; zero gateway methods ran in that attempt. The original failure receipt and logs are retained under original/evidence. Only its inactive private compiler temporary was later retired, after process/file checks, with a separate receipt retained on the Mac. No shared cache was deleted.

The constrained resume reused the identical source, workspace and local fixture, then actually compiled and ran the three methods. Its original receipt is under original/evidence-resume-1. The reported resource estimate distinguishes observed global disk changes from attributable job growth.

The subsequent Apple simulator producer stopped before binding because eight lazy GoModSum fields were absent from its fresh derived workspace. All 760 module paths, versions, replacements and other fields matched the gateway graph. This controller change copies only those eight previously authenticated checksums into the owned derived go.work.sum, after verifying the original Go/SumDB receipt, original lookup evidence and current cached go.mod bytes. It preserves strict complete graph comparison and never modifies native source go.mod, go.sum or go.work.sum.

The Apple metadata-only failure remains at /Users/m1/builds/pinkha-dual-native-v1-70f0b2a66286-simulator/evidence. A separate explicit resume accepts only that exact successful-preparation/failed-graph sequence and retains all original command evidence. Its eventual native build result is recorded separately.

## Custody

- Actual gateway root: /Users/m1/builds/pinkha-dual-native-v1-70f0b2a66286-gateway.
- Original gateway controller commit: 00a25d25f1a64e6b6665d97d178645d0337dd3e0.
- Native archive SHA256: 9197ea5c9f8a832430fce44b36aeeeb27099fff6e745ec6197e9a3493ffd51db.
- Original test binary SHA256: db53bdb3dd9ece9f16f8b40ae11ef4ba75781f283034deb44d766950c428e3b0.
- Original transfer archive SHA256: 774a10614e4e2fc45dc4788c6bb0c6fc5df9d357f244c0a0be70314fa48c818a.
- Oracle originals: /mnt/development/projects/evidence/dual-engine-native-binding-20261125/gateway-originals-70f0.

Every copied original file is inventoried in original-files.json. The Apple slice and affected app acceptance remain required before D can be completed.
