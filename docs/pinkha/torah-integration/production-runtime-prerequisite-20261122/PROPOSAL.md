# Original production runtime and selected-Space prerequisite
Date: 2026-11-22. Source-only bounded audit; no product edits, native calls, account reads, tests, build dispatch, entitlement changes, runtime creation or capability issuance.

## Frozen inputs
Anytype producer: 56d5d0b68d9d46b93ea31fdc69873d5f1d9ee793. Current actual producer run: 45003378181, with sole observer job_725e7ed4038b. This audit does not change that input.
Maktabah source snapshot: a17d696da53e358d1e0e486cdfa761e3093632b5.
SOURCE_INDEX.json identifies complete original source snapshots by immutable Git blob and SHA256. Search-only facts are retained separately and explicitly scoped.

## Existing real editor entry and its prerequisite
OriginalEditorFramework/AnytypeOriginalEditorHost.swift exposes openExistingEditor outside the DEBUG/simulator guard. It requires the real original AccountManager account, matching BasicUserInfo usersId, captured original account/source lifetimes, and an actual already-created native object in its Space. It uses the original prepared page session/coordinator/view. The caller binding is an identity request, not an account or Space authorization certificate.

The existing qualification runtime is wholly DEBUG && targetEnvironment(simulator). Its admitted bundle/process, empty account/user defaults, fresh exclusive repository, original local-only WalletCreate/AccountCreate, one claimed process and no reset are intentional acceptance boundaries. Those guarantees do not initialize an existing production account or authorize reuse of a caller-selected account/Space.

## Concrete original runtime path
AuthService is the original boundary for wallet/account creation, recovery, selection and logout. It delegates to AuthMiddle with the original server configuration, original AccountWriteTransition and named RPC binding. BasicUserInfo and AccountManager updates occur through that original path. LoginStateService owns middleware configuration plus the original account services/subscriptions and their logout cleanup. The original AuthCoordinator/LoginCoordinator/InitialCoordinator use these services and the original local authentication/seed/recovery flow.

LocalRepoService selects Application Support/Anytype/middleware-go through the original file-location implementation. No repository or credential data was accessed in this audit.

AppConfigurator also invokes analytics, Firebase, Sentry, UI/media and other application-global configurators. Exposing or replaying that complete aggregate inside Maktabah is not a bounded SDK bootstrap. MiddlewareHandlerConfigurator installs the original global Invocation handler; GlobalServicesConfiguration retains the original event listener and starts other original handlers. A production adapter must explicitly retain and factor the required original components with their real ownership/cleanup, rather than constructing a second backend or replacing global handlers without ownership.

Recommended implementation boundary: a separately reviewed original runtime host component that admits the host storage/configuration before constructing those original services, retains their original instances, presents the original authentication/launch route, and observes the actual AccountManager transition. Its opened-account result must be derived from the original service outcome and lifetime; the host must never set AccountManager or BasicUserInfo from its own DTO. A public API name or constructor is not committed by this document.

## Actual host storage prerequisite
TargetsConstants selects group.io.anytype.app.dev or group.io.anytype.app from CoreEnvironment. CoreEnvironment reads CompilationCondition from Bundle.main, caches its first result, and defaults to debug when the key is missing. Therefore a framework compile configuration alone does not choose the host storage group.

The immutable host search for CompilationCondition in Source, Maktabah.xcodeproj and ChavrusaText.xcodeproj returned no match. The five tracked host entitlement files all list other group IDs. This is a source configuration mismatch, not a claim about a signed device artifact or an executed runtime failure.

The original UserDefaultByAppGroupStorage is a critical qualification: it captures the selected suite when constructed, falls back to UserDefaults.standard and migrates that value, and writes both stores. It does not validate an entitlement. BasicUserInfo uses the generic userId and analyticsId keys. Consequently the absence of the original group must not be described as proof of a startup failure, and a stored identifier cannot be treated as authenticated runtime authority.

Before a production host bootstrap, define a bounded original storage configuration/migration contract that uses a genuinely admitted host group, is fixed before CoreEnvironment/storage first use, preserves original standalone Anytype behavior, and prevents accidental adoption of unrelated host default values. Do not add another app's group entitlement blindly. Device/container/signing validation and any migration behavior remain unimplemented and untested.

## Concrete selected-Space gap
Anytype/Sources/ServiceLayer/ActiveSpaceManager/ActiveSpaceManager.swift is the original selection manager. At this frozen source, setActiveSpace assigns activeSpaceId, cancels a previous Task, and starts a new Task which awaits WorkspaceOpen, widgets preparation and type/property subscription startup before publishing AccountInfo. It has no attempt/account lifetime check at those publication boundaries. Its error path unconditionally clears current selection. stopSubscription clears cached selection/streams but does not cancel or drain setActiveSpaceTask.

A source-derived interleaving is possible: start A suspends in an original service; selection B or stop happens; a non-cooperative A continuation resumes and publishes stale AccountInfo or clears B. This audit did not execute the interleaving. The existing throttled SpaceViews publisher also cannot establish immediate permission revocation. Its current cached workspaceInfo is not an opaque destination authority.

WorkspaceService.workspaceOpen forwards the requested Space and withChat flag to the real generated RPC and returns result.info.asModel. AccountInfo contains accountSpaceId and spaceViewId; its Identifiable id is a hashValue, not native identity. The wrapper itself does not compare the returned accountSpaceId with the request.

Recommended narrow next change, separate from the current producer: fence the original manager's selection attempts and shared-service startup/stop before suspension; capture the actual original account lifetime at selection; retire old selection synchronously before replacement/stop/account retirement; settle and drain owned startup/cleanup so an old continuation cannot start or stop shared dependencies belonging to the new selection; admit publication only for the exact current attempt and fresh original WorkspaceOpen response with accountSpaceId equal to the requested Space and a consistent actual SpaceView identity. Stale/failure/stop continuations may clean only their owned attempt. Do not rely on Task.cancel alone.

Only that original successful selection boundary may mint an opaque, privately constructed passive selection capture. It must retain the exact original account and selection lifetimes, not recapture an already invalid generation. Any subsequent dispatch still requires actual Participant and SpaceView permissions and the unchanged native SpacePermissions.canEdit predicate, source/scene lifetime and exact native request restrictions. A selected-Space capture by itself grants no object create, schema write, identity mapping or ACK. Existing-object document Owner must not be borrowed as the authority for a new annotation.

The first implementation review should include the complete manager, callers, original shared-service cleanup and the source-bound candidate before tests. New focused controls should prove paused old selection versus replacement/stop, stale errors, account transition, canceled startup and exact response mismatch. They must use the actual actor/lifetime wiring with explicit RPC/UI probes. Those would be new gap controls; no previously passing Participant/Space/composition/SQLite suites should be replayed.

## Device acceptance is a separate required product
The generated original framework target supports iphoneos and iphonesimulator, but the actual current acceptance driver fixes the SDK/destination/product paths to iOS Simulator and requires vtool IOSSIMULATOR. Existing narrow signing exceptions reject device use. These observations are from the retained scoped source search; they do not prove a device build.

Keep the current Maktabah DEBUG/iOS Simulator guards and current strict simulator admission. After genuine simulator qualification, add a separately source-bound arm64 IOS/Release build, original dependencies/resources and genuine signing/platform/device admission. Do not relabel or widen acceptance of a simulator product. A successful StageB on its current route will not prove production/device embedding.

## Sequence and open dependencies
1. Preserve and complete the currently frozen genuine producer run; triage terminal evidence before any next source seal.
2. True-merge reviewed original component/held-read changes on the root-owned integration branch, preserving original provenance and all exact-input passing evidence.
3. Implement the separately reviewed original runtime/storage and selected-Space boundaries. Preserve user-owned original accounts and authenticate via the original path.
4. Original schema persistence/recovery, actual annotation classification, held original readback and local durable mapping/body-ACK remain separate dependencies. Current metadata decoder or permission composition does not authorize native creation.
5. Qualify a genuine device product and original runtime with actual signed host evidence, then exercise production user/Space switch and lifecycle behavior.

No runtime, storage, selection capability, device framework, schema write, identity receipt or production transport has been added or qualified by this audit.
