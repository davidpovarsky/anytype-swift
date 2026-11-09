# Universal native Torah properties — implementation and acceptance

Status: implementation published for focused Xcode verification; NOT COMPLETE. Physical iPad: `PENDING_DEVICE`.

- Branch: `codex/torah-native-derived-properties-20261103`.
- Baseline: `eee21ca08707137360a4dec5174df6133ebfbdaf`.
- Verified upstream develop: `9115c1c054e7ebf55e08e03c2dbb12871cc84450`; merge base `d5650321577a209505a3277c8437b7608cff1cb9`.
- Pinned Heart: `d98420b1113536afd08cde6de9a5816f6d27ffff` (unchanged).
- Exact revision-13 Heart patch SHA-256: `63fdf9ccab6398d3618bb989aa62dd83a536a1fb78033ffdfa23d2fbfaed8bfe`.
- Exact Swift protected integration diff SHA-256: `b9e758a4bd41e26fbff9c277349f018d0cdcff261535c961946cc2f52886bed8`.

| Gate | Verified status | Evidence |
|---|---|---|
| Go Page / Note / custom and infrastructure exclusion | EXECUTED_PASS | Native product + lifecycle and 48 contract tests |
| Native filtered membership, mixed Types, live add/remove | EXECUTED_PASS | Real generated middleware API; fresh local-only account |
| Fresh data reopen / rebuild | EXECUTED_PASS | Real SQLite lifecycle/recovery test |
| Space isolation and native Property IDs | EXECUTED_PASS | Real second Space; distinct fixed-key definition IDs; no membership leakage |
| Swift projection, identity and initial provisioning | EXECUTED_PASS | 14 portable Swift tests; does not establish UI behavior |
| Original Heart regressions | EXECUTED_PASS (953), SKIPPED (1) | state/basic/smartblock/detailservice/spaceindex; existing TestReplayTreeDumpShadow external-fixture opt-in skipped |
| Swift app picker, object-vs-Type attachment, empty rows and canonical routing | NOT_RUN_XCODE | Added real modified-Heart integration scenarios for Page/Note/custom |
| Original Swift UI, mixed Set columns and filters | NOT_RUN_XCODE | Added native UI scenarios, screenshots and accessibility attachments |
| New XCFramework / app / IPA marker and hashes | NOT_RUN | No IPA before focused Xcode gates |
| Physical iPad | PENDING_DEVICE | Owner acceptance script below |

## Implementation

Projection depends on real user-content object class/layout and lifecycle, not authoring Type IDs. The pinned engine resolves `resolvedLayout`; legacy `layout` remains a fallback. Cache integrity covers both layout keys and infrastructure predicates. Canonical context associations remain the only association payload. All derived values remain local/read-only and generic writes remain rejected.

The original ObjectRelationAdd RPC uses a narrow downstream attachment adapter for the three fixed native keys. It persists selection as original native RelationLinks, never a duplicate association payload or Tag Option. Original state filtering retains these definition links while still excluding derived values. Live ObjectShow injects empty placeholders and a private, local attachment list from those links. ObjectRelationDelete removes selection while preserving canonical data and indexed membership.

The existing object Properties panel exposes its original PropertyCreation picker for object scope. Type editing keeps the original recommended/featured/hidden semantics. The catalog never synthesizes recommendations from definition discovery. Object-specific selection overrides Type hiding for that object, survives Type changes, and drives the optional Sources header. The three original writing Types retain their provisioning defaults. Hierarchy Type classification is unchanged.

## Changed files and provenance

Per-file before/after hashes and exact protected hunks: `evidence/native-derived/8494cfb347/approval/revision-13/source-inventory.json` and `swift-integration.patch`. Complete 32-file pinned Heart inventory and patch are beside them. The original worktree and all pre-existing untracked research files are untouched.

| File | Ownership | Change |
|---|---|---|
| `.github/workflows/pinkha-native-derived.yml` | DOWNSTREAM_OWNED | Pin exact revision-13 patch and SHA; keep manual build/test routing. |
| `.github/workflows/pinkha-native-fast-ipa.yml` | DOWNSTREAM_OWNED | Pin exact revision-13 patch and SHA; keep manual build/test routing. |
| `.github/workflows/pinkha-native-ipa-fast.yml` | DOWNSTREAM_OWNED | Pin exact revision-13 patch and SHA; keep manual build/test routing. |
| `AnyTypeTests/Pinkha/TorahNativeDerivedProductIntegrationTests.swift` | DOWNSTREAM_OWNED | Real Page/Note/custom picker, isolated attachment, empty rows and mixed Set fixtures; correct stale baseline test API calls. |
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
| `Tools/PinkhaNativeDerived/build_native_ipa.py` | DOWNSTREAM_OWNED | Add tests-only gate and focused policy run before any device packaging. |
| `Tools/PinkhaNativeDerived/validate_native_engine.py` | DOWNSTREAM_OWNED | Expose focused projection contract validation through the existing native workspace runner. |
| `Tools/TorahNativeDerivedSpike/integration/heart_test.go` | DOWNSTREAM_OWNED | Supply actual basic-document layout in the native SQLite fixture. |
| `Tools/TorahNativeDerivedSpike/integration/production_engine_test.go` | DOWNSTREAM_OWNED | Actual middleware Page/Note/custom, object selection, mixed subscriptions, Space isolation and lifecycle safety. |
| `Tools/TorahNativeDerivedSpike/prepare_heart_integration.py` | DOWNSTREAM_OWNED | Generate exact original-RPC attachment hooks, native metadata filtering and local placeholders. |
| `Tools/TorahNativeDerivedSpike/projection_test.go` | DOWNSTREAM_OWNED | Reverse obsolete Page rejection; cover Note/custom and explicit classification. |

| `Tools/PinkhaNativeDerived/build_custom_heart.py` | DOWNSTREAM_OWNED | Verify the new marker in every thin Mach-O architecture of every XCFramework binary. |
| `docs/architecture/UPSTREAM_EXCEPTION_REGISTER.md` | DOWNSTREAM_OWNED | Record current owner authorization, exact protected diffs and verified/open gates. |
| `approval/revision-13/native-heart-integration.patch` | GENERATED_REVIEW_ARTIFACT | Complete exact 32-file patch against the unchanged pinned Heart. |
| `approval/revision-13/native-heart-integration.json` | GENERATED_REVIEW_ARTIFACT | Per-file before/after hashes and exact patch SHA. |
| `approval/revision-13/swift-integration.patch` | GENERATED_REVIEW_ARTIFACT | Exact nine protected Swift integration diffs. |
| `approval/revision-13/source-inventory.json` | GENERATED_REVIEW_ARTIFACT | Ownership and before/after hashes for changed repository files. |
| `UNIVERSAL_NATIVE_TORAH_PROPERTIES_REPORT.md` | DOWNSTREAM_OWNED | Verified acceptance matrix, file summary, provenance and pending device script. |

## Validation commands

Commands and exact source hashes are recorded in `evidence/universal-properties-r13/{go-contract,native-product-v7,native-product-final,native-regression}/results.json`. Native commands use the existing `Tools/PinkhaNativeDerived/validate_native_engine.py` with the fresh pinned `heart-universal-r13` checkout, verified Tantivy 1.0.6 and Go 1.26.5. No owner Spaces or historical documents were opened.

`swift test --package-path Modules/PinkhaKit --filter "TorahDocumentPropertyProjectionTests|TorahNativeSchemaProvisionerTests"` — 14 tests passed; log `evidence/universal-properties-r13/swift-portable-v2.log`.

`git apply --check` against the untouched pinned Heart checkout — passed. Python compilation and Swift syntax preflight — passed, not counted as native app acceptance.

## Physical iPad script — PENDING_DEVICE

1. Install the new unsigned IPA after signing it locally. Create a fresh test Space.
2. Create Page P1, Page P2 and a Note. Before selection, verify no forced Torah rows or Sources header.
3. On P1, Properties → Add Property: choose מקור/ות, נושא, מילה / ערך. Verify empty native rows and canonical picker routing. P2 must remain unchanged.
4. Add reference/topic/word. Tap a source chip to read it; use the separate compact + to add more. Add 12 references and open +N overflow.
5. Edit Page Type, add a native definition, hide and reveal it. Verify the same ID and normal effect on P1/P2 without changing Note Type.
6. Create Page-only, Note-only and Page + חידוש + custom-Type Sets. Enable columns and apply source/topic/word membership filters; verify actual matching objects and live add/remove.
7. Switch חידוש → Page → חידוש. Verify only selected/Type-configured properties appear, object-specific Sources persists, and associations remain.
8. Reopen the app offline and check native values, selected empty rows and filters. Check a second Space and a read-only object; canonical/order storage must stay hidden while הורה remains available.

No migrations, historical backfill, signing/release, T2 changes, default-branch merge or personal-Space mutation were introduced. Rollback is the reverse of the recorded source diff on this isolated branch; no data rollback/migration is required or provided.
