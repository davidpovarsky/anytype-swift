# Original and current personal navigation

This W1 change adds the engine/Host contracts for original Heart navigation contexts, the current Home preference and native local last-opened time. It is a normal child of catalog/metadata commit 0b8f03a13d332fc44ed89fc9d6389658d6cfc5e0. W3 owns integration; W2 owns application presentation and gestures.

## Actual qualification

The qualified set is **26 distinct methods: 23 retained source-equivalent passes and 3 newly executed passes**. It is not one successful 26-method execution.

| Evidence | Actual result | Attribution |
| --- | --- | --- |
| Attempt 1, fad0f014 | FAIL before test start; optional-chain fixture compile error | Kept unchanged, 0 accepted methods |
| Attempt 2, f266f1f7 | 26 starts, 24 passes, 2 failures | 23 unaffected passes retained; one previously passed Home method was affected by the fixture correction |
| Attempt 3, 6325a1a2 | 3 starts, 3 passes, 0 skipped | Two originally failed methods and the affected Home method now qualified |
| Aggregate | 26 distinct qualified methods | Separate original/targeted executions; the original failed owner remains exit 1 |

Attempt 3 is SentinelX job_e7a3fa38196b, completed 2026-11-28 04:42:34 UTC after 104.12 seconds, exit 0. All seven new owned command groups exited normally and are positively absent. No signals, forced cleanup, old PID reprobes, native accounts or migration replay occurred.

The new Swift log is 2,721 bytes, SHA256 635949599b32f8280052c095f4ae4fcea14bebe079d92bd234ad262e42d180c5. It reports these three selected cases:

- NativePersonalNavigationContractTests.testHomePreservesAbsentEmptyUnknownAndClosedWireVariants
- NativePersonalNavigationContractTests.testOriginalLastOpenedDescriptorAndDecodedBindingKeepExactSourceIdentity
- NativePersonalNavigationHTTPTests.testAcknowledgmentSurvivesAnEnclosingSessionRetirementWithoutPrivateReadback

The one new owned synthetic loopback fixture observed 55 requests: 54 GETs and one POST. It retained exactly one native-shaped acknowledgment before session retirement, then closed through normal stdin EOF. The earlier 13 fixtures and 9 writes remain attributed only to attempt 2. Synthetic fixtures do not establish native guest authority, storage isolation or real native mutation behavior.

## Production behavior

Five production files change: AnyHTTPClient receives a narrow dedicated bound-request path, AnyNativeAccountRunBinding binds account/network/run identity, and three Host adapters expose original navigation, current preferences and actual-open observations. The catalog and metadata readers are inherited unchanged from the parent.

Original workspace, Home, Archive and Widget contexts retain their native identities and byte-preserved evidence. Original Home values do not become new current settings automatically. Current Home keeps absent, explicitly empty, supported built-in, object and unsupported values separate. Stored object references must still resolve through current membership and a materialized nontrashed object.

Last-opened uses the fixed built-in local datetime descriptor pinkhaLastOpenedV1. It records a real current open in whole Unix seconds represented as exact native milliseconds. Archived historical timestamps are not replayed into this current local field. Ordinary current authenticated members may use this private local behavior under READ authority; guest-shaped and foreign account contexts are refused by this Host contract.

A prepared mutation captures its original account/network/run, workspace and lease generation. A restarted engine with the same account is a different authority. Only dedicated bound settings/local-property routes are accepted. A successful response must carry the matching engine acknowledgment headers. There is no older unbound write fallback.

The synchronous onAcknowledged callback runs before the first awaited readback check. The caller can retain known native acknowledgment even when the enclosing application session is retired and throws CancellationError. Acknowledgment does not grant a private read or another mutation. The store's bounded session ledger prevents a second dispatch of the same intent; it is not a durable crash-recovery journal.

See CONSUMER_CONTRACT.md for the W2/W3 integration contract.

## Why the targeted correction is sufficient

The JSON fixture originally sent typed canonical comparison bytes to a JSON decoder. Four wire/evidence sites now use JSONEncoder; canonical comparison bytes remain unchanged. The correction affected two contract methods, so the previous Home pass is explicitly superseded.

The session-retirement fixture originally expected AnyHostError. The unchanged AnyApplicationSession cancels its registered task when the run is invalidated; its enclosing perform fence therefore throws CancellationError. The corrected fixture requires that exact cancellation, an inactive session, actual fixture owner retirement, one retained acknowledgment, one callback and one write. The original prohibition on delivering private readback remains.

The input manifest and retained-evidence review join all 112 complete Swift files against attempt 2. All 107 production files and 110 complete files are unchanged. The two changed test files invert exactly to their prior full-file hashes. No other selected method or embedded HTTP server changed. The 34 earlier Type/metadata/provider methods are unselected.

## Retained original artifacts

The original outputs remain at:

- /mnt/development/projects/evidence/pinkha-original-navigation26-20261128/components-attempt1
- /mnt/development/projects/evidence/pinkha-original-navigation26-20261128/components-attempt2
- /mnt/development/projects/evidence/pinkha-original-navigation26-20261128/components-attempt3

The full current compiled source ledger is 778,568 bytes, SHA256 6f73981ffa2f0c5ca5619bd970d6aaa5f221579ecd40afc8aff9767c49ef735e, at components-attempt3/compiled-source-inputs.json. The prior ledger is 777,175 bytes, SHA256 ce38612884f316845702391f443989f19fbef0cd493af915b7f75d3ea536c499. The raw result files in this packet bind those originals without reserializing them.

The current producer preserves all 28 qualified Products. Its test runner is 10,945,216 bytes, SHA256 763aa7fbe7c791a5c437dd511d4b8c31adce46111ceeb2c761a24b246ba791e6; its shared test image is 34,045,000 bytes, SHA256 9c7a68eba5690293ef633d837292c8213aa0e119b44baaabc0ceeb3a930d097b. Historical failed build Products were neither qualified nor reused.

Finite runtime gates remained ROOT 2,181,038,080 bytes admission / 2 GiB live; DEV 973,078,528 admission / 512 MiB live; 384 MiB owned output; 3 GiB available memory; 900-second main plus 120-second final verification, outer 1080. Actual owned peak was 206,540,800 bytes. All source, fixture, admitted-input, compiler correspondence, dependency-product and current-product completion checks passed.

## Remaining acceptance boundaries

This is engine/Host component and synthetic HTTP qualification. The companion native N24 bound-server implementation is a separate source/runtime delivery; W3 must join its actual acceptance before enabling these routes in the app. This commit provides no Apple UI, live cross-account Home, native crash-resume ledger, P2P/cloud or whole-Space migration acceptance.

The existing 182-operation migration and Native159 cold/offline catalog acceptance were not replayed. C's completed-migration cold-context owner is a separate implementation and must supply the real destination plan, saved mappings and current owner after application restart. W1 does not wire a source-review draft into destination authority.
