# G05: read-only Add Property lookup and pre-add policy

This isolated source correction removes optional Torah provisioning from the Add Property picker's typing, lookup Retry and pre-add identity check. The picker reads the existing synced manifest and native descriptors. The explicit user-selected add still uses the original Anytype object, Type or dataview mutation.

The exact review base is `6581508faffa748ca51d97e6ea51ecf6400fef35`. The five Swift candidates are bound in `candidate-manifest.json`; all earlier source and acceptance evidence remains separate. There has been no Swift compilation, XCTest, Native call, Apple build, simulator execution, visual acceptance or physical-device test for this tranche.

## Source finding and scope

The prior production loader awaited `awaitInternalIdentity`, then `canAddPropertyAsync`, and then the native catalogue lookup. Those paths could call the existing `bootstrapSpace` implementation when the optional native schema was missing or a descriptor lookup failed. That implementation can provision properties, repair Type defaults and refresh Type relations. The old loader could also suppress every ordinary existing row after identity resolution failed, even when the ordinary search itself completed. Its existing VM regression supplied a finished loader result and did not exercise this production path.

This is a source-demonstrated call-path defect, not a reproduction of the historical physical-iPad report. The two historical Properties-set UI passes and their failed or unrun native postflight remain retained. No physical-device fix or persistent-data result is inferred here.

## Changed behavior

`PinkhaTorahPropertyPolicy.loadPickerManifest` accepts an already verified same-Space cached manifest or calls the existing read-only `PinkhaSpaceManifestStore.loadManifest` route. The latter performs manifest discovery and `ObjectShow`; it does not bootstrap or save a manifest. The picker validates the requested Space, current manifest schema, completed state and both canonical/order ID-and-key pairs before exposing existing choices.

`PinkhaPropertyPickerSearchLoader` uses that verified manifest for the original broad document/Type predicates. It reads existing native descriptors through a catalogue wrapper that explicitly disables provisioning. Missing or failed native descriptors keep the dedicated Torah lookup error and Retry. When internal identities are verified, ordinary existing properties remain available and selectable, including a user property with the same Hebrew display name as an internal field. Canonical/order rows are excluded by positive identity, and foreign-Space, deleted or empty-ID search rows are rejected.

If the manifest cannot establish the internal identities, the picker reports the existing explicit lookup error and keeps unresolved rows closed. It does not invent safe custom IDs or classify internal fields by display name or format. Original format creation remains available. A later Retry performs the same read-only lookup.

The ViewModel changes one call site: the existing pre-add guard now uses the throwing read-only `canAddPropertyFromPicker` method. Otherwise a row that survived native-only lookup failure could still enter optional provisioning at selection time. All actual mutation methods, object-versus-Type semantics, hidden-property reveal, callback/dismiss publication, failure Retry and cancellation behavior remain unchanged.

The original public and non-picker catalogue APIs keep their bootstrap behavior. The production catalogue gains an injected bootstrap closure solely so the meaningful component regression can observe accidental provisioning without contacting a Native service. Its default remains the original bootstrap call. The picker uses the explicitly false provisioning path. The existing `IdentityStore`, its invalidation behavior, all initialization/bootstrap entry points, the three original writing document Types, Native engine/protocol/schema and persisted storage are unchanged.

## Exact regression inventory

The existing `PropertyCreationSearchTests.swift` remains an exact 10,826-byte prefix, SHA256 `1bdd1c498a685902f7c8e8a0980b4e09b90d2e34ee74f13316e8ec1a2532c3e4`. All nine original method bodies are unchanged. The six `PropertyCreationSelectionTests` methods are also unchanged.

The additive `PropertyPickerReadOnlyLookupTests` suite contains **three methods and seven cases**:

| Swift method | Cases | What its actual production path checks |
| --- | ---: | --- |
| `ordinaryChoicesSurviveNativeFailureWithoutProvisioning(nativeSearchFails:)` | 2: false, true | Missing descriptors and failed native search; empty/Hebrew/English queries plus Retry; ordinary choice retained; canonical/order and foreign rows absent; read-only selection allows the ordinary field and refuses both internal fields; zero policy and catalogue bootstrap calls. |
| `unresolvedIdentityKeepsInternalFieldsClosed(mode:)` | 4: unavailable, wrong-space, missing-canonical, missing-order | Explicit identity failure and no guessed ordinary safety; no native descriptor search or provisioning; actual read-only selection guard refuses or reports the provider error. |
| `readOnlyManifestCancellationPropagates()` | 1 | Provider cancellation propagates through the real loader before ordinary search or native lookup, with no completed empty/error result. |

These tests instantiate the production loader, catalogue and policy with the original service-boundary seams. They do not inject a finished VM result. All seven cases are **written, NOT_RUN**.

The smallest affected original methods to execute with the new source are:

- `AnytypeTests/PropertyCreationSearchTests/providerCancellationPropagatesThroughLoaderAndPicker()`;
- `AnytypeTests/PropertyCreationSearchTests/catalogCancellationStopsAtTheSearchBoundary()`;
- `AnytypeTests/PropertyCreationSearchTests/preCancelledCatalogDoesNotSearch()`.

The new full selectors belong to `AnytypeTests/PropertyPickerReadOnlyLookupTests/` with the three signatures above. Actual compiled enumeration must supply their device/runtime identifiers before dispatch. The existing Properties-hosted profile selects the original nine-plus-six methods; it must not silently claim the new suite. A future exact source-bound hosted successor must qualify the new file and the actual compiler input before selecting the three methods/seven cases. Current Core22, earlier products and historical results do not include this new suite merely because its filename already belongs to the target.

## Preservation evidence

`source-inverse.json` records an actual local Git reverse-apply of the five-file patch and byte-for-byte reconstruction of every original. This is a source check, not a runtime test.

The original source-retention map has 129 rows. The candidate updates only required picker shared/replacement blobs plus an appended validation note in rows121–124 and adds one new policy row, for130 rows. Every other row remains unchanged. The policy file exists in the protected baseline with blob `8a5abc0a225ab9ca2d3db9fe9670b5f35753886e`; the newly added test and loader do not exist in that baseline. The existing shared helpers and unchanged original manifest/eligibility sources remain pinned.

The upstream exception register receives an append-only entry for the single existing VM call-site redirect. It explains why the downstream helper still needs this narrow hook and preserves all old entries. The change does not alter the original Anytype picker View, styling or action layout.

Independent source reviews and the actual prospective source-retention output are retained alongside the exact inputs. They do not establish Apple typechecking, macro compilation or UI behavior. No optional broad test replay is required to preserve earlier valid evidence.

## Separate bounded follow-up

The existing native descriptor cache has a distinct source-demonstrated race: `set` and `setDiagnostics` are not conditioned on the cache/Space revision, while `invalidate(spaceId:)` only advances the revision used by Type relation writes. An older native lookup can complete after Retry and replace a newer descriptor/diagnostic observation. The loader also samples shared `lastLookupDiagnostics` after awaiting descriptor values.

That race is **not fixed by this tranche**. Its separately scoped successor should capture the existing cache/Space revision, atomically admit a result only under the same revision, and return per-call diagnostics to the picker. A controlled old-read → invalidate → fresh-read → late-old regression must prove the outcome. It should preserve the legacy APIs and initialization/provisioning behavior. No broad `IdentityStore` rewrite or untested freshness claim is included here.

## Remaining acceptance

The source correction still requires Apple compilation, the exact new3/7 and affected original methods, the original Properties UI/native workflow on one valid owned fixture, actual error/Retry UI evidence, and physical-iPad confirmation when a device is available. Correlated runtime stage/reason evidence for the original physical report remains unproven. No new App build or runtime gate is opened by publishing this source.
