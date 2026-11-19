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

The controller requires four distinct actual host PIDs and nonces, one App source, relative native-store location, account, Space and manifest, an unbroken persisted ledger hash chain, and four actual named XCTest passes with zero skips/failures on the selected OS27 ARM64 device. Replacing both a ledger and its reported canonical/public/block baseline is explicitly rejected.

### App-update container relocation (receipt protocol v2)

Apple's [Testing iOS App Updates, TN2285](https://developer.apple.com/library/archive/technotes/tn2285/) documents that an app update changes the absolute container path. The controller resolves the current container after each install and XCTest execution. It does not treat the OS-assigned container UUID as persisted account identity.

Immediately before and after every runtime replacement, with the prior native account stopped, the controller compares the complete relative file/directory inventory of `Library/Application Support/Anytype/middleware-go`: every regular file size and SHA256 must match, as must the private ledger and credentials. Missing, extra, changed or symlinked entries fail. Only aggregate hashes/counts go into public proof. No native files, credentials or private ledger are moved or restored by the controller.

The ledger retains `rootPathSHA256` as the original creation location and binds the invariant `rootRelativePath`. Each phase records `currentRootPathSHA256` separately. Swift obtains the current root through the production service, checks its relative location, recovers the original account and verifies the original data. The controller independently checks the reported current root against the simulator's actual current data container. The absolute path may change; the original account, ledger chain, source and canonical/public/block identities must not.

After the first accepted native phase, the original credential inventory is retained in the controller's private work directory with mode 0600. Evidence scanning uses those original credentials even if a later install loses or relocates the container. The inventory is never uploaded or cached; its contents cannot be replaced by later credentials. This preserves diagnosable failure evidence without permitting credential-bearing logs.

## Evidence and credentials

The disposable wallet response masks both mnemonic and accountKey in the normal invocation logger. Recovery sends accountKey alone. These credentials are written only to a private0600 file in the disposable simulator container; no Keychain credential is created.

Native xcodebuild output and original xcresult stay in private work. Only an explicit list of original text logs, XCTest summary/tests JSON and per-phase receipts is copied into proof, after scanning every candidate for both complete credentials in UTF8 and UTF16. Missing credentials withhold native output; finding either credential withholds all native evidence. The raw xcresult, private ledger/secret file and account data are never part of the upload. DerivedData activity logs are moved into private work before the separate compilation cache is saved.

The original build logs and runtime receipts remain in proof. The workflow packages only that proof directory. Rejection controls exercise stale processes, different sources/accounts, changed canonical/public/block baselines, unavailable runtime capability, missing targets/disclosure, missing stop observations, hidden skips, repeated PIDs, differing build flags and credential-bearing output. They are not counted as Apple or native acceptance.

## Limits

A passing run proves only this same-source Apple account/reopen/fallback sequence. Actual Linux JSON/Protobuf export coverage is a separate gate. This route does not establish Space-wide index freshness, full R01-R09 acceptance, visual UI navigation acknowledgement, physical-iPad behavior, the complete required UI matrix, TestFlight or release acceptance. Coverage remains explicitly incomplete indexedTargetsOnly on r15 and indexedDocumentsOnly on r14.

The parent dispatcher must add a route to this reusable workflow after integration review. It owns dispatch coordination; this producer does not modify the existing dispatcher or start another heavy Apple job.

## Optional fifth process: production host freshness

The reusable workflow adds boolean input `include_freshness`, default false.
The parent can use its existing `t5_component=index-freshness` selector under
`route=t5-apple-pairs`; no additional workflow_dispatch input is required.
The same two application builds and identical test-only flags are used. The
controller completes and validates old-create, new-upgrade, old-edit and
new-recover before launching a distinct r15 new-freshness process.

That fifth process selects the original account and verifies the original
ledger/source/root/Space, canonical bytes, block identities and r14 title edit.
It retains the same production AnytypeTorahSpaceRelatedDocumentsService instance
through every mutation. Writes go directly through ClientCommands; there is no
explicit host/repository invalidation or reconstruction after a write.

Every observation first reads the actual native private index, queries the
production Swift service, and reads the native index again. It checks exact
current-Space identities and targets, and then records live ObjectShow canonical
bytes and actual block graph nodes where relevant.

| Order | Actual observation |
| --- | --- |
| 1 | Original document, Note block, and sourceQuote block all appear. |
| 2–3 | Note unlink removes its result without deleting the Note/block; exact original canonical bytes restore its result. |
| 4–6 | SourceQuote reference changes from Genesis 3:3 to 3:4; both source queries are checked, then original bytes restore the original result. |
| 7–8 | Native archive removes the Note; unarchive restores it and its original canonical payload/block. |
| 9 | Deleting the Note block retains the canonical native candidate but removes its exact target from Swift. |
| 10 | Deleting the quote block does the same for sourceQuote. |
| 11 | Deleting the Page leaves two dangling native candidates and no Swift targets; native ObjectShow must specifically report not-found/deleted. |

After block deletion, both native membership reads must still include all three
canonical candidates. The production service must exclude the absent exact
block targets and return staleCandidates alongside indexFreshnessUnverified.
The original graph nodes are included in the receipt; the Python controller
independently computes reachability and rejects a merely asserted false bool.
Canonical unknown fields must survive updates and exact restoration.

The fifth process records exactly four ObjectSetDetails calls, two archive calls,
two BlockListDelete calls and one ObjectListDelete call. It does not recreate the
account, Space, objects or blocks. The final removals intentionally affect only
the disposable fixture, after the four compatibility phases passed.

The first four reports remain in phase_reports. The optional report is separately
published as freshness_report. Its ordinary readbacks and targets are explicitly
labelled BEFORE_FRESHNESS_MUTATIONS, so they cannot be interpreted as preservation
after intentional deletions. Native account stop, not-running verification, and
AppShutdown still precede publication. Ledger hashes and five distinct process
IDs/nonces bind the whole sequence.

If accepted on Apple, the counts are two builds, five named passing Swift/native
invocations and eleven host freshness observations, with zero failures/skips.
Eleven observations are not eleven XCTest invocations. The phase's status is
PASS_ACTUAL_SWIFT_NATIVE_LOOKUP; coverage remains indexedTargetsOnly,
spaceWideFreshness=NOT_PROVEN and navigationStatus=NOT_RUN. The product flag
remains OFF. UI navigation acknowledgements and physical-device behavior retain
their separate acceptance gates.

The fifth-phase evidence uses the same explicit allowlist and complete credential
scan as the first four phases. Raw xcresults, private account data, keys, and
mnemonics remain outside the uploaded proof and compilation cache.

## Optional real Inspector UI after the fifth phase

The default pair remains unchanged. The additive `--include-native-ui` option
requires `--include-freshness` and preserves an independent pair-result receipt
before reusing the exact retained r15 App on a separate fresh iPad account.
The UI runner alone is rebuilt. UI failure/cancellation fails the optional route
without replacing the already completed pair evidence. See
[T5_NATIVE_UI_CONTRACT.md](T5_NATIVE_UI_CONTRACT.md) for the exact methods,
container/source boundaries, original screenshot receipts and secret policy.
Automated UI PASS still requires separate visual review; product lookup stays OFF.


## Public projection mismatch diagnostics

The private ledger retains a per-field JSON snapshot of exactly the same eight
public projection fields already included in the mandatory full projection hash.
On a mismatch, the native test emits one `T5_APPLE_PAIR_PUBLIC_PROJECTION_MISMATCH`
JSON line before throwing the original `public-derived-projection-changed`
invariant. It records the actual source, phase, process and object identities,
whole-projection hashes, and only differing field names, presence and per-field
hashes. Controlled values are limited to known property keys in an attachment
array (at most 16 entries), boolean readiness, small integer projection versions,
and a fixed status vocabulary. Source identities, labels and arbitrary values
are represented only by digests. The existing complete-credential scan still
controls publication of the native log.

This is diagnostic evidence, not an acceptance result. The fixture does not attach
additional properties, the hash still includes attached-property membership and
order, and the failed phase does not advance its ledger or issue a PASS receipt.
The first diagnostic run must identify the actual differing fields before any
fixture or runtime correction is proposed.
