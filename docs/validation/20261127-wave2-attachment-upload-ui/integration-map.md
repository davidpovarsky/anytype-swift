# Ordinary attachment upload: current source mapping

Status: read-only integration preparation. The exact Wave1 source/test packet is
requested in HQ51 comment1220951086952852. No API-dependent UI implementation is
present in this folder yet. The source-only checkpoint is not a promoted Native
contract, Apple product, or executed upload.

## Pinned current UI and original components

- App source read: `cee06ac951f735514059e616fbea48f07d4e7c09`.
- `Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeAttachments.swift`:
  SHA256 `9e88bb9abd3536b76ccde71a102ba88ca82e3a9dd0c27e28850ae79359cfde73`,
  Git blob `a08350fa183bb54a3e0ed686750b343ca59409db`.
  Existing list/open/MiniApps/status/retry behavior remains the preimage.
- `Modules/PinkhaKit/Sources/PinkhaKit/PinkhaDocumentTransferPicker.swift`:
  SHA256 `baad5d49111bd474a22c6e641b2747b0e5f19b2b006e4ad4d3bf52409e699020`,
  current Git blob `a941ce82f1985d4923db8ae0451912706bee4c1f`.
  This existing shared UIKit wrapper supports `.open([UTType])`, one selected
  file URL, exact one-shot delegate completion, and cancellation as success(nil).
  It does not itself hold security-scoped access or snapshot file contents.
- Existing Archive presentation illustrates scoped access and NSFileCoordinator
  for a bounded local read. Its JSON/archive/migration path is not an upload
  adapter and must not be repurposed.

## Existing lifecycle and authority

`AnyNativeAttachmentsPresentation.init` captures the exact mounted document
owner and registers revoke/cancel plus asynchronous close/drain with the
document. `close()` cancels and awaits its single owned task before releasing
owned preview directories. `requireActive()` validates task cancellation,
active state and `document.requireMounted(owner)`.

`AnyDocumentPresentation.canMutate` also guards write permission, navigation,
draft review, composition, semantic-anchor work, MiniApps and the foreground
surface. `hasPendingEdits` includes unsaved, unmapped, composing and saving
state. These UI flags do not replace a fresh native target ACL/lease check.

The existing storage Retry is an independently authorized, one-shot scheduling
action followed by separate status and metadata readback. It is not a retry of
file creation. Its notice, metadata bracket and known204 distinction must stay
unchanged when adding upload.

## Required typed API boundary (checkpoint only)

Wave1 checkpoint1220950767889704 advertises
`try await objects.makeFileAttachmentCreator()` using the original captured
client/workspace/private journal. Its component-only initializer fails closed.
ObjectCreator source pin is
`deb279cc959d535f4264072043069112403475bb1a300288f4628a959f4ce95a`;
contract pin is
`877f25249eea3ec03ee96d6d956b817326a1f349c6b95201ff44362687ef8ff3`.
Exact source/error/receipt/test signatures are not guessed from this note.

The intended read/write split is already documented by Wave1: local bounded
fingerprint; scoped intent with mutation ID; one durable reservation and one
upload dispatch; known-ID recovery through metadata/content-digest/metadata
reads; unknown acknowledgement does not resend. After lease/account loss, an
error may expose only the original scoped file reference and byte count, not
resolved native metadata. UI publication still requires current authority.

## Open source-integration points before implementation

1. Read the complete exact Engine/Host sources, their30 declared tests and the
   contract/review manifest. Source-only test declarations remain NOT_RUN.
2. Use the original picker and retain security-scoped access only for the owned
   local operation. Verify the actual uploader's snapshot/regular-file/size/
   cancellation guarantees before adding any UI staging. No unbounded Data
   load, persistent file-provider URL, or mutation of the selected file.
3. Add/Upload requires a currently mounted writable document without pending
   editor work; native read and single fresh write admission remain separate.
   Reconciliation is read-only and must not inherit upload permission or resend.
4. The same intent/mutation ID is required for recovery. The current sheet is
   freshly constructed; `AnyNativeLibraryRecovery` stores only in-memory
   navigation/text recovery, not durable attachment intents. Define the smallest
   explicit intent carrier across close/reopen and cold recovery after reading
   the real Host contract. Never open a second protected journal or infer an
   acknowledgement by matching a filename.
5. After a qualified success, fetch the actual current native file list and
   bind the returned file/object/Space/content identity before displaying the
   row. A request acknowledgement alone is not a list row or durability PASS.
6. Scope of future review: stale completion after sheet/document/account
   retirement, cancellation while provider bytes are being read or sent,
   changed selected content, known/unknown acknowledgement, same-intent
   reconciliation, read-only/ACL changes, exact native list readback and all
   unchanged existing9e88 operations.

No Host/Engine edit, source branch mutation, Oracle growth, compiler, Native,
Mac, simulator, real upload or generic controller was performed for this map.
