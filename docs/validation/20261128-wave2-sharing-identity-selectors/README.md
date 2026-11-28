# Sharing UI identity selectors

## What changes

The shared Members and Join views lacked deterministic selectors for individual membership and invitation actions. This change adds **23 accessibility identifiers in one existing source file**, used by both engines.

It preserves all five existing identifiers and every original source line. No label, layout, accessibility grouping/trait modifier, capability check, confirmation, mutation, cancellation or lifetime code is changed. Actual compiled accessibility behavior still requires observation. No test, native contract, dependency or resource file changes.

The source is based on `e84da535ef04fbdde56ae200bdac78fce32e96e0`. The later final `b8521ca8d9d88f62aeb8e246de2c1ae2dd798588` changes only the documentation tree; the entire Modules and NativeApp trees are identical. Final integration remains W3-owned.

## Exact identity

| Source | Bytes | SHA-256 | Git blob |
|---|---:|---|---|
| Original | 16,251 | `55b9913dd3bd8c8eb712944a87d6bde5cae98bd4aa1bf8bc3d553a83e3fb820b` | `bfc0259edf2e74ddbdc59d9cb5175653a59aa61d` |
| Updated | 18,316 | `389572bee9aae2688cae835c054041e302ccc8057a37c1972719a8968c7a5849` | `2d9d5c2e7142b1d97af7b46a59704f2aa9e4813e` |

`replacements.json` contains 23 unique literal replacements. Applying them in order yields the updated source; reversing them in reverse order restores the complete original. Each change only inserts an accessibilityIdentifier line. The original 22-line proposal is recorded separately in the source proof; Root adds the analogous identifier for the existing member-removal action.

## Selector contract

All identifiers below start with `pinkha.sharing.`. Placeholder identities come from the actual current native sharing snapshot, and role is the unchanged enum raw value.

| Control or state | Suffix |
|---|---|
| Members error / refresh / close | `members.error`, `members.refresh`, `members.close` |
| Confirmation buttons | `confirmation.confirm`, `confirmation.cancel` |
| Member row / current role / rendered non-active status | `member.row.<member.id>`, `member.role.<member.id>`, `member.status.<member.id>` |
| Member actions / role choice / removal | `member.actions.<member.id>`, `member.changeRole.<member.id>.<role>`, `member.remove.<member.id>` |
| Request row / approval menu / role choice / decline | `request.row.<member.id>`, `request.approve.<member.id>`, `request.approveAs.<member.id>.<role>`, `request.decline.<member.id>` |
| Invitation row / revoke | `invitation.row.<invitation.id>`, `invitation.revoke.<invitation.id>` |
| Join screen / error / close | `join.screen`, `join.error`, `join.close` |
| Distinct join outcomes | `join.result.active`, `join.result.awaitingApproval`, `join.result.loading` |

The generic `members`, `createInvitation`, `shareInvitation`, `invitationInput` and `join` identifiers remain unchanged. A row identifier is a source-level hook; its actual container/child exposure must be observed in the compiled app. Actual system Copy, Paste and permission controls have no newly invented app identifier.

Native invitation `recordId` supplies invitation identity; private `inviteToken` supplies shareValue. This change never puts private invitation values into identifiers. Member identity, accountID and current requestRecordId are distinct. Explicit row namespaces and one variable identity per identifier avoid ambiguous concatenated identity/request tuples. The optional role suffix is a fixed no-dot enum case.

## Validation and remaining acceptance

Root verified exact original and updated byte/Git hashes, all 23 unique replacements, the complete inverse, all original lines in order and preservation of the five existing identifiers. The original dd251 rendered-title test is unchanged; it still requires exactly one visible, enabled, hittable localized navigation-title text.

This is **source-only preparation**. No Swift compiler, XCTest, native operation, account action or invitation action ran. The change does not establish a sharing mutation fix or mounted acceptance. The independent peer review records its own source scope.

W1 must supply fresh matching owner/recipient/Space/member/request fixtures and current capabilities. The single-account reopen helper's `firstMatch` must not be reused for two accounts; the intended saved account requires a real identity-to-label binding and proven uniqueness. Request IDs stay in native fixture/readback evidence, not inferred from account or displayed suffix.

W3 must use the matching shared App to observe compiled selectors, system Copy/Paste, actual approval/decline and role/removal actions, revoked-link failure and close/reopen behavior, with native post-write readback. A generic error message alone does not prove revocation caused failure. Existing owner900 is not replayed by this source work.

The original first Apple order remains **22 methods / 34 cases → real application preparation → the four original UI methods**. Mixed App/OS language, iPhone/iPad, light/dark and visual/accessibility acceptance remain open. Physical-device work remains NOT_RUN when no device is available.
