# Original production account/bootstrap ownership

## Status and source boundary

This is a source audit and bounded integration design. It does not establish an authenticated Maktabah account, a compiled external bootstrap API, native import qualification, or device readiness. Product composition is `59d229f2e57b6e868d817696d4609e1ed170a6c9`; this branch's closed-Host proposal was added at `7a566ddf29b1a0a42220353923145506db7899c9`. The retained original framework product source is `de63125b97cd5b91a1fa4f4b71d03738076e735f`.

`ACCOUNT_BOOTSTRAP_SOURCES.json` binds every inspected original path below to its full Git revision, blob, size and SHA-256. The selected-Space schema hook is separately bound by `COMPOSITION.json`. No credential value, wallet material or user data was read for this audit.

## Actual original entry points

| Stage | Original implementation and observed behavior |
| --- | --- |
| Original application setup | `AnytypeApp` in AppScene.swift installs the original AppDelegate. AppDelegate invokes AppConfigurator, which installs the original Invocation handler, middleware event listener, metrics, view providers and other application integrations. |
| Original persisted login | ApplicationCoordinatorViewModel.loginProcess reads the existing BasicUserInfo user ID, obtains the saved seed through SeedService, calls AuthService.walletRecovery, and then AuthService.selectAccount. Missing identity or failure routes to the original authentication view. |
| Original interactive recovery | AuthCoordinatorView presents the original LoginCoordinatorView/JoinCoordinatorView. LoginViewModel uses the original local-auth UI when reading Keychain, WalletRecover, SeedService.saveSeed, AccountRecover and account-show event subscription before AccountSelect. The account ID from the event is selection data, not an editor capability. |
| Actual account ownership | AuthService.startAccount owns the original transition and cancellation. Only after the native call returns does it assign BasicUserInfo/AccountManager; it then waits for the transition's actual release and constructs OriginalAuthStartupSource from the original account lifetime. Equal identity strings cannot replace its captured source/token. |
| Actual account subscriptions | LoginStateService starts and owns the existing SpaceViews, Participants, profile, ActiveSpaceManager and other subscriptions under that same OriginalAuthStartupSource. It retains actual task handles and drains them before stopping and clearing original state. |
| Original selected Space | Original SpaceHub/SpaceLoadingContainer routes call ActiveSpaceManager.setActiveSpace. It captures the concrete account and actual SpaceView, invokes the original WorkspaceOpen through the captured binding, waits for actual drain, validates the returned SpaceView/Space identity, and mints OriginalActiveSpaceSelection from its private attempt. The composed source additionally invokes the actual schema registration hook using current original permission captures. |
| Original editor | AnytypeOriginalEditorModule.openExistingEditor expects an already authenticated original account and an explicitly existing object. Its public Binding is identity data. It captures the actual AccountManager lifetime and host source, then uses the original PreparedEditorPageSessionFactory/coordinator/controller. It does not initialize a wallet, restore an account, select a Space or import an archive. |

The current exported module has **no unguarded production account/bootstrap or original account-selection UI entry**. inspectResources explicitly constructs no AppDelegate, Factory service, account, Space, document or editor. The Debug Simulator acceptance runtime is not that entry. Maktabah's saved annotation profile and UUID do not imply a live Anytype account in its own process.

## Persistent storage and host integration prerequisites

LocalRepoService resolves Application Support/Anytype/middleware-go inside the current application's sandbox. This is the existing original repository location; it does not refer to another installed application's repository. A production bridge must keep this existing store and must not create a disposable qualification directory, automatically clear a repository, or silently switch the root on relaunch.

SeedService uses the original Keychain query with service `com.anytype.seedPhrase`, account `AnytypeSeedPhrase` and after-first-unlock-this-device-only accessibility. Its query supplies no shared access group. The original KeychainStore uses Security framework queries. The external host must use its own genuine signed application Keychain access; it must not claim access to another app's saved account or copy qualification credentials into this route. Existing original interactive recovery, local authentication and error handling should remain the actual user route.

BasicUserInfoStorage uses UserDefaultByAppGroupStorage. TargetsConstants currently chooses `group.io.anytype.app.dev` or `group.io.anytype.app` from CoreEnvironment; the latter reads the main bundle's CompilationCondition and caches it. UserDefaultByAppGroupStorage can migrate matching standard-default keys into the group suite and writes both stores. This is an explicit external-host storage/signing prerequisite, not evidence that Maktabah owns either group. A production bridge must validate the host's configured, genuinely accessible storage before any such getter or Factory initialization. If a host-specific group/namespace is required, it needs a separately reviewed storage configuration change that preserves the original app defaults and migration behavior; changing bundle IDs or silently falling back is not an account proof.

AppConfigurator also starts application-specific integrations including Firebase, notifications, analytics and global services. Calling the whole configurator from Maktabah would be a new host integration, not a harmless editor constructor. The original AppScene global environment modifier also associates the original legacy view provider with the actual window and changes the window's interface style. An embedded route must explicitly own its controller/environment integration and avoid assuming it owns the host's AppDelegate, notification delegate or every application window.

## Proposed external account-session bridge

This is a separate, unimplemented bridge requiring a concrete source patch review. The intended public entry presents the existing original account/recovery/selection UI, retains a single original runtime owner, and returns only a closed session after actual original authentication and selection have completed. It must not accept a mnemonic in an evidence packet, arbitrary repository paths, a fabricated account status, caller-supplied selected-Space authority, or the qualification runtime's environment flags.

A viable bridge must establish these steps in order:

1. Validate the real host bundle/storage configuration before any group-default migration or original service construction. Claim the process's original runtime initialization once; do not overwrite an already installed unrelated Invocation handler or create a second Container/account engine.
2. Retain the original Invocation message handler, additive middleware event listener, required original account event subscriptions and view-provider registration. Each original dependency used by the chosen authentication UI must be explicitly accounted for. Reusing a single shared original configurator boundary is preferable to copying its implementations, but the exact factoring and necessary environment dependencies still need review.
3. Present the original ApplicationCoordinator/Auth/Space selection flow or a narrowly factored original coordinator seam. Persisted login must still traverse the original SeedService and AuthService; interactive recovery must still traverse its original UI and Security-backed storage. No raw seed is exported to Maktabah's annotation API, logs or source evidence.
4. Obtain the actual OriginalActiveSpaceSelection only after original account startup, original subscriptions, WorkspaceOpen and schema registration have completed. Freeze that exact selection/account token and actual participant/SpaceView permission captures with the existing host source. A one-time account ID check is insufficient.
5. Construct the original Host through a shared internal factory that consumes this fully captured binding. Keep the existing public openExistingEditor behavior intact for its current callers.
6. On host-source, selection, account or permission retirement, synchronously revoke new source-bound writes/mounts. Preserve actual already-admitted native work and its historical result until its real completion/drain; do not infer drain from task cancellation, a Cancel RPC response or view dismissal.
7. On logout, delegate to original AuthService.logout and LoginStateService cleanup. Preserve the original AccountStop-before-drain ordering and successful-stop-required behavior. A retained import's Cancel/Observe/Release access must target only its already-owned historical handle and must not manufacture fresh current write authority.

The account session may be reused while its exact original account/selection source remains valid. It is not a serialized capability; after process restart, original persisted login and Space selection must run again, producing new live ownership. A saved local annotation/source receipt can be compared after that recovery but cannot recreate the previous process's lifetime.

## Proposed source boundaries and independent next patch

The original four-path closed Host proposal remains recorded separately. Its source restriction and shared internal Host factory can be implemented independently in two existing paths:

- `Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/EditorDocumentWriteOwner.swift`
- `OriginalEditorFramework/AnytypeOriginalEditorHost.swift`

This independent prerequisite does not add a public bootstrap, mint a selected session, invent native RPCs or change existing public-open behavior.

The later closed-session facade and import adapter remain new files in the earlier proposal. A real external account bootstrap will additionally require an owned framework facade (proposed `OriginalEditorFramework/AnytypeOriginalEditorAccountSession.swift`) and a reviewed shared original initialization/coordinator seam. AppConfigurator/GlobalServicesConfiguration, ApplicationCoordinatorView/Model, original environment setup and any host storage configuration are dependency candidates, not an approved blanket edit list. No product changes to those paths have been made.

The native owner is independently reviewing bounded Start/Observe/Cancel/Release. Start must privately prepare, register and start once; Cancel/Observe/Release must retain historical operation access after source retirement. Proposed native wire bounds are the existing v1 limits of 65,536 compressed bytes, 512 entries and 8 MiB expanded data. Exact archive ownership, per-write ACL and source-container proof still require the native owner's concrete source review. No generated API name or durability guarantee is assumed.

## Affected qualification

New external production qualification must use the final composed source/native Lib and generated client. It must exercise genuine first login/recovery, persisted account relaunch, original selected-Space registration, same-source Host construction and source/account/permission retirement around actual import/write admissions. It must verify that startup failures and native import cancellation leave no falsely reusable account/attempt, and that copied terminal history survives retirement without allowing new writes.

The existing retained signed consumer EN/HE gate qualifies de631 resources/public-host linkage only. The Stage B saved-edit/reopen/new-PID acceptance remains its own actual runtime case. Neither can be relabeled as qualification for this new production bootstrap or native import ABI. Device readiness additionally requires actual device slices, host entitlements/provisioning and genuine device acceptance for the same final composition.
