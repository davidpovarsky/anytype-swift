# Pinkha upstream exception register

As of 2026-10-22, no new upstream-file edits have been authorized by this policy update. Existing divergences are LEGACY_UNREVIEWED, not permissions.

Future exception: original upstream SHA, exact path/hunk, approved owner instruction/reference, why a downstream adapter fails, focused regression tests, review date and rollback. No agent self-approval.

## 2026-10-25 — TorahInspectorKit revision pin

- Upstream baseline: `upstream/develop` at `d5650321577a209505a3277c8437b7608cff1cb9`; upstream `Anytype.xcodeproj/project.pbxproj` blob `8c3872c414a5f22cd6b05d2dbb99ec64a33b13b0`.
- Exact authorized hunk: `Anytype.xcodeproj/project.pbxproj`, change only the `XCRemoteSwiftPackageReference "TorahInspectorKit"` revision from `59b6f4629da6a7edd625de0ae004d04dbbc037de` to `0a026e1c0b7d572c5affea6d31bda7b8ba0d4646`.
- Owner approval: `Anytype_Torah_Inspector_Embedded_Search_Implementation_Prompt_2026-10-25.md`, sections 0, 3 and 6, explicitly requires the new Kit commit, both immutable revision literals, CI and two pushed feature commits.
- Necessity: Xcode resolves the app's direct `TorahInspectorUI` product from this project-level pin. A downstream adapter or the separate `Modules/PinkhaKit/Package.swift` pin cannot select that product revision.
- Focused regression gates: TorahInspectorKit package/UI suite; PinkhaKit package suite; `TorahAssociationNativeRepositoryTests`, `TorahNativeUIParityTests`, `TorahSearchLayoutTests`, and `TorahSearchLayoutScreenshotTests`; unsigned device build.
- Review date: 2026-10-25.
- Rollback: restore the one revision literal above and the matching downstream package/workflow literals to `59b6f4629da6a7edd625de0ae004d04dbbc037de`; do not revert any other upstream hunk.
