# Pinkha on Anytype — Architecture Specification

## 1. System Topology and Separation of Concerns

Pinkha is built as a clean product layer directly above Anytype iOS. Anytype's storage, middleware (Heart), sync, block editor, and database/dataview capabilities are preserved intact.

```text
┌────────────────────────────────────────────────────────┐
│                   Anytype Upstream                     │
│  - Object Engine & Middleware (Heart)                  │
│  - CRDT Sync & Network Stack                           │
│  - Protobuf Block Schema                               │
│  - TextEditor & Focus Architecture                     │
│  - Dataviews, Sets & Collections                       │
│  - Discussions & Search Interactors                    │
└─────────────────────────┬──────────────────────────────┘
                          │ (Narrow, explicit hooks only)
                          ▼
┌────────────────────────────────────────────────────────┐
│               Pinkha Downstream Layer                  │
│                                                        │
│  Modules/PinkhaKit (Portable Domain & Models):         │
│  - PinkhaRuntime feature gate                          │
│  - PinkhaSpaceManifest & Schema Migrator               │
│  - TorahAssociationRepository & Semantic Models        │
│  - Hierarchy & Sparse-Rank Order Policy                │
│                                                        │
│  Anytype/Sources/Pinkha (App & UI Integration):        │
│  - PinkhaSpaceBootstrapService                         │
│  - PinkhaHomeSectionsView & Navigation Tree            │
│  - Primary Writing Types (חידוש, מאמר, מחקר)          │
│  - Document-Scoped Editor Session & Search             │
│  - Torah Source Quote Blocks & Inspector Host          │
└────────────────────────────────────────────────────────┘
```

## 2. Inviolable Architectural Invariants

1. **No Heart Modification**: No custom forks of `anyproto/anytype-heart`, no custom protobuf schemas, and no newly invented native block protobuf types.
2. **Canonical Data Store**: User-created documents, navigation hierarchy, and Torah associations reside solely in Anytype objects and block fields. SQLite is never used as an authoritative store for user-created data.
3. **Editor Stability**: Anytype's block-row identity, first-responder lifecycle, and focus architecture remain untouched. Source insertion and typing must never cause keyboard dismissals or row-binding destruction.
4. **Clean Downstream Packaging**:
   - `Modules/PinkhaKit`: Portable package with no UI dependencies or old Rust engine components.
   - `Anytype/Sources/Pinkha`: All UI and coordinator integrations placed under this dedicated directory.
5. **Reversibility**: Every hook into upstream code is gated by `PinkhaRuntime.enabled`.

## 3. Phase 2 Hierarchy & Home Architecture

- **Canonical Hierarchy Separation**: Navigation parentage is never derived from generic links (`ObjectDetails.links`, backlinks, `createdInContext`). The canonical parent is mapped via `manifest.parentPropertyKey` and sibling ordering via `manifest.orderPropertyKey`.
- **Sparse-Rank Ordering**: Siblings are ordered using sparse numeric ranks (initial step: 1000.0). Midpoints are computed for insertions. Dense ranks (< 0.001) trigger isolated sibling rebalancing without affecting descendant nodes. Unranked items fall back deterministically to localized title and objectId tie-breakers.
- **Root Document Canonical Ordering**: Root writing documents (חידוש, מאמר, מחקר) use the same canonical sibling ordering model as folders, receiving `nextAppendRank` computed against existing root siblings.
- **Node-Kind Agnostic Sibling Reordering**: Sibling reordering (Move Up / Move Down) operates uniformly across both folders and documents within any shared parent or root level.
- **Unbounded Hierarchy Querying**: Hierarchy search and subscription queries utilize Anytype's native unbounded marker (`limit: 0`) rather than arbitrary caps, allowing complete tree rendering at scale (>1000 items).
- **Cycle Prevention**: Cycle detection is enforced at the domain/mutation layer in `PinkhaHierarchyMutationValidator` and safely handled by `PinkhaHierarchyBuilder`. Self-parenting (`A.parent = A`) and descendant parenting (`A -> B -> A` or deep cycles) are strictly rejected.
- **Safe Folder Deletion Re-Ranking**: Direct children of a deleted folder are reparented to the deleted folder's parent via `PinkhaHierarchyOrdering.planSafeFolderDeletion`. Children are assigned sparse ranks strictly greater than existing destination siblings while preserving their relative order, preventing rank collisions and orphaned documents.
- **Move Destination Disambiguation**: The move destination picker displays full ancestor breadcrumbs (`snapshot.parentPathString(for:)`) and sorts folders alphabetically by full hierarchical path (`snapshot.pathString(for:)`), resolving ambiguity between folders with identical names in different subtrees.
- **Design System Iconography**: Hierarchy rows and context menus use Anytype design system assets (`.CustomIcons.folder`, `.CustomIcons.pencil`, `.CustomIcons.trash`, `.X24.Arrow.up`, `.X24.Arrow.down`, `.X18.redAttention`) rather than unstyled system glyphs.
- **Error Visibility**: All hierarchy and document mutations enforce `do/catch` error handling, logging failures to `EventLogger(category: "Pinkha")` and presenting native feedback alerts to the user.
- **Home Integration Hook**: Home layout delegates section rendering to `PinkhaHomeSectionsView` via a narrow hook in `HomeWidgetsView.swift` when `PinkhaRuntime.enabled` is true. The native wallpaper, header, SpaceInfo, bottom glass navigation, and iPad readable content width are preserved intact.

