# Original annotation production contract — isolated proposal

Status: bounded data types, conservative recovery policy, an unwired internal original ObjectShow read adapter, and an isolated participant-role prerequisite in the original ParticipantsStorage actor. No production runtime, native annotation registration, mapping writer, acknowledgement, transport or public original-editor facade is enabled by this branch. The raw read adapter has not executed against the native engine. Producer qualification remains a separate source-bound Apple gate.

## Existing authority

The existing Maktabah TorahAnnotationEnvelope v1 and AnnotationExchangeLedger remain the sole exchange wire, encoding, digest and delivery authority. The complete canonical envelope is at most 64KB, including original opaque rich-body bytes and unknown retained data; preview, title and editor-revision bounds remain unchanged. These new Swift types are deliberately not Codable and never encode, hash, truncate or rewrite that envelope.

Consumer envelope source reviewed: Maktabah 5d0a11f6a799bee9deb23dc91b29e832bec14335, Source/ChavrusaText/Annotations/Exchange/TorahAnnotationEnvelope.swift and AnnotationExchangeLedger.swift. The additive creation-fence component is published at source e78ddef1cd156bd2118e1ed23eb56376e65d0a7c, evidence HEAD 0cdb968f2c1330e7235c22304ca982b532a78a60. The downstream consumer owner retains responsibility for its additive SQLite schema and real reopen controls. Original envelope/v1 tables, PRAGMA user_version and original ACK rules are not changed here.

Task authority: Asana cross-app 1220545194715722, stages A–F, and Maktabah docs/hq-integration/cross-app-stage-a-20261120/README.md. Full editor, annotation classification, import/delivery, two-way merge and physical iPad acceptance remain open.

## Exact value contracts

| Value | Fields and meaning | Authority boundary |
| --- | --- | --- |
| TorahAnnotationNativeScope | destination, account, space, namespace, annotationUUID | Exact existing host destination plus existing envelope identity; identifiers are bounded 1…512 ASCII [A-Za-z0-9._:-]. Values do not select or authenticate an account/Space. |
| TorahAnnotationNativeCommitment | scope, existing messageID, mutationID, positive exchange revision, canonical sourceDigest and payloadDigest | Copied from the existing immutable pending delivery/version and source witness. Both digests retain existing lower-case SHA256 grammar. No additional digest or namespace authority. |
| TorahAnnotationNativeIdentity | full scope and actual original native objectID | objectID is admitted only as a nonempty bounded native identifier, not generated from annotationUUID. This DTO does not persist a mapping. |
| TorahAnnotationNativeCreateAttempt | attemptID, exact commitment, notDispatched / mayHaveDispatched / nativeObjectObserved(actualID) | In the production adapter, attemptID is exactly the existing durably stored messageID. No separate attempt UUID is minted at dispatch, retry or recovery. Once dispatch may have happened, no crash/restart can reset the attempt. |
| TorahAnnotationNativeCandidate | identity, actual native type ID/state/classification, original creation attempt/commitment, optional applied commitment and original snapshot digest | Explicit inputs to pure assessment; not engine proof, global uniqueness or an SDK receipt. |

Separate assessments choose only the next step: first-create preparation, direct existing-object verification, durable creation uncertainty, owner unavailability, not-materializable, or a typed conflict. Identity assessment and applied-commitment assessment are separate. Finding an existing native identity never means that the body was applied or a delivery may be acknowledged.

## Classification

A normal annotation must use a dedicated original native annotation type outside PinkhaSpaceManifest.registeredDocumentTypes. Those existing registered document roles remain chiddush/article/research. Do not register annotation as an ordinary Note or a writing document, and do not create a second Note as a fallback.

The annotation UUID and classification survive short/long body changes, rich block editing, full-screen expansion and relaunch. Length/block count/view expansion are not classification inputs. Explicit promotion is a separate retained-owner operation into the original chiddush/article/research type; an encountered promoted object produces a conflict requiring explicit resolution, rather than silently demoting it. A highlight-only record or tombstone never enters the create path.

Original native type registration, its exact schema/metadata fields, migration/backfill and every AnyTapy visibility/filter surface require separate original readback and UI evidence. This proposal does not claim that a type value alone hides an object from search, recents, object lists or creation menus.

## What the actual original Heart permits

Original native base: d98420b1113536afd08cde6de9a5816f6d27ffff. The producer uses original Heart r14 from source b5dc53b799a70269b8082734106d8cd30a99fc44, run44203168617, artifact14383247626. Its patch SHA256 is fb96818eb57bd9e0be8da90a11831bcccc7ca8e72cc0a4e9a065500feb7cc077. SOURCE_PROVENANCE.json records the exact inspected Git blobs and confirms that the r14 patch does not replace the relevant create/search/indexer implementations.

- core/create.go builds the original ObjectCreate request from details/internal flags/template/type. The ordinary public request does not supply the internal creator UniqueKey.
- core/block/object/objectcreator/creator.go and smartblock.go create the ordinary native tree; the internal template UniqueKey route does not establish caller-chosen idempotency for an ordinary custom annotation.
- core/block/object/objectcache/tree.go puts the native tree using its original signed native identity. That storage commit is separate from Maktabah's SQLite delivery ledger.
- core/object.go queries the per-Space ObjectStore index. pkg/lib/localstore/objectstore/spaceindex/queries.go provides indexed query/count transactions, without an authoritative creation-absence fence.
- core/block/editor/smartblock/smartblock.go logs an indexing failure in runIndexer without returning that failure to roll back the native object. Consequently, an already-created native object can have zero index results.

This is a source-backed reason that zero search results after an uncertain ObjectCreate do not authorize a second create. It is not a claim that a fabricated test executed the real engine. No UUID-as-uniqueKey contract is invented.

## Create and recovery ordering

1. The host validates the existing immutable pending delivery, source witness and actual destination; it captures the original runtime account/Space and source/scene lifetimes.
2. The consumer transaction reserves one exact attempt for the full scope and current delivery commitment. An earlier uncertain commitment blocks a later revision. A known native mapping prevents creation even when the search index is empty.
3. Before the first admitted native call, the consumer durably advances the same attempt to mayHaveDispatched through a true outermost SQLite COMMIT under the original serialized-access lock. The existing connection must be in autocommit before entry and again after the successful outermost commit; a nested SAVEPOINT release is not a dispatch fence. The native RPC cannot start until this top-level commit returns. Repeating the transition must refuse. A crash immediately after the commit is conservatively uncertain, even if the native call never happened.
4. The original native adapter may issue one ObjectCreate with approved annotation type and approved identity metadata as part of that original creation. Its returned actual ID is a candidate for direct original readback; a cancellation/error after dispatch retains uncertainty. The native schema/adapter for this step is not yet implemented here.
5. Recovery uses any known actual ID directly through original ObjectShow. Missing/deleted/archived/denied/wrong-bound known objects do not cause a replacement object. If no ID was returned, an index search may discover candidates but zero matches keep uncertainty and multiple matches are a conflict.
6. One candidate with exact identity/creation commitment/attempt is only a request for fresh direct verification. It does not prove global or multi-client uniqueness.
7. Only a separate current-owner, original-native identity readback receipt can establish the durable scope→actual-object mapping. Identity recovery may be persisted while the original outbox delivery remains pending.
8. Body application, original export/readback and matching applied exchange commitment require a different receipt. The existing exact ACK is permitted only after that proof and a final current-owner/source/destination check.

No timeout, timestamp, retry count, zero-index result, new process, unrelated pending delivery, DTO or caller boolean upgrades uncertain creation into a safe second create. A definitive operator-supported reconciliation/migration path remains a separate future product decision.

## Required runtime proof boundary before public facade wiring

The eventual production facade must capture the actual original AccountManager/BasicUserInfo account and lifetime, retained selected Space and original native permissions. It must use the same original engine/editor/service graph as the qualified host and revalidate immediately before native dispatch and after every relevant await. It must not create a qualification-only account, reset a real runtime, select a personal test Space or call the DEBUG qualification SPI as a production transport.

The host may supply expected scope/commitment values, but only a sealed runtime implementation can construct a destination capability after checking them against the actual original runtime. No public initializer or caller-supplied implementation/boolean may construct a capability or a positive receipt.

The future facade must expose two distinct opaque result types, with non-public initializers:

- Identity-readback receipt: exact full scope, actual object ID, native annotation type/classification, creation identity/attempt and fresh original ObjectShow evidence, issued while the captured account/Space/owner/source is still current.
- Applied-body receipt: the identity proof plus the exact existing appliedExchangeRevision/messageID/mutationID/sourceDigest/payloadDigest and actual original body export/readback evidence. A copied metadata marker, matching revision number or a merely present snapshot digest is insufficient. This is an exchange revision, not a global native monotonic revision.

A private initializer alone is not this authority. Identity verification and one-shot consumption must remain inside the retained original exclusive-read barrier, which prevents the same editor's new writes from interleaving. A copied observation returned after releasing that barrier cannot become a receipt.

After acquiring the original SQLite serialized-access lock, consumption attempts the original Owner's synchronous source/account/document admission and validates the exact retained commitment immediately before the true top-level transaction. The transaction rereads the actual pending delivery, canonical payload/source and current exchange revision, enforces the existing scope/attempt and mapping constraints, and completes its outermost COMMIT while the original admission and exclusive-read barrier are still retained. No await may separate final admission, transaction validation and COMMIT. A nested SAVEPOINT release is not durability.

The original lifetime lock atomically orders admission against retirement; it is not held for the whole database operation. If retirement wins admission, no new mapping or ACK is admitted. If admission wins, the already-admitted synchronous transaction may finish while the original account/document teardown waits for its admissions to drain. This preserves the original engine/editor lifetime semantics; it does not promise instantaneous revocation or rollback of an already-admitted operation.

Post-COMMIT owner validation can throw after local bytes are durable. That outcome is committed-then-retired, or committed without current publication. It must not be reported as a rollback, clear/reset the creation fence, replay native create, or let a successful current-owner/UI receipt escape. A durable mapping is a stored fact that a later owner must independently revalidate. Identity mapping alone leaves body delivery pending and never grants ACK.

The implementation must separately record actual transaction phase and original Owner outcome. A failed/unknown local commit is not proof of native rollback; uncertain delivery is retained and actual storage must be read before any reconciliation. Controls must distinguish definite rollback on an observed commit failure from durable COMMIT followed by a thrown retirement error.

Before a public writer is enabled, joint controls must execute the unchanged original Owner/Lifetime admission code with the original real SQLite wrapper: retirement before admission, retirement during an admitted transaction, post-COMMIT retirement, actual COMMIT failure, exact delivery/source revalidation, and teardown waiting for admitted work to drain. These controls do not manufacture native annotation identity or body receipts. A raw TorahAnnotationNativeCandidate or positive pure assessment never substitutes for the actual native proof, and the current consumer intentionally exposes no identity writer.

## Native schema and original deployment dependencies

The minimum immutable native creation marker is a protocol/schema discriminator, dedicated annotation type/classification, namespace and canonical annotationUUID, exact creation destination/account/Space, creation messageID (also attemptID), mutationID, exchange revision, existing source snapshot digest and payload digest. Creation provenance is immutable. A known shared object under another account needs a separately justified adoption operation; it cannot rewrite the creator scope or use matching namespace/UUID alone as authority. Candidate discovery must not filter away conflicting creators before assessment.

The canonical UUID spelling for the marker is the existing Foundation UUID.uuidString form (uppercase hexadecimal with standard hyphens), including messageID and mutationID. This semantic marker spelling does not rewrite the canonical envelope's original retained bytes, unknown fields, or payload digest. Account/Space/native object identifiers remain case-sensitive, and SHA256 values retain the existing lowercase hex grammar.

The actual original Heart supports fixed schema-type and relation keys through ObjectCreateObjectType and ObjectCreateRelation, followed by original derived-state creation. This is a possible way to register the dedicated schema without silently changing the existing schema1 manifest. It does not authorize a UUID-derived ordinary annotation object. Any fixed key must use the original delimiter-safe codec and be verified through native type/relation readback; apiObjectKey and display names are not identity. No schema registration is implemented by this proposal.

The current producer qualification route targets an arm64 iOS Simulator framework with Debug qualification SPI. The current consumer mount/qualification paths retain DEBUG and simulator guards; ordinary device/Release builds do not restore this SDK. A genuine device framework/distribution and original production account/runtime configuration are separate required development and verification steps. A simulator StageB pass cannot be presented as production/device embedding, and the disposable qualification account factory cannot be repurposed as production authentication.

## Conflicts and existing ledger contract

Mapping identity is destination/account/Space/namespace/annotationUUID. Its reverse uniqueness is destination/account/Space/actualNativeObjectID. The consumer owns this local database invariant; it does not imply cross-client/global engine uniqueness.

Wrong scope, wrong object/type, non-present object, promoted classification, ambiguous candidates, mismatched original attempt, a different pending commitment, stale/newer applied exchange revision, changed payload/source digest or message/mutation identity remain explicit conflicts. No last-write-wins rule or timestamp ordering is added.

The existing outbox remains pending during uncertainty, incomplete application or lost authority. Its original ACK still binds existing messageID plus exact destination/account/Space/namespace/UUID/revision/payloadDigest. Recovery of identity is not ACK and must not overwrite the existing opaque body or source witness.

## Implemented files and verification scope

Two downstream-owned Foundation Swift files under Modules/PinkhaKit/Sources/PinkhaKit/Torah contain data values, validation and pure conservative assessment: TorahAnnotationNativeIdentity.swift and TorahAnnotationCreateRecovery.swift. The new internal Anytype/Sources/Pinkha/Torah/Annotations/OriginalAnnotationObjectReadback.swift binds an existing original prepared session, actual AccountManager lifetime and BasicUserInfo identity; it performs strict original ObjectShow under the same Owner's exclusive read gate. Its returned ObjectDetails are raw observations, not receipts. There is no public facade or application caller. The prior raw-read adapter step did not edit original Heart, generated schema, an existing original class, peer property paths or the consumer database. The separate participant prerequisite below now changes only its original ParticipantsStorage class.

All 52 new portable controls compiled and passed on Windows Swift6.3.3 against the exact two policy sources. They exercise uncertainty, ambiguity, immutable attempt commitments, account/Space drift, known identity recovery, stale/reordered commitments and distinct identity/application assessment. Source hashes, actual commands and complete outputs are retained in evidence/RESULT.json and its adjacent logs; controls/run_controls.py reproduces the route. These controls do not simulate or claim actual native create/search/indexing/visibility behavior. Native adapter execution, crash injection with actual Heart, full UI/filter/performance/migration and two-client/device acceptance remain required.

The new raw adapter passed source syntax only and was independently read by root; Apple module compilation and actual native read execution remain pending. It does not satisfy the stronger held-barrier receipt factory or database commit seam described above. No unchanged 52-control policy suite was rerun for these documentation/runtime-boundary changes.

Root review of this concrete contract and the later actual native schema/readback implementation is required before enabling public facade wiring. The user's standing development authorization remains in effect; this is an engineering integration gate, not a repeated permission request.

## Original participant prerequisite and current recovery guard

The original ParticipantsStorage actor now derives an internal OriginalParticipantEditPermission from its original decoded participant subscription. Its initializer is file-private. The capture binds the actual AccountManager lifetime source/token, the exact participant identity/role/status, and byte-exact Space. It uses the original active status and native canEdit predicate; moderator permission is not an edit substitute. The original first-record selection and public decoded participant stream remain intact.

Its original start/stop lifecycle now reserves the actual start attempt before suspension, retires captures before stop, drains that start before one original unsubscribe, joins duplicate stops and refuses restart after an uncertain failed unsubscribe until an explicit successful stop. Task installation and publication require the exact active attempt. On storage deallocation, both channel-pin and edit-role snapshots retire and the consumer Task is cancelled.

This remains only a participant prerequisite. It cannot establish full Space edit authority without the separately captured original SpaceView/account lifetime and the exact native legacy rule: participantCanEdit && (!isLegacyStream || isOwner). No public facade, create operation, native schema, receipt or identity writer is enabled. The independently reviewed source/receipts are in participant-role-lifecycle-20261122/README.md: sixteen new actual-actor/role controls on exact 0f input plus one new deallocation control on exact 7fc; the earlier sixteen are not replayed. Dependency probes do not claim native decoder/RPC/Combine/Apple execution.

An old uncertain creation commitment R1 can survive while the current local head is R2 or a tombstone. Fresh-dispatch validation correctly requires the current head/source to match its pending delivery; it is not automatically the validation contract for identity-only recovery of R1. The eventual adapter must conservatively conflict, or capture the immutable R1 creation commitment and a separate current local guard and revalidate both inside the same original serialized top-level COMMIT. Identity alone never applies the body or grants ACK.

Local persistence nested inside the original exclusive-read barrier must retain that read lineage. The original synchronous admission uses requiresEditing: false for this boundary; the default mutation admission is correctly rejected under a read barrier. This grants no new native mutation RPC. Existing actual Owner/SQLite primitive and held-read component evidence is a separate dependency; it does not manufacture native annotation identity or prove every combined retirement/COMMIT scenario.
