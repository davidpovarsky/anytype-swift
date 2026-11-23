# Proposed closed Host boundary after schema composition

This is a bounded implementation design awaiting review of the native owned-import protocol. The only implemented product composition on this branch is the eight-file schema/Invocation/selected-Space patch. No method described as proposed below exists yet or grants runtime qualification.

## Base and existing originals

Use product composition `59d229f2e57b6e868d817696d4609e1ed170a6c9`, based on SDK control `4aa7b02b8e4cb8c124dd59ddb656746481d9aa6a` and original framework product source `de63125b97cd5b91a1fa4f4b71d03738076e735f`. This keeps the original editor, prepared-session factory, write owner, source lifetime and public identity Binding. The exact 4909542 selected-Space hook and authenticated generated client are already composed.

Existing authoritative types are `OriginalActiveSpaceSelection`, its private attempt and frozen capture, `EditorDocumentWriteSourceBinding`, `OriginalParticipantEditPermission` and `OriginalSpaceViewPermission`. The source binding's `requiringSpaceEditPermission` uses the exact original native policy and actual account capture. Its `performOperation` carries named-RPC admissions and existing drain tracking.

`AnytypeOriginalEditorSnapshot` is immutable payload data with provenance and archive hashes. Its public decoder is not native import admission. `AnytypeOriginalEditorBinding` also carries identities only. `OwnedQualificationSpace`, qualification bootstrap/import and process-resume APIs remain simulator-only; they are not candidates for promotion.

## Proposed smallest Swift changes

| File | Proposed bounded change |
| --- | --- |
| `Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/EditorDocumentWriteOwner.swift` | Add one internal restriction on an existing source binding. Require its private account capture; obtain `selection.capture(matching: accountCapture, spaceId: selectedSpaceID)`; append that exact frozen capture through the existing private restricting initializer. Preserve all original captures, parent lineage, named-RPC restriction and host-currentness predicate. Validate before and after. Do not create a replacement selection lifetime or compare account strings as authority. |
| `OriginalEditorFramework/AnytypeOriginalEditorSelectedAnnotation.swift` (new) | Add the closed production Host session and a host-persistence source descriptor. The descriptor contains profile/annotation/revision/source/body commitments and is data only. The session has no public constructor, accepts no account/Space selection strings or caller completion flags, obtains the current original concrete ActiveSpaceManager selection and real account lifetime, and freezes the actual permission captures. It retires synchronously when host source or selected original ownership retires. |
| `OriginalEditorFramework/AnytypeOriginalEditorHost.swift` | Factor the existing original controller/session construction into a shared internal path. The new closed session supplies the fully captured source binding to `PreparedEditorPageSessionFactory.prepare`. Keep the public existing-object method and its current behavior. The original coordinator, controller, Host and one-mount check remain the actual UI. |
| `Anytype/Sources/Pinkha/Torah/Annotations/OriginalAnnotationSelectedImport.swift` (new, after native contract) | Adapt only the genuine generated owned-import protocol to the closed session. Own the admitted archive bytes, exact source/attempt and native handle; request cancellation without declaring completion; retain actual Done/Result history; require the actual parser root mapping and original current ownership before making an editor binding. Do not use ordinary early-return `ObjectImport` as a terminal result. |

These four paths are a proposal, not an approved edit allowlist. Any exact public API/compiled-profile additions belong to the later new-framework producer and must be reviewed from the final native/generated composition. No Maktabah product edit is part of this patch.

## Why the fully captured binding must reach the original editor

The current public `openExistingEditor` correctly builds its own host/account source binding for an explicitly existing object. Calling it after a one-time selected-Space check would not put the selection and permission generations into the actual original RPC admission captures. The proposed internal path carries the existing host source, exact account capture, selected attempt and both permission captures through the original prepared session and write owner. A later equal account ID or newly minted permission snapshot cannot revive a retired session.

The host source descriptor must be captured from the actual saved annotation owner. Its `sourceIsCurrent` observation remains synchronous and without database/network side effects, as in the existing Host API. It proves host persistence currentness only. Native account/Space authority still comes from the original selected owner and actual native admission.

## Native protocol contract to resolve with its owner

The retained native source at `455e1c55d765b25f8dd63bd472964057e5cbffc7` supplies application-private `prepareOwnedAccountImport`/`startOwnedImport` and `OwnedImportOperation.Start`, `RequestCancel`, `Done` and `Result`. Application admission verifies the actual retained app, wallet account and usable matching account-directory lease before registration. Result becomes observable only after the actual original Execute, finalizer and mapping copyout return. That constructor does not supply archive/ACL/attempt authority and currently has no production RPC caller.

The native owner must choose and qualify the exact generated start/cancel/observation contract. The current generated mobile wrapper uses `context.Background()`. The original Swift Invocation dispatches through `DispatchQueue.global(qos:).async`; RPC calls are not serialized by that queue. Swift cancellation still does not supply native cancellation or drain. Bounded start plus nonblocking status/cancel, with an actual native completion notification as a wake-up hint, is a candidate contract; the authoritative result must come from the registered operation's real Done/Result. Names, payload fields and retention behavior must match the reviewed native contract before this Swift adapter is written.

Required ownership properties:

1. Start accepts exact bounded archive bytes or a newly native-owned staged archive, never an arbitrary caller path as authority. Parser/root-map provenance must come from this original execution. The target is the actual selected original Space, and native membership/ACL must still pass.
2. The host attempt binds the saved source revision/body/source witness, exact selected account/Space capture and once-owned archive. Expected IDs are comparisons. A caller-provided UUID, digest or matching name cannot substitute for native admission.
3. Registration precedes native Start. The closed returned native handle retains the actual app/account/Space and attempt. Repeated Start must neither retry an uncertain create nor create another operation.
4. Cancel requests cancellation on the admitted original handle. Swift task cancellation, RPC return, native cancellation request and terminal drain remain four different observations.
5. Source retirement stops new writes and mounting. Already admitted native work and its copied terminal history remain owned until the actual operation and original dispatch admissions drain. A special closed cancel/history path must target only that owned handle; it must not re-enable ordinary dispatch through a retired SourceBinding.
6. Only actual terminal native mapping, file observations and original persisted readback may identify the imported root. A successful import result alone is not semantic body equality, a current lease or ACK. The old qualification observer's exclusive disposable-account assumptions do not apply to production.
7. On ambiguity, timeout, permission/source loss or partial mutation, retain the exact attempt/history and leave the local annotation commit unresolved. Do not silently retry, delete native objects or claim rollback. Host CAS and final body/readback acceptance remain separate.

A blank saved annotation needs the existing original blank-object creation route with the same closed source and schema ownership. It must not be represented by fabricated importer bytes or seeded qualification fixtures. That sibling operation's exact native call and required readback should be included when the production contract is reviewed.

## Affected qualification only

The next actual gates must bind the final full source, not the old de631 binary: genuine native endpoint/owned-import terminal evidence; exact new native Lib exports and generated Swift symbol linkage; real Invocation response/error/drain behavior; selected account/Space/permission/source retirement before and after admission; and genuine original imported-root edit/capture/readback through the downstream saved annotation owner. New controls should cover the new composition boundaries, while retaining prior source-bound outcomes without replay.

The device gate additionally needs actual iOS device slices for the same native/dependency composition, appropriate signing/provisioning, real import/link/resources and original editor acceptance. Debug simulator SPI and ad-hoc simulator products provide no device result. Live exchange and ACK stay unenabled until their own actual criteria pass.
