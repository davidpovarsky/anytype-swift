# Ordinary FilesV2 attachment contract

**Status: source implementation under review; component and native qualification pending.**

The UI owner is Wave 2. The Engine/Host adapter owner is Wave 1. Wave 3 owns final application integration and the native producer. This adapter uses the existing ordinary native file route and does not change the migration API.

## Native operation and identity

The native operation is `POST /v1/spaces/{spaceId}/objects/{objectId}/files`. The body is the original file bytes, not JSON, multipart data, or base64. The `name` query parameter and `Content-Type` header are metadata hints. The original native resolver owns MIME sniffing/refinement and filename extension completion. A successful response is HTTP 201 with the original `FileInfo`: `fileId`, `objectId`, `size`, `inline`, `durable`, `cached`, and optional `rootCid`, `name`, `mime`, `variant`, `variantOf`.

The response does not contain its account or Space. The adapter binds those fields to the original admitted request and validates the returned object, file and byte count. Ordinary attachment creates an original file owned by the existing object; it is available through the object's existing FilesV2 list/query. It does not allocate another object or an editor block. The native engine chooses inline versus content-addressed storage.

The wire surface is present in the original Any `8fbd1e819fb132ac0e0a848d2ddf5c5714189b81` lineage used by the qualified 1594/1599 source products. Their previous file proofs remain at their original versions and scope. The new Swift adapter is not qualified merely because the underlying route was previously exercised. The pending SDK read-authority/lifetime correction and the shared Apple native producer also retain their independent gates.

## Public sequence for the UI

1. Keep security-scoped access to the selected local file while fingerprinting and staging it. Call the bounded local fingerprint helper off the main actor. The helper returns the original byte count and SHA-256; it does not dispatch a native operation.
2. Construct one `AnyNativeFileAttachmentIntent` with the exact `AnyTorahWorkspace`, target object ID, a new 32-character lowercase hexadecimal mutation ID for this user action, metadata hints, byte count and content digest. Preserve this intent for recovery. Reusing its mutation ID with changed content, metadata or target is refused.
3. Obtain the typed service with `try await objects.makeFileAttachmentCreator()` from the existing `AnyNativeObjectCreator` in the document presentation. This factory captures the original client, workspace and existing `AnyNativeCreationJournaling` instance. It neither opens another journal nor admits a mutation. The explicit creator initializer remains available to the workspace owner with that same journal. Opening a second protected journal owner for the same workspace is not an ownership-transfer mechanism.
4. Call `attach(_:fileURL:authorizeRead:authorizeAttachment:)`. `authorizeRead` is side-effect-free: it checks the active consumer/session, actual account/Space and current read authority. It can be called more than once. `authorizeAttachment` performs fresh write authority and admits the one user mutation. A duplicate call for an already reserved intent cannot consume another native dispatch.
5. Publish the returned attachment only to that still-current UI/session. The result follows native metadata readback, bounded plaintext content verification and another native metadata read. Use its original file reference with the existing durability/status API.

The local fingerprint and private staging copy are two bounded passes. The second pass checks the exact first digest and source identity before dispatch. A changed file is refused before sending. Files range from zero bytes through 512 MiB; larger inputs are explicitly refused by this adapter. The entire file is never loaded into one Swift `Data` value. Ordinary files of both native storage tiers use the same raw-body route.

## Durable ownership and response handling

The adapter extends the existing metadata creation journal with the `fileAttachment` intent kind. The journal retains the scoped mutation identity and its fingerprint, then the original file ID. It does not retain the local source URL, plaintext file, name or MIME hint. One durable reservation owns the permitted POST. The reservation precedes the mutation-approval callback; an approval failure after reservation remains conservatively unresolved and cannot silently acquire a replacement dispatch.

After a valid 201 response, the original-scope receipt callback records `.created(fileID)` before checking the postflight account, consumer lifetime or cancellation. Thus an account change does not redirect the journal write into the newly active account. The client never follows a redirect or obtains a replacement body stream for a replay. Transport interruption, malformed success, a response bound violation, or failure after dispatch ownership has been consumed cannot authorize an automatic resend.

When a later check fails, `AnyNativeFileUploadUncertain.knownReceipt` carries only an `AnyNativeFileUploadAcknowledgement`: the originally scoped file reference and byte count. It does not expose the native name, MIME, root CID or storage state after the lease has failed. Full metadata is confined to the original-scope retention callback and a successfully authorized result. The Host validates the acknowledgement's scope and size before returning its identity-only recovery error.

Native Attach has no established caller-supplied idempotency key. A missing acknowledgement with no known ID cannot be attributed safely by matching filenames or identical content among concurrent uploads. Such a reservation remains unresolved. An explicit native error remains available as a typed status/code, but it is not treated as a rollback receipt and does not erase the reservation.

## Readback and recovery

The successful warm path requires the 201 metadata to agree with the first metadata read. It then reads plaintext content in bounded native HTTP ranges, verifies its complete byte count and original SHA-256, and reads metadata again. Account, Space, object and file identities use exact UTF-8 comparison. The immutable name, MIME, root CID and inline tier must remain stable across the readback. Cache availability and durability may legitimately advance; the final result reports the last actual native observation.

When the original file ID is recorded, `resume(_:authorizeRead:)` performs only metadata/content reads. It does not upload, create a replacement file, or consume another write approval. A new creator using the same durable journal can perform this recovery after a process restart or a lost UI acknowledgement. A recorded reservation without a file ID remains an explicit uncertain outcome.

The journal stores the original file ID and input fingerprint, not the native-normalized 201 metadata. A cold resume therefore proves current stable metadata plus the original content digest. It does not assert that the native metadata has never changed since the initial acknowledgement. Complete historical metadata reconstruction is a different contract.

| Outcome | Caller-visible meaning | Permitted continuation |
| --- | --- | --- |
| Source/digest validation failed before dispatch reservation | No POST was admitted | Correct the source/selection and use the intended user action policy |
| `.writeUncertain` with only a reservation | Native creation cannot be ruled out; no reliable file ID was retained | Keep the unresolved action; never silently resend or invent a replacement ID |
| `.nativeResponse(status:code:)` | Preserve the actual native status/code; reservation stays unresolved | Show the original failure and reconcile through the existing scope; no automatic resend |
| `.knownFileUnverified(fileID)` | The original ID is known but complete readback or final lifetime validation failed | Retain the original ID and use `resume` after valid authority is restored |
| Verified returned attachment | Exact current scoped file/content readback passed | Display it and read actual durability/status separately |

The low-level `AnyNativeFileUploader` is an Engine transport building block. The UI uses the Host creator so that durable ownership, duplicate suppression and recovery are present for every user action.

## Storage and resource boundaries

The uploader uses an exclusive private directory and regular file, restrictive permissions, no-follow descriptors, one-MiB copy/hash chunks and a bounded 65,536-byte response delegate. Header-declared and chunked response overflow are refused before unbounded accumulation. The original content digest is checked before consuming dispatch ownership. The source descriptor and staging inode/metadata are checked around copying and sending.

Staging is a temporary private plaintext copy, separate from the native engine's encrypted file storage. Apple data-protection and backup-exclusion attributes are applied before staging plaintext on the supported platform. Normal completion removes the owned staging copy. A process crash can leave private temporary residue pending owner/system cleanup; this source implementation does not claim that deferred cleanup has already occurred or that a temporary copy proves cloud custody.

A 201 receipt, successful readback, or cached file is not proof of cloud backup. Inline files are durable by their original native tier semantics. Full-tier files use `AnyNativeFileDurability.status` and the existing explicit `retry` contract. A native storage-limit failure preserves local availability and the original file identity. The UI must not clear the cache or infer upload completion from a retry 204.

## Qualification plan

The proposed focused component suite contains six source/staging methods, eleven bounded-loopback transport methods, and thirteen Host journal/recovery methods. It must enumerate all thirty exact methods with no skips. These are component and real loopback HTTP controls, not a native-account or Apple acceptance claim. A separate narrow original-native route/readback observation is required for the adapter's end-to-end qualification. Existing file transfer, partial-download, crash/offline, network and quota receipts are reused only where their source is unchanged.

The source predecessors, discovered ACK-binding gap, strict test failures, actual controller/source closure, command lifecycle and resource receipts must accompany the final handoff. Until those receipts exist, this contract remains source-only.
