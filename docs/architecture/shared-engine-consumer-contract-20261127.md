# Engine contracts for Hanlin, MiniApps and Otzaria consumers

This handoff is owned by Wave 1. Wave 3 owns application integration and release; Wave 2 owns editor and account-transition UI. The document defines how consumers use the existing Engine, Host and native boundaries without opening an alternative account store or implementing an independent synchronization path. The acceptance table below distinguishes published implementation, actual Oracle evidence, and remaining gates.

## Scope and lifetime

Every read or mutation is bound to an exact account, Space, object where applicable, and the originating owner's lifetime. Opaque identifiers and persisted value fingerprints use exact UTF-8 bytes. Canonically equivalent Unicode text is not a replacement identity. User-visible text may be formatted for display without changing the stored or signed value used by these contracts.

An account switch, same-account reselection, closed Space or retired presentation invalidates the originating owner. A consumer carries that original owner's lease through asynchronous work and revalidates it at dispatch and delivery. Looking up the latest global account after an await cannot authorize a request created by an older owner. Cancellation alone is neither a native rollback receipt nor proof that a mutation's transport has drained.

Current native authority is required even when content or metadata is cached. Member-facing native FilesV2 guards cover content, metadata, list, status, statistics and cache operations. The separate keyless broker Query/Payloads transport exchanges sealed content and is not a member-facing plaintext reader. A removed member must receive the original typed refusal; the caller must not fall back to a file on disk, an old cache object, a second engine or a stale snapshot to obtain the refused data. Independently qualified offline availability still obeys the current local signed ACL and account/Space scope.

## Consumer boundary map

| Need | Existing boundary | Required consumer binding |
| --- | --- | --- |
| Create an ordinary object | `PinkhaAnyHost.AnyNativeObjectCreator` and the existing `AnyNativeCreationJournaling` owner | Exact immutable intent, one original mutation ID/fingerprint, fresh write admission and current final read authority |
| Attach a file to an existing object | `objects.makeFileAttachmentCreator()` followed by `attach(_:fileURL:authorizeRead:authorizeAttachment:)` | The same document's original client, workspace and protected creation journal; preserve the complete original intent |
| Recover an acknowledged attachment | `resume(_:authorizeRead:)`, or the opaque receipt overload after a genuine owner transition | Existing original reservation and file ID or actual retained native acknowledgement; current same-scope authority |
| Observe backup or request one retry | `PinkhaAnyEngine.AnyNativeFileDurability.status` / `retry` | Full account/Space/object/file reference; side-effect-free read callback and separate one-dispatch retry authorization |
| Resolve a stored file link | `PinkhaAnyHost.AnyNativeFileReference` | `any://f/<space>/<file>` is a locator; the active account and object authority must still be established |
| Carry a full transport file scope | `PinkhaAnyEngine.AnyNativeFileReference` | Account, Space, object and file IDs; this is a different type from the Host URI locator |
| Prepare an ordinary Bookmark | `AnyNativeObjectCreator.makeBookmarkCreationFrameReader()` and `AnyNativeBookmarkCreationFrameReader.frame` | Original client/workspace and read authority; require the versioned native capability and exact returned definition condition |
| Read or append Heart cutover data | `PinkhaHeartCutoverClient` on the qualified native source/runtime profile | Frozen original request, signed result/claim correlation, original read lifetime, and the native account-run binding when enabled by qualified integration |
| Prove Heart FullSpace readiness | `PinkhaHeartSpaceIndexClient` / `PinkhaHeartSpaceIndexSnapshot` | Matching Space, canonical key and index generation; complete stable before/after state under the same read lease |

The two `AnyNativeFileReference` types must be module-qualified in code that imports both modules. A Host URI does not carry an account ID or a native permission. No consumer should deserialize it as a fully authorized Engine reference.

## One mutation and its recovery

The Host journal records a scoped intent identity and fingerprint before dispatch ownership is consumed. An intent cannot be changed while retaining its mutation ID. Concurrent callers, repeated button actions and a reopened sheet must use the same owner and reservation to reconcile an existing operation. An uncertain response must not silently allocate a new object, file or operation ID.

A valid native acknowledgement is retained under the original scope before a late cancellation or account-change refusal can hide its payload. Durable journal recording and current authorized delivery are separate events. A known original ID supports readback; a reservation without a reliable ID remains unresolved. Matching a filename, URL, content digest or a new list entry is not sufficient to invent a missing acknowledgement among concurrent operations.

File upload owns its sole transport, serial callback queue and private staged body until the task completion and session invalidation callbacks have both finished. The owner transition must join the actual operation and close/release the original protected journal through its existing ownership rules. No caller-created closed flag or fixed delay substitutes for those completions.

The original attachment creator can be retained in bounded process memory across that completed transition solely for `retainedRecoveryReceipt(for:authorizeRead:)`. The fresh owner for the same exact account, Space and object supplies both read-authority checks. The old actor performs only a private memory export; it does not query its closed journal or retired native client. The new creator resumes the original reservation through the new current native reader. The complete sequence and acceptance limits are in [the ordinary attachment contract](ordinary-file-attachment-contract-20261127.md).

This opaque acknowledgement is intentionally not serializable or caller-constructible. Process loss before the original ID becomes durable can leave an unresolved reservation. The caller preserves its bounded original Codable intent under the existing account/Space storage policy, and does not use the journal fingerprint as a substitute for that intent.

## FilesV2 storage, transfer and quota

Ordinary upload uses the original raw-body route `POST /v1/spaces/{spaceId}/objects/{objectId}/files`. The native engine chooses the storage tier. A successful upload binds the response to the original request and performs metadata/content/metadata readback with the original complete plaintext digest. The Host adapter accepts zero through 512 MiB with bounded copy/hash passes and HTTP ranges; the whole body is not accumulated into one Swift value.

File identity includes the original object and file IDs. Thumbnail identity also includes its native `variant` and `variantOf` relationship. An original image and its thumbnail remain distinct files with their own byte counts, digests and content-addressed roots. A consumer must not substitute one for the other merely because an image resolver can redirect to a preferred variant.

Local cache availability and remote custody are independent observations. Inline storage has the original native durable semantics; a full-tier file requires the native verified custody state. Successful local readback, a warm cache and HTTP 201 do not establish remote backup. A retry HTTP 204 acknowledges the request only; read the native status again before reporting progress or completion.

The existing durability adapter exposes `durable`, `inflight` and `limited` with the actual `cached` bit. A storage-limit refusal preserves the original file reference and local content. Do not clear the cache to recover from a quota failure, mark a limited file durable, or add a consumer retry loop. The original native queue retains its own ten-minute limited-file retry policy. Private native diagnostics are redacted from descriptions and must not be copied into shared analytics.

Cache eviction is subject to current native authority and the original backup precondition. The full-tier Offload sequence actually passed: one acknowledged eviction, a fresh operating-system-offline cache miss with zero plaintext, cloud retrieval of the same root CID and original 8,192-byte plaintext while the sender was absent and P2P disabled, then a second fresh offline reopen with the exact original digest. The separate retained thumbnail stayed cached with its original `thumb`/`variantOf` relationship and metadata throughout. All four owned native groups closed normally. The offline miss retains the original native HTTP 500/internal envelope; this proof does not establish a new typed offline user-interface error.

## Bookmark definition condition

The additive capability is `nativeBookmarkObjectCreate: 1` under the existing `pinkha-torah-native-v1` capability contract, alongside `currentWriterObjectCreate: 1`. The read-only preparation route is `POST /v1/spaces/{spaceId}/pinkha/bookmark-create-frame`; its request contains `typeId` and `collections` and performs no object creation or journal reservation.

Its closed response contract is `pinkha-native-bookmark-create-v1`, version 1, with exactly `contract`, `version`, `accountId`, `spaceId`, `typeId`, `collections`, `propertyOwnerId`, `propertyId`, `canWrite` and `frame`. The response binds the exact type, canonical requested/URL-owner collection union, mapped URL property and an opaque native condition. The Swift reader rechecks current authority, actual account and cancellation before delivery. The caller keeps the exact returned condition and URL bytes when constructing the immutable creation intent.

The native conditional path revalidates the definition heads and relevant schema under the original sorted definition locks at durable admission. Current ACL admission remains independent. A changed type or URL definition is a conflict, not permission to recreate the object with a newly read condition under the old intent. A failure after a known root has been created preserves that original ID as an uncertain result; it cannot justify a replacement object.

The optional condition preserves the legacy intent fingerprint when absent. Consumers must check the actual capability before using the conditional path. The new ordinary Bookmark path and the separately qualified migration importer have distinct contracts and evidence; an imported Bookmark proof does not establish ordinary creation acceptance.

## Heart account-run, cutover and index boundary

The additive `PinkhaNativeAccountRunBinding` contains the exact account ID and an opaque native run ID. The reviewed activation envelope carries the original AccountSelect request through the original native implementation once and captures that invocation's successful run under the native owner lock. A later global getter must not mint an activation binding for an older caller.

Each acknowledged activation, including same-account reselection, has a distinct run. Retirement, stop, replacement and process restart invalidate the old binding. A delayed request presents its frozen binding to the finite native dispatcher before private reads, roots, signatures or appends. If retirement wins, the old request is refused before effects. If the operation is already admitted under the existing native lease, replacement drains it through durable completion. The original signed result and post-commit durable receipt remain correlated with the original request.

FullSpace readiness requires the complete authoritative object set and a stable index generation. An empty, partially loaded or changed index is not a complete proof. Semantic text anchors and signed association records retain the original claim/object/property identities through cutover and recovery. Consumers must not regenerate those identities from display text or discard a durable signed receipt merely because its initiating view has retired.

Wave 3 binds these engine boundaries to the application's actual owner activation. Native component acceptance alone does not enable an unqualified Apple factory. The two native products retain their own complete source manifests and runtime identities while using the shared contracts. Each account and Space retains its own protected namespace and ownership; a consumer does not open both engines over an account store as a recovery shortcut.

## Current acceptance and delivery scope

| Deliverable | Published or actual evidence | Scope still requiring completion |
| --- | --- | --- |
| Ordinary attachment Host/Engine | Commit `063d3ef0b16392f67e5044faa81cf8689a75dab2`; aggregate 35 component methods; separate fresh native method with two attachments and cold OS-offline reopen | Mounted caller and actual Apple protected-journal owner transition |
| Current FilesV2 authority and Offload | Commit `972f6c2eaed18fdcfa4e5f885d519b3fb18a9aa7`; 34 SDK events and 18 typed removed-member metadata refusals, online and fresh OS-offline; separate actual full-tier Offload/refetch/cold proof `75cfb31e711b2653905a76cf6faf3573976d3c88fa0548238b85c1ae916b85fd` | Final combined native/Apple binding and large-file production cloud custody |
| Post-close acknowledgement export | Four genuine component passes retained in the qualified 31-method aggregate; production attachment creator unchanged | Real mounted/protected-file owner transition is separate |
| Exact value and Bookmark condition | Seven exact-value, 20 frame and four post-close methods are qualified: 21 retained passes plus ten new HTTP passes in `8a4ca85c7b7c0349c03e50145554324b7670129d029adbb31fbf8040910d82d8`; native source installation `2f8eb0f7a73ddfc5ea57df10c79521d88215e964822f6afa65ee98ed91861400` | 13 new native methods and fresh bodyless warm/crash/cold creation remain separate gates |
| Heart final source union | Original cutover/core/RPC evidence retained; full 4,952-file corrected source receipt `aa39281fa7cbcd8625438f7fe46b211d11d04be07a5769ce364ada007f174837` preserves all production bytes | Actual Native103 and Swift23 qualification, then Wave 3's owner-activation/Apple integration |
| Original migration | Original 182 operations, 159 heads, 156 snapshots and 332 archive entries remain preserved at their accepted source scope | Functional original-definition correspondence, signed-history availability and remaining C-specific Native proofs |
| Existing network and transfer controls | Original 12 network, two ACL-enforcement and two Linux P2P scenarios retained; independent-account file/range/crash/resume/cold evidence retained | No claim that those historical tests were rerun on every future combined binary; production cloud capacity remains an explicit limitation |

The retained quota observation was made at 05:42:45 UTC on 27 November 2026: the service reported `limitBytes: 0` and `usageBytes: 21070`. It is a historical observation, not a refreshed current limit. The two small retained full-tier files have their own accepted custody/recipient-offline evidence; the four-file large-cloud claim is not complete. Neither a new source commit nor a retry acknowledgement changes that fact.

### Primary evidence locations

The source publication receipt for ordinary attachment is `/mnt/development/projects/evidence/pinkha-ordinary-file-upload-20261127/recovery-source-publication1/result.json`, SHA-256 `b5935154d9b72f4b4e40c2b10490b3770aabfd8bd07cf190a4b5579de46ce333`. Its separate native receipt is `native-attempt2/result.json` under that same parent, SHA-256 `8b7a4dd471777d31dc37a7a95e7c00430c9d1463d540c95b9905f49146693159`.

The FilesV2 publication receipt is `/mnt/development/projects/evidence/pinkha-w1-final-authority-publication-20261127/attempt2/result.json`, SHA-256 `f70e4ea6c21c28b0242471e183c4345cc4babe0fcf172bc43f6b17dda5f0c208`. Native production receipt `9282a20d65d2dc3006a9a256e6fbeda926089b84efc770609d4e32b54cb89602` is `/var/lib/pinkha-c-filesv2-20261126/final-authority-native1/result.json`; actual metadata refusal receipt `8aaaf6fd04eb535bea79116ceaeac5a0dab6293d2d40bb1202616a6cef1c94ee` is the same parent's `metadata-authority-http-20261127/attempt1/result.json`.

The original Host31 receipt is `/mnt/development/projects/evidence/pinkha-bookmark-creation-contract-20261127/components-attempt1/result.json`, SHA-256 `9aa1b527c5df731f27f103cdeab2d93f672ba5d13bd9061167826ce5ef6aa465`. It remains failed. The successful 21-retained/10-new continuation is the same parent's `http10-attempt1/result.json`, SHA-256 `8a4ca85c7b7c0349c03e50145554324b7670129d029adbb31fbf8040910d82d8`; its complete source admission is `01c2db0d00d02e123c4697fcf034b4afe8214430fabf406e64192379af2da7c5`.

The positive Offload receipt is `/var/lib/pinkha-c-filesv2-20261126/positive-full-tier-offload-20261127/attempt2/result.json`, SHA-256 `75cfb31e711b2653905a76cf6faf3573976d3c88fa0548238b85c1ae916b85fd`. The earlier attempt `875ed86695e1cf5acc8ef38f5b6e553cb8d2fb2ef4cb885e52727d61a0e162da` remains failed before any Offload dispatch. Its fixture expected an original file where the retained protected PNG was a thumbnail; the successor binds the original thumbnail relationship explicitly without changing the native implementation or the target-file predicate. Each later qualification or publication must retain its own raw receipt and exact source/product linkage.
