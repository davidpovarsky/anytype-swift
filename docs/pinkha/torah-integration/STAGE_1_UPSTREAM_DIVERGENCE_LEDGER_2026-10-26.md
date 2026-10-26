# Stage 1 upstream divergence ledger — 2026-10-26

Status: audit snapshot; no authorization is implied by an entry in this ledger.

## Baseline

- Repository: `C:\Users\DAVID\Code\anytype-swift`
- Fork HEAD audited: `c2663ab6178044eab0b0a03faefa4f802fed932c`
- Branch: `pinkha/torah-associations-native-ux-persistence-localization-2026-10-20`
- Audit-time `upstream/develop`: `d5650321577a209505a3277c8437b7608cff1cb9`. A pre-commit refresh later advanced the ref to `b781a7734ecd70813cf19b10a5262ed193bb1e2b`; all H1–H10 target blobs were unchanged and this historical audit was not rewritten.
- Merge base: `d5650321577a209505a3277c8437b7608cff1cb9`
- Fork delta: 217 added or modified paths; 44 modified paths existed in original upstream.
- Pre-session worktree: clean. The six paths called out in the execution prompt had already been captured by commits `c0350cec75` and `c2663ab617`; this audit did not rewrite them.

For the complete, machine-verifiable zero-context range list—including the tens of thousands of localization catalog hunks—run:

```powershell
pwsh -File Scripts/pinkha-upstream-divergence-audit.ps1 `
  -BaseRef d5650321577a209505a3277c8437b7608cff1cb9 `
  -HeadRef c2663ab6178044eab0b0a03faefa4f802fed932c
```

The script emits every original path, full upstream and fork blob SHA, numstat, and every exact `--unified=0` old/new range. It is read-only and excludes downstream-added paths by verifying that the path exists at the base ref.

## Classification rules used below

- `LEGACY_UNREVIEWED`: present before this Stage 1 session and not covered by a recorded exact-hunk approval.
- `KEEP_APPROVED_HOOK`: only the `TorahInspectorKit` package pin hunk in `project.pbxproj`, recorded in `UPSTREAM_EXCEPTION_REGISTER.md`; no neighboring hunk inherits that approval.
- `EXTRACT_SAFE_NOW`: active Pinkha dependency can be removed downstream-first. Reverting the original hunk still requires owner approval because the original file itself would be modified.
- `FROZEN_NO_TOUCH`: generated, protobuf, or bulk catalog output; no Stage 1 edit is allowed.

## Every modified original path

All entries existed at `upstream/develop`. `U` and `H` are full upstream and fork blob SHAs.

### Workflows and shared integration

Each workflow change adds or alters fork CI behavior. All are `SHARED_INTEGRATION`, `LEGACY_UNREVIEWED`, `AUDIT_ONLY`; their risk is fork CI/release drift, not runtime editor behavior.

| Path | U | H | Hunks |
|---|---|---|---:|
| `.github/workflows/automerge.yaml` | `0ec0bc4f14d6c37235d74acebdd9d21fbdad536d` | `f6431cd77fbbcc9582810c11c7c10eef70972491` | 3 |
| `.github/workflows/branch_build.yaml` | `4516001e339e092dda183c5f249ec2c4eed7dc2f` | `98a6c70b521feb5b5a720f3c14e2d097bf890da6` | 9 |
| `.github/workflows/claude-code-review.yml` | `bc519ee19035000fb9c819af72849c99cc3dc532` | `20cae5ec7b3891c4e78ee6f45ad38e29d9fb1dcb` | 4 |
| `.github/workflows/claude.yml` | `412cef9e6785990d352aec5b9df3141e878fe3b5` | `3e5eca101463317678bc628da1d58204ebb78d8b` | 2 |
| `.github/workflows/dev_build.yaml` | `45fccb704e4df564337c1a3d11eab4955236d8e5` | `9b66174e55ea2d7676fe2a11b58593a0b20c491e` | 11 |
| `.github/workflows/generator_checks.yaml` | `a1d63cb6fa82a978843eb7d5ac883e60230a1abe` | `5a34d86e9f049eb7d2bb572f2e5e2ae140ebbf0b` | 6 |
| `.github/workflows/ipa.yaml` | `7a4c6bfbb0bad5fbb0b4d7145a31145a2e5e759e` | `ba46aca106d2f6f0d2cff4a66c659063382b5054` | 17 |
| `.github/workflows/license-checks.yml` | `6cf867c7e7f70a915d7a7905a11fd747c3640880` | `09497d5483e8ba03a9945674c1826102e2d2af9e` | 7 |
| `.github/workflows/link_issue_to_release.yaml` | `b140a0e1f28b72d140903d68630d73257f492327` | `0d06849b03a79b783e0be0065cc74d8327c4383b` | 6 |
| `.github/workflows/pr_tests.yml` | `838048ca8786bde5cabda1dc9e91a6a7c2ebe6a5` | `8178cefd864f3d97d38f6ddd34d447705ea3ba75` | 9 |
| `.github/workflows/release_build.yaml` | `8933acca4e8922fb32aa5d905ed65443710b85f4` | `0601a8876c53997bf0b8d0e43eb75d66eaf305c7` | 12 |
| `.github/workflows/test_fastlane_build.yaml` | `be756ecaa48852cedc3c8625c671959d0205f5f0` | `27f744e5cab1e0637278efd8bfeb778306841ac2` | 9 |
| `.github/workflows/update_cache.yaml` | `dfc3d7859c00a0c5521b0546454edaa89fe168fa` | `b25478e44b73d3b56760d497cf5539e939b7515f` | 9 |
| `.github/workflows/update_middleware.yaml` | `b68211802cd6c7a775a5d0d3136e72bc1c95d2d2` | `0e34a806c829c0279ab1c6ae850ddfcbcd3e5bed` | 18 |
| `.github/workflows/update_middleware_nightly.yaml` | `7eb9c48bc869716809d5b5b4dfc4170f0bc552f6` | `c90696be1928137d450b6b4b3078b40ec25bcb4e` | 2 |
| `Anytype.xcodeproj/project.pbxproj` | `8c3872c414a5f22cd6b05d2dbb99ec64a33b13b0` | `e65978b8a3beb512b5f544723b8aeaa04466633f` | 9 |
| `CLAUDE.md` | `89cfcbb3aa72249e66e97b51c3615fe1eabba417` | `32ed83db447c308d42fe7e87ebf2c249c35fd4ee` | 1 |
| `Scripts/middle-download.sh` | `324f238aaa79ae63c126a4458a935872b8ba57b0` | `37cc8650216bbece56172b29130c509c612d5f6a` | 4 |

`project.pbxproj` is `SHARED_INTEGRATION`. Its package revision pin is `KEEP_APPROVED_HOOK`; its other eight hunks are `LEGACY_UNREVIEWED` / `AUDIT_ONLY`. `CLAUDE.md` is repository governance and `AUDIT_ONLY`. `middle-download.sh` changes middleware-download behavior and is `LEGACY_UNREVIEWED` / `AUDIT_ONLY`; middleware semantics are out of Stage 1 scope.

### Original app/service Swift sources

These 19 files describe the committed HEAD divergence audited before implementation. Every listed pre-existing hunk remains `LEGACY_UNREVIEWED`. The separately approved H4 hook adds one new worktree hunk to `TextBlockContentView.swift`; it does not authorize or reclassify that file's older hunks.

| Path | U → H | Exact zero-context ranges | Behavior, risk, decision |
|---|---|---|---|
| `Anytype/Sources/PresentationLayer/Common/SwiftUI/Search/Common/SearchView/Cell/SearchCell.swift` | `bea6bd3baf7b2903bfef96947a0ecc6cf006e42f` → `d768257dae186a39d949c70e3841da16756bc9a2` | `-5/+5,-7,0/+8,39,-11,3/+50,2,-18,0/+57,24,-24,3/+86,5,-29,3/+93,5,-69,0/+136,33` | Generic selection/trailing action/accessibility/asset sizing. Broad caller risk. `EXTRACT_SAFE_NOW`: active Torah row dependency was removed downstream; original hunk remains unchanged pending approval. |
| `Anytype/Sources/PresentationLayer/Common/SwiftUI/Search/Common/SearchView/SearchView.swift` | `d3e87901a7db8bb1fbbc36d238c2791d19998422` → `9dc9013dfdc7176113989bba544547ef52494f18` | `-44,4/+44,5,-50/+50,0,-126,0/+127,45` | Extracted generic shell used by Pinkha. Broad search-screen risk. `EXTRACT_SAFE_NOW`: Torah now owns its sheet composition; original hunk remains unchanged pending approval. |
| `Anytype/Sources/PresentationLayer/Flows/EditorPageFlow/EditorPageCoordinatorView.swift` | `4a6194485dc40aebe3da32530dc36a8c1b6c1e84` → `a33fb6ac29c8c5421e7491d11b23053d49359440` | `-16/+16,6,-17,0/+23` | Injects Torah editor session/coordinator state. Editor lifecycle risk. `REQUIRES_EXACT_OWNER_APPROVAL`. |
| `Anytype/Sources/PresentationLayer/Flows/EditorPageFlow/EditorPageCoordinatorViewModel.swift` | `f8f29b26a7152f8d619f2f89415566617e9bfe6b` → `475d21bff972b2a146f5dbe4404945e7402ac973` | `-11,0/+12,-37,0/+39,7` | Exposes Torah session/navigation. Coordinator API risk. `REQUIRES_EXACT_OWNER_APPROVAL`. |
| `Anytype/Sources/PresentationLayer/Modules/HomeWidgets/Container/HomeWidgetsView.swift` | `2d4e1a58711805848d8a9c33b04518dc51b74bbc` → `adb9c4f5085711de409f2bda0cddc92c9bad6bf9` | `-4,0/+5,-90/+91,6` | Adds Pinkha home entry to a global host. Non-Pinkha surface risk. `REQUIRES_EXACT_OWNER_APPROVAL`. |
| `Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/EditorPageModuleAssembly.swift` | `18d34881d05dcbdf0204eb5131c5d2779dcc7c75` → `4a2ee344be652729d053837343d1dce058cedb7f` | `-7/+7,6,-18/+23,6,-60,0/+71,-80,0/+92,-130/+142,2,-221,0/+235,2` | Builds and injects Torah services/session. DI and editor construction risk. `REQUIRES_EXACT_OWNER_APPROVAL`. |
| `Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/TextBlockContentView.swift` | `ae90a1f4a91e0204c4d11d2464113a729f9f1f12` → `aba80ccd797160822bbeee2e102a30c9b8c7786a` | `-20,0/+21,5,-26,0/+32,3,-28,0/+37,-55,0/+65,19,-64/+92,-69,0/+98,16,-209,0/+254,50` | Torah badge/action plus physical leading/trailing constraints. Cell reuse, text width, RTL collision risk. `REQUIRES_EXACT_OWNER_APPROVAL`; downstream extraction needs a tiny host slot first. |
| `Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/BlocksOptionView/BlocksOptionItem.swift` | `db308e5a541bf50ab2367771e60b51e2f29972d2` → `2f7789e9cadd4d5365d53de9cef85db9aa11e756` | `-10,0/+11,2,-50,0/+53,2,-81,0/+86,4,-112,0/+121,4` | Adds Torah block-option actions. Menu parity risk. `REQUIRES_EXACT_OWNER_APPROVAL`. |
| `Anytype/Sources/PresentationLayer/TextEditor/EditorPage/EditorPageBlocksStateManager.swift` | `df6b9f7224213afa86610a14910333cb7fa91d20` → `f04ddd47117f5c76c14dabdbfeac72862d7034e8` | `-88,0/+89,-104/+105,2,-113,0/+116,-266/+269,11,-557,0/+571,6` | Torah action routing and block state. Diffable state/reuse risk. `REQUIRES_EXACT_OWNER_APPROVAL`. |
| `Anytype/Sources/PresentationLayer/TextEditor/EditorPage/EditorPageController+DragNDrop.swift` | `57bf03de28b724fbf7accd25a8a3b9b0b60ca104` → `e56e24788e7c80dbfd93e6567d68d5cc3ca1aa4c` | `-1,0/+2,2,-11,0/+14,9,-31,0/+43,22,-33/+66,-49,0/+83,16` | Source-quote drag payload/drop behavior. General drag/drop risk. `REQUIRES_EXACT_OWNER_APPROVAL`. |
| `Anytype/Sources/PresentationLayer/TextEditor/EditorPage/EditorPageController.swift` | `910ae8982dbfc0d765894901c037da9e921938d7` → `9bf51837c66a59cb5bd3866b04c55dc2009da3ca` | `-91/+91,6,-105,0/+111,3,-758/+766,-760,0/+769,-766,0/+776,28` | Torah cell accessories, selection interaction, session lifecycle. Editor controller risk. `REQUIRES_EXACT_OWNER_APPROVAL`. |
| `Anytype/Sources/PresentationLayer/TextEditor/EditorPage/EditorPageView.swift` | `9a01d63497acafb234cd1ba6f3224319a8629e01` → `7a32bf7fc6fb8c7fefcc10158abc166011c49c7d` | `-11/+11,6,-13/+18,6` | Passes Torah session into editor view. Host view API risk. `REQUIRES_EXACT_OWNER_APPROVAL`. |
| `Anytype/Sources/PresentationLayer/TextEditor/EditorPage/EditorPageViewModel.swift` | `580d555bcac0abbb03449e72c9c38d09ae6e1415` → `fd1f60e3c9cfc04848215d55f66de3d08d3c2740` | `-6,0/+7,9,-17,0/+27,2,-36,0/+48,2,-73,0/+87,2,-86,0/+102,2,-88,0/+106,12,-91,0/+121,48` | Torah commands/source insertion and block creation. Mutation/data-loss risk. `REQUIRES_EXACT_OWNER_APPROVAL`. |
| `Anytype/Sources/PresentationLayer/TextEditor/EditorPage/EditorPageViewModelProtocol.swift` | `f496f32b08a5fa49bb7d811cd6c5a2fa40a0ec33` → `12970c3d84ed808e67419cd85220cb4200990789` | `-3,0/+4,-14,0/+16,-39,0/+42,3` | Expands editor protocol for Torah. All conformer/test-double risk. `REQUIRES_EXACT_OWNER_APPROVAL`. |
| `Anytype/Sources/PresentationLayer/TextEditor/EditorPage/Utils/EditorNavigationBarHelper/EditorNavigationBarHelper.swift` | `6628574fdb5d6c46ec9e71171e71d522082571af` → `4598cbdd2b8d2532c9885a95892fad9cb7e84e16` | `-4,0/+5,85,-20,0/+106,2,-50,0/+138,2,-55/+144,14,-62,0/+165,7,-66,0/+176,2,-82,0/+194,8,-143,6/+262,7,-149,0/+270,-151,0/+273,3,-155,0/+280,6,-215,0/+346,-283,0/+415,-289,0/+422,31` | Large Torah toolbar/menu/placement implementation. Highest navigation/layout risk. `REQUIRES_EXACT_OWNER_APPROVAL`; target for downstream extraction after a host slot exists. |
| `Anytype/Sources/PresentationLayer/TextEditor/EditorPage/Utils/EditorNavigationBarHelper/EditorNavigationBarView.swift` | `ab7606cd185e5183d587c9dc97988e0098ff348c` → `e3649f99bb82c4157b58e71d10b118ff18b50a04` | `-11,0/+12,3,-93,0/+97,51` | Adds Torah navigation controls/layout. Width and RTL risk. `REQUIRES_EXACT_OWNER_APPROVAL`. |
| `Anytype/Sources/PresentationLayer/TextEditor/EditorPage/Views/NavigationBar/EditorNavigationBarTitleView.swift` | `a6be8dd9cfbd5a0d01a471b173d13b31ce1b245e` → `adcba8b5093b660e82804bc804fe37aefeef1806` | `-24,0/+25,8` | Exposes title width for Torah controls. General title-layout risk. `REQUIRES_EXACT_OWNER_APPROVAL`. |
| `Anytype/Sources/PresentationLayer/TextEditor/EditorPage/Views/NavigationBar/Settings/UIEditorBarButtonItem.swift` | `4d1a9dad4a11935a2f6931f7b35769b1700a4c1e` → `dfdefcd3fa2e02e76b66c15701e4218c3a58d2ea` | `-9/+9,6,-11,0/+17,2` | Extends button item for Torah actions. Toolbar API risk. `REQUIRES_EXACT_OWNER_APPROVAL`. |
| `Anytype/Sources/ServiceLayer/ActiveSpaceManager/ActiveSpaceManager.swift` | `42f92c023c6cf80d6c62139b50f45840c1b3d240` → `a0b729b10e80067cd94466295b2296d56c4931ba` | `-75,0/+76,2` | Globally schedules Pinkha bootstrap while runtime flag is enabled. Non-Pinkha Space mutation risk. `REQUIRES_EXACT_OWNER_APPROVAL`; must be gated by explicit Pinkha ownership before release. |

Priority order for isolation: navigation-bar helper; text block content; editor controller/state/view model/assembly chain; ActiveSpace bootstrap; generic search pair; remaining menu/home surface hooks.

### Localization, generated, and vendor-adjacent paths

| Path | U | H | Class / state / decision |
|---|---|---|---|
| `Anytype/Resources/Strings/he.lproj/InfoPlist.strings` | `c5a7c0cfad6783ca3b54f9e9c3f828e3f259ef1c` | `76a30e2685b4496c14e36b68bf20152f21087ad5` | `UPSTREAM_OWNED`, `LEGACY_UNREVIEWED`, `AUDIT_ONLY`; five localized plist entries changed. |
| `AnytypeWidget/Resources/he.lproj/LocalizableWidget.strings` | `2403427a18b8540259f32999d940184cd9d88638` | `06e910a84d546ef3d6a03f6ddd5d1805656c62c9` | `UPSTREAM_OWNED`, `LEGACY_UNREVIEWED`, `AUDIT_ONLY`; two widget strings changed. |
| `Modules/Loc/Sources/Loc/Generated/Strings.swift` | `d6d31b5184872678a74c11c85c06ebcddd1099df` | `59734004d96d3f55be78513515413aaa108bb608` | `GENERATED_OR_VENDORED`, `LEGACY_UNREVIEWED`, `FROZEN_NO_TOUCH`; generated accessors (+69). |
| `Modules/Loc/Sources/Loc/Resources/Auth.xcstrings` | `3e24d1cb37126fd422e3404ab0e44767beb377d5` | `86c6301edc3c17fe01eb563bb045161eb397c8f2` | `GENERATED_OR_VENDORED`, `LEGACY_UNREVIEWED`, `FROZEN_NO_TOUCH`; 2,001 hunks. |
| `Modules/Loc/Sources/Loc/Resources/UI.xcstrings` | `f27d4e53c6f0c7baeb8d3f1359f61c36efd381e3` | `e439720df26033c7dd4a0ba18d09ebfb3ceb81d2` | `GENERATED_OR_VENDORED`, `LEGACY_UNREVIEWED`, `FROZEN_NO_TOUCH`; 18,544 hunks. |
| `Modules/Loc/Sources/Loc/Resources/Workspace.xcstrings` | `f6fbfdc94c5fe083fb711119c09993d92e3f767a` | `8e8054aa2ff6e0e034b09c213a0623e877ea2038` | `GENERATED_OR_VENDORED`, `LEGACY_UNREVIEWED`, `FROZEN_NO_TOUCH`; 13,420 hunks. |
| `Modules/ProtobufMessages/Sources/Loc/Resources/LocalizableError.xcstrings` | `98ad98f9a92a8e5da52c161f57d9f7036a5bea4f` | `d4f933aa9b31819a4859413b71868d66722e3c99` | `GENERATED_OR_VENDORED`, protobuf-owned, `LEGACY_UNREVIEWED`, `FROZEN_NO_TOUCH`; 2,387 hunks. |

These paths are not an RTL repair seam. Stage 1 must not bulk-rewrite them.

## Stage 1 session boundary

- Owner-approved worktree hooks H1–H7 and H9 were applied after exact blob revalidation and are recorded in `docs/architecture/UPSTREAM_EXCEPTION_REGISTER.md`. They are the only new upstream-source edits in this session.
- Owner-approved H8 and H10 were applied after their three exact pre-edit blobs were revalidated. `TextBlockIconVIew.swift` remains byte-identical to upstream/HEAD; only the approved call in `TextBlockContentView.swift` and the three approved H10 changes differ from the prior worktree.
- Downstream additions in this session: pure writing/navigation policy and tests, Pinkha UIKit/persistence/navigation adapters, Pinkha-owned Torah search-shell/result-row composition, this ledger, the read-only audit script, the validation report, and the corrected H8/H10 proposal.
- The original generic `SearchViewShell` and enhanced `SearchCell` remain in place because deleting their legacy hunks would itself be an unapproved edit. Active Torah code no longer depends on those extensions.

### Approved worktree hooks added after the committed-HEAD audit

| Hook | Path | Verified pre-edit blob | State |
|---|---|---|---|
| H1 | `Modules/Services/Sources/Models/Block/BlockInformation/BlockInformationConverter.swift` | `f90bf2c39869ec4d0a835422af6e9f5f2f0b4f4f` | `KEEP_APPROVED_HOOK` |
| H2 | `Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/TextBlockContentConfiguration.swift` | `4d8279bf06b9440569d15a9c0856d33b5993d147` | `KEEP_APPROVED_HOOK` |
| H3 | `Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/TextBlockViewModel.swift` | `d825db1fa99d1d85385f3038df23883f51877a4a` | `KEEP_APPROVED_HOOK` |
| H4 | `Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/TextBlockContentView.swift` | current legacy-context `aba80ccd797160822bbeee2e102a30c9b8c7786a` | `KEEP_APPROVED_HOOK`; legacy hunks unchanged/unapproved |
| H5 | `Anytype/Sources/PresentationLayer/Common/UIKit/TextView/Views/TextViewWithPlaceholder.swift` | `d53f8c26d3636e777fa76c65380fea6279fd68fa` | `KEEP_APPROVED_HOOK` |
| H6 | `Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/TextBlockActionHandler.swift` | `861843b0c1962e37ccd86b2a10cf60ac05e9d001` | `KEEP_APPROVED_HOOK` |
| H7 | `Anytype/Sources/ServiceLayer/Block/BlockActionHandler/BlockActionHandler.swift` | `4fdcc6f3bd8346b145946bac32b0d6b8c2ef1abd` | `KEEP_APPROVED_HOOK` |
| H9 | `Anytype/Sources/PresentationLayer/Common/SwiftUI/Navigation/PageNavigationBackButton.swift` | `0659188a73f335c9419d9bc10db03d7d0c53dd32` | `KEEP_APPROVED_HOOK` |
| H8 | `Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/TextBlockContentView.swift` | approved H4-context `55c30c6a1805fbb75d846618f4b6037e512a1795` | `KEEP_APPROVED_HOOK`; `TextBlockIconVIew.swift` unchanged |
| H10a | `Anytype/Sources/PresentationLayer/Common/SwiftUI/NavigationView/FullScreenSwipeNavigationController.swift` | `0ee63a6623cab25b318ac97c9313eb19855cb1eb` | `KEEP_APPROVED_HOOK` |
| H10b | `Anytype/Sources/PresentationLayer/Common/SwiftUI/NavigationView/AnytypeNavigationView.swift` | `a7755dbf09680be2116b7523f82cc733c4ee42cc` | `KEEP_APPROVED_HOOK` |
