# T5 related-document publication — source audit

Status: source review only. No Oracle, Mac, compiler, Native, simulator or XCTest operation was performed. Product changes were not made during this audit. The subsequent scoped correction has its own candidate and review evidence.

## Exact source

The App source is `d8a2c67b6dae09a7b769e803a319de3d3080019c`. Its `PinkhaTorahPresentation` package still pins TorahInspectorKit `9058b489e9acc271b4f8ef69e2ed24648f93b4ed`. `source-manifest.json` records 24 primary GitHub file reads, their Git blobs, SHA-256 and byte counts. The complete bytes are retained locally; the review covered the named paths and relevant declarations, not every unrelated method in those files.

## Existing boundaries

| Path | Publication and authority boundary | Source-level conclusion |
|---|---|---|
| Heart Notes service → Space related service → shared Inspector repository | The service binds the query and live Object.Show result to the requested Space, rechecks canonical/projection eligibility and propagates current authority errors. The exact current-Space denied/invalidated errors are typed. | No proven former-Space result publication was found in this path. This does not establish actual Native ACL acceptance. |
| Native Notes service → `AnyNativeTorahRelatedPresentation` | Initial query, current metadata and final query are compared. Metadata must match the exact object and Space. `AnyApplicationSession.perform` validates the account/run lease before and after the operation. | Existing guards remain necessary. An incomplete generation still reports `indexFreshnessUnverified` and cannot authorize unlink. |
| Shared Kit repository → related-documents panel | Each selected reference has a flight UUID/generation. Retirement cancels flights, removes generations/cache, and notifies the exact repository's panels to discard old rows. Late completions cannot restore the retired cache. | Typed authority failure removes previous results. An ordinary transient refresh failure deliberately retains previous rows with an explicit previous-results notice and Retry. That behavior is not represented as current/fresh acceptance. |
| Shared search presenter | Query, scope and request identity gate suggestions and resolution; view disappearance invalidates the presenter's requests. Resolved navigation validates the original document context. | This source-provider suggestion path is separate from Space-wide related-document indexing. No readiness is inferred from provider suggestions. |
| Native Properties → `showDocuments(with:)` | Uses the real typed index, metadata and session lease, but only the document epoch/modal booleans gate successful UI delivery. Failure publication has no ownership guard. | Concrete presentation-lifetime defect described below. |

The owner wiring is explicit: Heart's `TorahEditorHostModifier` deactivates its shared session on editor disappearance. Native `AnyDocumentPresentation.unmount` deactivates the same shared session, and `AnyUIPresentationLifetime.revoke` invokes registered document revocation synchronously. These are application lifetime boundaries; they do not substitute for current Native permission decisions.

## Concrete finding: Properties lookup can outlive its presentation

At the audited App source, `AnyNativePropertiesView.propertySection` starts an unstructured `Task` for Related documents. `AnyDocumentPresentation.showDocuments` captures only the document's epoch, then performs its reads. Its successful path checks that Properties is currently shown and no competing child is currently visible; it does not check the identity of the Properties presentation or lookup that initiated those reads. Its catch writes `message` unconditionally.

A source-permitted ordering is:

1. Properties presentation A starts a lookup and the read suspends.
2. A closes. The document remains mounted, so its epoch is unchanged. No lookup token is retired by this close.
3. Properties presentation B opens on that same document. Its modal booleans again satisfy the old lookup's success guard.
4. A's delayed success can open its result in B. A's delayed failure can overwrite current feedback, including after unmount/revoke because that catch has no guard.

This is a demonstrated missing source fence, not a runtime reproduction or proof that another Space's data was displayed. The direct Properties rows/title also remain in the old document model after unmount; the audit does not infer visual exposure merely from retained memory.

Root authorized a minimal follow-up: synchronously capture request ownership at the user action, include the Properties presentation and document owner, retire/cancel at close/unmount/revoke, gate results/errors/cleanup, and retain the exact native read body. Only controlled noncooperative late success/error/reopen regressions are in scope.

## Readiness seam and Wave1 ownership

Heart currently uses `AnytypeT5NativeRelatedLookup.current()` and `AnytypeTorahSpaceRelatedDocumentsService.loadRelatedDocuments`. The expanded lookup is enabled only by the explicit build/runtime capability. Both existing Heart result paths still include `indexFreshnessUnverified`; ready-looking row metadata alone does not remove it.

Wave1's primary HQ update `1220951663961726` identifies the separate `PinkhaTorahSpaceIndex` protobuf, original service/RPC mapper/bridge and gated Swift client. That work remains Wave1-owned. Once its exact promoted contract is delivered, the existing Heart service boundary can consume its typed readiness/current-Space decision; no duplicate index, wire or storage implementation is needed here. The native HTTP lane already consumes `AnyNativeIndexReadiness` and a generation at `AnyGuardedTorahIndex`, then rechecks it around metadata. No current producer/fixture admission follows from this source audit.

Historical T5 36+9 evidence remains unchanged. No prior Native calls or UI journeys were replayed.

## Primary references

- [App related-document presentation](https://github.com/davidpovarsky/anytype-swift/blob/d8a2c67b6dae09a7b769e803a319de3d3080019c/Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeTorahRelatedPresentation.swift)
- [App document presentation](https://github.com/davidpovarsky/anytype-swift/blob/d8a2c67b6dae09a7b769e803a319de3d3080019c/Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyDocumentPresentation.swift)
- [Native Properties view](https://github.com/davidpovarsky/anytype-swift/blob/d8a2c67b6dae09a7b769e803a319de3d3080019c/Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativePropertiesView.swift)
- [Heart Space related service](https://github.com/davidpovarsky/anytype-swift/blob/d8a2c67b6dae09a7b769e803a319de3d3080019c/Anytype/Sources/Pinkha/Torah/UI/AnytypeTorahSpaceRelatedDocumentsService.swift)
- [Shared editor session](https://github.com/davidpovarsky/anytype-swift/blob/d8a2c67b6dae09a7b769e803a319de3d3080019c/Modules/PinkhaTorahPresentation/Sources/PinkhaTorahPresentation/TorahEditorSession.swift)
- [Pinned Inspector repository](https://github.com/davidpovarsky/TorahInspectorKit/blob/9058b489e9acc271b4f8ef69e2ed24648f93b4ed/Sources/TorahInspectorCore/TorahInspectorRepository.swift)
- [Pinned panel state](https://github.com/davidpovarsky/TorahInspectorKit/blob/9058b489e9acc271b4f8ef69e2ed24648f93b4ed/Sources/TorahInspectorUI/TorahPanelLoadState.swift)
