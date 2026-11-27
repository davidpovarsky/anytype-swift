# Hanlin source inclusion for the next shared Apple build

Status: **source audit only; Swift compilation, compiled test discovery and execution are NOT_RUN**. This handoff is based on immutable Anytype source `680364279e08dc69d7d7eee8f6f13169ea8d0be4` and canonical Hanlin `45d5d90512c304d3457774b185741b7ef7d801db`. Root owns the final merged source, build admission and execution. The frozen `8f2c11713fb8a40ae13444104723666ffef68afe` product and its SDK385/native8ac admission are unchanged.

## Concrete registration correction

The original Stage1 project uses explicit source lists. Adding `Tests/HanlinSaveMessageAcceptanceUITests.swift` to Git alone did not include it in that target. This successor adds exactly four records: its `PBXBuildFile`, `PBXFileReference`, Tests-group entry and Sources-phase entry. No existing record, scheme, build flag, fixture, Swift implementation, pin or native source changes.

The before project blob is `67ea652b07c67b5523c29e6f34052b65eb212caf`; the after blob is `7ad813a47eb07c94ab88227c676075f238a3849c`. Four literal inverse removals reconstruct every original byte. The existing `Tools/PinkhaNativeDerived/rerun_original_ui.py` function `ui_only_project` was executed locally against a private source copy. It retained the new membership and every original source entry while performing its original removal of the App subproject binding. This was project generation only, with zero compiler, simulator or native calls. Its actual generated file identities are retained in the JSON handoff. The first audit's overly broad assertion that the entire file-reference section must remain unchanged failed because the original generator deliberately removes the App reference; that original local probe is preserved, and the corrected audit allows precisely that original removal.

## Exact compilation closure

`compiler-source-selection.json` supplies immutable Git blobs, SHA256 values and byte sizes for each required owned Swift source. The relevant original project, scheme, test plan, package manifest, main lock, module lock, SDK pin and materializer identities are also included.

| Target | Owned Swift files inspected | Inclusion in the original build |
|---|---:|---|
| `PinkhaHanlinCore` | 24 | Original SwiftPM default `Sources/PinkhaHanlinCore` path. |
| `PinkhaAnyHanlin` | 12 | Original SwiftPM default path, including the original parser conversion and real atomic-body worker. |
| `PinkhaHanlinUI` | 18 | Original SwiftPM default path, including original shared message UI, parser bridge and closed native helper/driver. |
| `Anytype` | 17 | Original synchronized App Sources group, including Heart body/context/worker and the new Heart acceptance coordinator. |
| `AnytypeTests` | 12 selected suites, plus 2 existing support sources | Original synchronized test group; exact materialized file identity remains required. |
| `PinkhaStage1AcceptanceUITests` | 1 new selected source | Four explicit project entries; the original UI-only generator preserves them. |

The two support files are `HanlinHostAdapterTests.swift` and `HanlinHostWriteTests.swift`. The new router tests use their existing helpers. Their inclusion does not ask to rerun all their unrelated methods.

Git contains both `AnyTypeTests` and `AnytypeTests`; the original project references the latter spelling. Existing Mac staging uses case-insensitive APFS. A lowercased path comparison is insufficient proof: the current `w3_compiler_lists` admission requires that the actual compiler input is the same physical file and has the exact frozen source bytes. Preserve that check. No directory is renamed or combined by this change, and no case-sensitive build is claimed.

The old frozen admission enumerates 43 hosted Swift source paths. Eleven additional owned source paths are required for this later milestone, yielding a minimum union of 54 before Root adds other lanes' changes. The JSON gives those eleven exact paths and identities. This comparison does not amend the old admission or transfer its compiler evidence to the new files.

For the future build, retain the actual Swift compiler invocation and the exact `SwiftFileList` for each target in the table. Every required source must occur once, with physical identity and bytes checked against the final frozen source. Keep the entire original Stage1 copy and generated project/scheme inventory before and after compilation. A source file being present in the repository, package or project is not a compiler-use receipt.

## Test selection after actual discovery

The complete method inventory in the JSON contains **111 hosted source methods in 12 suites**. This is Mini's original 97-method inventory, plus four pure support/conversion parity methods, five immutable Save-intent methods and five original message-projection methods. All ten earlier suite method names remain present; nine of their complete files remain byte-identical and the conversion file has its four additive methods. The 106 Save-related methods include the two existing shared-worker cancellation methods; the other five methods cover the original message projection and bounded sticky uncertainty.

| Suite | Source methods | Scope |
|---|---:|---|
| `PinkhaHanlinSaveMessageStateTests` | 42 | Identity, canonical events, bounded ACKs, semantic witnesses and metadata close/CAS transitions. |
| `PinkhaHanlinSaveMessageConversionTests` | 19 | Actual original parser and strict supported conversion; four identity-free eligibility parity/bounds/cancellation methods. |
| `PinkhaHanlinHeartSaveBodyTests` | 10 | Actual protobuf values and strict readback codec fixtures, without Heart service effects. |
| `AnyHanlinAtomicSaveBodyTests` | 5 | Original parser/native-value fixtures and complete atomic ACK shape. |
| `AnyHanlinWriteApprovalTests` | 2 | Body-bound, once-only original approval. |
| `HanlinSaveMessageJournalTests` | 9 | Real protected Apple filesystem owner and aggregate replay/removal; no document creation. |
| `HanlinSaveMessageWorkerTests` | 5 | Original shared worker and journal with controlled native callbacks. |
| `HanlinSaveMessageRouterTests` | 6 | Actual router and controlled original delegates. |
| `HanlinSaveMessageConsentLayoutTests` | 1 | Original UIKit full-body consent layout for the two authored sizes. |
| `HanlinHostCancellationTests` | 2 | Original consumer worker drain after revocation or early receipt. |
| `HanlinMessageSaveIntentTests` | 5 | Immutable request identity, exact UTF8 bounds, original result correlation and no reminted attempt. |
| `HanlinOriginalMessageProjectionTests` | 5 | Original SDK event projection and sticky uncertainty even at the 256-label cap. |

The requested selectors are `AnytypeTests/<suite>` for these twelve suites. They are candidate suite selectors, not proof that the compiled product discovers them. Require fresh compiled discovery of every listed method, then retain actual Swift Testing parameterized case identities and counts from the product. No absent selector, zero-test result or skip satisfies this gate. The counts above are source methods, not discovered or passed test cases.

The new native UI selector is:

```
PinkhaStage1AcceptanceUITests/HanlinSaveMessageAcceptanceUITests/testOriginalSDKMessageSaveConsentAndNativeReadback
```

It is one authored method intended for separate Heart and Any executions on the same newly admitted product. It uses real original SDK message completion, original Save action, native Cancel for one invocation and native Allow for a second, the original journal, and fresh full native readback. Its present scope is an English baseline. It does not cover native Stop, account or engine replacement, genuine lost ACK, failed final semantic readback, original-editor reopening of the saved page or cold replay. Those remain distinct unimplemented matrix rows. `HanlinSaveMessageAcceptancePreparationTests.requalifyRetainedNativeSaveFixture`, mentioned as a prospective name in the earlier matrix, was not implemented: the real preparation is the read-only mounted in-process helper. Do not select an invented preparation test.

## Dependency and runtime limits

The shared Xcode lock contains exact `swift-ai-sdk` revision `abf0921c6e89e6521cc2b510ff11016b45a0ef08`, original streaming parser `5cbb4b6c950051f98f02a0b0ae56756f5174a9b8`, Swift Markdown `25cb61d3482054b09ae76ca4f281b1bfe7fe5a43`, Collections 1.3.0 at `7b847a3b7008b2dc2f47ca3110d8c782fb2e5c7e`, and retained TorahInspectorKit `9058b489e9acc271b4f8ef69e2ed24648f93b4ed`. This handoff does not change any pin. The module-local `Package.resolved` is a retained partial graph and lacks the streaming-parser entry; it is not an isolated iOS package-resolution receipt. The shared App uses its main Xcode lock. No resolver was run or lock rewritten.

Before the new build, verify the actual canonical45 materialization marker and full per-file inventory, the four original package manifests, actual resolved checkout HEADs, and the coherent native manifest/binary identities. The JSON includes the four canonical package manifest hashes. Changes from the separate original companion owner must be reviewed and merged without discarding the accepted cancellation and rich-payload quota source; this document does not select a companion successor.

The actual five-method/seven-case canonical cancellation proof remains at `/Users/m1/builds/hanlin-wave3-cancellation-0a24e2c13b9b/eof-drain-385289`, with reviewed receipt SHA256 `c5fd9839ee7e2d2675d1de644230a23703a718af35c30797d5f5b83e923e747b`. Its earlier exact source/dependency limits remain intact; this compilation handoff neither reruns it nor relabels it as new UI/native acceptance. The six new canonical rich-payload quota tests remain a separate original SDK test-target requirement, not methods silently included in the App's test plan.

The new Swift conditional-Markdown adapter does not qualify the retained native8ac runtime for full-body Save. Actual current native route and source/binary qualification is required. The closed helper makes a fresh read under the real captured session; it does not manufacture missing native support. No account has been allocated or prepared here, and no Save fixture is qualified. Root must allocate separate genuine retained custody after the actual new product exists; the reserved T5 account remains untouched.

The remaining native scenario specification is the original matrix delivered to Root, SHA256 `7561ded2f777c26a784ac0405100f7a7a8bbd5a8139ee9d20ce9f22ec75d7e62`. Baseline compilation or the controlled suites cannot complete that matrix or enable ordinary production Save.
