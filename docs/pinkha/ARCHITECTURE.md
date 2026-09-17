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
