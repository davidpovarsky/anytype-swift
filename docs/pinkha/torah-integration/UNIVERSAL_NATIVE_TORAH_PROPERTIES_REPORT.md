# Universal native Torah properties — implementation and acceptance

Status: implementation published for focused Xcode verification; NOT COMPLETE. Physical iPad: `PENDING_DEVICE`.

- Branch: `codex/torah-native-derived-properties-20261103`.
- Baseline: `eee21ca08707137360a4dec5174df6133ebfbdaf`.
- Verified upstream develop: `9115c1c054e7ebf55e08e03c2dbb12871cc84450`; merge base `d5650321577a209505a3277c8437b7608cff1cb9`.
- Pinned Heart: `d98420b1113536afd08cde6de9a5816f6d27ffff` (unchanged).
- Current revision-14 Heart patch SHA-256: `fb96818eb57bd9e0be8da90a11831bcccc7ca8e72cc0a4e9a065500feb7cc077`. Historical revision-13 receipts retain their original hash.
- Exact Swift protected integration diff SHA-256: `ef03244203b78b77135855addb510c4b73835a0cdf84387546bbddb0fc2259a7` (nine unchanged production hooks; updated manual scope input).

| Gate | Verified status | Evidence |
|---|---|---|
| Go Page / Note / custom and infrastructure exclusion | EXECUTED_PASS | Native product + lifecycle and 48 contract tests |
| Native filtered membership, mixed Types, live add/remove | EXECUTED_PASS | Real generated middleware API; fresh local-only account |
| Fresh data reopen / rebuild | EXECUTED_PASS | Real SQLite lifecycle/recovery test |
| Space isolation and native Property IDs | EXECUTED_PASS | Real second Space; distinct fixed-key definition IDs; no membership leakage |
| Swift projection, identity and initial provisioning | EXECUTED_PASS | 14 portable Swift tests; does not establish UI behavior |
| Original Heart regressions | EXECUTED_PASS (953), SKIPPED (1) | state/basic/smartblock/detailservice/spaceindex; existing TestReplayTreeDumpShadow external-fixture opt-in skipped |
| Swift app picker, object-vs-Type attachment, empty rows and canonical routing | EXECUTED_PASS | Real Xcode native integration 42740484502: 1 passed, 0 failed, 0 skipped; Page/Note/custom actual native objects and filters |
| Original Swift UI, mixed Set columns and filters | EXECUTED_FAIL (2), EXECUTED_PASS (1) | Compact header add/document search/overflow passed. Native row picker locator and Page property lookup require focused UI follow-up |
| New XCFramework, exact patch and every binary architecture | EXECUTED_PASS | Runs 42682425225 and 42687999643; newly built revision-13 framework |
| App and new unsigned IPA hashes / extension IDs | NOT_RUN | No IPA before focused Xcode gates |
| Physical iPad | PENDING_DEVICE | Owner acceptance script below |

## Implementation

Projection depends on real user-content object class/layout and lifecycle, not authoring Type IDs. The pinned engine resolves `resolvedLayout`; legacy `layout` remains a fallback. Cache integrity covers both layout keys and infrastructure predicates. Canonical context associations remain the only association payload. All derived values remain local/read-only and generic writes remain rejected.

The original ObjectRelationAdd RPC uses a narrow downstream attachment adapter for the three fixed native keys. It persists selection as original native RelationLinks, never a duplicate association payload or Tag Option. Original state filtering retains these definition links while still excluding derived values. Live ObjectShow injects empty placeholders and a private, local attachment list from those links. ObjectRelationDelete removes selection while preserving canonical data and indexed membership.

The existing object Properties panel exposes its original PropertyCreation picker for object scope. Type editing keeps the original recommended/featured/hidden semantics. The catalog never synthesizes recommendations from definition discovery. Object-specific selection overrides Type hiding for that object, survives Type changes, and drives the optional Sources header. The three original writing Types retain their provisioning defaults. Hierarchy Type classification is unchanged.

The main future upstream-sync risks are the original Heart RPC/state hooks that retain native property-definition RelationLinks, and the Swift BaseDocument/property-panel connection points. Custom association logic remains in downstream modules. A future Heart upgrade must review its native attachment representation before replaying the recorded narrow hooks; this change does not introduce an upgrade or migration path.

## Changed files and provenance

Current per-file before/after hashes and exact protected hunks: `evidence/native-derived/8494cfb347/approval/revision-14/source-inventory.json` and `swift-integration.patch`. Complete 35-file pinned Heart inventory and patch are beside them. Historical revision-13 evidence is immutable. The original worktree and all pre-existing untracked research files are untouched.

| File | Ownership | Change |
|---|---|---|
| `.github/workflows/pinkha-native-derived.yml` | DOWNSTREAM_OWNED | Pin exact revision-13 patch and SHA; preflight iPad, verify fresh framework reuse and cache focused Xcode build outputs; keep manual routing. |
| `.github/workflows/pinkha-native-fast-ipa.yml` | DOWNSTREAM_OWNED | Pin exact revision-13 patch and SHA; keep manual build/test routing. |
| `.github/workflows/pinkha-native-ipa-fast.yml` | DOWNSTREAM_OWNED | Pin exact revision-13 patch and SHA; keep manual build/test routing. |
| `AnyTypeTests/Pinkha/TorahNativeDerivedProductIntegrationTests.swift` | DOWNSTREAM_OWNED | Real Page/Note/custom picker, isolated attachment, empty rows and mixed Set fixtures; correct stale baseline test API calls. |
| `AnyTypeTests/Pinkha/TorahAssociationNativeRepositoryTests.swift` | DOWNSTREAM_OWNED | Repair obsolete fixture to use the existing native adapter/store probe; preserve canonical write/read/remove assertions. |
| `AnyTypeTests/Pinkha/TorahNativeUIParityTests.swift` | DOWNSTREAM_OWNED | Reverse obsolete Page/Note exclusions and assert discovery does not attach properties. |
| `Anytype/Sources/Models/Documents/Document/BaseDocument.swift` | SHARED_INTEGRATION | Build rows from actual native object attachments and Type lists. |
| `Anytype/Sources/Pinkha/Torah/Properties/PinkhaTorahNativePropertyCatalog.swift` | DOWNSTREAM_OWNED | No synthesized attachments; real live Type lists and stale-fetch protection. |
| `Anytype/Sources/Pinkha/Torah/Properties/PinkhaTorahPropertyPolicy.swift` | DOWNSTREAM_OWNED | Normal object/Type/Set target policy, library discovery, selection-driven header. |
| `Anytype/Sources/Pinkha/Torah/UI/PinkhaDocumentMetadataRowModel.swift` | DOWNSTREAM_OWNED | React to actual Sources attachment and property publications. |
| `Anytype/Sources/Pinkha/Torah/UI/PinkhaTorahPropertiesModel.swift` | DOWNSTREAM_OWNED | Use shared normal-document policy for canonical editing. |
| `Anytype/Sources/Pinkha/Torah/UI/TorahNativePropertyViews.swift` | DOWNSTREAM_OWNED | Preserve canonical editing and object-selection removal permissions. |
| `Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/FeaturedRelations/FeaturedPropertiesBlockViewModel.swift` | SHARED_INTEGRATION | Refresh optional source header from actual parsed properties. |
| `Anytype/Sources/PresentationLayer/TextEditor/EditorPage/Views/Settings/Properties/Views/ObjectFieldsView/ObjectPropertiesView.swift` | SHARED_INTEGRATION | Reuse original picker in object panel; empty-state and attachment controls. |
| `Anytype/Sources/PresentationLayer/TextEditor/EditorPage/Views/Settings/Properties/Views/ObjectFieldsView/ObjectPropertiesViewModel.swift` | SHARED_INTEGRATION | Object-scoped picker, normal-document rows and selected-property removal. |
| `Anytype/Sources/PresentationLayer/TextEditor/EditorPage/Views/Settings/Properties/Views/TypePropertiesView/TypePropertiesView.swift` | SHARED_INTEGRATION | Identify original Type Add Property control for native accessibility testing. |
| `Anytype/Sources/PresentationLayer/TextEditor/EditorPage/Views/Settings/Properties/Views/TypePropertiesView/TypePropertiesViewModel.swift` | SHARED_INTEGRATION | Allow normal native definition removal from Type recommendations. |
| `Anytype/Sources/PresentationLayer/TextEditor/Set/Views/Popups/RelationsSettings/RelationCreation/PropertyCreationView.swift` | SHARED_INTEGRATION | Localized lookup failure and retry in original property picker. |
| `Anytype/Sources/PresentationLayer/TextEditor/Set/Views/Popups/RelationsSettings/RelationCreation/PropertyCreationViewModel.swift` | SHARED_INTEGRATION | Object additions use object RPC; hidden reveal exclusions and verified catalog diagnostics. |
| `Anytype/Sources/PresentationLayer/TextEditor/Set/Views/Popups/RelationsSettings/SetPropertiesViewModel.swift` | SHARED_INTEGRATION | Allow native column/Type-property removal without a writing-Type gate. |
| `Modules/PinkhaHeart/engine/index.go` | DOWNSTREAM_OWNED | Project all normal document classes; inspect resolved layout and reject infrastructure. |
| `Modules/PinkhaHeart/engine/recovery_cache.go` | DOWNSTREAM_OWNED | Include every object-class eligibility field in integrity proof. |
| `Modules/PinkhaHeart/torah/binding.go` | DOWNSTREAM_OWNED | Bind Space and canonical property without authoring-Type IDs. |
| `Modules/PinkhaHeart/torah/projection.go` | DOWNSTREAM_OWNED | Remove fixed writing-Type requirement; require explicit normal-document classification. |
| `Modules/PinkhaHeart/torah/properties.go` | DOWNSTREAM_OWNED | Register private local attachment presentation metadata. |
| `Modules/PinkhaHeart/transport/import.go` | DOWNSTREAM_OWNED | Use the universal binding for canonical import remapping. |
| `Modules/PinkhaKit/Sources/PinkhaKit/Schema/TorahNativePropertySchema.swift` | DOWNSTREAM_OWNED | Expose the private local attachment-key constant; keep writing-Type defaults. |
| `Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahDocumentPropertyProjection.swift` | DOWNSTREAM_OWNED | Universal document-Type availability plus shared layout/lifecycle eligibility. |
| `Modules/PinkhaKit/Tests/PinkhaKitTests/Torah/TorahDocumentPropertyProjectionTests.swift` | DOWNSTREAM_OWNED | Universal and infrastructure/lifecycle boundary assertions; preserve hierarchy classification. |
| `PinkhaStage1Acceptance/Tests/PinkhaStage1AcceptanceUITests.swift` | DOWNSTREAM_OWNED | Drive original Page/Note/custom object and Type pickers, canonical values, reopen, mixed Set and accessibility evidence. |
| `Tools/PinkhaNativeDerived/build_native_ipa.py` | DOWNSTREAM_OWNED | Tests-only runtime gates; real configuration selection and content-verified source timestamp cache for focused reruns. |
| `Tools/PinkhaNativeDerived/rerun_original_ui.py` | DOWNSTREAM_OWNED | Verify unchanged production inputs, reuse cached app/test fixture, compile only UI runner and resume failed methods. |
| `Tools/PinkhaNativeDerived/package_evidence.py` | DOWNSTREAM_OWNED | Include exported accessibility text alongside original xcresults, JSON and screenshots. |
| `Tools/PinkhaNativeDerived/validate_native_engine.py` | DOWNSTREAM_OWNED | Expose focused projection contract validation through the existing native workspace runner. |
| `Tools/TorahNativeDerivedSpike/integration/heart_test.go` | DOWNSTREAM_OWNED | Supply actual basic-document layout in the native SQLite fixture. |
| `Tools/TorahNativeDerivedSpike/integration/production_engine_test.go` | DOWNSTREAM_OWNED | Actual middleware Page/Note/custom, object selection, mixed subscriptions, Space isolation and lifecycle safety. |
| `Tools/TorahNativeDerivedSpike/prepare_heart_integration.py` | DOWNSTREAM_OWNED | Generate exact original-RPC attachment hooks, native metadata filtering and local placeholders. |
| `Tools/TorahNativeDerivedSpike/projection_test.go` | DOWNSTREAM_OWNED | Reverse obsolete Page rejection; cover Note/custom and explicit classification. |
| `Tools/PinkhaNativeDerived/build_custom_heart.py` | DOWNSTREAM_OWNED | Verify the new marker in every thin Mach-O architecture of every XCFramework binary. |
| `docs/architecture/UPSTREAM_EXCEPTION_REGISTER.md` | DOWNSTREAM_OWNED | Record current owner authorization, exact protected diffs and verified/open gates. |
| `approval/revision-13/native-heart-integration.patch` | GENERATED_REVIEW_ARTIFACT | Complete exact 32-file patch against the unchanged pinned Heart. |
| `approval/revision-13/native-heart-integration.json` | GENERATED_REVIEW_ARTIFACT | Per-file before/after hashes and exact patch SHA. |
| `approval/revision-13/swift-integration.patch` | GENERATED_REVIEW_ARTIFACT | Exact nine protected Swift integration diffs plus the manual dispatcher artifact input. |
| `approval/revision-13/source-inventory.json` | GENERATED_REVIEW_ARTIFACT | Ownership and before/after hashes for changed repository files. |
| `UNIVERSAL_NATIVE_TORAH_PROPERTIES_REPORT.md` | DOWNSTREAM_OWNED | Verified acceptance matrix, file summary, provenance and pending device script. |
| `Tools/PinkhaNativeDerived/create_disposable_ipad.py` | DOWNSTREAM_OWNED | Select a compatible available iPad/runtime and boot before expensive compilation. |
| `Tools/PinkhaNativeDerived/install_verified_heart.py` | DOWNSTREAM_OWNED | Reinstall only this task's exact new revision-13 artifact after file, patch, source-inventory and thin-architecture verification. |
| `.github/workflows/torah-inspector-ipados27.yml` | SHARED_INTEGRATION | Pass the existing manual source-run input to exact artifact verification; no automatic triggers added. |

## Validation commands

Commands and exact source hashes are recorded in `evidence/universal-properties-r13/{go-contract,native-product-v7,native-product-final,native-regression}/results.json`. Native commands use the existing `Tools/PinkhaNativeDerived/validate_native_engine.py` with the fresh pinned `heart-universal-r13` checkout, verified Tantivy 1.0.6 and Go 1.26.5. No owner Spaces or historical documents were opened.

`swift test --package-path Modules/PinkhaKit --filter "TorahDocumentPropertyProjectionTests|TorahNativeSchemaProvisionerTests"` — 14 tests passed; log `evidence/universal-properties-r13/swift-portable-v2.log`.

`git apply --check` against the untouched pinned Heart checkout — passed. Python compilation and Swift syntax preflight — passed, not counted as native app acceptance.

## Physical iPad script — PENDING_DEVICE

1. Install the new unsigned IPA after signing it locally. Create a fresh test Space.
2. Create Page P1, Page P2 and a Note. Before selection, verify no forced Torah rows or Sources header.
3. On P1, Properties → Add Property: choose מקור/ות, נושא, מילה / ערך. Verify empty native rows and canonical picker routing. P2 must remain unchanged.
4. Add reference/topic/word. Tap a source chip to read it; use the separate compact + to add more. Add 12 references and open +N overflow.
5. Edit Page Type, add a native definition, hide and reveal it. Verify the same ID. P1 keeps its explicit object attachment; P2 follows the Type visibility. Note Type is unchanged.
6. Create Page-only, Note-only and Page + חידוש + custom-Type Sets. Enable columns and apply source/topic/word membership filters; verify actual matching objects and live add/remove.
7. Switch חידוש → Page → חידוש. Verify only selected/Type-configured properties appear, object-specific Sources persists, and associations remain.
8. Reopen the app offline and check native values, selected empty rows and filters. Check a second Space and a read-only object; canonical/order storage must stay hidden while הורה remains available.

No migrations, historical backfill, signing/release, T2 changes, default-branch merge or personal-Space mutation were introduced. Rollback is the reverse of the recorded source diff on this isolated branch; no data rollback/migration is required or provided.

## First Xcode attempt — 42682425225

Native framework build **PASS** on Xcode 26.3, exact patch `63fdf9ccab6398d3618bb989aa62dd83a536a1fb78033ffdfa23d2fbfaed8bfe`. Marker verified separately in device arm64, simulator x86_64 and simulator arm64. The subsequent simulator setup **FAILED** because the old first-available-runtime selector paired an M5 iPad with iOS 18.5. No Swift app tests ran and no IPA was built. Selection now uses compatible installed pairs, newest runtime first, before native compilation. That first run did not preserve its framework, so the second run rebuilt it from the same exact revision-13 source.

## Second Xcode attempt — 42687999643

Source commit `2476b44098c874e463ccbb60fbefaaa115073fee`. Compatible disposable iPad boot **PASS**. Exact custom Heart build and all architecture marker verification **PASS**. Newly built framework uploaded as `Pinkha-Universal-Verified-Heart-r13` before the app gate. Current patch/source/file/architecture hashes must all match before any focused reuse; revision-12/stock artifacts are rejected. Xcode `build-for-testing` **FAILED** in the test target after 66 minutes: the new universal fixture called an internal Services memberwise initializer, and existing policy/repository test fixtures referenced obsolete APIs/classes. No native XCTest or UI test ran. Fixtures now use the public Page/Note keys, the actual ObjectDetails/MockBaseDocument APIs, and the existing native repository adapter. The canonical isolation suite is included in the focused policy gate. The next run reuses only this exact new Heart artifact. A branch-scoped Xcode build cache now preserves compilation outputs across focused corrections; it does not cache simulator account data, test results, or acceptance receipts. Actual Xcode test configurations are selected by BlueprintName, excluding generated cached copies. All runtime gates remain mandatory.

## Focused rerun — 42707755876

Exact framework artifact reinstall **PASS**, including every thin-architecture hash. The run was stopped early during app preparation to strengthen the existing compact source-add UI scenario: it now actually taps `+`, verifies the original document-scoped search, captures it, reopens the document and checks overflow separately. No native test or UI PASS is attributed to this cancelled attempt. All validation continues through GitHub CLI/API.

## Native runtime attempt — 42710042670

Source `661fbf3541950235868309c37f09165c5bc6d844`; real Xcode 26.3 test-host compilation **PASS** with the exact verified revision-13 Heart. Actual iPad Pro 13-inch M5 simulator, iOS 26.2. Native API suite: **0 passed, 1 failed, 0 skipped**. Three empty native rows were present, but their first snapshots reported `isEditable == false`; a later eventually condition timed out. The previous helper omitted its call site, so the exact later condition is not inferred. Policy and original app UI suites did not run; no IPA exists. Raw xcresult, summaries, full native test log and framework/install receipts are retained in this run artifact.

The fixture now waits for real participant-derived editing permissions and editable rows, retains the opened Type documents for the full scenario, and records the exact file/line for any future timeout. Page/Note/custom/mixed-Set checks run before the older writing-Type scenarios. Production permission checks are unchanged. Evidence is uploaded before the large build-cache save; exported accessibility text is included. Cache timestamp restoration is permitted only after matching each current source file SHA-256 to the cached source-input manifest, so changed source remains a normal build input. These changes have syntax/helper checks only until the next real Xcode execution.

## Focused native attempt — 42727270837

Source `2345c5769608a8edc140148c4ea04aa0dc1c2ce2`; exact revision-13 framework reused from run 42687999643. Real app/test host compilation passed. The native test body took 51 seconds; the full job took 99 minutes, dominated by build/setup/cache transfer. Page/Note/custom discovery, object-only empty rows and canonical picker routing, unchanged other objects/Type lists, real native filtered membership and explicit Type recommendation assertions all executed without reported failure. Original writing rows, Type editors and hide/reveal also advanced without issues. The one compound test still FAILED: its old global filter expected only one document although all four correct linked documents now matched, and its Type-switch condition expected no native rows despite object-level attachment metadata. Policy/repository and original UI gates were not run; no IPA was produced.

Only the downstream integration fixture changes in this correction: assert the exact four global members and separately the writing-Type-scoped member; derive post-switch expected presentation from actual object attachments plus visible Type configuration. Type recommendation cleanup now verifies all original lists were restored. App/Heart/protected integration sources are unchanged. Reuse the existing exact framework and content-verified DerivedData cache; do not rerun already passed Go, engine regressions or portable Swift checks. The failed compound native fixture is required to prepare the new disposable account for the still-unproven original UI gate.

## Native API and policy acceptance — 42740484502

Source `dee60eef8395a8a92998f08d7e7eb66701e7febc`: actual native API **1 passed / 0 failed / 0 skipped**; policy/canonical isolation **19 tests passed** (23 invocations including parameterized cases), no failure or skip. Original UI: **1 passed / 2 failed / 0 skipped**. The compact Sources + opened the actual document-scoped search, and overflow passed; screenshots are retained. The first failure searched for an Other container although the real canonical picker was open and its identifier propagated to the text field. The second failure displayed the original property picker with a real Retry diagnostic, so its cold lookup still requires investigation. Page/Note universal native API behavior is now genuinely proven, but UI acceptance and unsigned IPA remain open.

The restored cache still caused substantial module work: the native project log compiled only a small set of targets, while the subsequent workspace UI build rebuilt many package modules. Focused continuation therefore reuses the accepted simulator app and unchanged compiled fixture directly. A generated copy of the downstream UI test project removes the app build dependency and builds only the XCTest UI runner, guarded by equality of every production source input with the accepted cache. It runs only the two failed UI methods; the 19 policy tests and compact-header case are retained as REUSED_VERIFIED_PASS. The compiled fixture is invoked solely to prepare a new disposable account/Space on a new simulator, without rebuilding or claiming additional coverage. Passive simulator logging and disposable lookup-state diagnostics are retained if it fails. Original app/project/Heart sources are unchanged.

## Startup read-only maintenance correction — revision 14

[נועם | DEV] [MAIN_SESSION]

Run [42751586692](https://github.com/davidpovarsky/anytype-swift/actions/runs/42751586692) proved reuse of the accepted simulator app: 5,627 identical production inputs and a generated Xcode graph containing only the UI test target, with no application/package compilation. Fresh fixture preparation passed. Both remaining UI methods failed; no new UI PASS is claimed. Passive native logs identified the cause: the three actual fixed-key definitions returned `readOnlyValue=false`, and the catalog correctly rejected them. The existing Heart `ReadonlyRelationsFixer` startup maintenance rewrote all read-only Tag/Status definitions, including these immutable derived definitions.

Revision 14 adds a two-line wrapper around the original query in `space/internal/components/migration/readonlyfixer/relationsfixer.go`. Downstream `pinkha_torah.go` excludes only the three exact fixed keys with matching bundled source identity and Tag format. Ordinary properties, display-name collisions, errors and all other maintenance remain unchanged. This prevents rewriting fresh native definitions; it does not repair historical false flags, introduce a new migration, or backfill existing Spaces.

Focused validation already passed against the exact new patch: **13 readonlyfixer tests, 0 skips**, and **1 real generated-middleware two-process restart test, 0 skips**. The second process waits until an ordinary same-name read-only Tag becomes writable, proving original maintenance ran, then verifies all three native flags/IDs and native search still agree. Test account data and seed stay in automatically deleted temporary files; no owner Space is used. Receipts are `evidence/universal-properties-r14/readonly-startup/results.json` and `native-readonly-restart-v2/results.json`. Those receipts record pre-commit HEAD plus exact tested source hashes; unchanged sources are not rerun just to update HEAD.

Retained verified passes: Go contract 48, projection/presentation/import 6, original engine 953 (one existing external-fixture opt-in skip), portable Swift 14, native policy/canonical isolation 19, and original compact-header add/search/overflow 1. The new Go implementation requires a new XCFramework and real native integration plus the two still-unproven UI methods. No other suite is rerun. The accepted r13 framework is used only to compare byte-identical interface header timestamps for cached Swift compilation; all runtime binaries must come from the new r14 build and differ from r13.

Additional changed downstream files: `Tools/TorahNativeDerivedSpike/integration/readonlyfixer_test.go` (startup exclusion and collision guards); `readonly_restart_test.go` (actual process restart); `Tools/PinkhaNativeDerived/reuse_matching_framework_headers.py` (hash-verified headers only, never old binaries). Existing app build tooling snapshots framework inputs, retains the 19/1 passes with unchanged Swift dependency guards, compiles the UI runner alone using the same dependency cache, and records reused counts separately. UI fixtures terminate the previous test app and avoid opening the same document twice. Manual dispatcher adds explicit `all`, `failed-ui` and `readonly-startup` scopes without automatic triggers. Framework identity moves to r14 in the three downstream workflows. The nine protected production Swift hooks remain unchanged; only the existing manual dispatcher input changes in the protected aggregate diff.

Status at publication: focused Go restart correction **PASS**; new r14 Xcode framework/native/UI gates **PENDING**; unsigned IPA **NOT_BUILT**; physical iPad **PENDING_DEVICE**. No completion is claimed before the remaining gates pass.

The final device build reuses the existing accepted DerivedData dependency checkouts and hash-matched inputs. Available GitHub caches contain simulator products only, so device-SDK compilation and linking are necessary; simulator binaries are never repackaged as a device app. No test is repeated by this route. The IPA receipt also records the actual app executable SHA-256.

## Real r14 framework; build timeout before tests — 42760706087

Exact r14 Heart framework **PASS**: device arm64 and simulator arm64/x86_64, marker and per-slice SHA verified. Actual device archive binary SHA `3010c265109cec4cbbaa957c86daa933b5c95e814cc0c428c287bc6873ef2144`; simulator archive SHA `e6fc5627b27bddc7d5d98e21dfaa3cc99e841652245d032bc57c6f741b1a77ea`. Saved as `Pinkha-Universal-Verified-Heart-r14` in run 42760706087. All 13 interface/header metadata files matched r13 and their timestamps were preserved; new native binaries were unchanged. Heart compilation took 65m19s. The combined job hit its 150-minute limit during Swift package compilation (Services), before ANY native or UI test executed. Cache save was cancelled too. No test failure or new functional PASS is claimed.

The log proves broad package recompilation despite restoring source timestamps and the old cache. Exact accepted Swift products remain available in cache 0eca3054d4d0468edebb1b72916914b5884d4a79. Inspection of the accepted Xcode link command proves the static Go archive is linked into dynamic `ProtobufMessages.framework`, not the main app executable. The next focused route uses the exact accepted Xcode linker command and existing object list to relink ONLY this runtime framework against new r14 Heart. All app/module/native-test/config source bytes and every native header/module-map must match the accepted build; the accepted app binary hashes and sealed bundle are checked. It copies the new runtime to all embedded app/test copies and renews only simulator ad-hoc seals. No Swift compiler, new project generation, production signing or release action is performed by this relink step. Original UI runner compilation remains one target. Actual native API and the two unproven UI methods must still pass; 19 policy tests and the header test remain reused.

`Tools/PinkhaNativeDerived/relink_verified_simulator.py` and `evidence/universal-properties-r14/relink/accepted-simulator-link.json` record this narrowly scoped build-product reuse and exact original Xcode command. The default all-tests route remains the normal Xcode build. No protected production source changes accompany this validation correction. Physical device remains PENDING_DEVICE.

## Focused relink preparation — 42779251181

Exact r14 artifact reinstall **PASS**; no Go or Swift compiler ran. Preparation stopped before touching the app because actions/checkout fetched only HEAD and the accepted comparison commit was absent (`fatal: bad object dee60eef...`). No native/UI test ran. The original accepted run's exact cache (dee60eef...) is now selected directly. A narrowly scoped `git fetch --no-tags --depth=1 origin <accepted-sha>` supplies only the comparison tree, without changing HEAD. Errors are exported immediately as JSON. Reused framework artifacts are no longer repacked/reuploaded, and an unchanged cache is not saved when preparation stops before successful relinking. The final device receipt records the actual Go carrier `ProtobufMessages.framework` hash/marker as well as the main app executable hash. All production sources and r14 native patch remain unchanged.

Run 42784365803 passed exact accepted source comparison, all native header ABI hashes, the three accepted app hashes, deep code-seal verification and cached Swift object presence. It stopped before linking because the response-file guard mistook the literal `@rpath/ProtobufMessages.framework/ProtobufMessages` install name for a response file. The classifier now accepts only `@/` absolute file arguments. No runtime source, native framework or compiled Swift input changes; no test or compiler ran in this preparation attempt. No unchanged cache or framework was reuploaded.

## Actual r14 runtime and native integration pass — 42786374694

Relink **PASS**, no Swift application/package compiler invoked. Exact new archive `e6fc5627b27bddc7d5d98e21dfaa3cc99e841652245d032bc57c6f741b1a77ea` appears in the real linker map. The new marker is present in actual `ProtobufMessages.framework`; both app and native-test embedded copies have SHA `ec563a8fb21189d3d46827b50615ed7249ae4b41ed0ee661146b3b4e66ef0b65`. Accepted Swift objects were unchanged, original app hashes/seal and native header ABI were verified. **Actual native API 1 passed / 0 failed / 0 skipped** with this runtime. Policy 19/header 1 remain reused.

UI runner build succeeded with one target and no app dependencies. No UI test method ran: simulator FrontBoard reported the runner bundle unknown during launch (XCTest represents this infrastructure error as one failed runner). Continue using this accepted new app and existing compiled UI runner, without Go, app relink, or app/package compilation. Explicitly install the actual runner `.app` via `simctl install`, verify its registered bundle container, export the actual xctestrun configuration, and run only the two unproven methods. Fresh native fixture invocation is setup for the new disposable simulator, not a new API coverage claim. No product source changed. UI/IPA remain pending; physical iPad PENDING_DEVICE.

## Original UI methods executed — 42792867898

Accepted r14 app and unchanged compiled UI runner reused; no app/Go/UI compilation. Explicit runner installation/registration **PASS**. Both actual UI methods ran and failed (0/2/0): their source-value assertions searched StaticText, while the original native rows expose values as Buttons. Accessibility proves the actual source row `Genesis 1:1`, topic `Creation`, human word label and the source after Page reopen; bootstrap reports ready with no false-readonly registration errors. These are observations/partial scenario proof, not complete UI-case PASS claims. The correction is test-only: exact-label matching within the named property row's value geometry (Button or StaticText), with Set labels scoped to the actual table. The row scope prevents a background/header chip from satisfying the assertion. Native word extraction uses the same original value elements. The next attempt compiles only the changed UI target; original app/native runtime/fixture and all prior unaffected passes remain reused.

Run 42798231887 reused the new app and prepared fresh disposable data. The changed UI source could not compile because the generated UI-only project still contained an unused Anytype subproject reference/original scheme, causing SwiftPM to demand its absent native input. No UI method ran. The generator now removes that unused file reference, proxy/dependency objects and old scheme from its generated copy only. Local structural smoke verified one independent UI scheme and no foreign project, with original project bytes unchanged. No app/Go build or framework download is added.

## Document UI phases proved; resume only remaining Type/Set interactions — 42801263371

Independent UI runner compilation **PASS**. The actual source/topic/word native-row assertions, canonical picker interaction and offline relaunch succeeded across all three writing documents and Page/Note/custom documents. Normal-document optionality, selected empty rows and selected Sources header assertions advanced successfully. Both compound methods then failed at Type-page navigation: the original Type page exposes `x24/More` and a direct `Properties, <count>` button, while the helper waited for document-only `More`. Actual Type-page accessibility is retained. No production defect is inferred from that locator failure; the whole old methods remain failed.

Preserve those executed document phases; do not repeat their full loops. The next two methods cover only the unproven original Type property lists/pickers, 12-chip Properties presentation and real native Set fields/membership/filter edits. Type navigation uses its existing Properties control; Set opening waits for its actual table. A few canonical picker writes prepare fresh writing-Set members; they are setup, not repeated document/reopen acceptance. The mixed Set uses real P1 Page/Note/custom objects already linked by the native fixture. Exact-label queries now filter before inspecting geometry, avoiding expensive traversal of unrelated accessibility elements. All checks remain on the accepted app/new native runtime; only the UI target recompiles. Existing successful phases are identified separately from the remaining method counts.

Run 42812211845 verified all three writing-Type native property lists (article/chiddush/research screenshots). The next unrelated 12-source Properties navigation hit an automation main-thread-busy snapshot; that replay is unnecessary because the unchanged header overflow/add already passed. Retain those passes and resume only Set interaction. The normal Type picker displayed the actual definitions, but a global label query tapped the underlying Type sheet while the foreground search result was offscreen. It now searches each of the three names in the original foreground picker and selects only a hittable exact-label Button, then verifies picker dismissal. No new app/Go build or product change. Whole two methods still failed; only the named completed phases are retained.


## Retain normal Type-picker phases; Set-only resume — 42817488590

All three normal Type picker search/select/dismiss phases (Page, Note, custom) advanced to the Set-settings call. Preserve those completed phases; neither Type nor document loops are selected again. The remaining methods failed at Set settings (the test used the localization key Fields, but actual English Loc.fields is Properties) and fresh writing-Set word-picker setup. The helper now clears actual previous search content before entering a new query and logs its exact query/result hierarchy on failure. Product inputs are unchanged. Original app/new r14 runtime, native fixture bundle, policy and prior UI passes stay reused. Only the UI runner compiles. Artifact service CreateArtifact timed out five times; this was a transport failure, not storage quota. Compact receipts and failure hierarchies are now printed in the job log as fallback. Whole Set UI gates and IPA remain pending.
