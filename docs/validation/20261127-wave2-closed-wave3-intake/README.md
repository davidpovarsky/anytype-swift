# Closed first-shared Wave3 intake preparation

This executable preparation is bound to the first shared source
`6aab20344fcf1c645d7c96e0b9ec034ef07003a9`, native manifest `8ac407e7…`
and canonical Hanlin revision `38528941720d9b4f2da8dce7afbc788c2e554a0c`.
The actual App build failed before the complete UI build or XCTest execution.
**The supplied frozen profile remains closed. It cannot admit those products.**
The failure and its original logs are retained; the marker test compiler fix
is separately published in `ecd3eae7764129fa5f958a361b32c9c4826c76e6`.
Wave3 must freeze a new source, staging/cache evidence and actual successful
producer before a separately reviewed derivative can admit a retry. There is
no command-line source, SDK, test-source or product override in this package.

## Preserved API and proof boundaries

The materializer inserts the reviewed fragment before `main` in a new copy of
historical common controller SHA256
`4ec8617c59da3183a68a53ea9f840e57738469f36f9a0bc5b5a00e806d73cd9c`.
Its inverse restores every original byte, and every original function/class
declaration is retained unchanged. The old controller is also written as a
separate unchanged file. The new common module embeds its exact original
gate/adapter controls and needs no additional runtime Python sibling files.
The existing F consumer's thirteen-file closure therefore keeps its shape.

The public API remains:

```python
source_proof, built, app = shared.admit_and_clone_products(
    admission, private_execution_root, evidence_directory, commands
)
```

The source-proof meanings remain `commit`, `sourceStateSHA256`,
`runtimeIdentity.identity`, `producerRuntimeProofSHA256` and
`nativeRuntimeExecutedByThisCheck=false`. Qualifying native identity is not a
native execution result. The existing product clone body still checks full
source/helper closure, product contents/modes/links, complete UI copy, exact
descriptors, and APFS copy equality before returning products.

The additive guard reuses the exact `Tools/MiniApps/receipt_admission.py`
SHA256 `9ce1288feb8f3c534bb7eb784909624fc66168473e93eedff2f2945583d6a18d`
`verify_source` and `verify_build` boundaries. It binds the root's actual
approved admission, exact executed producer and sequential inverse to the
original producer. It supplements that gate with original App/UI process
receipts, full retained App15 preservation inventories, stage plan and cache
qualification, both original Native slices and their actual command/log
evidence, canonical SDK file verification, all before/after dependency
boundaries, and every real swiftc/FileList witness. It requires the frozen
43-native/9-UI source inventory; no declaration-only compilation credit is
accepted.

## Reproduce the closed preparation

Provide the exact historical common controller and an `original-inputs`
directory containing the six named files in `materialize_wave3_intake.INPUTS`.
Every file is checked against its literal SHA256 before it is read as code.
The files are the original receipt gate, Wave3 adapter and stager, reviewed
`9b1405ea…` producer, its `5e18f0a7…` inverse, and original `617b1639…`
producer. Existing Git copies or retained original control snapshots may be
used; mismatched bytes are rejected.

```text
python3 -B materialize_wave3_intake.py
  --historical-common /absolute/original/combined_heart_semantics_current.py
  --original-inputs /absolute/original-inputs
  --frozen-profile /absolute/package/frozen-profile.closed.json
  --frozen-profile-sha256 <sha256-of-that-exact-closed-file>
  --output /absolute/fresh-private-preparation-directory
```

The output receipt says
`PREPARED_EXACT6AAB_SHARED_INTAKE_NOT_PRODUCT_ADMISSION`. It records zero
builds, tests, simulator commands and cloned products. Importing or preparing
the module does not invoke its main runner. Every public qualification entry
rejects the supplied closed profile before reading products or issuing a
command.

Portable controls can be run with `PINKHA_WAVE3_HISTORICAL_COMMON` and
`PINKHA_WAVE3_PREPARATION_INPUTS` set to those same exact inputs. Five controls
cover early closure, source override and incomplete-ready rejection, changed
original/embedded validator rejection, failed-producer rejection, and
unchanged input/output custody. Their fixtures are synthetic. They are not
Swift, XCTest, UI, build or acceptance results.

## Observed failed attempt

The actual first-shared failure receipt SHA256 is
`fe20d23dd30d1faf852776b7cfe1b6ac68e4c95dd68c67072fbc14213743efc8`,
with status `FAIL`, error `app FAIL_BUILD` and exact source6aab. Original App
stdout SHA256 is
`ac9a61ff8e68e42ed3dd1828ebf71ce78128caa45d936757adf38aeefb76cf75`
(13,850,120 bytes). Root independently verified unchanged clean source
before/after SHA256
`7bb9ad1facb2563f49dcca8b8eab29a5a91897e4c8cecad4fd21bd40da6685dd`
with 4,518 inventory entries. No successful shared producer receipt exists
for this failed attempt. Do not replace these observations with a later
retry result or reuse the old absent-cache claim after the failed compile.
