# T5 Apple same-source runtime pair

## Scope and status

This is a new, independently invoked acceptance workflow. It does not replace the Startup, existing OS27 UI, r14 runtime, or r15 runtime-build workflows. The first publication contains source, rejection controls and a Swift syntax parse only. **Actual Apple pair execution is NOT_RUN.** The product lookup flag is unchanged and remains disabled.

The reusable workflow accepts two explicit original runtime run IDs:

- r14: run44203168617, artifact14383247626, Pinkha-Universal-Verified-Heart-r14. This is the same runtime used by Startup PASS44216444722 on App997807b79c664568edf9f1973875f7e9148b77b6.
- r15: a successful run of the separately reviewed r15 build-only route. Run44225433140 was in progress at the source handoff; its outcome is not inferred here.

The original artifact ZIP digest, archive payload, immutable947fbde native inventory, Heartd98420b source, patch hashes, file inventory and all three actual binary slices are verified before app compilation. r14 and r15 retain their exact original source inventories.

## Same source and real capability

One clean published App checkout must equal the actual GITHUB_SHA. Both builds use exactly these test-only flags:

OTHER_SWIFT_FLAGS=$(inherited) -D PINKHA_NATIVE_DERIVED -D PINKHA_NATIVE_T5_LOOKUP_V1

The second flag is confined to this workflow's build invocation. No product xcconfig, feature flag, native source or generated API is edited. Actual package locks, resolved Kit revision, prepared Hanlin source receipt and app source SHA must remain equal across both builds.

The first build's products are preserved before the second runtime is installed and relinked in the same DerivedData. Only recorded product path references in xctestrun are rebound to the preserved product directory. Code bytes are inventoried before testing and compared with the actual installed app after each execution. There is no simulator uninstall or erase between phases.

The Swift fixture invokes AppGetVersion and the production AnytypeT5NativeRelatedLookup.current() in every process. r14 must remain unavailable even if private rows written by r15 survive a downgrade. A phase name, fixture parameter or stored private version cannot activate the production capability.

## Four native test processes

The named test TorahT5RuntimePairTests/realSameAccountRuntimePairPhase is selected once per phase on one freshly created OS27 ARM64 iPad simulator:

1. old-create: create one real local-only wallet/account/Space, install the optional Note Type, bootstrap the real manifest, and create Page document-context, Note block-context and custom-type sourceQuote targets.
2. new-upgrade: recover the exact original account key, select the same account/Space, and discover all three targets through the real Swift host adapter and running r15.
3. old-edit: recover the same account using r14, keep the explicit document-only fallback, and make one ordinary Page title edit.
4. new-recover: recover with r15, observe the old-runtime edit, and rediscover the original three object/block targets.

Only an actual ACCOUNT_STORE_NOT_MIGRATED error allows AccountMigrate followed by another select. Later phases cannot create another wallet, account, Space or fixture.

Each phase requires canonical byte hashes (including unknown sentinels), public projection hashes, exact original object/block identities, reachable block text, manifest bytes and ordinary titles to remain intact. The initial Note title is taken from native ObjectShow: its layout legitimately moves the requested name into a text block and can leave an empty name detail.

Every phase finishes AccountStop(RemoveData:false), then requires ACCOUNT_IS_NOT_RUNNING from the original AccountPreloadRemainingSpaces RPC, and only then calls AppShutdown. AppShutdown acknowledgement alone is insufficient because the pinned native implementation hides Stop errors.

The controller requires four distinct actual host PIDs and nonces, one App source, root, account, Space and manifest, an unbroken persisted ledger hash chain, and four actual named XCTest passes with zero skips/failures on the selected OS27 ARM64 device. Replacing both a ledger and its reported canonical/public/block baseline is explicitly rejected.

## Evidence and credentials

The disposable wallet response masks both mnemonic and accountKey in the normal invocation logger. Recovery sends accountKey alone. These credentials are written only to a private0600 file in the disposable simulator container; no Keychain credential is created.

Native xcodebuild output and original xcresult stay in private work. Only an explicit list of original text logs, XCTest summary/tests JSON and per-phase receipts is copied into proof, after scanning every candidate for both complete credentials in UTF8 and UTF16. Missing credentials withhold native output; finding either credential withholds all native evidence. The raw xcresult, private ledger/secret file and account data are never part of the upload. DerivedData activity logs are moved into private work before the separate compilation cache is saved.

The original build logs and runtime receipts remain in proof. The workflow packages only that proof directory. Rejection controls exercise stale processes, different sources/accounts, changed canonical/public/block baselines, unavailable runtime capability, missing targets/disclosure, missing stop observations, hidden skips, repeated PIDs, differing build flags and credential-bearing output. They are not counted as Apple or native acceptance.

## Limits

A passing run proves only this same-source Apple account/reopen/fallback sequence. Actual Linux JSON/Protobuf export coverage is a separate gate. This route does not establish Space-wide index freshness, full R01-R09 acceptance, visual UI navigation acknowledgement, physical-iPad behavior, the complete required UI matrix, TestFlight or release acceptance. Coverage remains explicitly incomplete indexedTargetsOnly on r15 and indexedDocumentsOnly on r14.

The parent dispatcher must add a route to this reusable workflow after integration review. It owns dispatch coordination; this producer does not modify the existing dispatcher or start another heavy Apple job.
