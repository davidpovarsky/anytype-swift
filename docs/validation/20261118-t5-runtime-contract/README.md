# T5 host runtime and partial-coverage contract

## Published dependency and scope

The host source in this change requires TorahInspectorKit `356c6af25d81bb6503ee3fa13aa09a48be386c8b` (coverage contract `62b35c063081d2f10459b302dbbdc6f551f47559` plus the verified UTF-8 Hebrew notice correction). The integration owner updates the application/package pins. This producer commit does not change the integration owner's workflow or pins.

The earlier R02 query and exact-block navigation change is `86ea0110aa47924225ab2503a39f7455bf4577bc`. This follow-up connects that query to fresh native ObjectShow records when the separately enabled host build and the exact running r15 Heart version both permit it.

`PINKHA_NATIVE_T5_LOOKUP_V1` is not enabled by this change. An old persisted private index-row version cannot enable the private lookup. An enabled build calls the actual AppGetVersion RPC and requires the complete reviewed Heart version, including both r15 markers and the full patch SHA-256. Empty, r14, partial, prefixed, extended, newline-suffixed and foreign-patch identities fail closed.

## Host behavior

The existing r14 document-only path is preserved. Shared candidate hydration now also rechecks the live ObjectShow root, object ID, Space ID, projection readiness/status/engine version and canonical payload pointer. A ready search result alone cannot bypass that fresh read. This live-read change affects the current document-only path and still needs Apple/native host acceptance.

The gated r15 path queries `_pinkhaTorahRelatedSources`, requires version 1 on both candidate and fresh ObjectShow details, evaluates the actual block graph, and validates exact canonical targets. It retains result/scan bounds, cancellation and current-Space fences. Quotes and block rows do not gain an unlink mutation. Malformed targets are not converted to a document destination.

The result reports `indexedTargetsOnly`, always includes `indexFreshnessUnverified`, and adds truncation/stale-candidate limitations when appropriate. It never claims complete Space-wide coverage.

## Executed validation

On Windows Swift 6.3.3, SentinelX job `job_899cf4bcf736` ran production source copied byte-for-byte into the portable package:

- `T5NativeRelatedLookupCapabilityTests`: 3 test functions, 11 invocations including 9 rejected-runtime arguments, all passed.
- `RelatedDocumentsRefreshTests`: 2 test functions, 2 invocations, all passed. These compile the actual Kit Core and exercise refresh/invalidation plus document-only -> exact block/quote -> runtime-fallback transitions.
- The two executions each recorded 61 source hashes; every copied source remained unchanged. The logs and JSON receipts are original bytes. Tests present in the portable package but not selected are not counted.
- Four changed Swift files parse successfully with the feature flag absent and present; `host-source-check.json` records exact source hashes and commands. This is syntax validation, not an Apple host typecheck.

The Kit Core result is also preserved in the Kit commit. Count it once across repositories.

## Remaining acceptance

Apple application compilation, real Inspector block navigation and its actual UI acknowledgement, physical iPad acceptance, packaged r14/r15 compatibility and same-database old/new process tests are not proved by these portable checks. A matching runtime string is a necessary gate, not evidence that those acceptance tests ran. The client flag stays absent until the native compatibility gates pass. T5 remains open in Asana.

The independent native-index CI run `44209244478` passed two real Heart store tests; its original artifact and receipt are maintained separately in `../20261118-t5-native-proof/44209244478/`. It does not turn these Windows results into Apple/native host acceptance.
