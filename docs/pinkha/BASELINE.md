# Pinkha on Anytype — Baseline Audit (Phase 0)

## 1. Repositories and Commit SHAs

### Upstream Anytype Repository
- **Repository URL**: `https://github.com/anyproto/anytype-swift`
- **Tracked Branch**: `upstream/develop`
- **Verified Commit SHA**: `325b60bcecd1119121093761e45ae24ab2eeb82e`
- **Commit Message**: `Merge pull request #5113 from anyproto/lock-screen-widget-quick-capture`

### Pinkha Implementation Fork (Anytype Fork)
- **Repository URL**: `https://github.com/davidpovarsky/anytype-swift`
- **Baseline Branch**: `pinkha/hebrew-localization`
- **Verified Commit SHA**: `794f2a2c5f62057c6f9a1824426b7d551b755338`
- **Branch Relationship**:
  - Behind upstream `develop`: `0`
  - Ahead of upstream `develop`: `4`
- **Feature Branch Created**: `pinkha/foundation-v1`

### Fork-Only Baseline Commits
1. `008a5b749a` `feat(loc): add complete Hebrew localization and update project settings`
2. `b8c983393d` `ci: add unsigned device IPA build workflow with public middleware download`
3. `8d21036f10` `ci: adapt ipa.yaml for unsigned iphoneos device IPA build`
4. `794f2a2c5f` `fix(loc): wrap plural localizations in variations dictionary for xcstringstool`

### Fork-Only Files Modified in Baseline
- `.github/workflows/ipa.yaml`
- `Anytype.xcodeproj/project.pbxproj`
- `Anytype/Resources/Strings/he.lproj/InfoPlist.strings`
- `AnytypeWidget/Resources/he.lproj/LocalizableWidget.strings`
- `Modules/Loc/Sources/Loc/Resources/Auth.xcstrings`
- `Modules/Loc/Sources/Loc/Resources/UI.xcstrings`
- `Modules/Loc/Sources/Loc/Resources/Workspace.xcstrings`
- `Modules/ProtobufMessages/Sources/Loc/Resources/LocalizableError.xcstrings`
- `Scripts/middle-download.sh`

### Old Pinkha Reference Repository (Read-Only)
- **Repository URL**: `https://github.com/davidpovarsky/pinkha`
- **Reference Branch**: `torah-ux-knowledge-tab`
- **Verified Commit SHA**: `05d7c931974108e4655a6d0581096c0775f388de`
- **Role**: Strictly read-only reference for Torah behavior, providers, reference normalization, and domain semantics.

---

## 2. CI and Build Verification

- **Workflow**: `.github/workflows/ipa.yaml` (`Build IPA`)
- **Configuration**: `Release-Anytype`, destination `generic/platform=iOS`, SDK `iphoneos`
- **Latest Verified Run**:
  - Run ID: `35217188265`
  - Status: `completed / success` (22m 39s)
  - Run URL: `https://github.com/davidpovarsky/anytype-swift/actions/runs/35217188265`
  - Artifact Name: `Anytype-Hebrew-Unsigned-Device-IPA`
  - Artifact File: `Anytype-Hebrew-Unsigned.ipa`

---

## 3. Known Existing RTL / Localization Scope

- The baseline repository contains the complete application-shell Hebrew localization and UI mirroring.
- TextEditor in Anytype currently operates with LTR-dominant block alignments and directionality; Editor RTL support is scheduled for Phase 9 as a separate focused phase using `pinkha.textDirection.v1` block fields.
