# Integrated migration components — 25 November 2026

The isolated integration branch has merged the prepared destination executor, native definition and semantic mappers, imported type presentation, captured Page composition, and the previously qualified V2 Apple native component producer. Full Space migration remains **not accepted**.

## Source and integration

Tested source: e8e8252db0412d793d235cadd5a5258633aa49b9.
Integrated V2 source: 20bee7319b07b955fa1632c0e807cbf93fa45658.
Branch: codex/chatgpt-wave15-migration-final-20261125.

Merged donor tips:
- Destination executor 2d02cd76f54d6ff99121664b4e51f6092467fcb7.
- Native definitions af45290ba78e60b8465096226e27e0364f116f3a.
- Semantic layout f1621492886a697d35d4cd91b19dcccacecedbfe and imported presentation 15c0dee736138639fc7d9182216a2e7f579071bb.
- Captured Page composition 0899aaccefc068836f6d5139de22f9fdd0181c28.
- Native Apple V2 composition and evidence ccbe86483b9548bc66961adffcb78fedcae9155f.

The Page merge resolves the earlier Basic=0 presentation qualification against the implemented v2 presentation contract. Other layout, default, derived-field and source-coverage refusals remain. No schema field or source row was removed to permit writes.

## Actual host integration

One current build executed 23 selected XCTest methods. Twenty-one passed, two were skipped because the definition tests use different explicit fixture environment names than the Page tests; no method failed. The two skipped original-capture methods then passed without rebuilding or changing product/test code. The exact same compiled test runner SHA was checked before and after that continuation. There are **23 distinct passed host methods**, not 25 methods and not native destination acceptance.

The original 144-object and 156-object source bundles were read through their immutable manifest and PB/JSON guards. The custom capture still reports its original 45492064232 source-method FAIL; this consumption does not rewrite it. Original source labels, values and blockers remain intact.

Two controller preflight errors occurred before any test invocation: a nonexistent package name in source census, and an obsolete assumed Swift test-binary layout. Both exact failures are preserved. The second was corrected using the observed Swift 6.4 product path. The skipped fixture tests were rerun alone.

The V2 merge leaves all four tested Host/Engine/Integration/Kit module trees byte-identical, as recorded in receipt.json. No repeat of these tests or native producer build was needed after that merge.

## Original Apple native evidence reused

The V2 source 3fb2ab3715173741cd4baabe01d588bade294891 already passed its actual iPad Simulator method at 2026-11-24T20:25:12Z with Any cf87c43ff0100c2dc43c3c105c82b1b070b3a7a3 and SDK e195f6c07a053c6588e39ffe72ee4fc44cf3d953. The original source includes collection-owner property support, five prepared definitions, one atomic six-record type part, two objects, two editor blocks, two deferred property updates, 4096-byte and 2MiB encrypted files, and two orderly SDK/store reopens. Original xcresult and custody records are retained by the donor under Docs/Validation/prepared-components-v2-apple-20261124.*. This is component acceptance in one XCTest OS process; it is not cold-process full Space migration.

The separate recovered 45501479246 peer proof is documented under ../20261125-native-peer-recovered. Its original controller FAIL is unchanged; original native online and cold Offline passes have independent custody verification.

## Remaining actual product gaps

The captured custom Space includes 126 property definitions, including 64 readonly or derived definitions, 20 types (16 non-Basic layouts), four options, two Pages, and native home/archive/workspace/widget objects. Seven bundled definition resolutions and two other native collections are explicit. One custom property has a non-null retained default. These current source facts are not discarded.

- AnyHeartNativeDefinitionPlan retains and refuses unqualified defaults, derived fields and non-Basic layout behavior.
- AnyHeartNativePageComposition refuses unaccounted source semantics and does not grant complete source admission.
- CaptureLoadedAccountSpaceWitness is a real Go API behind pinkha_loaded_account_witness, but no shipping gomobile/RPC capture bridge or concrete live source-authority adapter was found in the current Swift application.
- DestinationExecutor reconciles native intents and stable IDs. A complete source-to-destination content comparison for every source row, history/settings/permissions and files has not run.
- The two apps still need the unified native-runtime composition owned by the D integration lane.

C stays open. No destination write authority, full migration, physical-device acceptance or TestFlight result is claimed here.
