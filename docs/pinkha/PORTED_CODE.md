# Pinkha on Anytype — Ported Code Registry

This document records code ported or adapted from `davidpovarsky/pinkha` and `TorahInspectorKit`.

## 1. TorahInspectorKit
- **Source**: `https://github.com/davidpovarsky/TorahInspectorKit.git`
- **Component**: `TorahInspectorCore`
- **Target**: Dependency of `Modules/PinkhaKit`
- **Role**: Reference parsing, book catalog, inspector data protocols.

## 2. PinkhaTorahCore (Selected Logic)
- **Source Repository**: `davidpovarsky/pinkha`
- **Source Branch**: `torah-ux-knowledge-tab`
- **Source Commit**: `05d7c931974108e4655a6d0581096c0775f388de`
- **Selected Components**:
  - `ProviderProtocols.swift` -> `PinkhaKit/Torah/ProviderProtocols.swift`
  - `SefariaClient.swift` -> `PinkhaKit/Torah/SefariaClient.swift`
  - `SefariaProviders.swift` -> `PinkhaKit/Torah/SefariaProviders.swift`
  - `TorahReferenceUtil.swift` -> `PinkhaKit/Torah/TorahReferenceUtil.swift`
  - `Hierarchy/TorahSourceHierarchy.swift` -> `PinkhaKit/Hierarchy/TorahSourceHierarchy.swift`
- **Adaptations**:
  - Replaced Leaf / LeafID with Anytype ObjectID.
  - Replaced custom SQLite association table with `TorahAssociationRepository` (Anytype Object property & block fields).
  - Preserved reference normalization, Sefaria API interaction, and hierarchy navigation.
