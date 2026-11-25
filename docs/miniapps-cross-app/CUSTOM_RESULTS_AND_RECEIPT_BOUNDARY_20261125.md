# Custom result scope and native receipt boundary

Source review date: 2026-11-25. Consumer implementation reviewed at
`36a138dda50d2fb0b874f0b1635a80bb4b33fe5c`; shared Bridge and producer catalog
reviewed at `86a6dde354947be9329fe1e8f4d45a433fe488c4`.
This is a source contract review. It does not grant native application, file,
simulator, device, signing, or TestFlight acceptance.

## What custom means in the current protocol

The shared `MiniAppResult` contains a request ID, status, operation, content
items, optional message, and string metadata. It does not contain a typed
return-side host command or host action identifier. `actionID` belongs to
`MiniAppCatalogItem` and the outbound `MiniAppInvocation`, not the returned
result. The current producer projection in
`AI_HLY/Downstream/ProductSplitIntegration/HanlinExternalMiniAppSession.swift`
does not populate that optional catalog field.

The current catalog advertises display, insert, replaceSelection and
replaceDocument for TextStudio, and display/custom for other projected apps.
This declaration does not define an Anytype action to dispatch. The shared
`MiniAppTextEditing` helper explicitly returns the original document unchanged
for display and custom.

Anytype currently handles custom with its native result sheet, using the same
presentation path as display. The shared presentation shows the message,
selectable text/JSON items, user-activated URL links and file ShareLinks.
Opaque result metadata is not interpreted as an executable command. Neither
the coordinator nor this viewer claims that an arbitrary host action ran.

The result is acknowledged after the user closes the sheet with its Close
button or dismisses it interactively. Before acknowledging, the coordinator
revalidates the original account/editor lifetime. Acknowledgment means that
this result was consumed by the viewer; it is not a receipt for an original
Anytype command or a document mutation.

No declared return-side command is being silently skipped under this schema.
Adding automatic host actions would require an explicit action contract,
authorization and corresponding original native action implementation. It is
not implemented by treating arbitrary metadata as executable instructions.

Relevant current sources:

- Shared `Packages/HanlinMiniAppsBridge/Sources/HanlinMiniAppsBridge/MiniAppContracts.swift`.
- Shared `Packages/HanlinMiniAppsBridge/Sources/HanlinMiniAppsBridge/MiniAppPreferences.swift`.
- `Anytype/Sources/Pinkha/MiniApps/PinkhaMiniAppsCoordinator.swift`.
- `Modules/PinkhaAnyHanlin/Sources/PinkhaHanlinUI/PinkhaMiniAppsPresentation.swift`.

## Original native mutations and recovery

Insert and replacement operations use
`PinkhaMiniAppsResultApplier` and the original native block services.
They are separate from the viewer acknowledgment path described above.

The app saves a request-specific edit plan before its first native mutation.
The private journal namespace includes the account, space and object identity.
Text replacement rereads the original block before the native write, compares
the captured content/marks, performs the original setText operation, and reads
the native state back before recording that block as applied. Recovery
recognizes the expected after-state. A newer changed state is preserved rather
than replaying the old replacement over it.

Inserted content is created with a request/index identity and the
`pinkhaMiniAppsRequest` native field in the initial block creation request.
After a crash before the local insertion receipt, the app looks for that marker
in the original native block graph. It refuses ambiguous multiple matches.
Once an inserted block is recorded, a later user edit or deletion does not
cause the result to be inserted again.

Files are actual native file blocks. The app uses the original upload service,
not a URL string inserted as document text. Before uploading it compares the
returned attachment bytes and a private upload copy, then rereads the original
block and its exact file state after those asynchronous operations. After
upload it downloads the original native file, verifies the exact bytes, and
rereads the marked native block again before saving the insertion receipt.
A completed upload encountered during recovery is accepted only through these
original native identity and byte-readback checks.

The journal is marked completed before the transport result is acknowledged.
A repeated callback whose journal is already complete can acknowledge the
pending transport result without repeating the native edits.

## The boundary is not atomic

The original native RPC, native readback, private JSON journal write and shared
Bridge acknowledgment are distinct operations. There is no native
compare-and-swap transaction encompassing both the document and this receipt.

A concurrent edit can still occur between a fresh read and a native RPC.
Independent changes can also partially complete before a later operation
fails. Context/cancellation validation, per-document serialization, request
markers, exact readback and the durable plan narrow these windows and allow
conservative recovery; they do not make the sequence atomic.

If validation or readback fails, the coordinator leaves the result pending
and reports the failure. Previously completed native changes may still exist.
This original-app behavior must not be described using the separate
embedded-editor private-draft/SQLite transaction guarantees of Maktabah.

The real original application acceptance, including warm/cold callbacks,
replay, preserved newer content and actual file bytes, must be reported from
its own executed results. This document is not a substitute for those tests.
