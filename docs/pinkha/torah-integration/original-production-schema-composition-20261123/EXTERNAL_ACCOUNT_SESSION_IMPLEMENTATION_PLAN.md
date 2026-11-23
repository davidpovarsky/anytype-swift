# External original account-session implementation plan

## Status and exact bases

This is a proposed source implementation, not an implemented or qualified bootstrap. The frozen Anytype product base is `89926d7839c09a629c195ec6dd9812fe56aad069` on `codex/otzaria-original-production-20261123`. Its authenticated generated AnnotationSchemaRegister outputs and selected-Space/source-binding prerequisites are already recorded in this packet. The original retained editor distribution was built from `de63125b97cd5b91a1fa4f4b71d03738076e735f`; its pending EN/HE resource/consumer runtime cannot qualify this later composition.

The external host inspected here is Maktabah `1969b2065469b55e38e42cbb838a469ffa6a80f7`. This plan makes no assumption that Maktabah owns an existing Anytype account, native repository, Keychain item or application-group entitlement. `EXTERNAL_ACCOUNT_SESSION_SOURCES.json` records the actual source bytes. No credential, application container, account data or device was inspected.

The smallest independent next prerequisite is four core environment/storage paths. A usable account-session facade requires the additional bounded source paths listed below. They are proposed allowlists for review; no product edit is authorized by this document itself.

## Concrete original composition

Use one process-owned original runtime. Present the existing original authentication flow through a narrowly parameterized `ApplicationCoordinatorView`, retaining its original `ApplicationCoordinatorViewModel`. Persisted login must execute that model's existing `loginProcess`: BasicUserInfoStorage -> SeedService.obtainSeed -> the registered AuthServiceProtocol.walletRecovery -> selectAccount. Interactive login remains `AuthCoordinatorView` -> `LoginCoordinatorView`/`JoinCoordinatorView` and the original LoginViewModel/LocalAuthService/SeedService/native account events.

The real Factory registration is `PinkhaHanlinAuthService(base: AuthService())`, not a directly constructed AuthService. Preserve this registration, its parent OriginalAuthAttempt, Hanlin account closure/resume and successful-stop-required state, the native AccountSelect/Create/Stop transition, and LoginStateService's captured startup/subscription/drain sequence. No new authentication engine, substitute account flag or direct BasicUserInfo assignment is needed.

For the embedded flow, the coordinator's initial content is a loading view and its existing application-state service receives the original `.launch` transition only after runtime setup. The existing loginProcess then routes missing credentials to original auth. Do not run the standalone InitialCoordinator's app-icon migration or crash-directory sharing UI in the host. This is a presentation entry seam; the seed/account selection implementation is unchanged.

After the original model reaches home through completed original authentication, the embedded home content uses the existing `QuickCaptureSpacePickerView`. That view is a neutral list/search/selection component: it takes original SpaceView values, selectedSpaceId, draftSpaceIds, isProcessing and an onSelect closure. Supply an empty draft set and actual current ParticipantSpacesStorage.activeParticipantSpaces data, with editable regular Spaces displayed. Do not reuse the Gallery picker, which includes gallery analytics and an install-to-new-Space action. Do not enter the full SpaceHubCoordinator, whose application shortcuts, sharing, notification, quick-capture and deep-link behavior is outside this account/Space selection UI.

The picker returns selection data inside the original framework. The owned coordinator invokes the existing `ActiveSpaceManager.setActiveSpace(spaceId:)`, then obtains `currentOriginalActiveSpaceSelection()` from the concrete original manager. That method returns the private original selection attempt; a Space ID or picker row never substitutes for it. The original setActiveSpace path still captures the account/SpaceView, invokes WorkspaceOpen under that capture, waits for real operation drain, validates returned identities, starts original type/property subscriptions and executes its existing PinkhaBootstrapHook. The UI's `SpaceView.spaceType == .regular` filter is only presentation: the model has a fallback for absent type data, so actual native schema/permission validation remains mandatory.

Call the already-composed `OriginalActiveSpaceSelection.registerOriginalAnnotationSchema(onDrained:)` under the same current selection. Retain its actual drained history and require the ordinary successful response plus current-source validation before producing the closed ready session. A response after cancellation or selection retirement cannot make the session ready, even if native schema application actually occurred. The native Lib export, generated Invocation and this call still require their genuine composed Apple qualification.

The public facade returns a closed account/selection session, with a private initializer and no account ID, Space ID, mnemonic, repository URL, capture token or qualification credential as authority input. Read-only identity data can be exposed for display. Its later editor/import methods remain a separate patch after the native and local saved-source contract is complete. The existing public Binding and openExistingEditor behavior stay intact.

## Proposed source allowlist

### Prerequisite E1: immutable embedded storage/environment

| Path | Proposed bounded change |
| --- | --- |
| `Modules/AnytypeCore/AnytypeCore/Utils/OriginalRuntimeEnvironment.swift` (new) | A process-sealed deployment context with the original standalone default and an explicit embedded-editor mode. Installation is permitted only before the first original environment/storage consumer; first use seals the chosen context. Validate the configured host group/container and retain an immutable fixed namespace. Conflicting/late installation fails. This is deployment configuration, not account or source authority. |
| `Modules/AnytypeCore/AnytypeCore/Utils/TargetsConstants.swift` | Resolve the app group through that sealed context; preserve both existing Anytype debug/release defaults for the original app. |
| `Modules/AnytypeCore/AnytypeCore/Utils/UserDefaultWrapper/UserDefaultByAppGroupStorage.swift` | Capture the sealed context during initialization. In embedded mode use the fixed original-editor namespace in the real host group and any intended same-namespace standard store; never migrate bare host keys such as userId. Preserve the original standalone migration/write behavior exactly. |
| `Modules/AnytypeCore/AnytypeCore/Utils/UserDefaultWrapper/UserDefaultStorage.swift` | Capture the same context before its cached first read. Apply the fixed embedded namespace to standard-default reads, writes and removals. Preserve the existing original-app keys and lock/cache behavior. |

Both storage classes are necessary. The group wrapper currently initializes its suite immediately and can migrate bare standard-default keys. The standard wrapper separately reads/writes UserDefaults.standard in its initializer and setter. Original settings include serverConfig and UserData.UserInterfaceStyle; changing only the group wrapper would leave the external host's standard defaults unisolated.

The namespace and chosen group must not change during the process, logout or account switch. There is no account migration from the standalone Anytype app. Existing future values under the same explicitly established embedded namespace may be reused on relaunch only through original authentication. A missing/inaccessible group fails before creating a Factory service or wrapper; an optional UserDefaults suite value alone does not prove entitlement access.

E1 does not initialize a wallet, start a service, present UI, open a selected Space or enable importing. Its source controls should cover first-use sealing, same/conflicting/late installation, namespace separation and preserved standalone behavior. No replay of unrelated 245/38 historical controls is proposed.

### E2: owned runtime and original account/Space presentation

| Path | Proposed bounded change |
| --- | --- |
| `OriginalEditorFramework/AnytypeOriginalEditorAccountSession.swift` (new) | The closed facade plus process-owned runtime/session state and retained task handles. Validate resources, deployment configuration and exclusive ownership before resolving original services. Compose actual original handlers/services, retain the original model and frozen selection, and implement source/session retirement and explicit original logout. No import RPC or public source token is added. |
| `OriginalEditorFramework/OriginalEditorAccountSessionView.swift` (new) | Embed the original coordinator/auth views and existing neutral Space picker. Keep current participant data, an owned selection task and a scoped hosting controller. All native operations delegate to original services. |
| `Anytype/Sources/ApplicationLayer/AppCoordinator/ApplicationCoordinatorView.swift` | An internal initializer for the owned model, embedded initial/home content and task ownership. Preserve the existing zero-argument initializer and original app view/task behavior. The external session retains the original account-state/app-state/file-event task handles across presentation dismissal; it does not spawn duplicate handlers in view .task modifiers. |
| `Anytype/Sources/ApplicationLayer/GlobalEnv/KeyboardDismiss.swift` | Add an internal scoped-root/view form that ends editing only in the owned presentation. Preserve the existing window form. |
| `Anytype/Sources/ApplicationLayer/GlobalEnv/PresentedDismiss.swift` | Add an internal scoped-root form which dismisses only descendants presented by the embedded root; preserve the original app window-root form. |
| `Anytype/Sources/ApplicationLayer/GlobalEnv/AppInterfaceStyle.swift` | Add an internal scoped-root form which applies the original preference to the owned hosting controller, not the host UIWindow; preserve the original app window behavior. |
| `Anytype/Sources/ServiceLayer/PushNotifications/PushNotificationsPermissionService.swift/PushNotificationsPermissionService.swift` | Consult the sealed deployment mode at the existing notification-registration/request/unregistration boundary. Embedded editor mode does not register, request or unregister the host application's APNs ownership. This applies to all existing original login callers without modifying their authentication logic. |
| `Anytype/Sources/ServiceLayer/Auth/LoginStateService.swift` | In the existing captured startup/stop sequence, keep the original account/SpaceViews/Participants/profile/permission and other native subscriptions intact. Explicitly scope only standalone application side effects (StoreKit transaction listening, notification icon/badge starts and their matching stop/clear calls). Preserve actor-owned task admission, retirement and real drain; no replacement subscription owner is introduced. |
| `Anytype.xcodeproj/project.pbxproj` | Add only the two new framework facade files to the existing original framework target. The shared Anytype sources remain in its existing synchronized source groups. Keep AppScene as the only excluded app entry point. Retain exact project/diff correspondence for the later build packet. |

These nine E2 paths plus the four E1 paths are the complete proposed product allowlist at this review stage. If implementation exposes an additional concrete dependency, report it before extending the list. No edits to AuthService, PinkhaHanlinAuthService, SeedService, KeychainStore, LocalRepoService, ActiveSpaceManager, the generated RPC outputs, current native Lib pins, existing Host/source-binding implementation or qualification SPI are proposed.

The old retained framework profile must remain an authentic record of its source. A later new-build admission must record this new product diff and its new source/ABI identity; it cannot silently rewrite the old original-tree pins and transfer their qualification.

## Runtime initialization and task ownership

The owned bootstrap performs the following sequence:

1. Inspect the actual main bundle configuration and the original framework/resource closure before any original service resolution. Validate that the declared CompilationCondition matches the distributed framework configuration and that the configured host group resolves through the actual signed application container API. Reject an unowned/previously initialized original runtime or an unrelated installed Invocation handler.
2. Install/seal E1, then resolve the existing Container services. Retain the original MiddlewareHandlerConfigurator instance, configure it once, and register the existing original text-attachment view provider. Start the original additive MiddlewareEventsListener. Await the original AccountEventHandler and FileErrorEventHandler subscription installation before account recovery can produce events. Keep one process owner; do not reset Container scopes or replace the auth/account/native services.
3. Retain the actual original ApplicationCoordinatorViewModel and its long-lived original app-state/account-status/file-event tasks. Install the scoped presentation environment on the owned controller. The callback/task owner outlives a successful login view dismissal so account deletion/status handling is not accidentally tied to the transient UI.
4. Execute the original persisted or interactive route. Any original migration/deleted-account branch remains its actual original view/state path. Account data becomes current only through original AuthService/native return, real transition release and original subscription completion.
5. Present the existing picker using original participant data, run the original active selection, freeze its actual source and call the genuine selected-Space schema registration. Validate before and after suspension and before delivering the session.
6. Retain the closed session's lifetime separately from the process/account owner. Returning a session does not manufacture the local Maktabah saved-revision/source owner or authorize arbitrary imports. The later closed source boundary must intersect it with the original captured host source and use the already-factored internal makeHost path.

The bootstrap deliberately does not invoke the whole AppConfigurator. That configurator also installs Sentry/analytics/audio/iCloud/Firebase and application global services. It does not install an AppDelegate or notification-center delegate, change the host window, run unrelated background services or override the Factory auth registration. The existing original core methods are composed directly and remain the implementation.

The account event listener is additive and process-owned. Keeping it for the lifetime of the single embedded original runtime avoids a second startup and does not imply an open account. A future runtime teardown must only remove its owned registrations where the original API supports it. The session cannot clear a global handler belonging to another owner.

## State, cancellation and retirement

| State | Admission and transition rule |
| --- | --- |
| Unconfigured | No original service, defaults migration or authentication task has run. Resource/deployment validation may fail without creating a session. |
| Configured | The storage context and one original runtime owner are fixed. No user/account identity is inferred from configuration. |
| Authenticating | Original persisted login or actual original UI owns WalletRecover/AccountRecover/Select/Create. The owned task/presentation cannot return a session early. |
| Selecting | The original authenticated account/subscriptions are current. The picker supplies data; WorkspaceOpen and the private original selection attempt establish the actual selected source. |
| Registering schema | The exact original selection, account generation, participant/SpaceView permissions and native call history remain captured. Cancellation/retirement prevents ready admission; real native completion remains historical evidence. |
| Ready | The private session contains the real frozen selection and current source. Each future Host/import admission must intersect it with the exact saved local source and named RPC permission. Identity strings alone grant nothing. |
| Retired | New selection-bound actions and Host construction fail synchronously. Already-admitted work keeps its historical owner/handle until original real completion/drain. A retired object is never revived by matching IDs or a later account generation. |
| Stopping / failed stop | Explicit logout uses the registered original AuthServiceProtocol.logout(removeData:false). Actual AccountStop happens before joining the retired startup; preserve the original successful-stop-required failure state. Do not declare stopped because a Swift task or view ended. |
| Closed | This session's own operations are drained/released. Closing a ready presentation/session does not erase persistent repository or credentials. Account logout is a distinct original operation. |

Cancellation of a pending bootstrap must request the original non-destructive Back/logout(false) path when it owns an actual pending startup, and await/retain its real result. View dismissal alone cannot complete that work. An explicit logout must remain possible after a failed stop. Account deletion or changing the actual account/selected Space retires the closed session by original lifetime observations, not solely a display-state comparison.

On process restart the session is gone. The same signed application's persisted original repository/defaults/Keychain may be recovered by the actual original login route, producing new lifetimes and a new selection. Previously saved annotation mapping/provenance is data to compare after recovery, not a serialized capability.

Native owned-import Cancel/Observe/Release is still a separate contract. Those operations must remain available for already-owned historical handles after source retirement without minting fresh current-write authority. Drain means the native operation's actual Done/Result, not a Cancel response or early ObjectImport return.

## Deployment and device prerequisites

| Boundary | Source work that can be prepared | Evidence still required |
| --- | --- | --- |
| Application group | E1 can support the existing declared Maktabah iOS group, `group.com.davidpovarsky.chavrusatext`, with a fixed original-editor namespace. The inspected entitlements also declare `group.com.davidpovarsky.itorah`; neither Anytype group is declared. | Actual final app signing/provisioning and successful container access. A source entitlement declaration is not a signed entitlement or access proof. |
| Defaults/environment | E1 can isolate both wrappers. Host integration can explicitly provide CompilationCondition matching the distributed framework. | Current Maktabah iOS Info/build settings have no CompilationCondition. The final built main-bundle value and first-use order must be observed. CoreEnvironment otherwise defaults/caches debug. |
| Seed Keychain | Reuse the original SeedService query and Security-backed storage unchanged. Its service/account are `com.anytype.seedPhrase` / `AnytypeSeedPhrase`, with device-only after-first-unlock access and no shared access group. | Genuine original login/recovery and persisted relaunch in the final signed host. No access to another installed app's seed is assumed or attempted. |
| Notification crypto | Embedded mode can keep the unrelated original notification-encryption event handler out of this account UI. | EncryptionKeyService separately uses TargetsConstants.appGroup as its Keychain accessGroup. An app-group filesystem check alone cannot qualify that Keychain path; it is not part of the proposed editor bootstrap. |
| Local repository | Reuse LocalRepoService's existing Application Support/Anytype/middleware-go under the host sandbox. | Actual native wallet/account open and relaunch against that persistent host repository. No disposable directory, path parameter, silent switch or automatic erase. |
| Local authentication | Present the original login/local-auth UI. | Maktabah's inspected iOS Info/build settings lack NSFaceIDUsageDescription. The eventual host integration must supply the original purpose in the main app's appropriate localized Info metadata, then verify real supported device behavior. Resource strings inside a framework are not proof of the host's built permission metadata. |
| Presentation | Add only scoped controller forms for original dismiss/keyboard/style environment helpers. | Real iOS presentation, original auth accessibility, cancellation and dismissal/host-window behavior. Do not call setupGlobalEnv, whose window-root effects are application-wide. |
| Resources/native linkage | Keep the original asset/font/localization/package closure, original Invocation, exact generated clients and native Lib export. | New exact-source compile/link and real Apple runtime for the final schema/bootstrap/import ABI, followed by appropriate device slices/signature/rpath evidence. Pending de631 EN/HE runtime does not transfer to this product. |
| Host-owned source | The account session and previously reviewed captured-selection restriction can be composed in source. | The actual Maktabah repository/scene/profile/annotation/revision owner, save CAS and invalidation must reach the closed Host through the accepted concrete source boundary. An account session alone is insufficient. |

No broad host-project activation is part of E1/E2. The eventual Maktabah host metadata changes are limited candidates in `Source/iOS-Info.plist`, its existing iOS build configuration and EN/HE InfoPlist localization if applicable, to be owned with the actual integration. Do not add Anytype's entitlement groups or unrelated capabilities as a shortcut.

## Exact import/reopen dependency

The current original qualification importer uses updateExistingObjects=false and a newly owned private target Space, checks root oldAnytypeID and uniqueKey collisions and requires real completion/mapping/ObjectShow. It does not establish production import safety in an existing selected Space. The native owner has directly traced original whole-graph matching and reused-object reset behavior; all imported object collisions need a defined disposition.

A genuine new imported graph could be adopted only after original native mapping, bounded mapping-aware readback and the same current local saved-source checks. The existing historical archive comparator is strictly same-native-identity: it compares root/Space, exact object IDs and complete bytes. Do not relabel that comparison as remapped-graph proof, alter the original archive provenance to fit, or import again after an unknown outcome.

The closed bootstrap intentionally adds no update flag, file path, arbitrary native object constructor or import-success callback. Native terminal mapping is not proof of a fully applied body, source CAS or Host acknowledgment.

## Verification and activation order

First review E1's exact bounded source diff and genuinely affected storage/control cases, preserving original-app behavior. Review E2 separately against actual original methods and lifetime ordering. Source controls or portable syntax checks do not qualify UIKit, Keychain, native account boot or permission APIs.

Compile/link the final original framework and native schema/owned-import ABI on Apple once the exact native producers are qualified. Then exercise genuine first login/recovery, persisted relaunch, actual regular-Space selection/schema registration, source/account/permission retirement and actual owned-import cancellation/drain. Retain any real post-cancellation native outcomes without turning them into new authorization.

Use the existing Stage B mounted original editor saved edit/reopen/new-PID case as its own gate after its actual retained SDK runtime is accepted. Production bootstrap/native/device acceptance remains separate; it needs the final source and genuine persistent account route. No source-only plan, public symbol appearance, synthetic account or qualification resume credential can satisfy those runtime gates.
