# Pinkha on Anytype — Phased Migration Plan

This plan tracks the 10 implementation phases defined in `הוראות.md`:

- **Phase 0 — Baseline Audit**: Verified git SHAs, verified unsigned device IPA build, created documentation suite. *(Complete)*
- **Phase 1 — Pinkha Foundation**: `PinkhaKit` package, `PinkhaRuntime`, `PinkhaSpaceManifest`, bootstrap service, default types (`חידוש`, `מאמר`, `מחקר`), default templates, unit tests. *(In Progress)*
- **Phase 2 — Hierarchy + Home**: `pinkha.parent`, `pinkha.order`, sparse ranking, cycle prevention, `PinkhaHomeSectionsView`, folder tree widget integration.
- **Phase 3 — Document Types + Creation**: Primary writing types on Home, bottom `+` create menu override, contextual child document creation.
- **Phase 4 — Document Search & Bottom Bar**: In-editor document search overlay, live block index, search result navigation.
- **Phase 5 — Torah Association Storage**: Anytype-backed document & block associations, Torah models ported from Pinkha.
- **Phase 6 — Document / Block Association UI**: Top-of-document associations bar, block action menu integration.
- **Phase 7 — Inspector & Source Insertion**: Document-scoped inspector session, read-only Torah source quote block, insertion anchor.
- **Phase 8 — Sources Tree & Books Tree**: Torah source hierarchy tree, Book Folders mapped to Anytype Sets/Dataviews.
- **Phase 9 — Editor RTL**: Per-block `pinkha.textDirection.v1` (`auto`, `rtl`, `ltr`), directional text-view configuration.
- **Phase 10 — Legacy Data Migration**: Importer mapping old Pinkha SQLite databases to Anytype Objects and Blocks.
