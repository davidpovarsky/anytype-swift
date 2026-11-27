# Ordinary attachment upload UI — reviewed source preparation

Status: **SOURCE_REVIEWED_NOT_COMPILED_NOT_RUN**. This packet is an isolated downstream UI change. It does not qualify a Native binary, Host contract, Apple product, filesystem crash behavior, device protection behavior, or mounted UI journey.

## Exact dependencies and publication

The source parent is `1384176f817605d6d97e07c7a1366a3d5fd8501c`, tree `c8d94e00158db1a25fa8f035fb48ce54b66d4a29`. That separately verified dependency commit has ordered parents:

- W3 source `e4556ba1edbf7c698eb04cb1ecc9caaeed34e1ff`, which already contains the published ordinary FilesV2 Host/Engine source `e96ba072887e7581ed6de20fdd81e0897c83763d`.
- Published related-document lifetime source `21d63bef8950f8b927f0d8d3b4b052758bc98fcb`.

The dependency merge imports exactly the lifetime tranche's four source/test leaves and 59 evidence leaves. The complete finite Merkle comparison preserves every other original blob and mode. The attachment child adds two Swift files and modifies three Swift files; its Document delta is exactly the separately reviewed 204-byte accessor. It does not copy the lifetime implementation into the attachment child.

Publication uses the GitHub source API on a new owned `codex/chatgpt-wave15-wave2-attachment-upload-20261127` ref because Oracle materialization remains reserved. It is not a CLI push or a working-tree cleanliness claim. No final branch, workflow, Package manifest, PBX project, source map, Native input, Hanlin SDK source, or test consumer is changed. The publication preflight retains both corrected inspection failures, the current 83-workflow exact audit, and primary reads of all 17 default-branch workflows. No build workflow is dispatched.

## User-visible behavior

The existing Attachments presentation gains Add through the original document-transfer picker. Picker cancellation remains the original local cancellation. A selected file is fingerprinted under its security scope, and one exact typed Host intent is durably saved before the original attachment creator is called. File staging, checksum validation, creation journal, write authorization and Native mutation remain owned by the published Host/Engine implementation.

The caller snapshot belongs to the existing `AnyNativeLibraryRecovery` owner. The Root → Library → Document route already requires and preserves that owner. The mounted Document accessor returns its same store; no replacement creation journal or recovery owner is created. The snapshot stores the original Codable intent only: no selected URL, file body, normalized Native metadata, grant, or error-only file ID.

The protected store uses a bounded private per-account/Space namespace, one stable physical lock, an actor claim held through actual task drain, no-overwrite creation, file and directory synchronization, and exact readback. The limit is 128 pending records per Space with a 32 KiB record bound; there is no eviction. Source review is not physical protection or power-loss acceptance.

Successful attach or same-intent resume must pass fresh scoped authority and an actual file-list reconciliation before the exact pending snapshot can be removed. A failed or uncertain write keeps the original intent. Check performs same-intent read-only reconciliation and never chooses a new mutation ID or resends a selected file. `noRecordedAttachment` is deliberately unresolved: absence in the currently supplied journal cannot prove continuity with the original journal or prove that an upload never happened. It does not enable removal, cancellation, or automatic resend.

The existing mounted status, explicit cloud retry, 204 acknowledgment distinction, preview, MiniApps import, open/close authorization, and per-Space access paths remain preserved. A later module-minted ACK-recovery API is outside this e96 source tranche and is not guessed here.

## Source review and retained findings

`root-source-review-v2.json` binds the exact five final sources. `editor-storage-source-review.json` independently covers the storage, ownership and test seam. `source-inverse.json` restores all three original complete files byte-for-byte. The separate accessor proof restores the entire published lifetime Document.

Earlier source candidates, the type-namespace correction, the original three UI findings, and their exact corrections remain in this packet. The final UI consumes one-shot approval before the last authority checks, treats an unknown/conflicting pending lookup conservatively, and retains noRecorded intent without the earlier discard behavior. The store's final documentation correction leaves the independently reviewed executable bytes unchanged.

## Pending actual acceptance

The new `AnyNativeAttachmentIntentStoreTests` declares **three methods / four cases** in the original `PinkhaAnyUITests` target:

| Method | Declared cases | Scope |
|---|---:|---|
| `originalIntentSurvivesNewStoreWithoutASelectedURLOrNativeReceipt` | 1 | Exact caller intent after a new store instance |
| `replacementStoreCannotAcquireOrOverwriteTheOriginalPendingIntent` | 1 | Exclusive ownership and no replacement overwrite |
| `malformedOrForeignSnapshotCannotBecomeARecoveryIntent(foreignWorkspace:)` | 2 | Malformed bytes and foreign scope rejected |

**None has been compiled or executed.** W3 must add the new source to its actual hosted source/compiler inventory before any hosted result claim. No XCTest selector or package mapping is fabricated by this packet.

Mounted acceptance still needs the matching actual App, Host and Native fixture: picker cancel; ordinary attach with exact content/file-list readback; same-intent cold reopen; concurrent/replacement presentation rejection; unknown-ACK/noRecorded read-only Check without resend; late permission loss/cancellation with task drain; and preservation of existing preview/cloud status behavior. Device file protection and crash durability require separate actual evidence. The original decoder's optional-name/MIME bounds are a separately approved follow-up; this upload packet does not silently change raw metadata semantics or infer whether the original Native list requires an inline field.

All Apple, Native, compiler, simulator, visual, physical-device and crash acceptance remains **NOT_RUN** for this tranche. Historical accepted drag and unrelated T5 journeys are not scheduled or replayed here.
