# Pinkha on Anytype — Ported Code Registry

This document records code ported or adapted from `davidpovarsky/pinkha` and `TorahInspectorKit`.

## 1. TorahInspectorKit (implemented in T1)
- **Source**: `https://github.com/davidpovarsky/TorahInspectorKit.git`
- **Revision**: `e8aefc626350c8ee0df9daf8d7de7e1dcd0ea418`
- **Component**: `TorahInspectorCore`
- **Target**: Dependency of `Modules/PinkhaKit`
- **Role**: Inspector text/relationship models, provider protocols and repository.
- **Scope**: Core only. `TorahInspectorUI` is deferred to T3.

## 2. PinkhaTorahCore (implemented/adapted in T1)
- **Source Repository**: `davidpovarsky/pinkha`
- **Source Branch**: `torah-ux-knowledge-tab`
- **Source Commit**: `24e074d5557dba632d36dbb71fda8cf9acb8d3ac`
- **Selected Components**:
  - Provider models/protocols/registry -> `Modules/PinkhaKit/Sources/PinkhaKit/Torah/`
  - Sefaria transport/providers -> `Modules/PinkhaKit/Sources/PinkhaKit/Torah/Providers/`
  - Source hierarchy -> `Modules/PinkhaKit/Sources/PinkhaKit/Torah/Hierarchy/`
  - Workspace and Inspector repository factory -> `Modules/PinkhaKit/Sources/PinkhaKit/Torah/`
- **Adaptations**:
  - Removed Leaf and SQLite dependencies from the provider/core layer.
  - Replaced provider metadata caches with discardable actor-backed in-memory caches.
  - Reused current Kit text/relationship types instead of copying legacy models.
  - Preserved canonical provider identities, raw payloads and rich source metadata.

The paths listed in the previous legacy specification did not exist on the
pinned target and should be read as planned legacy paths, not evidence of a
completed port. The authoritative per-file mapping is
`docs/pinkha/torah-integration/SOURCE_PORT_LEDGER.md`.
