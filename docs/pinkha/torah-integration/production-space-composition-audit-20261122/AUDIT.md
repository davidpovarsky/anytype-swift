# Original full Space authority: source composition audit

## Scope

This is a read-only source audit retained after Space evidence HEAD `af987cd17494c6b456efaed591e1a30ca4c1d09a`. It changes documentation only. The passed Space packet and its index remain byte-identical. No test, build, RPC, schema change, identity writer, receipt factory, or ACK was executed or added.

The two prerequisites are separate published inputs: Participant source `56f896321686f3a929383b49a207c60d67104d31` (evidence `ab0feb2b34dcacf64084e9e9787ddb828da155ea`) and Space source `37731bcfdfda320b3a58356b54719e904c399810`. This audit does not claim that their composition has compiled or passed runtime acceptance. [SOURCE_INDEX.json](SOURCE_INDEX.json) binds 17 complete source files by immutable commit, Git blob, SHA256, size and exact symbol lines. [VERIFICATION.json](VERIFICATION.json) records the preserved source and packet trees.

## Frozen account and operation boundary

`EditorDocumentWriteSourceBinding` owns a **private frozen `accountCapture`** (line 219). Its initial constructor captures the original account lifetime once. The existing inheriting path retains that same account capture and source lifetime, and explicitly carries an original parent Owner plus intersected RPC restrictions. `channelPinCapture` (265–273) is the existing opaque-permission seam that compares a permission with this private capture. The captures array does not identify a substitute account authority. [source_binding]

The next internal composition should validate the existing binding; match both opaque Participant and Space prerequisites to that same actual account source/token and byte-exact target Space; evaluate the original permission constructor; and retain both exact captured role/view generations. It must preserve the existing source predicate, parent and named-RPC restrictions. Recreating a SourceBinding from currently matching account values would recapture generations and is not the proposed seam. No caller-supplied role, `canEdit`, account capture or configuration boolean should construct this authority. [source_binding] [participant_prerequisite] [space_prerequisite]

Original `performOperation` (310–345) validates before and after the asynchronous operation, preserves its lease/drain behavior, and supplies the existing Invocation binding. `prepareDispatch` (347–364) validates again, enforces named RPCs and existing restrictions, and acquires the frozen captures at actual dispatch. These are the existing admission boundaries to extend; the audit proposes no alternate dispatcher. [source_binding]

## Original permission rule and configuration source

The original `SpacePermissions(spaceView:participant:isLocalMode:)` derives owner and edit status from the original Participant value. Its actual edit rule is:

```swift
canEdit = participantCanEdit && (!spaceView.isLegacyStream || isOwner)
```

An admin or writer therefore does not gain edit authority for a legacy stream solely from `participant.canEdit`. Account/role/view liveness remains a separate prerequisite, supplied by the opaque captured observations. [space_permissions] [participant_predicates]

The production construction site is `ParticipantSpaceStorage/ParticipantSpacesStorage.swift`, `updateData` (94–100). It obtains `isLocalMode` from its original injected `ServerConfigurationStorageProtocol`:

```swift
serverConfigurationStorage.currentConfiguration().middlewareNetworkMode == .localOnly
```

`ServicesDI` registers this storage as a singleton. The implementation returns its existing `UserDefaultStorage<NetworkServerConfig>(key: "serverConfig", defaultValue: .anytype)`. The original mapping is `.anytype → .defaultConfig`, `.localOnly → .localOnly`, and `.file → .customConfig`. A future hook using the constructor should read this real source internally, not accept a caller assertion. In the audited source, **canEdit itself is independent of isLocalMode**; other rights such as sharing, leaving and permission editing are not. This audit establishes no new configuration lifetime and does not generalize edit admission to those rights. [original_permission_construction] [server_configuration] [network_mode_mapping] [configuration_di] [space_permissions]

## Selected Space and existing-object limits

`Host.openExistingEditor` (225–280) claims its actual host source lifetime, checks both original AccountManager and BasicUserInfo account identities, captures the original account lifetime, and gives that exact SourceBinding to the prepared original session. Its contract opens an explicitly bound **existing object**; it does not select/authenticate an account, create a repository, or materialize a destination object. A new-object operation has no original document Owner yet and cannot borrow an unrelated document Owner as its destination authority. [host_open] [account_source] [basic_user_info]

`ActiveSpaceManager` stores an active Space ID, task and published AccountInfo cache. It awaits the real `WorkspaceOpen` and subscription preparation before publishing. The audited source provides no captured selected-Space lifetime. Its UI cache/stream, and the throttled combined ParticipantSpaceViewData cache, must not be promoted into opaque destination authority. A valid Space permission proves that Space's current source restrictions, not that the host still selects it. A facade dependent on global active selection needs a genuine host-selected source generation or separately reviewed original selection hook. This is a future contract requirement, not a reproduced defect in the current manager. [active_space] [workspace_rpc] [original_permission_construction]

## Held-read and durable mapping limits

The current raw `OriginalAnnotationObjectReadback.readFreshDetails` returns ObjectDetails **after** `withExclusiveRead` has returned. That value is observation only, not a held-read identity receipt or local mapping permission. [raw_readback]

The retained production contract requires any future native receipt consumption to remain inside the actual original exclusive-read lineage: acquire the existing SQLite serialization; invoke original synchronous admission with explicit `requiresEditing: false`; validate the exact pending delivery/source/revision and commit at the actual outer transaction boundary; then return while the native read lineage remains held. No await belongs inside that database transaction. Original default synchronous admission requests mutation and cannot upgrade a read lineage. A completed local COMMIT followed by `completedWithoutOwnership` remains a durable fact without current-owner success publication; it cannot authorize rollback-by-assumption, recreation or ACK. Existing primitive controls are not acceptance for a future native receipt adapter. [source_binding] [production_contract]

The root owns combined integration; the Anytype author owns the next internal composition after producer priority. This audit leaves the production facade, actual selected-destination grant, native annotation identity, body receipt and mapping writer unavailable.

[source_binding]: https://github.com/davidpovarsky/anytype-swift/blob/af987cd17494c6b456efaed591e1a30ca4c1d09a/Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/EditorDocumentWriteOwner.swift
[space_permissions]: https://github.com/davidpovarsky/anytype-swift/blob/af987cd17494c6b456efaed591e1a30ca4c1d09a/Anytype/Sources/ServiceLayer/ParticipantSpacesStorage/Model/SpacePermissions.swift
[participant_predicates]: https://github.com/davidpovarsky/anytype-swift/blob/af987cd17494c6b456efaed591e1a30ca4c1d09a/Anytype/Sources/Models/Extensions/Participant+Extensions.swift
[participant_prerequisite]: https://github.com/davidpovarsky/anytype-swift/blob/56f896321686f3a929383b49a207c60d67104d31/Anytype/Sources/ServiceLayer/ParticipantStorage/ParticipantsStorage.swift
[space_prerequisite]: https://github.com/davidpovarsky/anytype-swift/blob/37731bcfdfda320b3a58356b54719e904c399810/Anytype/Sources/ServiceLayer/SpaceStorage/SpaceViewsStorage.swift
[original_permission_construction]: https://github.com/davidpovarsky/anytype-swift/blob/af987cd17494c6b456efaed591e1a30ca4c1d09a/Anytype/Sources/ServiceLayer/ParticipantSpaceStorage/ParticipantSpacesStorage.swift
[server_configuration]: https://github.com/davidpovarsky/anytype-swift/blob/af987cd17494c6b456efaed591e1a30ca4c1d09a/Anytype/Sources/ServiceLayer/ServerConfigirationStorage/ServerConfigirationStorage.swift
[network_mode_mapping]: https://github.com/davidpovarsky/anytype-swift/blob/af987cd17494c6b456efaed591e1a30ca4c1d09a/Anytype/Sources/ServiceLayer/ServerConfigirationStorage/NetworkServerConfig.swift
[configuration_di]: https://github.com/davidpovarsky/anytype-swift/blob/af987cd17494c6b456efaed591e1a30ca4c1d09a/Anytype/Sources/ServiceLayer/ServicesDI.swift
[host_open]: https://github.com/davidpovarsky/anytype-swift/blob/af987cd17494c6b456efaed591e1a30ca4c1d09a/OriginalEditorFramework/AnytypeOriginalEditorHost.swift
[account_source]: https://github.com/davidpovarsky/anytype-swift/blob/af987cd17494c6b456efaed591e1a30ca4c1d09a/Anytype/Sources/ServiceLayer/Account/AccountManager.swift
[basic_user_info]: https://github.com/davidpovarsky/anytype-swift/blob/af987cd17494c6b456efaed591e1a30ca4c1d09a/Modules/Services/Sources/Services/BasicUserInfoService/BasicUserInfoStorage.swift
[active_space]: https://github.com/davidpovarsky/anytype-swift/blob/af987cd17494c6b456efaed591e1a30ca4c1d09a/Anytype/Sources/ServiceLayer/ActiveSpaceManager/ActiveSpaceManager.swift
[workspace_rpc]: https://github.com/davidpovarsky/anytype-swift/blob/af987cd17494c6b456efaed591e1a30ca4c1d09a/Modules/Services/Sources/Services/Workspace/WorkspaceService.swift
[raw_readback]: https://github.com/davidpovarsky/anytype-swift/blob/ab0feb2b34dcacf64084e9e9787ddb828da155ea/Anytype/Sources/Pinkha/Torah/Annotations/OriginalAnnotationObjectReadback.swift
[production_contract]: https://github.com/davidpovarsky/anytype-swift/blob/ab0feb2b34dcacf64084e9e9787ddb828da155ea/docs/pinkha/torah-integration/production-annotation-20261122/CONTRACT.md
