# Torah object properties — implementation and owner gate, 2026-11-03

[נועם | Engineering] [MAIN_SESSION] — NORMAL mode, no delegation.

**Status: IMPLEMENTED / GITHUB_DEVICE_BUILD_REQUESTED. The owner approved the exact five-file patch and subsequently directed GitHub full compilation and IPA export. The original Properties sheet is connected to the downstream rows in source. Build/package results will be recorded from the existing dispatcher; UI/hardware acceptance remains separate.**

## Repository and authorization

- Repository: `C:\Users\DAVID\Code\anytype-swift`.
- Branch, unchanged: `pinkha/torah-associations-native-ux-persistence-localization-2026-10-20`.
- Start/end HEAD: `4554f0c027f5871cf64597e7662eb7c627110f46`.
- Live upstream/develop, rechecked before the approved application with `git ls-remote`: `e21834498cd6d8a85e91f69767caec793220a190`.
- Merge base: `d5650321577a209505a3277c8437b7608cff1cb9`.
- Baseline: five modified tracked files and 18 untracked status entries. Those changes were preserved. The baseline navigation-gesture change, architecture/data/schema/master-plan edits, Package.resolved and earlier proposal/evidence files were not edited.
- End state after owner approval: 19 modified tracked files and 28 untracked status entries, including the preserved baseline. Implementation and evidence remain unstaged. No commit, push, workflow dispatch, branch switch, signing, release, migration or personal-Space mutation occurred. No merge conflicts were introduced or resolved.
- Asana Stage 2 `1219881057229920` and project `1219604672449660` were read. No Asana writes occurred. The unified-Type/schema-v2 proposal remains outside this cycle.

The attached implementation brief preserves the prior-owner-approval rule. The owner's explicit `מאשר!` response approved this cycle's exact five-file patch. That approval is recorded in `docs/architecture/UPSTREAM_EXCEPTION_REGISTER.md`; earlier Stage 1 exceptions were not used as authorization.

## Implemented downstream code

1. `TorahDocumentPropertyProjection` reads canonical v2 records, requires the exact Space/object/document target and `.context` role, excludes note and quote associations, groups ref/topic/word separately and deduplicates canonical identities and stable IDs without modifying input. Input ordering and complete item metadata are retained.
2. Eligibility uses the three existing manifest mappings `chiddush/article/research`, exact Space identity and manifest v1. No type or property registration, template alteration or `writingKind` was added. Actual deployed Space Type IDs were not inspected on a device in this session.
3. `PinkhaTorahPropertiesModel`, section and row use the original `TagPropertyView` renderer with presentation-only `Property.Tag.Option` data, native regular property typography, 40% name width, minimum 48-point row, native placeholder/+N, localized names, full accessibility values and disabled editing. They do not create a native Property or Tag option in storage.
4. A downstream string catalog and `Loc.Pinkha.Torah` extension supply `מקור/ות`, `נושא`, `מילה / ערך` and English labels. Generated localization files are unchanged. Xcode resource compilation remains NOT_RUN.
5. `presentSearch(scope:initialCategory:host:)` sets category and clears query/state before presentation. Existing callers retain the document/block API and open References by default. Search category remains independent of association target.
6. The existing presentation modifier routes one shared session's search and Inspector bindings to either the editor or the original Properties sheet. The approved native hook now mounts the same modifier inside Properties. No new session, repository, search engine or picker is created. Actual nested-sheet behavior is NOT_RUN.
7. The existing References/Topics/Words control remains. In property mode, its preview displays only the selected kind; switching category clears its old query, and selected results retain their real kind and land in the matching projection.
8. The existing header now receives only projected context sources. Topics and words no longer appear as source chips. Its source-inspection action is retained.
9. Mutation actions validate the frozen target and live edit policy. Presenter cancellation prevents a delayed provider resolution from submitting a later write; rapid duplicate actions share one active request. Already-submitted native writes retain their frozen target and are not claimed to be retractable. Read-only snapshot reads remain allowed.
10. Picker previews synchronize from the same session snapshot. Stale Inspector chip activation resolves the current stored item by ID. Link/unlink continue through the existing serial canonical repository and its readback path; that storage implementation was not changed.
11. The connected Properties filter removes only the manifest-identified canonical property's ID/key from displayed sections, retaining ordinary and hidden native rows. When a live session has no cached manifest, the downstream model waits for identity resolution, with an error/retry state, rather than exposing unclassified raw JSON. The payload/property identity and permissions are never rewritten. Native runtime verification of this connected filter is NOT_RUN.

### Registration versus presentation versus persistence

| Layer | Actual result |
|---|---|
| Native Anytype registration | Existing three writing Types, templates and internal association property preserved; no new schema registration |
| Property UI | Three projected rows connected to the original list by the exact approved hooks; native execution pending |
| Persistence | Existing canonical v2 document payload and single-writer repository reused; no second store |
| Anytype Set queries | These projected rows are not independent queryable native Properties |

## Ownership and changed files

The Pinkha source/package/test and acceptance-harness changes are **DOWNSTREAM_OWNED**; these trees are absent from the verified live upstream tree. The five host files listed below are **UPSTREAM_OWNED** and changed only by the exact owner-approved patch. New localization resources are downstream-owned. No vendored, Heart, Go, protobuf or generated sources changed. The exception register was updated as downstream policy documentation.

Modified:

- `Anytype/Sources/Pinkha/Torah/UI/PinkhaDocumentSourcesFeaturedContent.swift`
- `Anytype/Sources/Pinkha/Torah/UI/TorahEditorHostModifier.swift`
- `Anytype/Sources/Pinkha/Torah/UI/TorahEditorSession.swift`
- `Anytype/Sources/Pinkha/Torah/UI/TorahSourcesSearchPresenter.swift`
- `Anytype/Sources/Pinkha/Torah/UI/TorahSourcesSearchView.swift`
- `AnyTypeTests/Pinkha/TorahAssociationNativeRepositoryTests.swift`
- `AnyTypeTests/Pinkha/PinkhaStage1AcceptancePreparationTests.swift`
- `PinkhaStage1Acceptance/Tests/PinkhaStage1AcceptanceUITests.swift`

Added:

- `Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahDocumentPropertyProjection.swift`
- `Modules/PinkhaKit/Tests/PinkhaKitTests/Torah/TorahDocumentPropertyProjectionTests.swift`
- `Anytype/Sources/Pinkha/Torah/UI/PinkhaTorahPropertiesModel.swift`
- `Anytype/Sources/Pinkha/Torah/UI/PinkhaTorahPropertiesSection.swift`
- `Anytype/Sources/Pinkha/Torah/UI/PinkhaTorahPropertyLocalization.swift`
- `Anytype/Sources/Pinkha/Torah/UI/Resources/PinkhaTorahProperties.xcstrings`
- This report, host proposal/preflight artifacts and `evidence/2026-11-03-object-properties/`.

## Exact approved and applied host exception

The [approved patch](../../architecture/TORAH_OBJECT_PROPERTIES_HOST_APPROVAL_2026-11-03.patch) is applied. Its SHA-256 is `d3b48f95133fd1d95cd9bec2779e3523da882473b80d7531bb19044b47df651a`. The [pre-edit blob preflight](../../architecture/TORAH_OBJECT_PROPERTIES_HOST_PREFLIGHT_2026-11-03.json) and [post-edit blobs](evidence/2026-11-03-object-properties/approved-host-blobs.json) retain exact identities. All five paths are **UPSTREAM_OWNED**:

| Path relative to `Anytype/Sources/PresentationLayer/TextEditor/EditorPage/` | Applied change and necessity |
|---|---|
| `EditorPageController.swift` | Pass its existing Torah session to the navigation helper |
| `Utils/EditorNavigationBarHelper/EditorNavigationBarHelper.swift` | Forward that session into the actual settings `UIHostingController`; give its existing More image the native localized accessibility label |
| `Views/Settings/ObjectSettingsMenu/ObjectSettingsMenuContainer.swift` | Forward the optional session to the original Properties coordinator; clear only its owned presentation on actual Properties dismissal |
| `Views/Settings/Properties/Coordinator/PropertiesListCoordinatorView.swift` | Forward the optional session to the original Properties view, preserving all ordinary routes |
| `Views/Settings/Properties/Views/ObjectFieldsView/ObjectPropertiesView.swift` | Mount the downstream model/rows/loading state and existing presentation modifier; apply the exact-ID display filter |

A downstream overlay cannot join the original view's private `LazyVStack` or filter its private native sections. The settings hosting controller is constructed separately in UIKit, so relying on the editor's SwiftUI environment would not establish session delivery. The patch forwards the existing instance through the actual composition path; default-nil parameters preserve other callers. No new global session registry is used.

Immediately before application, all five original blobs still matched the approved preflight and `git apply --check` passed. After application, the actual five-file Git diff matched the approved artifact exactly, with 28 insertions and 8 deletions. `git apply --reverse --check` passed. **Owner approval is explicit and recorded; no additional host hunk was added.**

Rollback: reverse only this exact host patch, after checking for later edits. Revert only the downstream files listed above and remove their new files individually if undoing the cycle. No stored-data migration or payload rollback is involved; preserve baseline dirty files and historical host exceptions.

## Executed verification

| Check | Status | Evidence |
|---|---|---|
| New projection suite | EXECUTED_PASS | 5 Swift Testing tests, including four 0/1/2/12 parameter cases; Windows Swift 6.3.3 |
| Projection + canonical + identity + payload suites | EXECUTED_PASS | 18 tests in four suites, zero failures |
| Swift syntax for integrated host, downstream UI and native/UI tests | EXECUTED_PASS | `swiftc -frontend -parse` after application; this is not SDK type checking |
| Exact approved host diff | EXECUTED_PASS | Actual five-file diff equals the approved artifact; no extra host changes |
| Host application and rollback applicability | EXECUTED_PASS | Pre-apply check and post-apply `git apply --reverse --check`, exit 0 |
| Applied tracked diff whitespace | EXECUTED_PASS | Whole-worktree `git diff --check`, exit 0 |
| Frozen sources unchanged; staged files absent | EXECUTED_PASS | Empty Services/protobuf diff and staged-file inventories |
| Local Apple toolchain availability | EXECUTED_PASS | `apple-doctor --json`: Windows, portable Swift only, `apple_sdk_available=false` |

Commands:

```powershell
swift test --package-path Modules/PinkhaKit --skip-update --filter TorahDocumentPropertyProjectionTests
swift test --package-path Modules/PinkhaKit --skip-build --filter 'Torah.*(Projection|Canonical|Identity|Payload)'
git apply --reverse --check -- docs/architecture/TORAH_OBJECT_PROPERTIES_HOST_APPROVAL_2026-11-03.patch
```

The initial shared-build attempt encountered a build-database lock. Only this session's identified Swift test processes were stopped; the subsequent compilation and tests completed. Existing deprecated replacement-API tests emitted warnings; no assertion was weakened. XCTest's zero-test banner is separate from the successful Swift Testing counts above.

Logs: [projection](evidence/2026-11-03-object-properties/projection-tests.log), [canonical regression](evidence/2026-11-03-object-properties/canonical-regression-tests.log), [syntax](evidence/2026-11-03-object-properties/swift-syntax.log), [proposed-host syntax](evidence/2026-11-03-object-properties/proposed-host-syntax.log), [worktree status](evidence/2026-11-03-object-properties/worktree-status.txt).

Post-approval evidence: [canonical regression](evidence/2026-11-03-object-properties/approved-host-canonical-regression-tests.log), [integrated syntax](evidence/2026-11-03-object-properties/approved-host-swift-syntax.log), [exact diff match](evidence/2026-11-03-object-properties/approved-host-diff-match.log), [whole-worktree whitespace](evidence/2026-11-03-object-properties/approved-host-diff-check.log). The earlier empty protected-diff snapshot describes pre-approval state only; the current approved diff is recorded separately.

## Native tests prepared, not executed

Added to the existing native repository suite: category/query/document-target reset; read-only reads and rejected writes; original/hidden property composition for all three mapped Types; unlink/new-session snapshot consistency; delayed-resolution cancellation and rapid duplicate taps.

Added `PinkhaTorahPropertiesAcceptanceUITests` to the existing downstream acceptance source, so it belongs to the existing UI target. It exercises the actual native menu and Properties sheet, all three Types, category reset, real provider link/unlink, row values, relaunch and preservation of original rows. The current Stage 1 class-selection commands do not automatically run this new class. On an authorized native test run, select it explicitly with:

```text
-only-testing:PinkhaStage1AcceptanceUITests/PinkhaTorahPropertiesAcceptanceUITests
```

It requires three fresh empty disposable objects in an isolated local-only simulator account. The existing native preparation test now supports `PINKHA_PROPERTIES_PREPARE=1`: it waits for all three real indexed Types, creates three additional fresh objects with the manifest's existing IDs/templates, validates their actual type/layout and captures their pre-existing visible native property labels before linking. It prints the resulting environment dictionary as `PINKHA_PROPERTIES_ACCEPTANCE_FIXTURE_JSON`. This optional preparation path is NOT_RUN; it does not run unless explicitly enabled and leaves the ordinary Stage 1 path unchanged. Prepare in English to match this UI scenario. Supply the real provider queries and expected display labels separately. Required UI test-runner environment:

```text
PINKHA_PROPERTIES_ISOLATED_SPACE_CONFIRMED=1
PINKHA_PROPERTIES_SPACE_ID=<disposable Space>
PINKHA_PROPERTIES_CHIDDUSH_ID=<fresh existing-Type object>
PINKHA_PROPERTIES_ARTICLE_ID=<fresh existing-Type object>
PINKHA_PROPERTIES_RESEARCH_ID=<fresh existing-Type object>
PINKHA_PROPERTIES_NATIVE_PROPERTY_LABELS=<captured JSON dictionary keyed by object ID>
PINKHA_PROPERTIES_SOURCE_QUERY=<real canonical provider query>
PINKHA_PROPERTIES_SOURCE_LABEL=<expected English display label>
PINKHA_PROPERTIES_TOPIC_QUERY=<real provider query>
PINKHA_PROPERTIES_TOPIC_LABEL=<expected English display label>
```

This test currently exercises English. RTL, Dynamic Type, narrow iPad/Stage Manager, native Tag option editing, read-only runtime, missing-provider behavior, Word selection, 12-item runtime overflow, Inspector transitions, cross-Space navigation, block links, offline/relaunch and physical hardware require further native execution. No UI screenshots, native ObjectShow readback, simulator acceptance, independent Roni verification, CI URL or device PASS was produced in this session. T2 multi-device sync remains BLOCKED.

## Remaining native verification and release gates

The exact five-file source approval gate is satisfied and its patch is applied. The subsequent owner instruction directs GitHub full compilation and IPA export; the required scoped source commit/push and existing manual dispatcher are now part of that requested work. Use `torah-inspector-ipados27.yml`, `route=ipa-only`, `require_full_acceptance=false`. A `[skip ci]` source commit preserves the prior owner stop on automatic simulator work. The source-approval reply alone was not treated as build authorization; the later explicit build instruction is the authority. No signing, release, merge or personal-Space mutation is authorized. The feature's runtime acceptance remains open until the real Properties/picker/persistence flow and original native routes are exercised.

Apple's [sheet binding contract](https://developer.apple.com/documentation/swiftui/view/sheet%28ispresented%3Aondismiss%3Acontent%3A%29) was checked. Routing only the owning host's binding is the implementation decision; reliable nested presentation remains a runtime acceptance requirement, not a conclusion from documentation.
