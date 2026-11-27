# Closed App product delta profile — 10 methods / 18 cases

This is a **profile-only source tranche** for the new G05, G07 and Bin regression methods. Its runtime gate always refuses. It adds no producer, process manager, simulator command, native account, runtime output path, workflow, or application source change.

The original Core22 controller and all its existing selectors, source files, execution functions, validators and lifecycle code remain unchanged. The complete published source/test handoff is App commit `2519140dd1966cedc4403b74f0f00479e9bd289f`, under `docs/validation/20261127-wave2-product-admission-delta`.

## Fixed scope and source custody

| Lane | Exact source suite | Original target | Hosted target | Methods / cases |
| --- | --- | --- | --- | ---: |
| `product-g05-readonly-hosted` | `PropertyPickerReadOnlyLookupTests` | AnytypeTests | AnytypeTests | 3 / 7 |
| `product-g05-revision-hosted` | `PropertyPickerNativeLookupRevisionTests` | AnytypeTests | AnytypeTests | 3 / 6 |
| `product-g07-drop-authority-hosted` | Two new methods in `TorahAssociationNativeRepositoryTests` | AnytypeTests | AnytypeTests | 2 / 2 |
| `product-bin-read-publication-hosted` | `AnyLibraryBinPublicationTests` | PinkhaAnyUITests | AnytypeTests | 2 / 3 |

`profile.json` contains the literal method/argument inventories and exact full-file hashes. The three existing compiled input paths are unchanged; their content hashes must be updated in the next actual complete producer inventory. This profile does not invent a new PBX source or accept a partial build.

`source-inverse.json` restores the complete published originals using finite byte offsets and pinned preimages:

- G05 `6ef0ad1e…` reverses first to the exact `6f17a932…` initial read-only tranche, then to original `1bdd1c49…`.
- Bin `b242b8bd…` reverses to the exact original `e46dc675…` input, preserving its two search methods.
- G07 `4a2463e6…` reverses to the original 68,698-byte `6132f482…` input. Its exact 4,608-byte append is `402e3dcd…`.

The unchanged original parser reads the full 15/35/4 declaration inventories. Suite membership and selected names are fixed by the pinned whole source. G07 requires a declaration-only memory view because its two new `@MainActor` lines occur between `@Test` and `func`. Only byte offsets 68,852 and 70,879 are removed from that exact append; the inverse reconstructs every original byte. The resulting parser view is `8becc019…`. No Swift source file is written or compiled from that view. Compiler witnesses always bind the complete original `4a2463e6…` bytes.

## API for Wave3's separately reviewed adapter

The profile exposes the requested finite names, with an explicit equivalent context API:

```python
HOSTED_LANES
fixed_contract(lane)
declared_contract(originals, lane)
selection_plan(originals, lane)
source_contract(
    originals, lane,
    source_commit=actual_admitted_source_commit,
    native_compilation_proof=actual_admitted_producer_native_proof,
)
validators(
    originals, lane,
    source_commit=actual_admitted_source_commit,
    native_compilation_proof=actual_admitted_producer_native_proof,
)
invocation_selectors(expected_identifiers, qualified_profile)
require_runtime_ready(...)  # Always raises in this source-only checkpoint.
```

`originals` must be the actual unchanged Core22 `Originals` class, loader SHA `aabcf1eec2643f331ed3ab3ae095e156c03de29c4a75ea32405819495af2c9cc`, with its original 15-file manifest SHA `81d178d6d829dc2eff201b8b8dcd190db2da79dc68a6cc06f36ca0d8a90d2778`. Its installed module identities and retained physical source bytes are rechecked. This is not an interface for arbitrary parser callbacks or source-path overrides.

`fixed_contract` and `declared_contract` expose **expected source-derived identifiers**, named `expected_compiled_identifiers`. They set actual compiler proof and actual enumeration to `None`, and claim zero executed tests. `selection_plan` likewise labels its output as a proposal and sets `execution_authorized=False`.

The future adapter supplies the native compiler proof from its already-admitted actual shared producer. `source_contract` calls the exact original `60fbe955…` witness and current `f16a1607…` RTL witness body. That proves selected original sources were direct `AnytypeTests` compiler inputs, using actual Git, retained FileLists and compiler invocation witnesses. It does not admit the App, Native, SDK, complete Products, job or runtime; those remain Wave3's original common admission responsibilities.

`validators(...)` returns one `CompilerQualifiedProfile` instance for a fixed lane. The adapter must keep that **same instance** through:

1. `invocation_selectors(expected_identifiers, qualified_profile)`;
2. `qualified_profile.validate_enumeration(actual_enumeration_payload)`;
3. `qualified_profile.validate_results(actual_summary, actual_test_tree, actual_udid)`.

The original enumeration parser must return exactly the expected methods in `AnytypeTests`, without missing, extra, repeated or requested-disabled methods. Result validation refuses before the same instance has observed actual enumeration. Original host-result and parameter-node validators remain unchanged. Source/compiler proof is rechecked before and after qualification.

The three new suites use exact suite selection. **G07 uses only its two named parameterless methods.** A zero or different compiled enumeration must stop; there is no legacy whole-suite fallback. Summary totals may use only the original method-count or case-count representation for the selected lane, while actual distinct passed argument nodes must prove every literal case.

## Runtime ownership stays with Wave3

Wave3 owns the separately reviewed adapter and fixed additional output namespace:

`RUNNER_TEMP/pinkha-hosted-property-cache-bin-RUN-ATTEMPT`

This module contains no path admission or output-writing code. The original Core22 output and receipts must remain intact. Wave3's specialization must retain the original descriptor/stage functions, owned process barrier, 180-second enumeration, 300-second method allowance, 600-second hosted-lane allowance, 120-second result reads, 180-second attachment export, 2 GiB live floor, and all same-job source/Native/SDK/Products/modes/links/installed-code checks. It must use a distinct App10/18 receipt identity and the explicit original-target mapping above.

The profile's unconditional runtime refusal cannot be opened by `runtimeReady: true`, an environment variable or a supplied receipt. A future reviewed integration remains a separate source artifact. No current producer or runtime entry point was edited here.

## Three affected old G05 methods remain separate

These existing methods changed and still require their own explicit source-compatible acceptance route:

- `PropertyCreationSearchTests/providerCancellationPropagatesThroughLoaderAndPicker()`
- `PropertyCreationSearchTests/catalogCancellationStopsAtTheSearchBoundary()`
- `PropertyCreationSearchTests/preCancelledCatalogDoesNotSearch()`

They receive **zero new-method credit**. The original Properties-hosted15 profile pins `1bdd1c49…` and assumes nine declarations in the whole search file. The current file `6ef0ad1e…` contains those nine plus six new methods. Its old route therefore needs an explicit whole-source/inverse compatibility successor that preserves its selected old scope; this new profile cannot silently repin it. The analogous old Library2 `e46dc675…` versus `b242b8bd…` source boundary is also preserved.

Original focus22/34, Core22/26, the separate Kit6/9 target and R08's zero-new-method Stage1 source update remain outside this new 10/18 scope.

## Verification retained

Five finite portable control methods passed in **0.257 seconds**, using the actual unchanged original Python loader/parser/result functions and exact published Swift bytes as read-only fixtures. They check full-file/inverse retention, old-prefix tampering despite unchanged new methods, inverse/validator tampering, unknown or unqualified scope refusal, and parameterized case loss/duplication/extra-old-method/summary-count failure. The fake result tree is explicitly marked synthetic; it is not an Apple or native result.

An audit hook prohibited every child process and observed none. There were no Swift, Apple, Native, simulator, remote host or compiler calls. The original control inputs were rehashed after the checks. `controls-attempt1` retains the original log and receipt; no historical accepted test was replayed.

The retained `portable_controls.py` records the exact executed workspace harness. `fixture-custody.json` identifies its complete original control and Swift inputs by immutable repository paths, commits, lengths and hashes; local locator paths describe that original run only. It is evidence for reproduction with those exact inputs, not a runtime entry point for an arbitrary checkout.

Actual combined source, successful shared producer, native compiler proof, compiled enumeration and runtime admission remain **unqualified / not executed** in this source checkpoint. No UI, drag/rollback, native persistence, ACL, VoiceOver, device, Release or distribution acceptance is claimed.
