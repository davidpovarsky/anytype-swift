# G03 Topic/Word routing — bounded source audit

Status: **existing typed management routes confirmed in source; current-product UI acceptance remains open.** No product file, controller, fixture, schema or Native contract was changed. No Oracle, compiler, Native, Mac, simulator or XCTest operation was performed.

## Decision

The inspected production paths do **not** cast Topic or Word identities into text-reference selections. The accepted implementation contract already routes typed links to a scoped management chooser. Original native Properties opens that chooser in the correct fixed category; the new engine additionally exposes kind-preserving Related documents navigation. A Topic/Word reader page is not implemented by the pinned Kit and is not claimed by this audit.

Consequently, this audit does not establish a product misrouting defect that justifies changing the reader or adding a new route. It narrows the G03-kind-routing queue entry to acceptance of the existing management/related-document capability. A separate request for Topic/Word detail-reader screens would require an explicit capability decision; disabled/omitted Open controls alone must not be reported as such a reader passing.

## Exact source and requirement boundary

- App: `cee06ac951f735514059e616fbea48f07d4e7c09`, final integration ref re-read at 2026-11-27 11:14:56 UTC and unchanged.
- Current App package pin: TorahInspectorKit `9058b489e9acc271b4f8ef69e2ed24648f93b4ed`, independently read from both PinkhaAnyUI and PinkhaTorahPresentation package manifests.
- T3 Asana `1219604675985547` explicitly retains source/topic/word type-correct routing. Its broader UI acceptance remains open. T6 `1219604717617397` does not certify source/reader navigation from the historical search-layout sign-off.
- Inspector-search task `1219878918433851` retains an older proposal to open/read results in the panel; that proposal was not itself an approval for Topic/Word reader implementation.
- Current tracked ADR `docs/pinkha/torah-integration/ADR-TORAH-ASSOCIATIONS-PRODUCTION-UX-2026-10-20.md`, decision 4 and limits: one REF opens Inspector; multiple or typed items use the scoped management chooser; Topic/Word must never become verse selections.
- Current tracked `ACCEPTANCE_MATRIX_2026-10-20.md`, OPEN-03, records exactly that chooser contract. Its historical CI labels are retained as historical claims, not re-executed or promoted to current acceptance here.
- Current required-coverage UI05 requires source/topic/word, standalone/embedded, loading/empty/selection, link/unlink/relaunch and hidden/visible behavior. UI08 requires enabled document-target navigation, back route and capability disposition. These remain separate from a Topic/Word reader.

## Production call paths

| Entry | Actual current route | Kind/target guard and limit |
|---|---|---|
| Original Anytype native property value, all three writing Types | `PropertyValueCoordinatorViewModel` → `TorahNativePropertyEditorView` → `TorahNativeDocumentPicker` → shared `TorahSourcesSearchPresenter` | The native property key resolves its definition; `.ref/.topic/.word` map to `.references/.topics/.words`. `fixedScope: true`; target is the actual Space/object document context, including Set-cell entry. No ordinary Tag option object is manufactured. |
| Source result / linked source in that picker | Shared presenter → reference resolution or guarded association → `TorahInspectorSelection` | Results require `.references`; association Open requires `.ref`, nonempty key, excluding the Note sentinel. The presenter checks current context before navigation. |
| Topic/Word result or existing linked chip | Existing matching picker exposes Link/Unlink, with typed provider resolution | Heart result rows have no primary Open action for these kinds; linked chip Open is disabled. The provider-specific Topic/Word resolver produces the corresponding typed canonical association. No text-provider request is made by these Open paths. |
| Original fallback projection row, when applicable | `PinkhaTorahPropertiesModel.edit(kind)` → `presentSearch(.document, initialCategory: kind, host: .properties)` | Explicit exhaustive kind mapping and frozen document context. This is not substituted for the original native row. |
| New-engine Properties value/menu | `AnyNativePropertiesView.propertySection` → Related documents, or Add in matching category | Open source is offered only when the same shared `.ref` guard succeeds. Topic/Word expose their exact item to Related documents; the Add action retains `.topics/.words`. No Topic/Word reader option is advertised. |
| Shared linked-block accessory | `openLinkedAssociations(blockId:)` | Exactly one openable REF enters Inspector. Multiple or typed items open the original exact-block management chooser. The generic chooser initially uses References and displays the scoped association set; this is the existing documented chooser behavior, not a text cast of its typed items. |
| Featured source header / G03 overflow | `documentPropertyProjection.sources` → `openDocumentAssociation` | Header input contains sources only. The already-published G03 hidden-source test must not be credited as Topic/Word navigation. |

### What the Kit can actually display

At the pinned Kit9058, `TorahInspectorSelectionScope` is only section/segment. `TorahInspectorRoute` is search/segment/source/fullSource. The public Inspector provider reads text by reference and relationships for a reference. The separate App provider facade has typed Topic and lexical resolution, but that is not a Kit detail-reader route.

The future G04 Kit26bec publication retains the exact Models, ProviderProtocols and Route blob identities, verified against its existing full-tree retention receipt. Its reader-lifetime correction therefore does not add a Topic/Word reader. It is not yet assumed to be the current App package pin.

## Existing evidence and finite acceptance

1. **Keep the accepted Native Topic/Word journey:** `NativeLaunchTests/testTopicAndWordLinksDriveDerivedRelatedDocumentsAfterColdReopen`, run `45087682296`, source `7293e4fd0bcabdcdb643d5768b777b8e87ff1b73`. Its original body explicitly says Topic/Word reader pages are not assumed. It creates real typed provider links, opens their Properties menus, navigates Topic-related document B→A, verifies Word-related A excludes Topic-only B, and verifies retained IDs/labels/Word results after cold reopen. The retained PASS remains historical and scope-specific; it is not an instruction to replay it or proof for a new App product.
2. **Existing original Properties selector:** `PinkhaStage1AcceptanceUITests/PinkhaNativeDerivedAcceptanceUITests/testNativePropertiesPickerChipsSetMembershipAndRelaunch` selects Source, Topic and Word through the real native value area on chiddush/article/research, then checks their actual labels after cold reopen. Use only its already-qualified original consumer/fixture when the shared product is admitted; no new broad selector is needed solely to assert typed picker routing.
3. **Canonical Source/Topic selector:** `PinkhaStage1AcceptanceUITests/PinkhaTorahPropertiesAcceptanceUITests/testOriginalPropertiesCanonicalLinkUnlinkAndRelaunchForAllWritingTypes` explicitly checks the original fixed-scope picker has no segmented category control. This covers its actual Source/Topic link/unlink contract, not Word removal.
4. **Future G02:** the already-published seed/native-baseline/Word-unlink/native-postflight sequence covers the missing Word cancellation/removal/cold persistence boundary for all three writing Types. It stays gated and does not gain Reader or current-product credit from this audit.
5. **Existing component selectors (source inspected only):** `TorahAssociationNativeRepositoryTests/embeddedTopicAndWordLinksPreserveKinds()`, `linkedBlockOpeningRoutesByAssociationShape()`, and `propertyRoutesResetCategoryAndTarget()`. The last includes all three categories and freezes the document target despite prior block context. No tests were run or newly selected here.

Current UI acceptance still needs the real admitted product, original fixture/custody, exact result nodes and retained screenshots/visual review. The English original Properties routes do not replace the outstanding Hebrew/RTL, readonly-role or accessibility acceptance matrix. No historical T5 calls or passed journeys were repeated.

## Explicit capability boundary

Neither inspected search view currently renders a dedicated message saying that Topic/Word reader pages are unavailable: it disables or omits their Open actions while retaining linking/management. This is **not** evidence that a Topic/Word reader exists. It is also not a proven violation of the accepted scoped-chooser contract.

If the final acceptance authority requires an in-product explicit reason in addition to the existing typed management destination, the smallest candidate would be a shared presentation-only capability description consumed by both search views and the Properties menus, keeping `.ref` guards and all canonical IDs untouched. That is a proposal only; no reader, attachment, index, schema, provider contract or product file was changed during this audit.

## Evidence

`source-manifest.json` binds all25 primary App/Kit files to exact repository/ref/Git blob/bytes/SHA256 and retrievable source URLs. Full code is not duplicated in this checkpoint. `requirements-reference.json` records task IDs and source requirements without raw comments. `audit.json` retains the original local audit hash references and source-only limits; its local full-code/raw-task/lookup receipts remain original working evidence, not packaged private inputs. Primary404 path-discovery responses were not treated as source observations.
