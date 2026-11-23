# Proposed closed native import contract

This is a source-level design for review. Names and wire fields below are proposed, not generated or linked APIs. No production route is enabled by this packet.

## 1. Owners and trust boundaries

The Swift closed Host owns the saved annotation revision and source witness. Its original account capture, selected-Space capture, SpaceView and participant permission captures must remain the ones used by the existing original dispatch owner. Public snapshot decoding validates data; it cannot create account, target-Space, filesystem, write or completion authority.

The native application owns the real app pointer, wallet identity and account lease. The original Space and signed ACL supply native membership and permission. Wire account and Space identifiers are expected-value comparisons and routing data. They are never sufficient admission by themselves.

The native importer owns an exact copied archive, its private staging directory, the fixed original PB import request and the existing OwnedImportOperation. It registers that operation with the existing application ownedImports registry before Start. The original Execute, file/upload drainage, finalizer and Result remain the source of completion.

An opaque registry handle is a new native-minted operation lookup token. It is not a progress process ID and does not replace the original Execute trace. Original process.NewNoOp().Id() remains empty. The new token must not be recorded as a fabricated original process ID.

## 2. Wire shape to review after native closure qualification

The proposed nested namespace is Rpc.Annotation.Import. Four commands are sufficient for the initial boundary.

| Command | Bounded request | Result and exact meaning |
| --- | --- | --- |
| Start | Copied archive bytes; archive SHA-256; expected actual account; selected target Space; expected source account/Space/root; closed Host attempt identity and source witness | A native-owned handle after app/lease registration. Acceptance of a handle means owned work was admitted to the lifetime registry, not that native permission, import, body comparison or Host save succeeded. Invalid envelope/budget/app binding fails without starting work. |
| Observe | Native handle only | Running, or Drained with a copied original Result. Drained is derived exclusively from the existing operation's Done. It includes actual cancellation history, native error category, real mapping observation/problems and original identifiers. No body ACK is inferred. |
| Cancel | Native handle only | Requests actual operation cancellation. The response does not claim drainage. Observe remains the only completion observation. |
| Release | Native handle only | Refuses while Done is open. After actual drainage, removes only the native-owned staging/results entry and returns its cleanup outcome. It cannot delete caller-supplied paths or native user objects. |

Start fixes PB, ALL_OR_NOTHING, IsSync, NoProgress, no notifications, no migration/new Space, NoCollection=true, updateExistingObjects=false, and no caller progress implementation. NoCollection is an existing original SpaceImport setting; it prevents an extra generated import collection. It must not be confused with rollback: ALL_OR_NOTHING does not undo already applied native writes.

Error categories should be finite and derived from actual failures: invalid archive; unsupported graph; account/lease unavailable; Space unavailable; permission denied; collision; cancellation; capacity; native failure; drain pending; unknown handle. Mapping observations and wire errors are historical facts. A successful original return is not a semantic body certificate.

Add native handle/attempt lookup to the existing ownedImportRegistry rather than adding another work engine. Its active operation map still prunes only actual Done. Historical entries retain the closed operation and immutable binding after active pruning so Observe/Cancel/Release work after source retirement. Registry capacity must be finite; capacity denial happens before work, and an undrained operation is never evicted. Exact limits belong in the reviewed implementation, not caller request fields.

The same attempt with the same retained binding can resolve to the same in-process handle; a different binding must conflict. This is not a durable exactly-once guarantee across process loss. The Host must retain pending/unknown outcome state and recover a known mapping or establish a genuine no-effects result before allowing a new import. A fresh process cannot infer that an earlier import did not run merely because its in-memory handle is absent.

## 3. Native-owned byte and filesystem admission

Validate before constructing a path-bearing original ImportRequest. The proposed native caps match the existing internal Swift archive layout: 65,536 compressed bytes, at most 512 members, at most 8 MiB aggregate expanded content. Reject over-limit data before allocation or expansion beyond the bound.

Require one complete ordinary ZIP with exact central/local framing, unique canonical UTF-8 names, regular members, valid CRCs, and a supported compression method. Reject absolute paths, backslashes, colon/control/dot components, traversal, symlinks, duplicate or canonically ambiguous names, ZIP64, encryption, hidden/overlapping members and an executable/self-extracting prefix. Bound all lengths, counts and protobuf nesting/map inventories.

Use the actual generated SnapshotWithType and related native protobuf models. Do not write a replacement object parser. Add wire-level ambiguity checks where generated decoding would otherwise accept duplicate map keys or collapse unsupported fields. Unknown or unsupported fields that the original import projection would drop must cause an unsupported-graph result, not a claim of preserved content. Preserve the original raw source bytes and SHA for later readback comparison.

Every actual fileObject source must be an exact admitted files/<single-name> member, with the original fileInfo/fileID requirements and a binary inventory equal to the declared source inventory. URLs, arbitrary absolute paths, missing binaries and extra unexplained binaries fail admission. These checks are necessary even while file import activation remains pending.

Create one private directory with a native-owned name and 0700 mode, write one new archive file with exclusive creation, and retain that ownership internally. Do not expose or accept its path through the wire. The original filename provider may stay unchanged: the only import path is this native-created regular ZIP, every source is a validated relative member, and the converter receives a TempDirProvider rooted exclusively in the same operation-owned directory. There is no shared OS-temp fallback.

Keep raw archive validation independent from app authority. Native Space loading and ACL queries must not run while holding the application Service read lock or registry mutex across callbacks. Prepare/register the real operation under the existing short admission lock; perform native graph and permission admission inside that registered operation before any write. A cancellation between registration and Start still runs the real pre-canceled Execute to its actual return.

## 4. Whole-graph disposition before effects

The complete native-converter graph must match the admitted archive inventory: one identified source root, no duplicate source/object/key aliases, no unaccounted generated collection, no silently omitted member, and a complete typed reference closure. Original normalization and remapping must be recorded. A bounded PB envelope does not imply that every SmartBlock type is supported.

Before assignIdsToAllObjects, classify every member and resolve relevant actual target lookups. Do not let an earlier FileObject upload precede validation of a later unsupported or colliding member. The existing original ID provider still produces actual mappings/payloads; its results must agree with the retained disposition before the next effect.

Candidate policy:

| Member | Required disposition |
| --- | --- |
| Annotation root and supported nested body Page objects | Fresh original payload and no oldAnytypeID/uniqueKey/source alias collision for any member. Recheck the actual assignment result; a reused ID is a collision. |
| Required existing schema definitions | Reuse only after actual target identity and mapped semantic definition match. Return copied native readback without calling ObjectCreator.Create, install/reset, favorite/archive or sync paths. No “same name” equivalence. |
| New supported schema definitions | Their original creation and reference mapping need explicit native qualification. Until then they are unsupported; do not auto-install or reset them through a body import. |
| Files and file objects | Byte inventory admission can be implemented now. Write activation additionally needs genuine uploader ownership/reuse disposition and mapping-aware file readback. Existing returned file IDs and file observations do not prove those guarantees. Unsupported cases reject before upload. |
| Workspace, widget, participant/profile mutation, chat, tombstones, unrelated templates or unqualified external references | Reject the whole graph before any original mutation. No silent member filtering or substitution. |

This table is a candidate policy, not a declared qualified supported set. An actual original ObjectListExport graph is required to determine which schema members and references a normal annotation contains. The retained evidence search in this packet found no qualifying graph. Do not silently reduce the product to one hand-built Page and claim general native annotation import.

The actual create boundary must enforce create-only behavior. A preflight absence check cannot settle a race. In the owned route, original CreateTreeObjectWithPayload returning ErrTreeExists must remain a collision. It must never fall back to reading an existing object's details as import success.

For the owned route, fail before the original workspace/widget branches, before implicit bundled installation, before resetState and before any effect on a verified reused member. Required bundled/schema objects must already have an admitted native definition; do not rely on an installer that can change them during body creation. Any supported new-object path must propagate original link-install, actual apply and sync errors that are currently only logged. Existing generic import behavior should remain byte-for-byte unchanged outside this opt-in closed route.

The importer may legitimately have partial historical effects before a later error or cancellation. Do not promise transaction rollback or delete existing target objects in cleanup. File cleanup must be restricted to genuinely owned outputs; if original uploader results cannot distinguish those from reused files, that file class remains unsupported.

## 5. Permission and retirement

At native operation admission, resolve the real regular target Space and actual executing account's signed ACL. Recheck live permission/currentness at each original write admission and preserve the original native permission checks at actual persistence. A caller boolean, cached picker item or wire Space string cannot replace this.

Cancellation and source retirement request cancellation of the registered original work. The app/account lease stays retained while that work is active. A reentrant AccountStop must return the original drain-pending error rather than wait for its own native callback or claim successful Stop. Historical Observe/Cancel/Release do not require newly acquired selected-Space write authority.

Permission rechecks alone do not prove an atomic barrier against concurrent ACL revocation. Existing-source analysis shows native content apply has its own ACL path, while root creation needs separate qualification. The qualification must establish the actual ordering at root creation and each apply. If revocation is observed before an admission, no new write may enter. If a write was genuinely admitted/applied before retirement, preserve that historical effect and its cancellation phase; do not retroactively call it absent.

No production activation is justified until the real root-create and apply revocation cases pass or the smallest original boundary repair is reviewed. This packet does not add an external ACL lock around native calls; doing so without examining nested lock/callback behavior could create a new deadlock.

## 6. Mapping-aware readback and Host commit

Keep original Done/Result separate from body equality. The four-command boundary must report original import completion and any qualified body-verification result as distinct facts. It must not advertise body verification merely because response.Err is nil, a mapping is complete, or objectsCount is positive.

For the proposed production annotation mode, retain the same registered original OwnedImportOperation through its additional genuine readback work. After original Execute and its import finalizer return, a package-private annotation verifier built from the actual retained app performs original export and comparison before this operation closes Done. It is a closed implementation, not a caller-supplied executor or completion closure. The old qualification mode has no annotation verifier and keeps its exact existing path. This opt-in lifetime extension must be implemented and qualified explicitly; it is not claimed to exist today.

AccountStop continues to see the same active registered operation while readback runs and returns drain pending on retirement. The verifier uses the same operation cancellation context, real wallet/account/Space and actual mapped objects. It cannot use an app pointer after Done. If cancellation or source retirement prevents a current read admission, retain the original import history and a failed/not-run comparison. Never upgrade it to a Host ACK.

Reuse the original native exporter, exact export flags and report. Require a complete original diagnostic report, correct source/root/member mapping, real file bytes and explicit cancellation state. The export service can clear a context.Canceled error, so a nil error alone is insufficient.

Fresh-ID verification needs an explicit bijection from source member IDs to actual original mapping results. Only proven typed identity slots may be remapped for comparison. Do not rewrite the saved archive/provenance or reuse the existing same-ID historical comparator as if it understood a new graph. Reject missing, duplicate, extra, ambiguous and unsupported reference mappings. Compare all supported block content, marks, ordering, nested references, relation values/schema, file content and meaningful metadata. Any ignored native-generated metadata must be precisely listed and justified by the actual original transformation; a generic “normalization” pass is not acceptable.

The original exporter already has waitExportTasks, which drains started tasks after Queue.Wait, and exportObjects finalizes the original queue before returning. Reuse those actual paths and qualify cancellation drainage; do not infer it from a progress identifier.

The precise mapping-aware comparator and this opt-in registered readback extension are a required later source slice. This plan does not invent their implementation or grant a digest. Only after genuine readback succeeds can the closed Host recheck its exact saved revision/source witness, account/selection and current permission and commit the resulting mapped binding. Cold storage reopen is a separate required acceptance case; live-object readback is labeled as such.

## 7. Implementation order

1. Add the native-owned archive admission implementation and a genuine original export-inventory fixture in an isolated source packet. No public Start route or SDK call is enabled.
2. Review actual graph inventory, then add only the supported member disposition and strict actual-create behavior, with targeted collision/no-mutation tests. Do not broaden support by removing a failing assertion.
3. Complete the registered original export/mapping-aware readback extension and the real permission/retirement cases. Existing mapped-object reopen remains a read/reopen route.
4. Add the reviewed protobuf schema and real generated Start/Observe/Cancel/Release methods, compile the genuine endpoint and generated Swift Invocation, and compose the closed Host only after all ownership constraints are real.

Each slice has a precise allowlist in PROPOSED_PRODUCT_PATHS.json. The first proposed product scope is archive admission plus actual export evidence. Additional paths remain proposals, and no generation/native CI is activated by this documentation checkpoint.

## Exact original source anchors

- [Existing-object identity lookup](https://github.com/davidpovarsky/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/core/block/import/common/objectid/existingobject.go) and [derived-object lookup](https://github.com/davidpovarsky/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/core/block/import/common/objectid/derivedobject.go) establish why the update flag is insufficient.
- [Original assignment order](https://github.com/davidpovarsky/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/core/block/import/processor.go), [FileObject upload](https://github.com/davidpovarsky/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/core/block/import/common/objectid/fileobject.go) and [actual creator](https://github.com/davidpovarsky/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/core/block/import/common/objectcreator/objectcreator.go) locate the required gates before effects and at native collision handling.
- [Filename provider](https://github.com/davidpovarsky/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/core/block/import/common/filenameprovider.go) and [Space import collection setting](https://github.com/davidpovarsky/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/core/block/import/pb/space.go) bind the path and NoCollection requirements.
- [Original export](https://github.com/davidpovarsky/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/core/block/export/export.go), [worker drainage](https://github.com/davidpovarsky/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/core/block/export/queue.go) and [snapshot projection](https://github.com/davidpovarsky/anytype-heart/blob/d98420b1113536afd08cde6de9a5816f6d27ffff/core/block/import/common/types.go) define the report, lifetime and field-preservation limits.
- [Actual owned-operation implementation](https://github.com/davidpovarsky/anytype-swift/blob/455e1c55d765b25f8dd63bd472964057e5cbffc7/docs/pinkha/torah-integration/native-owned-import-lifetime-20261122/native/core/block/import/owned_import_operation.go) and [actual app/lease registry](https://github.com/davidpovarsky/anytype-swift/blob/455e1c55d765b25f8dd63bd472964057e5cbffc7/docs/pinkha/torah-integration/native-owned-import-lifetime-20261122/native/core/application/owned_import_admission.go) are the existing lifecycle owners.
- [Original Swift archive layout](https://github.com/davidpovarsky/anytype-swift/blob/de63125b97cd5b91a1fa4f4b71d03738076e735f/OriginalEditorFramework/OriginalAnnotationNativeArchiveLayout.swift) and [archive comparison](https://github.com/davidpovarsky/anytype-swift/blob/de63125b97cd5b91a1fa4f4b71d03738076e735f/OriginalEditorFramework/OriginalAnnotationNativeArchiveComparison.swift) supply the existing data bounds and comparison context. SOURCE_INVENTORY.json binds the exact bytes of every referenced input.
