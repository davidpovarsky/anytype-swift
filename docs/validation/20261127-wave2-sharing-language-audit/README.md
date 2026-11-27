# Sharing language audit — negative source finding only

**This is a source-only negative finding, not sharing or mixed-language UI acceptance.** At exact current source `a72f2e1ee3032cc1170c3ab07a9ae6b0eefa2dfd`, the bounded audit found no new production language bypass in `PinkhaSpaceMembersView`, `PinkhaJoinSpaceView` and their small package-resource chain. No production, test, resource, permission or Native-contract change is proposed or included.

## What the source establishes

The shared views explicitly localize their static labels, errors, roles/statuses and confirmations through the `PinkhaSharing` module bundle. The three model error strings are English localization keys rendered by `LocalizedStringKey`, rather than direct untranslated error text. All **50 required keys** have nonempty English and Hebrew entries, and the interpolated confirmation formats have matching String-placeholder counts. The target processes its own Resources with English fallback; no missing `Loc` integration was demonstrated.

The original audit, README, complete key/value coverage and source manifest are included byte-for-byte. `immutable-source-references.json` supplies exact commits, Git blobs and SHA256 values for the four freshly read primary bodies and three narrowly reused current bodies. Large UI/model/test sources and raw API wrappers are not copied again. The two NativeRoot language corrections remain separate work.

## What remains open

The existing selector remains:

`PinkhaAnyNativeUITests/NativeLaunchTests/testNativeSharingInvitationConfirmationCancellationAndColdReopen`

Its original allowance is **900 seconds**. It uses Hebrew app launch arguments and accepts either English or Hebrew labels while exercising invitation create/revoke Cancel/Confirm and cold reopen. This does not establish exact language selection, and this audit does not invalidate or extend its original functional scope.

Both **English App / Hebrew OS** and **Hebrew App / English OS** label and visual observations remain pending. They require the existing coordinated acceptance lane, an actually admitted App, and appropriate **fresh W1-owned fixtures**. Do not reuse consumed invitations or invent recipients/member state. No actual account or invitation operation occurred in this audit.

Source/resource presence is not proof of the compiled localization bundle or runtime language resolution. No locale bug is inferred from a Foundation/SwiftUI API difference. No test, selector, controller, resource or product change is warranted from the bounded negative finding.

## Publication and activation boundary

This packet adds only this evidence subtree on a fresh owned branch over `a72f2e1ee3032cc1170c3ab07a9ae6b0eefa2dfd`. It leaves all inherited source, test, resource, preparation and failure evidence unchanged. Root complete-packet review is required before Git publication; publication itself grants no runtime, fixture, compiler or product activation. All existing admission and coordination gates remain unchanged.

No tests, compiler, host, Mac, Native, private-account read, invitation operation, process query or signal was performed. The separate missing-two Bookmark continuation and its actual-result boundary remain unaffected.
