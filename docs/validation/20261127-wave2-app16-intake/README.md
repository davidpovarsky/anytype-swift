# Wave 2: additive App16 editor and shared product admission

This control package admits the completed App16 producer for source
`a089ff29a5c0a7e415aac800844505f099a5561d`, native manifest
`8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b`.
It does not compile an application or claim application acceptance.

Coordination update on 2026-11-27: Wave 3 selected the next integration/build
source and requested that the waiting App16-a089 build not start (HQ51 comment
`1220940831283556`). The root reports the owned waiting process absent and zero
builds started. This package is retained as reviewed a089 preparation. The next
actual build is owned by Wave 3; no current runtime-ready claim is made.

The product source includes the saved focus correction `2fbc3e1a` and the
XCTest enumeration correction in `a089ff29`. The separately frozen focus
profile requires exactly 22 methods and 34 literal parameterized cases.
The original preparation and four editor UI methods remain selected by
`first-editor`, after the focused suite succeeds.

## Qualified controls

| Input or output | SHA-256 |
| --- | --- |
| Final compiler-qualified App16 builder | `9b1405ea44ba9cce3fca47a88127fc798fedab3d1b05f6e3728da3597d19929c` |
| Final builder inverse delta | `5e18f0a7cdb25cc30d010eb0c19819fe778cb338366763f06f76fef649189970` |
| Actual source staging receipt | `ed896be868e973f0bdd704612b641547f51b15509805d4d66b7461be88507d21` |
| Actual App15 source/product preservation | `11ab2f45511d8b7917709c1706475538b9ea4ed228e1dc908dfa55a331cacc74` |
| Cache correction receipt | `26b16e0bb4266f6f15bd445f70a4032f027c36ca6ec6c255b2e6f9608f7f7245` |
| Materialized shared collector | `4ec8617c59da3183a68a53ea9f840e57738469f36f9a0bc5b5a00e806d73cd9c` |
| Materialized host acceptance runner | `e8776c517b57fffbe5e941be0df64eade3b4fcc6c5411aceffa56adaec0c681b` |
| Focus 22/34 profile | `c495985b9afc278c13ec8900049f9835cee5fd74fc368e2e7b264ecf718c5812` |

The final producer's 90 nonoverlapping byte spans restore the original
`617b163951a9692909bef38a4991ded8c53e8c21ad9278a9564222fce1a57a68`
builder exactly. Its process lifecycle, source inventory, native identity and
dependency validation functions are unchanged. The compiler input comparison
now treats the actual APFS `AnyTypeTests` / `AnytypeTests` spelling equivalently
and requires each of both reviewed test paths exactly once.

The original staging record's `originalIntermediatesAndPackagePathsReused=true`
was subsequently disproved by the observed absence of compiler intermediates
and SourcePackages. That record is retained. Intake requires the separately
pinned correction, explicitly records the false reuse claim, and binds the
six-GiB app allowance, one-GiB UI allowance, two-GiB emergency floor and
512-MiB concurrent-growth allowance. It does not require those cache paths to
remain absent after a successful compilation recreates them.

## Materialization and shared API

Run `materialize_app16_control.py` with `--original-control`, `--source` and
`--output`. `--source` is the actual clean App16 source root. The original
control is the exact eight-file closure at:

`/Users/m1/development/anytype-root-active-20261125/app15-host-control-1dcd-a117-8ac-t5`

The output directory must be new. The materializer checks all original hashes,
retains the entire original shared file, and inserts `app16_intake.py` before
its original `main`. Every one of the 26 original function/class definitions
remains byte-identical; deleting that insertion reconstructs every original
byte. App15 admission continues to call its original function. The new intake
dispatches only for the exact App16 source.

The API remains:

```python
source_proof, built, app = shared.admit_and_clone_products(
    admission, root, evidence, commands
)
```

`root` must already be an unaliased directory with mode `0700`; `evidence`
must exist. `commands` is the unchanged `shared.Commands` instance. The call
creates `root/helpers`, retains source/native/SDK proof, and clones and verifies
all App and UI Products. `built["app"]` and `built["ui"]` each contain
`products`, `inventory`, `copies`, `descriptor` and `originalSelection`; `app`
points to the verified cloned `Anytype.app`. Page154 and NativeUI16 can reuse
this API and proof before their respective UI execution paths.

Admission retains the original fields: source commit/root, producer receipt and
logs, source-before/source-after inventories, complete product inventory,
original UI copy record, runtime identity records at all three boundaries, and
both product manifests and descriptors. Every file pin remains exactly
`{"path": ..., "sha256": ..., "bytes": ...}`.

The additional `app16Producer` object has exactly these keys:

- `builder`, `builderDelta`, `stagingScript`, `stagingInput`, `stagingReceipt`,
  `preservationReceipt`, `cacheQualification`, `compilerInputs`: file pins.
- `phaseReceipts`: `app` and `ui`, each containing `result` and `processExit`
  file pins from this actual producer invocation.
- `compilerFileLists`: map from each original compiler-list path recorded in
  `compilerInputs` to its preserved file pin.

Successful producer status must be
`PASS_COMBINED_MAIN_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE`. Both phases must
have successful original logs and exit records with positive process-group
absence, no cleanup errors and no forced termination. A historical App15 UI
continuation cannot satisfy App16 intake. Actual build receipts must be pinned
only after this builder succeeds; no receipt was fabricated by these controls.

## Remaining-lane selection and evidence

`focus-lifecycle-only` and `first-editor` keep their original execution and
result gates. The canonical source-a089 host runner retains the saved XCTest
parenthesis normalization fix. The only two new host deltas are an accurate
22/34 scope sentence and the fixed plan `t5-remaining-freshness-only`, selecting
only `t5-remaining-freshness`. It cannot replay the accepted nine or historical
36 native calls. `t5-native-ui-only` retains its preparation, two UI methods and
both R08 appearances.

Four portable admission controls passed in `app16-control-attempt1.log`:
exact original definition preservation and plan scope; rejection of changed
original controls and old profiles; eight cache-claim mutations; rejection of
incomplete or historical producers while preserving original App15 dispatch.
These are Python control checks with zero application builds, native calls,
simulators or XCTest invocations. The earlier focus profile's four portable
controls and its original failed fixture attempt remain in the neighboring
focus evidence directory. No prior failure evidence is deleted or relabeled.

Actual App16 compilation, the 22/34 UIKit execution, original editor
preparation, four UI methods, visual RTL coverage and physical-device coverage
remain pending the coordinated Mac run. The package does not promote its
portable checks to any of those acceptance results.

## Reusing the controls for Wave 3's selected build

The materializer and shared API are reusable after a separately reviewed,
explicit source/producer profile is pinned. An unknown later source must not
be substituted into this a089 package. Supply the full selected commit/tree,
actual clean before/after source inventories, reviewed final builder and
reversible delta, staging/preservation/cache receipts, successful original
App/UI logs and phase exits, compiler input evidence, native/SDK identity and
all product/descriptor inventories. Update the named fixed pins and fragment
hash in a new control commit, preserving the original byte-inverse and all
execution/result validators. Re-run the narrow portable controls and publish
the new materialization hash before any actual acceptance invocation.

Wave 3 also owns the T5 middleware-warning UI follow-up. The a089
`t5-native-ui-only` plan is retained for provenance and must not be executed as
acceptance of that newer UI correction. Bind the reviewed UI-only donor or
next complete producer through its explicit, preserved source/product proof.
