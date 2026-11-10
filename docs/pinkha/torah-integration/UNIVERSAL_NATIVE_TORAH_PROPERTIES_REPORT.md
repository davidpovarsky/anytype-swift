# Universal native Torah properties — implementation and acceptance

Status: implementation published for focused Xcode verification; NOT COMPLETE. Physical iPad: `PENDING_DEVICE`.

- Branch: `codex/torah-native-derived-properties-20261103`.
- Baseline: `eee21ca08707137360a4dec5174df6133ebfbdaf`.
- Verified upstream develop: `9115c1c054e7ebf55e08e03c2dbb12871cc84450`; merge base `d5650321577a209505a3277c8437b7608cff1cb9`.
- Pinned Heart: `d98420b1113536afd08cde6de9a5816f6d27ffff` (unchanged).
- Exact revision-13 Heart patch SHA-256: `63fdf9ccab6398d3618bb989aa62dd83a536a1fb78033ffdfa23d2fbfaed8bfe`.
- Exact Swift protected integration diff SHA-256: `d8c06111e16d5d88f034b7144869cacf23bc18e12b6e578cdc3ab427f0295c84`.

| Gate | Verified status | Evidence |
|---|---|---|
| Go Page / Note / custom and infrastructure exclusion | EXECUTED_PASS | Native product + lifecycle and 48 contract tests |
| Native filtered membership, mixed Types, live add/remove | EXECUTED_PASS | Real generated middleware API; fresh local-only account |
| Fresh data reopen / rebuild | EXECUTED_PASS | Real SQLite lifecycle/recovery test |
| Space isolation and native Property IDs | EXECUTED_PASS | Real second Space; distinct fixed-key definition IDs; no membership leakage |
| Swift projection, identity and initial provisioning | EXECUTED_PASS | 14 portable Swift tests; does not establish UI behavior |
| Original Heart regressions | EXECUTED_PASS (953), SKIPPED (1) | state/basic/smartblock/detailservice/spaceindex; existing TestReplayTreeDumpShadow external-fixture opt-in skipped |
| Swift app picker, object-vs-Type attachment, empty rows and canonical routing | EXECUTED_FAIL — native API gate | Run 42710042670 compiled; 0 passed / 1 failed. Initial row editability and an unnamed timeout failed before Page/Note scenarios. Rerun pending |
| Original Swift UI, mixed Set columns and filters | NOT_RUN_XCODE | Added native UI scenarios, screenshots and accessibility attachments |
| New XCFramework, exact patch and every binary architecture | EXECUTED_PASS | Runs 42682425225 and 42687999643; newly built revision-13 framework |
| App and new unsigned IPA hashes / extension IDs | NOT_RUN | No IPA before focused Xcode gates |
| Physical iPad | PENDING_DEVICE | Owner acceptance script below |

## Implementation

Projection depends on real user-content object class/layout and lifecycle, not authoring Type IDs. The pinned engine resolves `resolvedLayout`; legacy `layout` remains a fallback. Cache integrity covers both layout keys and infrastructure predicates. Canonical context associations remain the only association payload. All derived values remain local/read-only and generic writes remain rejected.

The original ObjectRelationAdd RPC uses a narrow downstream attachment adapter for the three fixed native keys. It persists selection as original native RelationLinks, never a duplicate association payload or Tag Option. Original state filtering retains these definition links while still excluding derived values. Live ObjectShow injects empty placeholders and a private, local attachment list from those links. ObjectRelationDelete removes selection while preserving canonical data and indexed membership.

The existing object Properties panel exposes its original PropertyCreation picker for object scope. Type editing keeps the original recommended/featured/hidden semantics. The catalog never synthesizes recommendations from definition discovery. Object-specific selection overrides Type hiding for that object, survives Type changes, and drives the optional Sources header. The three original writing Types retain their provisioning defaults. Hierarchy Type classification is unchanged.

The main future upstream-sync risks are the original Heart RPC/state hooks that retain native property-definition RelationLinks, and the Swift BaseDocument/property-panel connection points. Custom association logic remains in downstream modules. A future Heart upgrade must review its native attachment representation before replaying the recorded narrow hooks; this change does not introduce an upgrade or migration path.

## Changed files and provenance

Per-file before/after hashes and exact protected hunks: `evidence/native-derived/8494cfb347/approval/revision-13/source-inventory.json` and `swift-integration.patch`. Complete 32-file pinned Heart inventory and patch are beside them. The original worktree and all pre-existing untracked research files are untouched.

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
