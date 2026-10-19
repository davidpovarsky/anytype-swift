# Pinkha on Anytype — Upstream Integration Hooks

Every modification to an upstream-owned file must be cataloged here:

| Upstream File | Pinkha Hook Purpose | Why Unavoidable | Approx Diff Size | Merge Risk | Gated By PinkhaRuntime |
|---------------|---------------------|-----------------|------------------|------------|------------------------|
| `Anytype.xcodeproj/project.pbxproj` | Link `PinkhaKit` package | Xcode target membership | ~10 lines | Low/Medium | N/A (Build config) |
| `ActiveSpaceManager.swift` (Phase 1) | Active-space lifecycle trigger `PinkhaBootstrapHook.handleSpaceActivated(spaceId:)` | Dispatch space schema bootstrap when space becomes active | ~2 lines | Low | Yes |
| `HomeWidgetsView.swift` (Phase 2 — Active) | Delegate home sections to `PinkhaHomeSectionsView` | Home layout composition | 6 lines | Low | Yes |
| `Modules/Loc/.../Workspace.xcstrings` (Phase 2 — Active) | Pinkha localization entries (en/he) | User-facing localized strings | ~19 keys | Very Low | N/A (Loc catalog) |
| `Modules/Loc/.../Strings.swift` (Phase 2 — Active) | `Loc.Pinkha` generated accessors | Type-safe localization access | ~40 lines | Very Low | N/A (Generated code) |
| `HomeBottomNavigationPanelView.swift` (Phase 3) | Context-sensitive create menu | Bottom panel action dispatch | ~10 lines | Medium | Yes |
| `HomeBottomNavigationPanelViewModel.swift` (Phase 3) | Creation policy delegation | Contextual child object creation | ~8 lines | Medium | Yes |
| `SpaceHubCoordinatorViewModel.swift` (Phase 4) | Startup routing & search routing | Space navigation coordinator | ~10 lines | Medium | Yes |
| `EditorPageView.swift` (Phase 4) | `.pinkhaEditorSession(...)` modifier | Document-scoped session lifecycle | ~3 lines | Low | Yes |
| `BlockViewModelBuilder.swift` (Phase 6/7) | Editor items decoration & quote model override | Top-of-document associations & source quote | ~10 lines | High | Yes |

## T2-L blocked-branch accounting — 2026-10-19

The mandatory native persistence gate failed before Kit/editor integration.
Consequently this branch makes **no final diff** to an upstream-owned editor,
navigation, Xcode project, localization or application bootstrap file. A
temporary `Container` registration in `PinkhaRuntime+App.swift` was removed
after the gate failed; the final file matches parent
`825437fb0f145ebe0430f27c3f099d0621246484`.

All retained T2-L changes are isolated to new Pinkha Torah storage/probe files,
focused PinkhaKit canonical-model additions, focused tests, the dedicated CI
workflow and evidence documentation. The planned Phase 3-7 hooks above were
not activated by this blocked assignment.

## iPad trial branch hooks — 2026-10-20

These hooks exist only on
`pinkha/torah-inspector-full-ipad-trial-2026-10-20`; they do not change the
prior blocked-branch accounting above.

| Upstream file | Trial hook | Why unavoidable | Merge risk | Safety boundary |
|---|---|---|---|---|
| `Anytype.xcodeproj/project.pbxproj` | Exact remote `TorahInspectorUI` product at the same immutable SHA used by PinkhaKit Core | The app target must import real Kit UI directly | Medium | Feature branch only; no stable branch merge |
| `EditorPageCoordinatorView(.Model).swift` | Own document-scoped Torah session, entry/presenter modifier and note navigation | Binds Space/object identity to actual editor lifecycle | Medium | Session is recreated per document/window; writes default OFF |
| `EditorPageView.swift`, `EditorPageModuleAssembly.swift`, `EditorPageViewModel(.Protocol).swift` | Pass the bounded session and install the shared native insertion handler | Host callbacks require the active editor's native block services | Medium | Quote insertion uses `setFocus: false`; generic insert defaults unchanged |
| `EditorPageController+DragNDrop.swift` | Separate `UTType.torahSource` external route | UIKit collection drop is the real editor insertion boundary | High | External `.copy`; existing `BlockDragConfiguration` remains `.move`; opt-in required |
| `BlocksOptionItem.swift`, `EditorPageBlocksStateManager.swift` | Single-block `קשר תורני` context action | Required block-scoped add/list/unlink entry | Medium | Hidden when no Torah session; exactly one selected block |
| `.github/workflows/torah-inspector-ipados27.yml` | Xcode 27 verification and unsigned separate-sandbox IPA | Stable Xcode 26.1 workflow must remain unchanged | Low | No signing keys or profile mutation; artifact requires user signing |

Pinkha-owned additions live under `Anytype/Sources/Pinkha/Torah/UI` and keep
provider composition, mutation gating, association preview, Notes bridging and
presentation state outside upstream editor files.

