# Shared sharing/invitation language audit

**No new production language defect was proven in this bounded source audit.** The exact current source is `a72f2e1ee3032cc1170c3ab07a9ae6b0eefa2dfd`. No product/test change is warranted from this finding, and no sharing operation or runtime acceptance occurred.

## Shared source chain

The existing Native root presents `PinkhaSpaceMembersView` and `PinkhaJoinSpaceView` from one shared `PinkhaSharing` source file. Both use explicit `bundle: .module` for UI labels. Model failures are English **keys** passed through `LocalizedStringKey(problem)`; the role/status rows also use localized keys. The confirmation helper resolves role names with `NSLocalizedString(..., bundle: .module)` and retains localized String-interpolation formats.

The target processes its own `Resources`, declares English fallback, and contains complete English/Hebrew tables. All **50 distinct required keys** have nonempty entries in both languages; all interpolated String-placeholder counts agree. The package has no `Loc` dependency and needs no new bridge on the inspected evidence. Member names/identity fallback text are user data, not untranslated UI copy. No private values were read.

The current view is SHA256 `55b9913dd3bd8c8eb712944a87d6bde5cae98bd4aa1bf8bc3d553a83e3fb820b`, Git blob `bfc0259edf2e74ddbdc59d9cb5175653a59aa61d`. `source-manifest.json` binds the four fresh primary source/resource bodies and narrowly reused current model/root/test evidence. `key-coverage.json` lists every required key and its source use.

## Existing acceptance boundary

The existing selector is `PinkhaAnyNativeUITests/NativeLaunchTests/testNativeSharingInvitationConfirmationCancellationAndColdReopen` with its original **900-second** allowance. It exercises create/revoke Cancel/Confirm and cold reopen. It launches with `(he,en)` / `he_IL` and accepts either Hebrew or English labels, including the rendered title. Those predicates preserve their original functional scope but do not establish exact language choice or both mixed App/OS directions.

Actual **English App / Hebrew OS** sharing labels and visuals remain pending. **Hebrew App / English OS** language-specific labels and visuals likewise need actual observation; bilingual matching alone is insufficient. Recipient join, member approval/decline, role-change and deliberate error-render cases still have no exact mounted selector mapped in the retained bounded sharing handoff. No selector was added or altered here.

Future observation must use the existing coordinated acceptance lane and an appropriate fresh W1-owned fixture. Do not reuse consumed invitations or invent recipient/member state. No fixture, account or invitation was accessed by this audit.

Source/resource availability is not proof that the compiled bundle or mixed-language runtime chooses correctly. This audit infers no locale-selection defect from Foundation/SwiftUI API differences. NativeRoot static/dynamic language work remains separately owned and was not duplicated.

## Scope

No edits to production or test files; no tests, compiler, host, Native, Mac, invitation, account, permission or process operation. The frozen missing-two continuation publication and its runtime boundary remain unchanged.
