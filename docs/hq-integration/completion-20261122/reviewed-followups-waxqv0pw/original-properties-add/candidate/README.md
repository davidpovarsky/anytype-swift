# Same-object Add Property: isolated source increment

This packet enables the existing prepared object's **Add Property** entry to present the original `PropertiesSearchData` / `PropertyCreationView` route. It changes only `OriginalEditorPropertyScope.swift` and `ObjectPropertiesViewModel.swift`.

The base source is `388a3726e7a38cf47aaeb32948013c395b8b2b01`; its published evidence child is `06b639ff196a66c19d22dda7ea28b47ce6801705`. Both preimages are retained under `base/`. The complete proposed postimages are under `source/`, and `original-property-add.patch` applies exactly to those two preimages. `SOURCE_MANIFEST.json` records the Git blob IDs, SHA-256 hashes and byte lengths.

## Source behavior

The existing opaque property identity snapshot now carries the actual canonical manifest returned by the existing source-bound canonical read. That manifest remains metadata for one operation and one issuing scope. The view model never stores the identity or manifest as permission for a future tap.

Add eligibility calls the original pure `TorahDocumentPropertyEligibility.includesDocument`. It preserves the original mapping of document ID, raw `details.type`, `resolvedLayout ?? layout`, deleted/archived flags, and internal-field **presence** checks. It does not add a registered-type allowlist. The prepared route also checks the actual current relation-value, detail and property-list permissions required by its existing modal writes.

The original `details.isTemplate` helper cannot establish this prepared route's template classification: it consults the global `ObjectTypeProvider` cache and falls back to a deleted-type placeholder. The initial `f348fa5d...` proposal used that helper and was rejected during source review. The rejected patch and postimages remain under `review/rejected-f348-template-cache/` and must not be published as the implementation.

The revised Add-only eligibility helper releases its temporary source read, then uses the **existing** `OriginalSearchMiddleServiceBinding.requireOriginal` and the same Owner's `ObjectSearch` read admission. Its original search uses `SearchHelper.includeIdsFilter([capturedTypeId])` and the exact captured Space. It requests ID, Space, layout, resolved layout and unique key. There is no `layoutFilter` in the request: the returned layout is checked **after** the native result, alongside exact cardinality, byte-exact ID/Space, and an actual nonempty protobuf string unique key without NUL. The template comparison uses that unchanged returned string and the original `ObjectTypeUniqueKey.template.value`. There is no cache, prefix, default or substitute service fallback. Full parent details, permissions and the raw type are checked again after the await.

The prepared section task keeps its original row projection after the canonical read. The extra type read controls only the Add hint. The hint stores a passive copy of actual details, parsed properties and permissions. Current getters compare that copy against the live document and source; a tap performs fresh canonical and type reads, then rechecks the complete captured state before presenting the modal.

The actual prepared subscription task is retained and awaited through a cancellation handler. That handler cancels only the captured task handle, so a pending Add observes view cancellation before the outer MainActor cleanup resumes. Subscription/request UUIDs identify UI work only. A cancelled predecessor cannot clear a successor's task or publish a late modal. Repeated Add taps do not replace an active request. Original relation, root-detail and permission updates are observed; unchanged state suppresses the initial duplicate read and unrelated updates. Canonical-identity notifications explicitly force a fresh read.

The prepared modal receives the same current object/Space and the retained issuing scope. Featured, sidebar, conflicted and legacy-featured exclusions, hidden IDs and the original no-op selection callback are preserved. The modal binding is published after the temporary read lease has returned. Existing modal selection/save remains responsible for its original before-Task named write reservation and actual native delegate.

## Verification and scope

`PRESERVATION_RECEIPT.json` records exact local patch application and ten static preservation comparisons. These confirm that the legacy Add expression/body and subscriptions, original row builder, existing value/removal routes, existing Owner/scheduling helpers, existing modal validation/write routes, and unqualified schema/type entry guards remain unchanged. The original eligibility argument mapping matches except for the required account-bound template classification and canonical manifest source. Ten immutable source references are bound in `references/SOURCE_BINDING.json`.

These are **source and patch checks**. No compiler, executable control, Apple build, Native UI run, service operation, account or repository mutation was performed for this packet by the author. The earlier fourteen property-modal controls remain historical evidence for their exact older inputs; they are not rerun or transferred as runtime acceptance of this changed Scope or Add route. The root agent owns any subsequent syntax execution and publication.

Type, dataview, library, schema editing, type-restriction selection and native Torah property routes remain outside this increment. Its source review does not establish Stage B, full Host acceptance, native property creation, or cancellation behavior on Apple runtime.

## Focused validation still required

1. Parse the two final complete Swift postimages once, then typecheck them in the actual Apple target to validate macro/concurrency and generated protobuf API use.
2. Exercise the original Add panel on an eligible prepared object with a real current manifest and type. Verify exact original exclusions, hidden IDs, existing-property selection and new-definition Save through the existing native route.
3. Hold the actual canonical/type read and change source/account, parent type/details, parsed properties or permissions. Verify no stale hint/modal or write admission; also cover view cancellation, overlapping reattachment and repeated taps.
4. Verify template classification with unavailable/incorrect global type cache but actual template result, and with missing, duplicate, foreign-Space, wrong-layout, non-string, empty or NUL-containing type results. None may produce an eligible Add result from a missing negative proof.

These are narrow remaining checks for the new path, not a request to repeat unchanged full suites. A missing current canonical manifest or type intentionally leaves the prepared Add entry unavailable; this packet never provisions the schema to make its own eligibility succeed.
