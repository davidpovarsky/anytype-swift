# Pinkha upstream exception register

As of 2026-10-22, no new upstream-file edits have been authorized by this policy update. Existing divergences are LEGACY_UNREVIEWED, not permissions.

Future exception: original upstream SHA, exact path/hunk, approved owner instruction/reference, why a downstream adapter fails, focused regression tests, review date and rollback. No agent self-approval.

## 2026-10-25 — TorahInspectorKit revision pin

- Upstream baseline: `upstream/develop` at `d5650321577a209505a3277c8437b7608cff1cb9`; upstream `Anytype.xcodeproj/project.pbxproj` blob `8c3872c414a5f22cd6b05d2dbb99ec64a33b13b0`.
- Exact authorized hunk: `Anytype.xcodeproj/project.pbxproj`, change only the `XCRemoteSwiftPackageReference "TorahInspectorKit"` revision from `59b6f4629da6a7edd625de0ae004d04dbbc037de` to `a2fa3a528ac2bccfa00ed206d7954083077fc847`.
- Owner approval: `Anytype_Torah_Inspector_Embedded_Search_Implementation_Prompt_2026-10-25.md`, sections 0, 3 and 6, explicitly requires the new Kit commit, both immutable revision literals, CI and two pushed feature commits.
- Necessity: Xcode resolves the app's direct `TorahInspectorUI` product from this project-level pin. A downstream adapter or the separate `Modules/PinkhaKit/Package.swift` pin cannot select that product revision.
- Focused regression gates: TorahInspectorKit package/UI suite; PinkhaKit package suite; `TorahAssociationNativeRepositoryTests`, `TorahNativeUIParityTests`, `TorahSearchLayoutTests`, and `TorahSearchLayoutScreenshotTests`; unsigned device build.
- Review date: 2026-10-25.
- Rollback: restore the one revision literal above and the matching downstream package/workflow literals to `59b6f4629da6a7edd625de0ae004d04dbbc037de`; do not revert any other upstream hunk.

## 2026-10-26 — Stage 1 Pinkha RTL hooks H1–H7 and H9

- Approval: explicit owner instruction in the 2026-10-26 Codex task approving only H1–H7 and H9 from `docs/pinkha/torah-integration/STAGE_1_CONSOLIDATED_UPSTREAM_APPROVAL_REQUEST_2026-10-26.md`, subject to the stated legacy-data safeguards. H8 and H10 were not covered by that instruction; their later, separate approval is recorded below.
- Baseline: `upstream/develop` at `d5650321577a209505a3277c8437b7608cff1cb9`; every blob below was revalidated immediately before editing.
- H1: `Modules/Services/Sources/Models/Block/BlockInformation/BlockInformationConverter.swift`, blob `f90bf2c39869ec4d0a835422af6e9f5f2f0b4f4f`; initialize the protobuf struct from `information.fields` instead of an empty dictionary.
- H2: `Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/TextBlockContentConfiguration.swift`, blob `4d8279bf06b9440569d15a9c0856d33b5993d147`; add the default-`nil` `pinkhaWritingContext` configuration seam.
- H3: `Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/TextBlockViewModel.swift`, blob `d825db1fa99d1d85385f3038df23883f51877a4a`; resolve and pass the gated Pinkha context when a text row is configured.
- H4: `Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/TextBlockContentView.swift`, upstream blob `ae90a1f4a91e0204c4d11d2464113a729f9f1f12`, approved current legacy-context blob `aba80ccd797160822bbeee2e102a30c9b8c7786a`; invoke the Pinkha UIKit adapter immediately after host styling.
- H5: `Anytype/Sources/PresentationLayer/Common/UIKit/TextView/Views/TextViewWithPlaceholder.swift`, blob `d53f8c26d3636e777fa76c65380fea6279fd68fa`; synchronize placeholder alignment when `textAlignment` changes.
- H6: `Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/TextBlockActionHandler.swift`, blob `861843b0c1962e37ccd86b2a10cf60ac05e9d001`; schedule the downstream automatic-direction coordinator from the existing text-change snapshot. The coordinator writes only for an existing automatic marker or an ID proven new by `SessionCreatedBlockIdsStorage`; marker-less legacy edits are display-only.
- H7: `Anytype/Sources/ServiceLayer/Block/BlockActionHandler/BlockActionHandler.swift`, blob `4fdcc6f3bd8346b145946bac32b0d6b8c2ef1abd`; after `setAlign` succeeds, record explicit Pinkha alignment. Metadata errors are caught downstream and never roll back or fail the already-persisted alignment.
- H9: `Anytype/Sources/PresentationLayer/Common/SwiftUI/Navigation/PageNavigationBackButton.swift`, blob `0659188a73f335c9419d9bc10db03d7d0c53dd32`; apply one semantic RTL image flip and replace the hard-coded accessibility label with `Loc.back`.
- Necessity: the host owns text configuration, UIKit styling, text-change/alignment actions and the visible Back button. Pinkha policy, gating, metadata encoding and persistence orchestration remain in `Modules/PinkhaKit` and `Anytype/Sources/Pinkha/RTL`.
- Focused regression gates: fields round-trip including unknown fields; new/session-created versus ambiguous legacy; explicit left/center/right reopen; metadata-failure ordering; attributed/typing paragraph style; placeholder/caret/IME/selection/undo/focus; normal Anytype no-op; LTR/RTL Back icon and localized accessibility.
- Review date: 2026-10-26.
- Rollback: revert only H1–H7 and H9 and remove their downstream Pinkha RTL adapters/markers. No migration or bulk user-data rewrite exists; do not touch legacy upstream divergences.

## 2026-10-26 — Stage 1 Pinkha RTL hooks H8 and H10

- Approval: explicit owner instruction in the 2026-10-26 Codex task approving exactly the corrected H8 and H10 unified diffs in `docs/pinkha/torah-integration/STAGE_1_CONSOLIDATED_UPSTREAM_APPROVAL_REQUEST_2026-10-26.md`. No neighboring or additional upstream hunk is authorized.
- Baseline: `upstream/develop` at `d5650321577a209505a3277c8437b7608cff1cb9`; all three pre-edit blobs were revalidated immediately before editing.
- Pre-commit refresh: `upstream/develop` advanced to `b781a7734ecd70813cf19b10a5262ed193bb1e2b`; every H1–H10 target path retained the exact approved upstream blob, so no approval context changed and no rebase/merge was performed.
- H8: `Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/TextBlockContentView.swift`, approved current H4-context blob `55c30c6a1805fbb75d846618f4b6037e512a1795`; invoke `PinkhaTextBlockLeadingMarkerAdapter` immediately after host leading-view recreation. Resulting H4+H8 worktree blob: `b196243f7a7aa8b7bcb9dae5e732158bf378e672`.
- H8 exclusion: `Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/Views/TextBlockIconVIew.swift` remains byte-identical at upstream/current blob `12334d6de523490f494dc030e5153807a34128fe`.
- H10a: `Anytype/Sources/PresentationLayer/Common/SwiftUI/NavigationView/FullScreenSwipeNavigationController.swift`, blob `0ee63a6623cab25b318ac97c9313eb19855cb1eb`; normalize progress through the bridge and reject only the custom full-screen recognizer under the exact Pinkha-RTL gate. Resulting blob: `95272eaf390fb5ccfd89ad6a6a0591d6d5e27b16`.
- H10b: `Anytype/Sources/PresentationLayer/Common/SwiftUI/NavigationView/AnytypeNavigationView.swift`, blob `a7755dbf09680be2116b7523f82cc733c4ee42cc`; pass the effective SwiftUI layout direction and current navigation item to the bridge. Resulting blob: `aae70d912429b2f55d47758cb3b40d1c35ac78c2`.
- Necessity: H8 must run after row reuse recreates the private numbered marker. H10 must run where the host owns the competing full-screen recognizer and where SwiftUI exposes the active app-language layout direction. Pinkha gating, public right-edge configuration, restoration and list-marker policy remain downstream in `Anytype/Sources/Pinkha/RTL`.
- Focused regression gates: 1/9/10/19/20/99/100 markers, narrow nested row geometry, RTL/LTR and cell reuse; public right-edge recognizer identity/delegate preservation; custom-recognizer exclusion only for Pinkha RTL; runtime direction/document/root/Inspector controls; iPhone/iPad simulator matrix in Hebrew and English; ordinary Anytype and Pinkha-LTR controls.
- Review date: 2026-10-26.
- Rollback: remove only the five-line H8 call, the H10 progress wrapper/begin guard/update call, and the corresponding downstream adapters. The original Anytype full-screen behavior and marker rendering then return without stored-data migration.
