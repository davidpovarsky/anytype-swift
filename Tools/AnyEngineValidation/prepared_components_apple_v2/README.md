# Prepared native components V2 on the dedicated Mac

This is the separate qualification candidate `v0.5.0-pinkha.prepared.components.2`, selected only by `PINKHA_ANY_NATIVE_ARTIFACT=verified-prepared-components-v2`. The original V1 source, artifact and all three failed consumer attempts remain preserved. The complete original runtime failure receipt is retained as `prior-v1-runtime-failure.json`; its actual sole XCTest failed at collection-owned property creation with HTTP 400 `type.not_a_type`. V2 is not a relabeling of that result.

## Exact native and Swift source

The manifest pins Any `cf87c43ff0100c2dc43c3c105c82b1b070b3a7a3` and any-sync-sdk `e195f6c07a053c6588e39ffe72ee4fc44cf3d953`, with complete binary Git patches from the original upstream revisions, every changed file/blob/hash, and the exact effective Git trees. Any-sync and any-store are unchanged. The two new actual Linux HTTP controls passed after retaining their original failed attempt; the evidence also records the current native owner-membership reconciliation correction.

The unchanged Swift definition wrapper from eda51b21/30892c5c and durable property-update wrapper from e760b61f are included. The new selected method is `AnyPreparedComponentsV2RuntimeTests/testManagedDefinitionsDeferredPropertiesAndFullFilesSurviveReopen`.

## Actual acceptance journey

1. Create an actual custom type and collection, a six-record atomic type part containing two datasets, fields and an index, and type-owned and collection-owned properties.
2. Read ordinary compiled native schema. Create two custom-type documents and native editor blocks. Omit the collection value from immutable object creation, then read the real object revision and prepare/commit its first collection-property SET through the public Swift property wrapper. Preserve its original revision and signed change.
3. Prepare separate full-file reservations for 4096 and 2097152 bytes. Reopen the native runtime and store, reconcile the original reservations, commit, and read every byte through native HTTP.
4. Reopen again, reconcile all definition/object/block/property/file intents without replacement, and reread exact schema, Unicode values, editor text, filenames, MIME, sizes and content hashes.
5. Require three distinct actual runtime and owner generations, two orderly reopens, the original sole XCTest PASS with zero failures/skips, immutable source/products and owned simulator/data cleanup.

The independent auditor admits all original intents, signed identities, exact source metadata and ordinary readbacks. An observation attachment alone cannot pass. It additionally requires two distinct property-update changes, their original expected revisions, and unchanged committed identities across both reopens. Native build success is recorded separately with zero executed tests.

## Execution and scope

Use `native_artifact.py` once with the verified Go1.27.4 compiler, shared qualified Mac caches and `/Applications/Xcode.app/Contents/Developer`. It builds only the two required ARM64 slices, under GOMAXPROCS=2, GOMEMLIMIT=6GiB and -p=2. Run `run_host.py` with a fresh owned consumer directory after the Mac queue owner grants the Swift/simulator slot. Actual test-without-building uses the installed supported `-collect-test-diagnostics never` flag; retained XCT attachments and original results remain mandatory. Package.resolved is seeded with the original exact three revisions.

Source admission has passed before publication; Apple execution is still pending at this source commit. Producer/consumer receipts use real local UUIDs, never borrowed Actions identity. A later Swift-only correction may reuse a native artifact only when its producer is an ancestor and its native inputs are byte-identical; previous failures remain immutable.

This is component acceptance. Full native source semantic mapping, full-Space destination completion, source history replay, network delivery, injected lost acknowledgements, OS-process crashes and physical-device validation are not established by this Apple journey. Prior independent Linux controls retain their own narrower provenance.
