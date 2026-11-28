# Read-only provider contract for consumers

## Type presentation and values

The versioned presentation contract is pinkha-heart-type-references-v1. Build AnyHeartNativeTypeReferencePlan from the existing AnyHeartNativeDefinitionCatalog and AnyNativeImportedDefinitionDirectory. The constructor requires complete exact source membership and evidence; a partial, foreign, or self-consistently altered catalog cannot select the original bindings.

Use presentation(sourceTypeObjectID:) to obtain the original Type presentation. Its groups cover recommendedRelations, recommendedFeaturedRelations, recommendedHiddenRelations, and recommendedFileRelations. Each group carries isPresent independently from its references. The canonical descriptor retains order and repetitions. orderedReferences is a separate first-occurrence display projection and must not replace the complete evidence arrays.

Each AnyNativeTypeReferenceTarget is one of:

- property: the actual imported property entry, its owner kind, exact AnyNativePropertyKey, and optional canonical value semantics.
- computed: the existing typed AnyHeartNativeComputedRelationBinding, with its own executable read contract.
- unresolved: an explicit noQualifiedNativeBinding or capturedProviderContractMismatch reason.

A reference key binds source Space and object identity using exact UTF-8 lengths and bytes. Source object IDs, relation keys, target property IDs, and computed-provider identities are not interchangeable. Links and backlinks must remain their explicit computed references; presentation must not silently omit them or synthesize writable aliases.

currentNativeTypeID stays nil for an archived-only Type. isMaterializedType is therefore distinct from having a preserved source description. permitsDestinationWrites and qualifiesOriginalFamilyBehavior remain false. A consumer may display unresolved references, but cannot manufacture their values.

AnyNativeTypeReferenceStore.readDefinition(sourceTypeObjectID:plan:lease:) uses only actual mapped immutable definitions. readValue(sourceTypeObjectID:sourceRelationObjectID:objectID:plan:lease:) requires the mapped Type and current object membership, reads the typed property or complete computed query through the existing adapters, and rechecks the exact workspace lease and current task. It returns definition/creation evidence for mapped properties. Multiple sequential observations do not become a cross-object atomicity guarantee.

## Original runtime descriptors

AnyHeartNativeRuntimeRelationBinding uses pinkha-heart-runtime-relation-v1. Its roles are readersLimit, writersLimit, sharedSpacesLimit, syncDate, syncError, syncStatus, spaceAccessType, and spaceDashboardId. The binding validates original descriptor identity and preserves the source readonly declaration, including false for spaceAccessType and spaceDashboardId. Its own permitsDestinationWrites remains false; a descriptor does not grant a native write capability.

The source numeric domains remain explicit:

| Source domain | Values |
| --- | --- |
| AnyHeartObjectSyncStatus | synced 0; syncing 1; error 2; queued 3 |
| AnyHeartObjectSyncError | none 0; incompatibleVersion 2; network 3; oversized 4 |
| AnyHeartSpaceAccessType | private 0; personal 1; shared 2 |

Do not reinterpret Any tracker values using these ordinals. Dashboard and source navigation implementation are separate from this binding; a descriptor alone does not map an original homepage to the native Space index.

## Quota observation

AnyNativeSharedSpacesLimitStore.read(binding:source:lease:) uses the existing client and exact destination workspace/account. An unavailable answer differs from observed(limit: 0). The limit is UInt32 and the original fetchedAt string retains native fractional precision through AnyNativeRuntimeTimestamp. HTTP delivery does not establish that a new coordinator query occurred.

The five accepted quota methods include the exact retained historical response, absent-versus-zero behavior, numeric/date precision, malformed-value refusal, and exact UTF-8 account initialization. They do not replay the historical network request.

## Runtime observation

AnyNativeRuntimeStateStore is initialized with the existing AnyHTTPClient, workspace, and expectedNetworkID. space(lease:) and object(_:lease:) are read-only. Returned scope includes exact account, network, Space, admitted authority identity, and signed ACL head. A guest authority identity is not silently replaced with the account's main identity.

Coordinator answers retain fetchedAt and missing Limits independently. Access value requires positive Personal-space provenance when the source semantics require it; currentSharing observations cannot invent that provenance. Object and Space synchronization samples preserve their basis, unknown/error state, counters, peer observations, and timestamps. A tracker sample does not prove object existence or Type, and an old successful confirmation does not prove the current network is online.

The actual HTTP fixture tests cover both scoped GET routes, retained delivery leases, account switch, engine restart, session retirement, cancellation before dispatch, foreign leases, unsupported endpoints, response limits, and foreign-network answers. Consumers must retain these boundaries when integrating the adapters; the publication makes no claim that downstream app call sites have already adopted them.

## Evidence and future work

The exact source and method inventories are in qualification/provider-component-inputs.json and actual/components-attempt3-result.json. The packet's pure validator independently parses the original XCTest log and checks the complete source/copy and fixture receipts. It does not execute a native account, replay a test, or rewrite any failure into a pass.

The Type25 component result is one completed slice. Real native catalog159 access, original encrypted-history recovery, full property-family behavior, source metadata publication, shared navigation writes, and platform integration remain separately qualified work.
