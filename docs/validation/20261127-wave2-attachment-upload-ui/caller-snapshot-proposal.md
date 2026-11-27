# Ordinary attachment caller snapshot — proposed UI scope

Status: design for source review. No product code, local file operation, upload, compiler, native call or Apple test has been executed.

## Published dependency

Use `davidpovarsky/anytype-swift@e96ba072887e7581ed6de20fdd81e0897c83763d`, its original `AnyNativeObjectCreator.makeFileAttachmentCreator()` factory, and the unchanged existing creation journal. The 26-file source intake is retained in `wave1-source-intake.json`; all 30 declared component methods remain unexecuted. The published Host intent is Codable and verifies its original canonical fingerprint on decoding. Its journal can look up that exact intent but cannot enumerate or reconstruct it.

## Owner and new files

`AnyNativeLibraryRecovery` already belongs to the account/Space owner and survives replacement document presentations during a background runtime restart. Add one lazily created, internal attachment caller-snapshot store to that owner. Do not change the existing navigation/text draft state or claim that it persists after process termination.

Proposed new UI helper: `Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeAttachmentIntentStore.swift`. It owns bounded caller-snapshot file I/O and a per-document in-flight claim. It has no native client, grant, creation journal, upload or ID-generation service. The recovery owner returns the same instance to replacement sheets. A claim stays held until every operation owned by the previous presentation has finished; cancellation alone does not release it.

One internal `AnyDocumentPresentation` accessor checks the original mounted owner and recovery workspace, then returns that store. Torah remains the sole writer of that file and will insert the exact approved accessor separately after its related-document lifetime delta. This lane owns the new store, the small recovery-owner addition and the additive Attachments UI behavior only.

## Protected original request

Use a separate caller-state namespace under Application Support:

`PinkhaAttachmentIntents/any/<SHA256(account, Space)>/<SHA256(objectID)>.json`

The proposed record contains a format version and the exact `AnyNativeFileAttachmentIntent`. It may also retain the identity-only original file ID reported by the failed original operation, bound to that exact intent. That observation cannot be inserted into the creation journal or used by `resume` until Wave 1 publishes its separately reviewed safe reconciliation API.

Never store the selected URL, a bookmark to it, plaintext file bytes, native-normalized name/MIME/root CID/storage status, account/session leases or authorization. Name and MIME are only the original caller hints already contained in the Codable intent.

Bound the store to one pending intent per document, 32 KiB per encoded record and at most 128 pending documents per Space (4 MiB of records). A different pending intent cannot overwrite the current one; capacity failure is visible and does not evict unresolved work. Resolve directory components physically, refuse symlinks and nonregular files, use bounded descriptor reads, 0700 directories and 0600 files. Apply Apple data protection before bytes are written; synchronize the file and containing directory around the atomic replacement. Reuse the existing `AnyMiniAppsJournal` protection/fsync pattern as a source reference only; leave its file, namespace and MiniApps contract unchanged.

## Upload and retirement ordering

1. A current, writable mounted document opens the original `PinkhaDocumentTransferPicker(.open([.data]))`. Cancellation before selection has no intent and no native side effect.
2. Keep the selected file's security-scoped access for bounded off-main-actor fingerprinting and the Host's second bounded staging pass. No new UI plaintext staging copy is needed. Cancellation joins the child before releasing access.
3. With the existing account/Space owner claim held, construct one intent for this explicit user selection. Save and synchronize the protected caller snapshot before invoking `attach`.
4. Obtain the creator only from `try await document.objects.makeFileAttachmentCreator()`. Read authorization checks the registered session lease, mounted presentation and actual target read ACL. One-shot write authorization additionally checks the current write ACL, original document mutation guard and the original user operation.
5. Publish a result only while that presentation and lease remain current. After verified Host return, read the actual FilesV2 list and require the exact original reference and stable file metadata/content identity. Only this qualified reconciliation removes the corresponding caller snapshot. Durability remains the existing separate status operation; a 201 or retry 204 is not cloud-backup acceptance.
6. Closing, unmounting or account/Space retirement cancels and drains the owned task, removes visible metadata and releases its claim after completion. The protected original intent remains available to the same account/Space on reopen.

## Recovery is read-only

Read and decode the same original intent after reopening. Under fresh current read authority, call original `resume`; do not allocate another mutation ID, reselect a file automatically or call `attach`. A known journal ID is verified by the existing metadata/content/metadata path and then by actual list reconciliation. A reserved entry without an ID remains unresolved. A known error ID cannot override that reserved entry.

A saved request interrupted before the Host reserved dispatch can yield `noRecordedAttachment`. The safe proposed user-directed discard requires that exact original response, positive completion of the owner claim's old task, current authority and exact pending-intent comparison. No filename/content search or arbitrary ID match can establish a missing dispatch. This branch remains a design decision for root review; until qualified, retain the request without resending it.

## Preserved boundaries and known gap

Keep the published Attachments status/retry/open/QuickLook/MiniApps source `9e88bb9abd3536b76ccde71a102ba88ca82e3a9dd0c27e28850ae79359cfde73` unchanged outside the new upload integration. In particular, original 204 retry acknowledgement and actual status remain distinct.

The original row decoder requires name/MIME with 1024/255-byte caps, while the new typed uploader allows optional native metadata and larger resolved bounds. Do not silently broaden that decoder in this tranche. A returned row that the current list cannot faithfully represent must fail reconciliation visibly and preserve the pending intent. Root may authorize a separately scoped projection repair.

Source and model evidence can be prepared locally. Real shared-App compiler inputs, native upload/readback, unknown-ACK handling, cold reopen, picker cancellation, revoked permission, UI/visual, accessibility and physical-device acceptance all remain pending.

## Superseding source decision after original journal inspection

Wave 1 confirmed in HQ51 comment `1220952869906550` that `noRecordedAttachment` means absence in the supplied current journal only. Reopening an absent namespace can create a fresh empty journal. This result cannot certify that the original request never dispatched. Root therefore superseded the proposed no-record discard branch: the e96 UI candidate retains the exact caller intent, shows an unresolved result and permits only read-only Check. It neither offers cancellation/removal for that outcome nor sends the file again. Original picker cancellation before selecting a file remains intact.

The implemented record contains only the format version and original intent; it does not store the optional error-only file ID discussed above. Wave 1 owns a separate forthcoming actual-201 recovery receipt API. No unpublished successor is consumed by this candidate.

Initial source review also moved one-shot upload approval before the final write/lease/mounted checks and made claim/lookup failures conservatively require checking. Only a positive no-pending observation under the held claim distinguishes a local selection/fingerprint failure before any snapshot may have been saved. All initial source, findings and exact corrective deltas are retained alongside the candidate.
