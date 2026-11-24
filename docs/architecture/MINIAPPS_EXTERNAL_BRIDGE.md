# Anytype external MiniApps bridge

The integration adds a square-grid MiniApps entry beside the original editor controls, in the object menu, in selected-block controls, and in the existing UITextView selection menu. Shared HanlinMiniAppsPicker owns Favorites, visibility, ordering and the new-window preference. Only the lightweight bridge and picker products enter Anytype.

## Context and transport

A nonempty native selection requests replaceSelection. A caret or toolbar invocation requests insert. Input text at a caret is deliberately empty; full document text remains in source.documentText. A MiniApp can explicitly return display, insert, replaceSelection, replaceDocument or custom output.

The real shared container is group.com.itorah.shared. Requests use hanlinminiapps://x-callback-url/run?request=<UUID>; returns use the actual resolved Anytype bundle scheme with host miniapps and path /return. Source metadata binds the original account, Space, object, scene, stable block IDs, UTF16 selection and original text/marks. Selected native files finish copying into the group before launch.

Cold callbacks use the original queued object deep link. Warm callbacks use the actual registered mounted editor. Pending results remain durable until their original document is ready. No private temporary container substitutes for a missing App Group.

## Native writes and replay

The existing BlockActionService performs text changes, insertion and file upload. Text changes retain native IDs, children, styles and unaffected marks. Multi-block/document-body replacement writes returned text to the first affected block and empties subsequent affected text blocks, preserving titles, non-text blocks and the native hierarchy.

A local write-ahead journal holds the original snapshot and exact plan before native writes. Current native content is compared before each write, and openForPreview verifies the saved result. If the original changed, returned output is inserted separately. Native BlockReplace cannot safely replace a block with itself because the original middleware unlinks the target after adding its replacement.

Inserted blocks contain a deterministic request/item ID and a request marker in the same native BlockCreate. Per-block verified progress survives relaunch. Duplicate callbacks resume the saved plan or acknowledge a completed receipt. The bridge is acknowledged only after native readback and a durable completed receipt. Display/error results remain pending until their actual result sheet is dismissed.

The existing text API has no atomic compare-and-swap or combined text/receipt transaction. Fresh preflight/readback and the journal do not claim to eliminate the race with an external concurrent edit between a read and a write.

## Signing identities

| Configuration | Existing identity | Existing group | Added group |
|---|---|---|---|
| Debug / Release-Nightly | io.anytype.app.dev | group.io.anytype.app.dev | group.com.itorah.shared |
| Debug-Anytype | io.anytype.app | group.io.anytype.app.dev | group.com.itorah.shared |
| Release-Anytype | io.anytype.app | group.io.anytype.app | group.com.itorah.shared |

The four original configurations retain team J3NXTX3T5S and their existing identities. Separate Debug-MiniAppsOwner and Release-MiniAppsOwner configurations use the already registered owner family below, under team NA6HPWARQ2. Config/Signing/MiniAppsOwner.xcconfig supplies the identity and native-storage group; no in-app setup is added. Tools/MiniApps/original-configurations.json records all 32 original main/UI configuration blocks, and owner_signing.py verifies they remain byte-identical to the recorded source.

| Owner target | Registered bundle ID |
|---|---|
| Main app | io.anytype.app.NA6HPWARQ2 |
| Share extension | io.anytype.app.NA6HPWARQ2.AnytypeShareExtension |
| Notification extension | io.anytype.app.NA6HPWARQ2.AnytypeNotificationExtension |
| Widget | io.anytype.app.NA6HPWARQ2.homewidget |

The original main-app capabilities are retained in the owner entitlements. The main app requests its private native-storage group and group.com.itorah.shared; Share and Notification continue to use the private native group. The current Widget does not access native shared storage and has no new group entitlement. Main, Share and Notification Info.plists resolve PinkhaNativeAppGroup from the same owner setting, which TargetsConstants reads before its original Debug/Release group selection. Unchanged configurations keep that original selection. This does not migrate or remove existing containers.

The main app also registers its resolved bundle ID as a URL scheme. MiniApps callbacks prefer this unique scheme, so an owner build can coexist with another installed Anytype build while preserving the existing anytype and product aliases.

Apple account audit run45279009510 verified the registered owner family and enabled group capability, but found no visible distribution profiles; subsequent fresh profile discovery found no prior native group grants. The isolated owner configuration declares the intended private native-storage group group.io.anytype.app.NA6HPWARQ2. owner-signing.json explicitly records PENDING_APPLE_GRANT, with null profile evidence. The simulator lane can compile with ad-hoc signing, then requires the actual built entitlements and Foundation/CoreSimulator group directories; it does not use substitute storage. The verifier remains strict by default for signed/device qualification, requiring VERIFIED_OWNER_GROUPS and an authoritative profile-evidence run. The simulator caller explicitly selects structural/configuration validation only, and its receipt retains the pending Apple-grant status. This separation permits real native testing while physical signing is still unproven.

## Validation

Thirteen new PinkhaMiniAppsEditPlannerTests passed on Oracle Swift6.4.3 against the actual bridge package, covering Hebrew/emoji UTF16 replacement, caret insertion, invalid ranges, mark preservation, native block IDs, conflict/replay, attachment identity and durable-plan round trip. A first test-helper compilation error was corrected before 13/13 execution. The initial twelve new/changed Swift source files passed frontend parsing; plists and diff checks also passed.

Run only the new portable suite with:

```sh
python3 scripts/validation/run_miniapps_consumer_tests.py --bridge-package /path/to/Hanlin/Packages/HanlinMiniAppsBridge
```

Logs: docs/validation/20261123-miniapps-consumer. These portable checks do not claim Apple SDK typechecking or an actual two-application native editor round trip; those remain a separate focused gate. Accepted SDK06/component/UI journeys were not replayed.

## Focused Apple acceptance source

The SDK is pinned to a774de24926ca13d563c45c42917d03b8c04296f. A source-only miniapps-native lane extends the existing manual dispatcher through route=wave15-acceptance and acceptance_lane=miniapps-native; no workflow YAML is changed. It uses the unchanged coherent Heart admitted by run45091223011 and the exact companion specified in Tools/MiniApps/producer.json, verifying the actual GitHub artifact, producer manifest and executable hash. Producer run45270839882 failed toolchain/disk preflight before compilation. Run45279691350 at c2791d54 also stopped before compilation when xcodebuild -showdestinations exceeded its dependency-resolution deadline; neither run produced a companion app. Run45285438881 then passed simulator boot and architecture selection but stopped on package-plugin validation before app compilation or the 12 selected cases. Run45292781318 was cancelled while queued with zero executed steps. The replacement producer is run45294462656 at the SDK pin above, with the modal lifetime correction, the shared picker toolbar correction and 14 selected producer cases. The existing authenticated dependency step waits at most 30 minutes for the exact compiled producer artifact; simulator execution does not wait on distribution-profile grants. Signed/device qualification remains separately pending.

The new selection is prepareMiniAppsDocument (one disposable native account/Space/Page), testNativeEditorPickerTextStudioReturnAndColdReopen (two actual producer/editor invocations: a warm return and a return that must launch the terminated source without manual navigation, followed by cold document reopen), testDuplicateCallbackDoesNotInsertAgain, and verifyReturnedNativeDocument (independent saved Heart block count and original identity). The focused lane selects Debug-MiniAppsOwner, validates the resolved owner bundle/private group/shared group, and records the source app's actual App Group entitlements and both completed journals; the two independent request markers and native block counts must survive duplicate callbacks and cold reopen. The fifth method, applySelectedTextAndPreserveNewerNativeContent, validates the native adapter on a second ordinary Page created in the same disposable account/Space. It builds the original editor assembly, replaces a Hebrew/emoji selection through the actual setText/applier, checks the original block ID/tree and unaffected marks, and verifies both completed-request replay and conflict preservation after a subsequent native edit. It also returns a small generated text file through the actual applier and original native upload service, replays the request, closes/reopens, requires exactly one completed native file block, and compares the bytes downloaded through the original content URL with the source bytes. The file object ID, block ID, byte count and SHA-256 are retained. It closes/reopens the document and reads the saved Heart blocks again. A test-owned mailbox inside the actual shared container isolates this controlled adapter input from automatic UI routing. Its separate receipt explicitly records zero producer round trips; the external UI journey count remains two.

Actual execution of all five methods is pending; declaration and syntax checks are not runtime acceptance.

Two focused SDK materialization checks passed: a missing exact pin is fetched into an owned temporary bare repository without changing the supplied shallow checkout, and a mismatched existing snapshot is retained unchanged. Existing workflows can keep their older immutable checkout while the consumer resolves its exact committed SDK pin without changing that supplied repository.

The e12cf1ce snapshot was materialized and hash-verified from the exact committed producer source. All four imported package tree IDs match the prior e3d5a51f pin byte-for-byte, so the accepted 13 planner and 2 SDK checks were not repeated. Exact package IDs, snapshot file count and manifest digest are recorded in docs/validation/20261123-miniapps-consumer/sdk-materialization-e12cf1ce.json. This source/materialization evidence does not claim a successful Apple build or native run.

The a774de24 snapshot is materialized from its exact committed producer source. Compared with e12cf1ce, only the shared MiniAppPicker.swift leaf changed; the Foundation bridge tree is identical. The existing 13 planner and 2 materialization checks remain retained without repetition. Exact old/new file SHA-256 values and package tree IDs are recorded in docs/validation/20261123-miniapps-consumer/sdk-materialization-a774de24.json. The changed picker still requires actual Apple compilation and native UI qualification; neither source hashing nor Linux parsing is recorded as that result.
