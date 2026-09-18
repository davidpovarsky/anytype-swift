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

