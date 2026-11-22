# APP-01: native document history slice

## Decision and exact boundary

The existing native Any application can already select an account and Space, browse and search eligible documents, edit canonical editor blocks, edit native properties, and transfer canonical source associations through Files. Those capabilities do not amount to whole-app parity. The smallest additional original flow supported by an existing native API is a **read-only version-history browser for the mounted native document**.

This work adds that browser. It does not add restore, document creation from templates, saved-query sets, file attachments, a migration importer, or new sync behavior. APP-01 and its mounted native acceptance remain open until the relevant app flows run against the actual product binary. EDITOR-02 semantic anchors and MIG-01 migration are separate work.

## Bounded parity audit

| Original flow | Existing native infrastructure | Current application composition | Remaining boundary |
|---|---|---|---|
| Templates | Native object creation accepts `from`; the `template` collection and template tests exist. | Library search deliberately excludes template objects. The guarded native creation journal exposes type, collections, and initial properties; it has no template-copy intent. | A template browser and copy intent must retain guarded creation/recovery. Calling the ordinary create route directly would bypass that existing guarantee. |
| Sets and collections | Native collection/type APIs and native query/subscribe routes exist. | Library navigation currently covers folders, documents, all documents, and Notes. | A saved-query/set experience requires an explicit native query definition and renderer; ordinary collection membership is not proof of saved-query parity. |
| Files | Native raw upload and plaintext download APIs exist. Canonical association import/export already uses Files. | Canonical transfer covers source-association envelopes, not complete document body or attachment parity. | Whole-body/file migration and attachment presentation remain separate; migration API work owns the native attachment primitives. |
| Version history | Pinned native history list/view/diff/record routes exist, with causal version identity and typed unavailable/large/truncated errors. | No history API consumer or saved-version browser was present. Undo of the last acknowledged edit is a different existing action. | Implemented here: bounded list and read-only saved-text preview. Actual mounted native execution is still required. |
| Sync composition | Native status and SSE endpoints exist; independent native peer acceptance has its own evidence. | No native sync-status consumer was found in the five Any application modules reviewed. | Status presentation alone would not prove transport, offline, mixed-version, or multi-client acceptance. No sync certification is added here. |

Source review used the exact app revision `e073b6ac48d15af1b0a630940b1440e3f65a45ac`, whose relevant Modules were retained through the later shared controller-only changes, and native Any revision `88fae2e5ae7d0f46d6707567a3123081faa8de9a`. The per-file primary-source SHA-256 and Git blob IDs are recorded in `validation/SOURCE_PROVENANCE.json`. The migration API audit uses the same native Any revision and SDK `854df54cdadd76006ae823cbd1b1d923138356d0`.

## Native API and authority provenance

All new network operations are reads through the existing `AnyHTTPClient`:

| Route | New use | Pinned primary implementation |
|---|---|---|
| `GET /v1/spaces/{space}/objects/{object}/history?limit=50&coalesce=false` | Ordered version pages, with the server's opaque cursor | Any `internal/server/handlers_history.go`, routes in `handlers_spaces.go`, wire types in `internal/api/history.go` |
| `GET /v1/spaces/{space}/objects/{object}/history/{version}` | One bounded synced causal cut | Same native implementation and wire definitions |
| `GET /v1/spaces/{space}/members/me` | Current reader membership before and after each history request | Existing `AnyHTTPTorahTargetAccess.validateMember(..., intent: .read)` |
| `GET /v1/pinkha/capabilities` and `GET /v1/spaces/{space}/pinkha/document-targets/{object}` | Current compiled document policy and exact generation proof | Existing `AnyNativeDocumentPolicyClient` / `AnyNativeDocumentTargetProof` |
| Existing auth and health reads | Account identity and native-run lifetime checks | `AnyHTTPClient` and `AnyApplicationSession` / `AnyHostLease` |

The history endpoint has no dedicated advertised capability flag. An absent route is an explicit unavailable state; the browser does not synthesize local history. The existing document-policy contract must still verify. Current membership and the native proof are checked on both sides of every successful history request; changed proof or an unavailable authority check discards its reply. There is no new transaction joining those independent native reads, and the history API has no live subscription. The checks establish authority at read/publication time; they do not certify immediate discovery of an unseen remote revocation while a previously read preview remains visible. Backgrounding, document retirement, sheet closure, and session invalidation revoke the local history owner.

## Data and lifecycle rules

Native ChangeID and cursor order are preserved. The author timestamp is display-only and is never a sorting, freshness, or access fence. A version is the projection of its causal past, not a wall-clock snapshot. Native history excludes local/account values and may omit datasets configured without history. The UI therefore describes a saved-text preview rather than a complete document export.

Each continuation is bound to account, Space, object, session generation, and native `engineStartedAt`. Pages contain at most 50 changes, with at most 20 pages / 1,000 changes per open browser. Cursor repetition and duplicate versions fail explicitly. A limit is shown as a limit, never as history exhaustion.

The reader requests a 1 MiB page and a 4 MiB version response. It bounds retained opaque data, nested depth, datasets (32), and total records (10,000). The shared HTTP client's response byte check happens after `URLSession` receives its `Data`; this slice does not add streaming transport limits. Missing versions, truncated history, oversized views, malformed replies, and permission/session changes have distinct presentation states.

The complete decoded `AnyJSON` envelope and native dataset/block values are retained, including unknown fields, unknown block types, and exact `Int64` values. This is semantic JSON retention, not a claim that original serialized wire bytes are preserved. Unknown fields are never written back from a reduced DTO. The preview renders stored text with its original Markdown notation, identifies unsupported blocks, and keeps unreachable blocks separate. It explicitly identifies data it does not render.

The saved editor preview reuses the existing block/snapshot parser without inventing version stamps. In pinned SDK source, `internal/history/replay.go` serves the scratch CRDT records, and `TestReplayBuildsProjection` explicitly asserts that `_ver` exists while `_applySeq` does not. The history adapter and HTTP handler preserve those rows. These are source-backed shape checks, not a claim that this upstream Go test was executed during this slice.

The browser owns independent state and never replaces the live editor's snapshot or undo receipt. `AnyNativeDocumentView` uses an item sheet and the existing child-presentation reservation. Opening history requires a mounted document with no pending edits; readers are allowed and write permission is not required. The browser joins the existing document revoke/drain lifecycle. Request epochs and IDs reject late results after refresh, version changes, page failures, unmount, or close, including a transport that ignores cancellation.

## Owned paths and acceptance

Seven Swift paths are owned by this slice: new `AnyNativeHistoryReader`, its focused tests, new `AnyNativeHistoryPresentation`, its focused tests, new `AnyNativeHistoryView`, the narrow `AnyNativeDocumentView` menu/sheet/reservation hook, and the separate mounted `NativeApp/UITests/NativeHistoryTests.swift`. `AnyDocumentPresentation`, `AnyNativeEditor`, and the existing `NativeLaunchTests` are unchanged by this slice.

The focused controls exercise actual reader, model, and session source with scripted transport/authority observations. They are not native HTTP, native ACL, product Apple compilation, or mounted UI evidence. No previously passed suite needs replay solely because these controls were added.

Those focused controls now pass on actual Swift 6.3.3 for Windows: nine XCTest reader methods and seven Swift Testing publication methods, with no failures or skips. The raw log, source closure, dependency pins, earlier build timeouts, and an evidence-only reproducible checker are preserved in `validation/portable-originals` and `validation/PORTABLE_HISTORY_AUDIT.json`. Windows compilation excludes the conditional SwiftUI/UIKit view bodies; the remaining Apple and native acceptance boundary is unchanged.

The new `PinkhaAnyNativeUITests/NativeHistoryTests/testSavedHebrewVersionsRemainReadOnlyAcrossCloseBackgroundAndColdReopen` method is prepared for actual mounted execution. It creates one disposable account/Space/document through the normal UI, commits two distinct Hebrew strings, learns each native ChangeID from a real saved preview, and verifies those two causal handles without using author timestamps. Once its own writes stop, it permits additional native records while preserving the relative order and saved content of the two selected handles. It checks that viewing old history leaves the live editor unchanged, that backgrounding clears the previous preview, and that both handles/texts survive a cold reopen. It does not inject unknown datasets, an ACL transition, pagination, or typed native error responses. Those boundaries remain explicitly `NOT_RUN` in its planned receipt until separately exercised.

The mounted method is a new, separately selectable method; the existing launch methods are not changed or selected by it. The source file alone, and a grammar-only parse, are not mounted acceptance.

| UI surface | Accessibility identifier |
|---|---|
| Existing document menu | `any-native-document-options` |
| History action | `any-native-document-history` |
| Native ordered list | `any-native-history-list` |
| One native change | `any-native-history-version-{ChangeID}` |
| Saved preview | `any-native-history-preview` |
| Saved native block | `any-native-history-block-{blockID}` |
| Close | `any-native-history-close` |
| List/version problem | `any-native-history-problem` / `any-native-history-version-problem` |

Required remaining mounted acceptance on an actual native Any product build:

1. Create two distinguishable saved edits in a disposable native document; open history from its menu, keep native order, and preview each saved text without changing the live editor or its undo state.
2. Open history as a reader; establish that the read succeeds without write permission. Remove current access or change account/Space/native run during a delayed read and verify no result is published into the retired view.
3. Load an actual continuation, verify version identity across pages, and exercise missing/truncated/too-large responses without turning them into empty success.
4. Leave, dismiss, background, and reopen the document/history sheet. A stale request must not revive the old owner or interfere with Inspector, properties, or another document child.
5. Retain native evidence for an unknown block/dataset and for saved Markdown with Hebrew text. Confirm the preview states its rendering limits and no restore/write route is issued.

Physical iPad parity, full original-app parity, network ACL transport, mixed-version behavior, migration, and semantic-anchor acceptance are not completed by this slice.
