# SDK06 source handoff — 18 November 2026

## Review state

Task: https://app.asana.com/0/0/1220542414733348/f

The source was first reviewed at base `5f023e9dc8d33cad7fac73103acd763cdcba8730` in `C:/Users/DAVID/Code/anytype-swift-chatgpt-sdk06-20261118`, branch `codex/chatgpt-wave15-sdk06-20261118`. The owner subsequently explicitly authorized Git staging, commits, pushes and integration; the initial publication block is resolved. The core source, component lane, selection entry and native acceptance source have been published on that branch. SDK06 remains open pending actual acceptance.

The original 17 source/test files were imported byte-for-byte from the preserved `anytype-swift-hanlin-adapter-20261115` tree before changes. Its replay-fix manifest SHA256 is `901883ea225e8d74e03f4bc5efa7d8d154412f6421aed2c4f4f837d1607b2975`. The original producer worktree and the separately active Hanlin worktree were never edited. The new host is developed from those components.

## Canonical dependency contract

`Tools/Hanlin/source.json` pins the published Hanlin commit `116cc6be0654a5d11bc56ba00e0310031107ee36` from https://github.com/davidpovarsky/hanlin-ai. GitHub Commit API returned this exact SHA; repository API returned `private=false`, `visibility=public`. There is no fallback to a moving branch. The initial source manifest/review patch records the earlier `e195ef50` snapshot as historical evidence; the current pin and new complete snapshot verification are documented in `CANONICAL_PIN_UPDATE.md` and `canonical-pin-116cc6-verify.json`.

The canonical products come from these existing nested packages:

| Package | Linked app products |
| --- | --- |
| `Packages/HanlinAgentSDK` | `HanlinHostContracts`, `HanlinAgentCore`, `HanlinPersistenceAdapters` |
| `Packages/HanlinPlatform` | `HanlinPlatformContracts`, `HanlinChatCore`, `HanlinScriptUI` |
| `Packages/HanlinPresentationSDK` | `HanlinChatUI`, `HanlinPresentationKit` |

The test target links HostContracts, PlatformContracts, AgentCore and ChatCore. The canonical package already pins `swift-ai-sdk` to `e7bf34111e603ca977becd007dd4e5bb109af857`; no substitute package products or copied AI implementation were introduced.

All three canonical manifests require `swift-tools-version: 6.2` and `.iOS("27.0")`. The four Anytype and four AnytypeTests configurations previously declared iOS17.0 and now declare27.0. This is a real compatibility change. Project-level and extension deployment settings are unchanged; no Hanlin products are linked to extensions. Availability checks cannot make a package requiring27 link into a target that declares17.

`prepare_sdk.py` reads `git archive` at the immutable SHA from a source repository containing that commit. It does not fetch, checkout, reset, stage or commit in the producer. It creates a separate ignored snapshot at `Dependencies/Hanlin`, preserves the canonical nested layout, rejects symlinks/gitlinks/LFS placeholders, and records a SHA256 manifest. Existing snapshots must pass a complete file-hash check. The pinned packages contain no gitlinks, symlinks or LFS pointer files.

### Required CI preparation

Use `Tools/Hanlin/ci-prepare.example.yml` after the Anytype checkout and **before SPM resolution**. The source is public, so the existing read-only `GITHUB_TOKEN` is sufficient; no new secret is necessary. A clean runner cannot resolve the three local package references until this step succeeds. Root should keep the existing Startup smoke separate and integrate this SDK only after that smoke is available.

For an existing source checkout:

```bash
python3 Tools/Hanlin/prepare_sdk.py --source /path/to/hanlin-ai
python3 Tools/Hanlin/prepare_sdk.py --check
```

The source checkout may have unrelated WIP; only immutable Git blobs from the pin are used.

## Host changes

### Canonical dispatcher compatibility

The original adapter required `idempotencyKey == nil` and rejected every request budget greater than32KiB. The actual Hanlin dispatcher supplies `idempotencyKey == request.id.rawValue`, defaults to a1MiB output budget, and permits budgets through8MiB. Consequently the original direct-call fixtures could pass while actual SDK tool calls never reached the native read.

The read adapter, combined host and creation-plan validation now accept the correlated SDK identity and the full request-budget contract. An unrelated nonnil key is rejected; nil remains valid for the existing direct adapter contract. The host's independent content cap is still32KiB, with24KiB raw text,128 text blocks, and at most512 scanned blocks. A larger transport budget does not authorize a larger read. The SDK separately checks the encoded enclosing result against the caller's budget. The protocol witness uses the canonical `HanlinHostProgressHandler` alias, preserving the producer's concurrency convention.

### Native presentation and lifetime

Three small native hooks were added: `ServicesDI` wraps the existing AuthService; SpaceHub passes its actual owner into the existing bottom panel; the panel hosts the Hanlin button. All additional behavior is under `Anytype/Sources/Pinkha/AI`.

The launch button resolves only its actual mounted window. It binds either the real mounted `EditorPageController` (and its actual document/selection) or the current Space's native controller. Ambiguous editors and presented root modals fail closed. **The button is in HomeBottomNavigationPanelView and the launcher requires `root.presentedViewController == nil`; document/selection entry on iPhone and iPad is not yet native-UI acceptance.** Existing source revision, account, participant, selection and scene fences remain enforced.

The sheet composes `HanlinChatView`, `HanlinChatMessageBubble`, `HanlinChatComposer` and `HanlinChatErrorBanner` from canonical Hanlin products. One canonical `HanlinAgentSession` and `HanlinAISDKAgentEngine` own generation, dispatch and cancellation. There is no replacement agent loop or renderer. HTTPS compatible-model settings and an API key are entered explicitly for the presentation. Existing secrets are never discovered or imported. These settings, draft and transcript are ephemeral; the canonical `HanlinInMemoryConversationStore` is used. Cloud/model calls were not made during implementation.

The actual mounted chat controller owns read-consent and exact-title write prompts, while the original source editor remains the authority. The app owns SDK result receipts. Closing/backgrounding/revoking the original source synchronously fences native dispatch, then invalidates the SDK. No stale payload is forwarded into a new account/Space/scene.

### Account metadata and native write safety

`PinkhaHanlinAccountOwner` retains one journal-opening task/actor per exact namespace, so multiple windows cannot acquire competing writers. Ordinary dismissal, logout and account switching preserve original uncertain-write metadata for late native callbacks and future refusal of automatic retries. The combined write catalog is available only with real mounted presentation, account owner and native confirmation readiness; the old boolean-free requirement barrier remains for uninstalled fixtures.

The user's existing explicit `removeData` logout choice closes presentations, blocks new openings, awaits existing opening tasks, poisons their journal actors and then removes only directories whose canonical namespace metadata proves the exact account. Late callbacks cannot recreate removed metadata. Unknown/corrupt ownership is preserved and surfaced as an error. Other accounts' records remain intact. A native-auth transition gate prevents actor reentrancy from selecting another account while an earlier logout waits for metadata work. No application Heart/auth implementation was replaced; the wrapper forwards native operations.

Native writes remain limited to creation of one standard Page with a confirmed nonblank title in the original writable Space. No bodies, templates, existing-object mutation, unconditional retries or rollback claims were added. `InvocationSettings.handler?.isLogEnabled == false` is still required; logging-enabled/unknown contexts omit the write capability. The native write acceptance run must verify this precondition rather than bypass it.

## Verification and limitations

| Check | Result |
| --- | --- |
| Published immutable SHA / public visibility | PASS through GitHub APIs |
| Canonical dependency snapshot and complete hash recheck | PASS, SentinelX `job_29359ee4dabd47629de04587ed3e33d7`, exit0 |
| Windows Swift syntax,24 host/test files, Swift6.3.3, Swift5 mode, `-D DEBUG` | PASS, `job_70aa1d8a35c540a0a09b34159c74a32c`, exit0; `swift-parse.log` |
| Python setup script syntax | PASS (`py_compile`) |
| Actual Apple host compile/link | Old pin: TEST BUILD FAILED in run44209702553 (canonical OpenUIBlock); revised pin: NOT_RUN |
| XCTest/Swift Testing execution | NOT_RUN |
| Native iPhone/iPad chat, consent, writes, selection/lifetime and navigation ACK | NOT_RUN |

The code contains57 test declarations across four suites (one is parameterized with two budget values, so58 cases are expected when supported iOS/DEBUG branches execute). The preserved suites contribute49 original declarations; eight declarations were added: six canonical consumer tests and two account-removal journal tests. The dispatcher tests exercise the real SDK dispatcher with the existing native-access fixture; they do not manufacture actual native authorization or claim native write proof.

The historical Apple preflight reported by root, run44192464820 on base5f023e9, reached Mac27.0.1/Xcode27/Swift6.4 and an iOS27 simulator, then stopped with INFRA_ERROR before build because the required Heart artifact was unavailable. The requested artifact is absent from run42760706087 and from the repository artifact search. Its seven-day retention is consistent with expiry, but the cause of removal has not been verified. Root owns the pinned runtime recovery workflow. Windows syntax parsing neither resolves Apple modules nor typechecks SwiftUI/UIKit, links, runs tests or validates native UI.

The runtime was subsequently rebuilt successfully in run44203168617. Actual SDK Apple run44209702553 reached compilation and failed in canonical Hanlin OpenUIBlock at the older pin before any test ran. The minimal published canonical correction is now pinned; its Apple rerun is still pending. The separate native consent/create lane and its exact Debug fixture contract are in `NATIVE_HOST_ACCEPTANCE.md`.

### Exact focused Apple command after runtime restoration

`HanlinSDKConsumerTests` and combined-host fixtures are under `#if DEBUG`. A Release-Anytype UI smoke does not run these tests. Use `Debug-Anytype`, which inherits `SWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG` from the project, and the existing Anytype scheme/test plan:

```bash
# First run CI preparation above and restore the exact existing Heart/runtime artifacts.
# Set SDK06_DESTINATION to the actual checked iOS27 simulator, e.g. platform=iOS Simulator,id=<verified UUID>.
: "${SDK06_DESTINATION:?Set the verified simulator destination}"
: "${RUNNER_TEMP:?Use a dedicated runner output directory}"
plutil -lint Anytype.xcodeproj/project.pbxproj
xcodebuild test \
  -project Anytype.xcodeproj \
  -scheme Anytype \
  -configuration Debug-Anytype \
  -destination "$SDK06_DESTINATION" \
  -derivedDataPath "$RUNNER_TEMP/HanlinSDK06DerivedData" \
  -resultBundlePath "$RUNNER_TEMP/HanlinSDK06.xcresult" \
  -only-testing:AnytypeTests/HanlinHostAdapterTests \
  -only-testing:AnytypeTests/HanlinHostWriteTests \
  -only-testing:AnytypeTests/HanlinHostReadWriteTests \
  -only-testing:AnytypeTests/HanlinSDKConsumerTests \
  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO
```

Inspect the real result bundle for nonzero discovered/executed tests and actual failures; source declaration counts alone are not a pass. Then perform native lifecycle/consent/receipt cases only in a disposable test Space after Startup reaches Home reliably. No TestFlight or production/user data operation is authorized by this handoff.
