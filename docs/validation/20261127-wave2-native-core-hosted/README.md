# Future native-core hosted source and consumer preparation

This is a separate, closed preparation for three published native UI component suites. It does not admit a product, compile Swift, execute XCTest, or replace the frozen 8f2 profile. Its immutable branch base is ff6836a6d4db7f1a19b94280d3b2f548e8d7d622; that base is not a tested build.

## Exact scope

| Future lane | Original suite | Framework | Methods / declared cases | Required source commit |
| --- | --- | --- | --- | --- |
| native-properties-hosted | AnyNativePropertyPresentationTests | Swift Testing | 9 / 9 | 54079356628487f7ecedf5cfe87434c8cc57ea36 |
| native-block-creation-hosted | AnyNativeTextBlockCreationTests | Swift Testing | 2 / 2 | dc582ba3239d6dcb66dbe1f7098b95349e4289f9 |
| native-typography-hosted | AnyNativeTextTypographyTests | XCTest | 2 / 2 | 33e31c64ca9e35e258a4d64cfe8690b08a6cbc39 |

Each lane has a corresponding fixed -only plan. Their compiled target is AnytypeTests only after an actual direct-source compiler witness. Their original package target remains PinkhaAnyUITests.

The existing properties-hosted profile is unchanged: its 15 methods are PropertyCreationSearchTests (9) and PropertyCreationSelectionTests (6). They do not cover the separate AnyNativePropertyPresentationTests suite. The two new Properties methods contain three internal scenarios; those loops are not separately enumerated cases. Typography's per-style, per-size, and inline-font loops likewise remain two XCTest methods.

The three original test files are not copied into AnyTypeTests, rewritten, stripped, or replaced by Linux component sources. This tranche adds direct SOURCE_ROOT PBX references to their original package paths. The branch base already includes the exact Add-block and Typography files. It still contains the older seven-method Properties file, so Properties540793 is an explicit dependency before any matching future product is built or qualified. This tranche does not fabricate that dependency in its base.

## Concrete omissions in the frozen build contract

The frozen 8f2 project has no source bridge for any of these three files. Its selected native source inventory has 43 entries and its package-source admission allowlist has four paths. Neither the full Stage1 UI copy nor a package test declaration proves that these files entered AnytypeTests.

The future PBX adds three exact file/build/group/source entries. Typography directly imports DesignKit and uses AnytypeFont and FontFamily; the hosted target lacked that dependency. The patch therefore reuses the existing DesignKit product reference 746F06002DB8E712005795F7 in AnytypeTests and adds one test-target Frameworks entry. No package definition, package version, lockfile, App target dependency, production Swift source, or existing test method changes.

The closed future inventory retains the original 43 native paths and adds the three package files, for 46 paths. The existing nine Stage1 UI paths remain unchanged. Retained paths do not imply retained content hashes: the future complete native inventory must come from the exact combined source freeze, including reviewed changes on inherited paths such as the G02 reader. No old43 compiled hash is silently reused.

## Consumer and receipt boundaries

The separately named receipt_admission_native_core.py changes only the fixed package-source allowlist from four paths to seven. Every original receipt-validator function is byte-identical to the reviewed 9ce1288f original. It is not installed as an active replacement for the historical gate. Wave3's next exact source/producer admission and the next common qualifier must deliberately bind this reviewed successor and the complete future native inventory.

The generated F host is a separate successor of the exact published 2e57294d host. It adds three fixed dispatch routes and a 15-file control closure containing the existing 13 files plus native_core_hosted_profile.py and native-core-closed-profile.json. The original 13-file closure, the separate 17-file G02 closure, and the common product qualifier are unchanged. The original descriptor binder, process lifecycle, result retention, source admission, source enumeration, test stage, and product checks remain byte-identical.

The profile reuses the exact native_compiler_witness API. It accepts the selected proof only from producerReceipt.nativeCompilationProof after the common product admission. That proof must identify the original tracked physical source bytes, an actual AnytypeTests SwiftFileList, and the actual swiftc invocation consuming that list. It is checked before and after execution. The original source/root/Native/SDK/Products qualification remains the common qualifier's responsibility.

The two Swift Testing suites use the existing declaration parser. The one exact Typography XCTest class has a finite source-bound declaration check for its two named parameterless methods. All three suites reuse the original suite-level selection, flat enumeration reader, actual result/device checks and case-node validator. No generic XCTest discovery, summary-count waiver, or source override was added. An unfamiliar actual enumeration or result representation remains a failure requiring review.

Both the F entry point and the profile's execution entry point unconditionally reject these future plans. Flipping a JSON ready flag cannot enable them. The closed profile has no future source commit, actual producer receipt, or actual shared admission. Activation requires a separately reviewed exact successor after the real source union and successful shared build exist.

## Evidence and limits

Materialization2 proves the exact complete byte inverse to the original project, gate and F host. The original gate declarations are unchanged; only invocation_selectors, host_validation_module, Consumer.execute_lane and main receive finite new dispatch checks in the F host. Materialization1 is retained as the earlier draft.

Six portable controls passed in 0.05831058799958555 seconds. They cover standalone closed startup before the helper closure exists; exact published declaration scopes and source drift; missing/extra/foreign compiled selection; inflated loop counts, skipped or duplicate results; immutable runtime closure; and the three exact inverses plus future path inventory. These are synthetic control checks, not Apple execution. The earlier five-control receipt is retained. The final source profile defers imports of original validators until their original admitted helper phase; the earlier draft's eager-import issue was caught before publication.

No Swift compiler, App build, UI build, native engine call, simulator, XCTest, UI acceptance, persistence acceptance or physical-device check was run for this tranche. Existing historical results remain tied to their original source and profile. The Add-block Linux component result remains its original component evidence and is not relabeled as hosted Apple acceptance.

Two distinct independent source reviews found no remaining blocker: root reviewed the PBX/import graph, the three direct-source registrations and the exact receipt-gate inverse; Torah reviewed the fixed selectors, original compiler/result validators, separate 9/2/2 counts and lazy helper imports. Their retained records are root-bridge-review.json and native-core-profile-review.json. Both are explicitly source-only reviews and grant no Apple runtime credit.

## Integration handoff

Integrate the required published source union and the narrow PBX bridge before the next matching build. Recompute every selected source hash from that exact frozen tree; obtain the actual source-before/after, Native/SDK, complete Products, UI copy, FileList and swiftc witnesses. Then prepare a new pinned common admission and activate only the reviewed fixed native-core plans against those products. No second App build is requested by this consumer.
