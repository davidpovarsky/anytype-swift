# Remaining Torah UI: exact startup prerequisite and shared-product selection

This tranche changes test startup only. It is **source preparation**, not an Apple
runtime result. The product/native preparation, T5 UI file, retained T5 account,
three writing types, original UI assertions and Set postflight remain unchanged.
No Mac build, simulator launch or XCTest execution was performed for this tranche.

## Why the startup correction is required

The original Inspector, embedded search, quote and Properties helpers waited for
Home/More without handling the actual unstable-middleware warning that blocked
the retained App15 T5 UI methods before Home. Wave3's original T5 correction at
`a82fa890a0114990e474b48830e4a2de3e32c79d` supplies the observed shape:

- One alert whose exact label is `Warning`.
- Exact text: `You launch app with a unstable middleware. Don't use your production vault. Your vault may be broken.`
- Exactly two actions: `Continue with current vault` and `Logout from current vault`.

The new shared **test-only** helper accepts only that exact shape, only after a
controller-bound disposable fixture check, and taps only the existing Continue
action. It retains the screenshot/accessibility hierarchy and binding hashes,
uses the original 120-second monotonic deadline, and requires no alert to remain.
Unknown/duplicate/changed alerts are left untouched and fail with original visual
evidence. No production warning, authentication or account API is modified.

The helper is embedded in the already-compiled
`PinkhaStage1Acceptance/Tests/PinkhaStage1AcceptanceUITests.swift`; this avoids a
new shared PBX project mutation. Four startup call sites change across three
existing files. The separate original editor helper and all T5 files are intact.
`verify_inverse.py` reverses only those call sites, the helper and CryptoKit
import, restoring all three exact donor files at
`2a95ad12d6e58c4895583a871f9a07f8902ce34e` byte for byte.

## Provenance: controller observation, not a new native echo

The three legacy fixture files contain actual Space/object IDs, but no native
token/source/run echo. The native fixture bytes and preparation sources are
unchanged. `torah_ui_profile.startup_environment` therefore requires the shared
consumer's original successful preparation result and invocation, exact admitted
source input, new owned-simulator receipt, installed original executable-code
hash, raw private fixture bytes and original UI environment. It binds their
hashes to source/run/attempt/lane/UDID and a unique controller token. The Swift
helper independently checks those bindings and raw fixture bytes before Continue.

For canonical Properties, the three writing document IDs are in the **actual
preparation console marker**, not the raw Stage1 editor fixture. The controller
must retain that console without rewriting it, feed it to the unchanged original
`property_environment`, and pass the same raw log to the binding factory. The
factory requires one unique marker and exact agreement for all native environment
fields; the console SHA is in the envelope and warning evidence. `fixtureSHA256`
alone is never described as proof of those three writing IDs.

## Original UI selection: 13 methods in six isolated lanes

The exact selectors, native preparation identifiers, files and pending hosted /
package selections are in `selector-inventory.json` and `torah_ui_profile.LANES`.
`inspect_original_lanes` compares all six definitions to the unchanged original
`run_wave15_acceptance.LANES`. Each lane requires a **fresh independent fixture**;
in particular native Properties and Properties Set cannot share mutated blank
universal documents. The original non-editor UI assertions prove **English UI**
only. Their admissions must request English; Hebrew search text is not Hebrew
interface acceptance.

| Lane | UI methods | Native preparation | Additional required contract |
| --- | ---: | --- | --- |
| inspector | 5 | `SimulatorAcceptancePreparationTests/prepareRealUIFixture` | Prelaunch mapped App PID, entry/final AX PID and process continuity |
| inspector-search | 1 | Same original preparation in its own fixture | Same mapped PID/continuity; provider open/back/link assertions |
| quote-drop | 1 | Same original preparation in its own fixture | Real editable anchor, quote/citation, two Undo/two Redo, two drags, relaunch |
| properties | 3 | `TorahNativeDerivedProductIntegrationTests/originalProductPipeline` | Three original writing types, 0/1/2/12 source headers, Page/Note/custom |
| properties-set | 2 | Same native pipeline in its own untouched fixture | Mandatory original same-account type-preservation native postflight |
| canonical-properties | 1 | `PinkhaStage1AcceptancePreparationTests/prepareRealApplicationState` with Properties flag | Original console parser and three writing IDs; link/unlink and relaunch |

The shared App + complete Stage1 UI build can serve these lanes with
`test-without-building`. The existing common qualifier remains the sole authority
for actual source/Native/SDK/App/UI products and compiler inputs. **No new source
may be admitted by substituting the old a089/App16 pins.** Admission and original
method enumeration/result/timeout validators must remain intact. This tranche
does not yet add runnable lane dispatch to the old e877 F consumer; that wiring
follows separately after review and the real Wave3 producer receipt.

### Required consumer wiring

1. Use `admit_and_clone_products(admission, root, evidence, commands)` unchanged,
   then `reviewed_ui_sources` before and after the selected UI phase.
2. Keep the existing `Consumer.execute_lane` ownership, preservation, shutdown,
   product-integrity and failure retention wrapper. Do not call `wave` outside it.
3. Retain original successful preparation result/invocation and private raw fixture
   on the newly owned simulator. For Inspector **both** lanes, prelaunch the exact
   installed App, verify loaded runtime/code and process start identity, and bind
   that PID. Preserve the original entry/final hierarchy continuity validator.
4. For canonical Properties, retain the actual preparation console under an
   original parser-compatible `command-*.log` name, preserving exact bytes/hash,
   call original `property_environment`, then supply the same console to the new
   binding factory. Never infer canonical IDs from the Stage1 fixture.
5. Run the unchanged selected methods through original compiled enumeration and
   xcresult validation. Preserve every source log, xcresult, attachment and raw
   native receipt. Screenshots still require actual visual review.
6. Preserve the full original Properties Set freeze/install/pre-AccountSelect
   identity proof and `TorahStage2TypePreservationTests/verifyExistingTypeRoundtrip`.
   UI2 PASS alone is incomplete; `UseDestinationArtifacts` is not a Simulator fix.

## Hosted Properties and separate Related package tests

The published Properties source at `2a95ad12` adds **15 parameterless methods**:
9 `PropertyCreationSearchTests` and 6 `PropertyCreationSelectionTests`. They belong
to **AnytypeTests**, and can use the same admitted App's hosted test product after
the exact two files are witnessed in its actual AnytypeTests compiler proof.
Select their 15 exact `Suite/method()` identifiers, use original compiled
enumeration/result checks and demand 15 actual passes with no skipped/extra case.
No additional account preparation or historical T5 native call is part of that
selection. These 15 methods remain **NOT_RUN**.

`AnyNativeTorahRelatedIdentityTests` has **5 methods / 7 literal cases** in the
**PinkhaAnyUITests Swift package target**. Two methods each have the two Boolean
arguments. This suite is not AnytypeTests or Stage1 UI; merely admitting the App
does not prove those package tests compiled or executed. It needs a separately
qualified package test product/dependency closure, coordinated with Wave3. It
remains **NOT_RUN**. Native T5 historical 36 and new 9 accepted calls are not
selected or repeated by these controls.

## Retained earlier outcomes

- Inspector original five-method run `44268689146`, source
  `70a505d68ca839b44c5215e809b1f059d64f4068`: preparation1/UI5 PASS, English light
  portrait iPad13 M5/iOS27.0. This scoped historical acceptance stays valid. Later
  batch runs `44304788730` and `44389628194` stopped before native/UI at simulator
  inventory timeouts; they are not new functional Inspector failures. Current
  source changes require an explicit affected-path reason for any replay.
- Embedded search task `1219878918433851`: original run `44389628194` is
  **NOT_RUN_SETUP**, because the earlier Inspector lane stopped before setup.
  Standalone Inspector five-method PASS did not execute this sixth method.
- Quote original qualification `44594932364` / `40789dc…`: native preparation1
  PASS; UI1 FAIL at partial typed anchor before any quote/Undo/Redo/drop phase.
  Original artifact14569948710 SHA
  `8a0f8a0cee3c67d84c4590308998ee54d1dc89aee993500365a180a79931cb85` and report SHA
  `6db35dba21c32eedd11873679d6aab0a2c32e24b4e6048c5ff92b972ea28119f` are preserved.
  The later `44948101231` running note has not been qualified by this audit; this
  file does not claim the earlier failure is the latest global terminal outcome.
- Properties Set `44562643472`/`44584920580`: preparation1/UI2 PASS but native
  postflight failed at unproved container relocation. `44609431815` / `cb0d813…`:
  preparation1/UI2 PASS, postflight NOT_RUN exit70 because the proposed destination
  artifact mode was device-only. The current pre-open proof controller is source
  ready; these original failures are not converted to native preservation PASS.

Sources: original source files in this repository; Asana T3 `1219604675985547`,
T4 `1219604770637161`, Inspector search `1219878918433851`, Properties
`1220541253593988`, and HQ51 `1220541349302681` (ownership comment
`1220941112701220`). No task completion or release acceptance is claimed.

## Validation scope

Independent editor and root reviews found no source-level blocker. Seven portable
synthetic Python control methods pass, including negative bindings and canonical
console mismatch. The exact-source inverse proof passes for all three UI files.
Any Swift parser result is syntax only: no Apple typecheck, XCTest, native call,
simulator appearance, accessibility or physical-device acceptance is inferred.
Actual Apple compiler/runtime/visual results remain pending the single shared
Wave3 product and coordinated execution.
