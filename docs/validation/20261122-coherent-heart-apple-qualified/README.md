# Original coherent Heart Apple proof qualified

Run [45046643716](https://github.com/davidpovarsky/anytype-swift/actions/runs/45046643716) at `58b9de8f7a26d798e18e301ad1ed8be14f2a8c14` passed its one selected actual XCTest on an ARM64 iPad mini (A20 Pro), iOS 27.2 (24B8117). The original SQLite row reports `CoherentHeartAuthorityTests/testActualCombinedLibSignedAuthorityAndSharedSwiftDecoding()` succeeded in 2.005605936 seconds. The original Apple summary and test tree agree: one pass, zero failures, zero skips.

The single original XCTest JSON attachment was independently decoded from the original xcresult payload and exactly equals the archived `actual.json`. Eight native files, including the original owner/reader/removed protobuf responses, are hash-bound to that attachment. The owner and reader return identical signed variants/provenance with changed authority; the removed reader has a typed permission denial and no payload. Native object search/show also deny current removed access without data. The shared Swift codec really decoded the positive responses and rejected the removed response.

`ORIGINAL_RESULT_AUDIT.json` records every one of the 181 original files. Artifact `14763843433` is 7823218 bytes, SHA256 `a2d8f1de53e5f2958722e08c252f57f479ba120dd4ecb1b9313d9ba8e36ac7c2`. `original-450466-selected.zip` preserves the complete actual test xcresult, the native responses, original receipts and selected small provenance records; its own manifest identifies all 71 selected files. It omits the redundant build-only xcresult and large build inventories/logs rather than substituting for the complete original artifact.

## Exact build reuse

The production and explicitly nonshipping fixture frameworks remain the original build from run `45035194823`, commit `78b8b6168f0a750d2b742d94b78c95aa4abf579a`. That earlier run failed before XCTest; only its successful build scope is reused. The current run performed zero framework rebuilds and zero old native/Swift method reruns. Its 451 controller/source inputs stayed unchanged during execution, including all 112 copied shared Kit/HeartEngine files.

| Original binary | SHA256 |
|---|---|
| Production simulator Lib | `1b317dd0d4a22222f0e2eac7769be65b301ffbf4e45c91be4ab4377b87dfa1d1` |
| Nonshipping fixture Lib | `84213a9393e7ae17633dce1c60f53afcf7a373f83069e60d9667d53f603642f9` |

The current host booted its owned simulator, built its exact required harness during startup, checked readiness, and executed the one unchanged selected method with `test-without-building`. The build/test arguments and owned UDID are bound to the receipt. Earlier runtime-selection and boot/cleanup failures remain separate original failures.

## Next actual consumers

Both were dispatched once at the same exact commit, using source run `45046643716` and profile `r15-attachment-authorized-current-read-v1`:

- [45047827580](https://github.com/davidpovarsky/anytype-swift/actions/runs/45047827580): shared SDK/editor lane, with 23 selected methods/32 cases followed by its dependent journeys.
- [45047830860](https://github.com/davidpovarsky/anytype-swift/actions/runs/45047830860): coherent Heart combined release acceptance lane.

Their original-byte installer must independently replay the original xcresult and verify the production archive and current shared source identities. At this evidence checkpoint their results are pending. This fixture/codec pass does not claim production-app execution, network ACL delivery, fresh iOS process reopening, physical iPad, full T2/T5, or release acceptance. The app capability remains OFF.
