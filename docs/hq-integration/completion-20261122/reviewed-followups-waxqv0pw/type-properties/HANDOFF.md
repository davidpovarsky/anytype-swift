# Original TypeProperties: bounded prepared-child continuation

## Frozen source

- Base: `davidpovarsky/anytype-swift` at `bbd11635598a77d98e7ffcb336fafee9a75eba10`.
- Patch: `original-type-properties-owned.patch`.
- SHA-256: `0a93b302ace640edef150621211cbf46aaacf4e641c942cd6caf1236d1fb4094`.
- Seven existing source files change. `CANDIDATE_INPUTS.json` binds their exact Git preimages and resulting bytes. The eighth source file, `OriginalEditorPropertyScope.swift`, is an unchanged reference and does not appear in the patch.
- No checkout, branch, commit, push, CI dispatch, account operation, or native RPC was performed for this increment. The frozen v11 producer remains untouched.

## Resulting route

`PropertiesListCoordinatorViewModel.showTypeRelationsView` captures the current parent's existing `PreparedEditorChildPreparation` before asynchronous acquisition. That same preparation opens the actual selected type in the actual Space with the original `.editDetails` and `.editPropertiesList` requirements. The resulting session is retained by the original coordinator, and its actual document identity must match the sheet data before presentation. The original `TypePropertiesView` receives this acquired session rather than resolving a second raw document.

Acquisition still uses the shared factory and `BaseDocument.openForOriginalEditorSource`. Already-open/cached external document adoption remains rejected. Failed acquisition never falls back to the legacy raw editor. A failed post-await publication retires only its acquired child and clears only its transient sheet state. Parent disappearance cancels a pending acquisition; child disappearance and sheet dismissal retire only the acquired child. Original `PreparedEditorPageSession.deinit` also invalidates its own session lifetime. No path blindly closes a shared document.

The original field rendering and the complete `TypePropertiesMoveHandler` reorder algorithm are preserved. The actual drop callback snapshots its rows and reserves the existing property scope synchronously before creating the asynchronous mutation. It requires the actual acquired document, original permissions and exact type identity. The final original service operation remains shared: `ObjectSetDetails` followed by `BlockDataviewRelationSet`, both targeting the selected type's original context ID. Referenced property IDs remain references; this route does not mutate those property objects.

The original `recordUpdatedTypeRelations` cache publication follows both RPCs. It now rechecks the same type owner's action permissions and uses that acquired type's Space. The unbound path retains its original Space resolution and native payload. There is no new storage engine, owner, dispatch tracker, catalog implementation or RPC implementation.

The owned sheet uses actual document subscriptions and a source-bound original `ObjectTypeListConflictingRelations` read. UI/cache publication rechecks currentness. The source-bound sheet does not launch automatic catalog provisioning or the unqualified asynchronous catalog refresh. Its nil/legacy route retains those original behaviors.

## Explicit remaining schema scope

| Original path | Current bounded behavior | Work still required |
| --- | --- | --- |
| Existing type reorder, including original cross-section move | Source-wired to actual prepared type owner and original native service | Apple semantic compilation; actual native drag, resulting original field order, revocation and sheet lifecycle acceptance |
| Type property-definition inspector/editor | External route remains unavailable; original nil route preserved | Acquire/retain the actual selected property document and qualify its original callback/service graph |
| Add property / create property / conflict-property addition | External route remains unavailable | Trace and bind `ObjectCreateRelation`, selected-property `lastUsedDate` mutation and all original selected-object callbacks |
| Reveal/hide/remove via existing catalog helpers | External route remains unavailable; original drag algorithm is distinct and remains original | Qualify `resolveCurrentTypeProperties` and `nativeProperties` without allowing their cache-miss bootstrap to mutate uncaptured schema objects |
| Automatic schema provisioning | Not entered by this owned sheet | Explicitly qualify every original extra schema-object acquisition and mutation before enabling |
| Already-open cached type document | Original source-bound acquisition rejects; generic original error toast, no raw fallback | A separate reviewed adoption contract, if desired; no relabeling or forced close |

These are internal implementation/acceptance boundaries, not missing user authorization or an external provider blocker. This increment does not declare the full editable Host or all schema/property writers qualified.

## Acquisition and notification trace

The exact original `DocumentsProvider` blob `4a65ab9d733aec50a54142a0d2bf67fa0754b706` distinguishes `document(...)` from `setDocument(...)`. The selected route acquires a `BaseDocument`. It does not create/open the separate `SetDocument` wrapper or mount a type `EditorPage`; consequently it does not enter that wrapper's independent schema-preparation task.

All actual `canonicalIdentityDidChangeNotification` occurrences were enumerated with `git grep` at the exact base and retained in `notification-search.json`. Exact source files are saved under `references`. The inspected notification consumers rebuild original local state; they do not themselves start a new schema RPC. The actual TypeProperties bootstrap and refresh are separately guarded. Existing global catalog and notification mechanisms are unchanged.

## Verification and evidence

- `source-audit-report.json`: eight bounded source preservation/admission invariants passed on the reviewed b2e35118 candidate. `source-final-admission-report.json` and `legacy-menu-preservation-report.json` bind the one-line final correction: the local-field menu is disabled only for a nonnil external scope, preserving the original nil-scope menu availability. They include exact Git preimages, byte-preserved original reorder algorithm and six original legacy schema action bodies, registered drop admission, exact original RPC target/service, guarded cache publication and actual fresh child retention. This is source evidence, not a Swift runtime test.
- `syntax-report.json` and `syntax-final-report.json`: the actual Windows Swift 6.3.3 compiler parsed all seven changed files with zero errors. After the one-line menu correction, only that affected View was parsed again; the other six exact results were reused. SwiftUI/UIKit semantic typechecking was not run.
- `patch-final-application-report.json`: `git apply --check --whitespace=error-all`, actual final patch application and all seven resulting byte comparisons passed in a new scratch directory. The prior b2e application receipt is retained separately.
- `peer-review.json`: integration agent's bounded source review found no concrete blocker. `peer-review-reconciliation.json` preserves the original receipt and proves all seven reviewed actual hashes match the reviewed b2e35118 regenerated manifest. The historical receipt observed two manifest rows while that manifest was being regenerated; `peer-review-final.json` records the reviewed one-line menu-preservation correction and the exact final patch. Six source hashes are unchanged.
- Previous owner/barrier/permission suites were not rerun. This patch changes none of their implementation files.
- Native editor UI tests: **0**. Actual native RPCs: **0**. Apple semantic compilation: **NOT_RUN**. No full-Host or Native acceptance is claimed.

The seven source files, final patch, manifest and final syntax receipt are additionally checkpointed in the new isolated Windows directory `C:\Users\DAVID\Code\Codex-Agent-HQ\build\original-type-properties-0a93b302-20261122`. The six unchanged syntax logs remain in the prior b2e35118 checkpoint directory. The producer checkout was not modified.

## Integration

Apply the seven-file patch only after checking the manifest's exact base blobs. It is disjoint from the History factory/version changes, channel role-lifetime work and root's EditorPageViewModel shake-undo change. It adds no target membership because all changed files already belong to the original target.

The next Apple compilation must include this increment before claiming its SwiftUI/type integration. The Stage B blank-note/two-block acceptance alone does not exercise this type-properties route; a native schema journey must separately prove the actual acquired type, original drag and both native updates, same source/account retention through awaits, and rejection after retirement or original permission revocation. Preserve all existing export, strict, source and consumer gates.
