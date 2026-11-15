# Object Properties add-button typography

- Owner direction: correct typography of the document Add Property button. This is distinct from historical Asana task descriptions; no runtime fix or broader task completion is claimed.
- Worktree: `C:/Users/DAVID/Code/anytype-swift-property-typography-20261115`; branch `codex/anytype-property-typography-20261115`; uncommitted base `9bf4c558bd621ddf9ce44decba3a48d19b20ad7f`.
- Fresh upstream `develop` advertised `9115c1c054e7ebf55e08e03c2dbb12871cc84450`; merge base `d5650321577a209505a3277c8437b7608cff1cb9`; target path exists upstream and is upstream-owned.
- The object button uses `Loc.addProperty`, `model.onAddPropertyTap`, and accessibility identifier `torah-object-add-property`; the exact Hebrew phrase was not found in source localization search. The existing button uses `Text(verbatim: Loc.addProperty).anytypeStyle(.uxBodyRegular)` as its label. Visibility, action, identifier, padding and inherited foreground remain.
- Native Type Properties rows use `.uxBodyRegular`. DesignKit defines the font as Inter regular, 17pt; the native helper applies its 24pt line height and kerning. This is a contextual source comparison, not proof of rendered Hebrew glyph metrics. This narrowly documented styled Text preserves the invariant intent of design-system typography; AnytypeText was rejected in review because it forces primary foreground and adds vertical padding.
- Production file Git blob: `cce9e8c1378bebcbd890fab2f647098dbbbf0a18`; raw SHA-256 `abe00a3edb00cf1f78878d0dd5c91ed867bc2d793c3ed3a11f114324ff761f08`.
- Verification: `git diff --check` PASS; source comparison PASS. Build, tests, UI rendering, RTL, Dynamic Type, simulator and physical device: NOT_RUN. Existing P0 and Stage 2 acceptance remain open.
- Rollback: restore the original implicit button label in this hunk; do not reset the worktree or revert unrelated changes. No commit, stage, push, build, CI or personal-Space test.
