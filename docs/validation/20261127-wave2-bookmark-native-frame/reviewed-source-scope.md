# Ordinary Bookmark creation with the published native frame

Status: **local source candidate, frozen for review; not compiled or run**. No production branch, Native installation, simulator, runtime controller, or final integration ref was changed.

## Source and dependency boundaries

The seven complete candidates are in `candidate/`, bound by `candidate-manifest.json` (SHA-256 `1ad4c5583443aa8c674e78f1b9620396d901d26e7730942109afd18369c94d32`). `source-inverse.json` reverses every change to the exact per-file review original. The underlying UI revision is `087748598c502d59e70b966507e64ac80038159a`. Its complete preimages remain in `current-source/`.

The two hierarchy review originals in `source/` additionally contain the already-published rename correction `9e4aa3f1b88d8f6bfec27cdf2cb47d07ffd416ce`. The other five originals are exact 0877 bytes. This is an explicit source composition, not an invented whole-repository commit. A coherent immutable integration base still needs to include that rename and W1's published Host contract `6866f0e83a48917b07d919f9c77087f3eb441aa8` before any product publication or build. The current PropertyStore Unicode comparator from `937a` and TorahInspectorKit pin `26beca175d64a4d34e3567f2bbb4bf308d714478` are preserved exactly.

`source-w1/` contains the primary 6866 Frame/ObjectCreator bodies, related published tests, and contract documents. `source-intake.json` binds those reads. This candidate does not modify W1's Frame, ObjectCreator, Engine or Native contract. `dependencies/` binds the current document, Properties and imported-type read paths used in the bodyless-route assessment.

The prior seven-file proposal remains intact at `../bookmark-create/`, and its docs-only review bundle is published at `78b1549c7a88bd4095b9abff90dd59364bd80ec6`. Its queue-ownership and queued-cancellation findings/reviews remain historical evidence. That precursor did not enable a production route.

## Resulting user flow

The existing creation sheet gains **New bookmark**. A single eligible imported Bookmark Type proceeds directly to the original-style URL input; multiple eligible Types require only that actual choice. The row uses the existing Anytype text field, localization and URL validator. It keeps the original URL-first flow, URL keyboard and submit behavior. There is no mandatory Name step and no fabricated web title or preview. The native Name starts empty; existing Rename and Properties remain available afterward.

The list of creation choices is gated by the actual current `nativeBookmarkObjectCreate: 1` capability, the existing writer capability, and the original imported-type eligibility. The submitted Type and property owner are read again. A missing capability or eligible Type leaves Bookmark creation unavailable. This is a product capability check, not a switch based on test status.

Initial submission obtains the real `AnyNativeBookmarkCreationFrameReader` from the existing object creator. Within the existing session and captured Library lifetime, it prepares the ordinary hierarchy plan, reads the native frame, validates the actual mapped URL owner/key and exact memberships, and calls `frame.makeCreationIntent`. The mapped source URL is added once to its original namespace. No Type, schema, Note marker, editor block, alternate Name field, or preview is created by this adaptation.

The pending value retains both that immutable frame and its immutable intent **before object dispatch**. The same live hierarchy repository receives a narrowly typed creator through the already-reviewed optional `using:` parameter. Its original `mutationTail`, membership/parent checks and readback remain unchanged. The adapter reconstructs the expected fingerprint from the original plan and retained frame before using the original object creator and journal.

## Authority, cancellation and retry

| Boundary | Source behavior |
| --- | --- |
| Initial preparation | The native frame is read under the original session lease, current account and captured Library epoch. The reader itself checks the true native capability, response identity and final authority. Preparation performs no object creation or journal reservation. |
| Before pending insertion | Cancellation, owner loss or frame rejection leaves no dispatched object. The final Library epoch/cancellation checks precede insertion. |
| Pending insertion | The original plan, frame and intent are kept together before entering the existing retry path. No later catalog refresh rewrites them. |
| Object dispatch | Fresh descriptor/owner matching and current member write permission precede the original guarded creator. Native writer authority remains independent of the earlier frame's `canWrite` observation. |
| Cancellation after dispatch | The existing Host creator retains and awaits its original journal worker. This candidate does not replace that lifecycle or infer failure from the absence of a UI success. |
| Uncertain retry | Retry reuses the same frame, mutation ID, URL values and fingerprint. It never invokes the frame reader. The original journal's reserved state remains uncertain; a known created/verified ID is inspected through the existing Host path. |
| Descriptor or owner change | The current binding/lease check refuses; it does not obtain a replacement frame under the old mutation ID. |
| Publication of success | The existing hierarchy read and a fresh native Properties read must agree with the original Type, Name, mapped URL and identity. A final current-authority check precedes result delivery. |
| Owner loss | Library revocation disables writes and advances its epoch. Old completion cannot publish into the new owner. The pending value is not rewritten or promoted to success. |

The original Library pending-creation array is **process-local**. This tranche does not add durable pending-object intent storage, rehydrate it into a new Library instance, or claim cold recovery of a lost pending frame. A deliberate retry while that pending request still exists uses fresh current authority and the same immutable request. No second journal, journal enumeration or fresh mutation ID is introduced as recovery.

## Bodyless document boundary

Current `AnyEditorDocumentStore` still requires the real bracketed native object/markdown reads, a nonempty native version, and a complete bounded `editor_blocks` result. Its actual snapshot parser permits zero blocks. The candidate supplies no synthetic response, placeholder block or fallback body. A successful empty-body native read can reach the existing Properties/Link route; document `canWrite` comes from current member authority, and the Properties model independently requires its current native snapshot and mounted mutation authority.

The existing empty-document presentation offers Add paragraph as a separate user action. Empty block count is not treated here as a body-edit permission. Fresh bodyless warm/crash/cold behavior and the mounted creation/open/Name/URL/Link flow remain separate acceptance obligations.

## Focused source test inventory

- `NativeBookmarkPresentationTests.swift`: the entire original 10,518-byte, seven-method prefix is unchanged. Four appended XCTest methods describe 17 bounded source scenarios: empty Name and exact URL/membership construction, hidden/managed/changed bindings, exact readback identity, and six mismatched or non-writable frame cases. The same-frame intent survives actual Codable reconstruction in the positive cases. The controlled decoded frame fixtures are explicitly not Native signatures; these are downstream source tests, not native creation evidence.
- `AnyHierarchyTests.swift`: the entire published 38,951-byte, 27-method prefix, including the four rename methods/eight cases, is unchanged. The exact previously reviewed two-method/two-case creator override and queued-cancellation suffix is appended. The original queue implementation remains byte-identical.

All new tests are **NOT_RUN**. No old suite, portable control, Swift compiler, HTTP server or Native process was run. Existing whole-class counts and source admissions are not silently updated. W3 owns the matching compiled source inventory, selection and actual product acceptance.

The 6866 publication's Host31 qualification is separate evidence. Root subsequently reported W1's Native13 receipt `a2af96b5caafba77bdfa6aee7f39b3584651f6f17106092d0421a9735426e87d`; this source review did not re-read or requalify that execution. It does not substitute for the still-pending bodyless consumer and Apple UI gates.

## Review artifacts

`source-proof.json` records full inverse checks, exact Unicode comparator/rename/queue preservation, original test prefixes, the Kit26 pin and the single initial frame-read site. `precursor-composition.json` records the prior proposal's application to the current sources. `inspection-stops.json` retains an initial local display-script type assumption; it was not a product or test failure. Root and peer reviews of this exact successor must be retained before publication.
