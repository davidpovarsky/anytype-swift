# Original annotation production contract — isolated proposal

Status: bounded data types and conservative recovery policy only. No production RPC, native registration, mapping writer, acknowledgement, transport or public original-editor facade is enabled by this branch. The producer remains independently qualified by its own source-bound Apple gates.

## Existing authority

The existing Maktabah TorahAnnotationEnvelope v1 and AnnotationExchangeLedger remain the sole exchange wire, encoding, digest and delivery authority. The complete canonical envelope is at most 64KB, including original opaque rich-body bytes and unknown retained data; preview, title and editor-revision bounds remain unchanged. These new Swift types are deliberately not Codable and never encode, hash, truncate or rewrite that envelope.

Consumer source reviewed: Maktabah 5d0a11f6a799bee9deb23dc91b29e832bec14335, Source/ChavrusaText/Annotations/Exchange/TorahAnnotationEnvelope.swift and AnnotationExchangeLedger.swift. The downstream consumer owner retains responsibility for its additive SQLite schema and real reopen controls. Original envelope/v1 tables, PRAGMA user_version and original ACK rules are not changed here.

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

Receipt consumption must revalidate the retained capability and original delivery witness. Retired owner/account/Space/source permits neither new mapping nor ACK even if a native mutation may already have occurred. A raw TorahAnnotationNativeCandidate or any positive pure assessment below can never substitute for those opaque runtime receipts. The consumer therefore implements no identity writer until this boundary exists and is reviewed.

## Conflicts and existing ledger contract

Mapping identity is destination/account/Space/namespace/annotationUUID. Its reverse uniqueness is destination/account/Space/actualNativeObjectID. The consumer owns this local database invariant; it does not imply cross-client/global engine uniqueness.

Wrong scope, wrong object/type, non-present object, promoted classification, ambiguous candidates, mismatched original attempt, a different pending commitment, stale/newer applied exchange revision, changed payload/source digest or message/mutation identity remain explicit conflicts. No last-write-wins rule or timestamp ordering is added.

The existing outbox remains pending during uncertainty, incomplete application or lost authority. Its original ACK still binds existing messageID plus exact destination/account/Space/namespace/UUID/revision/payloadDigest. Recovery of identity is not ACK and must not overwrite the existing opaque body or source witness.

## Implemented files and verification scope

Only two new downstream-owned Foundation Swift files are added under Modules/PinkhaKit/Sources/PinkhaKit/Torah: TorahAnnotationNativeIdentity.swift and TorahAnnotationCreateRecovery.swift. They contain data values, validation and pure conservative assessment. No original Heart, generated schema, original class, peer property path, shared facade or consumer database is edited by this proposal.

All 52 new portable controls compiled and passed on Windows Swift6.3.3 against the exact two policy sources. They exercise uncertainty, ambiguity, immutable attempt commitments, account/Space drift, known identity recovery, stale/reordered commitments and distinct identity/application assessment. Source hashes, actual commands and complete outputs are retained in evidence/RESULT.json and its adjacent logs; controls/run_controls.py reproduces the route. These controls do not simulate or claim actual native create/search/indexing/visibility behavior. Native adapter execution, crash injection with actual Heart, full UI/filter/performance/migration and two-client/device acceptance remain required.

Root review of this concrete contract and the later actual native schema/readback implementation is required before enabling public facade wiring. The user's standing development authorization remains in effect; this is an engineering integration gate, not a repeated permission request.
