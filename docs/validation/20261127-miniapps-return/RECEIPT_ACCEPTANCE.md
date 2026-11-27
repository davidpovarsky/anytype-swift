# MiniApps acceptance on the new shared product

## State and ownership

This is an additive consumer of a new, original shared App16 build receipt. It
does not change the fixed-source guards in the historical App14, App15 or
MiniApps-only controllers. Product source and controller source are independent
identities. The integration owner supplies the exact product commit and build
receipt; the controller is installed from its own exact committed Tools tree.

The compiled isolation source was delivered in `8dac7be22a875fa1904ff4729c919562ce259181`
and `910ffea8b8328600f357895a6e91d501fc72fee2`, above the callback retention fix
`68b6ba362dc8f531a318e91c1fe0cf34d5da7695`. This control/audit milestone does not
edit either compiled test file, application code, project membership or pins.

No new Mac application acceptance has run in this lane. Root owns the one shared
build and all build/test resource scheduling. A retained Debug build or a passed
Python control is not Release, device or TestFlight acceptance.

## Actual evidence admission

The concrete input uses schema `pinkha.miniapps.receipt-input/1`. Its SHA256 is
supplied explicitly to the runner. All paths refer to existing original bytes;
missing evidence is an error.

| Input | Required relationship |
| --- | --- |
| Product commit/tree | Source-before and source-after are byte identical; the actual source checkout has the same HEAD, tree and clean status. Every observed code file is unchanged. |
| SDK and companion pins | Original `Tools/Hanlin/source.json` and `Tools/MiniApps/producer.json` must equal exact Git blobs at the product commit. They are separate identities. |
| Build receipt | Only `PASS_COMBINED_MAIN_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE`, exact product commit, zero test executions and successful original app/UI command logs are accepted. |
| Executed build producer | The expanded producer file must equal `controllerSHA256`; the orchestration wrapper cannot substitute for it. |
| Root build admission | The actual producer must bind its root source admission, original preservation receipt and reviewed `204f8fbb25c3b21f419fc1a8818eb46ed492e561` base. Source, staging, cache, native, SDK and generator pins must agree. |
| Native assembly | The original assembly receipt must have `PASS_ASSEMBLED_TWO_QUALIFIED_SLICES_NOT_APP_ACCEPTANCE`; its source manifest and runtime identity agree with the build. |
| Build inputs | Every original `inputs` key ending in `SHA256` has an exact file reference, including native binary, native manifest, package lock, SDK materialization, staging and cache qualification. |
| Complete products | Original app-derived and ui-derived file/symlink inventories must match every actual product byte. Missing, extra, duplicate and escaping entries are rejected. |
| Compiled test sources | Original UI copy receipt, generator, unchanged generated project/scheme inventory and both native/UI compiler-input proofs are mandatory. |
| Actual compiler use | Each retained SwiftFileList binds the original swiftc command line, 1-based line number and line SHA256, module name and original list path. `WriteAuxiliaryFile` alone does not qualify. Each selected source appears once in every qualified list and has the same actual file identity and bytes. |
| Controller commit | A manifest made from exact Git blobs covers every Python helper under Tools, including transitive imports. Extra or modified helpers are refused. |
| Dependency evidence | Separate exact references for Hanlin, Heart, Any and TorahInspectorKit are required. These do not silently transfer qualifications between different source graphs. |
| Apple toolchain/runtime | Original Xcode version, Swift version and simulator SDK build observations are rechecked. The owned simulator's arm64 OS version/build and iPad/iPhone family must match the actual xcresult. |

The original producer's source snapshot intentionally filters extensions. JSON
pin files and non-Swift files copied into the UI project are therefore bound to
the same exact Git commit, not falsely expected in that filtered snapshot.
Case variation in an APFS compiler path is accepted only for the same actual
file with matching bytes. A different file with identical contents is refused.

## Preparing a concrete input

Use the Mac's verified Python 3.12 interpreter and the same admitted Xcode
environment. The current machine's generic `python3` is not assumed to provide
`hashlib.file_digest`. These helpers do not change global Xcode selection.

1. Materialize the complete committed Tools tree for the chosen controller
   commit into a separate control directory. Do not install new controls into
   the frozen product checkout.
2. Run `prepare_receipt_input.py controls --repository REPOSITORY --commit
   EXACT_CONTROL_COMMIT --output NEW_ABSOLUTE_MANIFEST`. This reads Git blobs;
   it does not check out or reset any tree.
3. Run `prepare_receipt_input.py input` with the original source/control roots,
   control manifest, build receipt, expanded producer, assembly, UI generator,
   compiler logs and the three original toolchain logs. Use repeated
   `--build-input NAME=/absolute/original/file` for every SHA256 input and
   repeated `--dependency Hanlin=/absolute/original/evidence` (and Heart, Any,
   TorahInspectorKit) for exact original evidence. Supply the observed runtime
   identifier/version/build/device type/family and native App Group.
4. The helper discovers exactly one original native and UI descriptor, binds
   actual bundle identity and `anytype` return scheme, writes the candidate
   contract, then performs admission. A failed candidate is preserved.
5. Review the concrete contract and its SHA256. Use
   `run_receipt_acceptance.py --contract ORIGINAL_CONTRACT --contract-sha256
   EXACT_SHA256 --output NEW_ABSOLUTE_OWNED_DIRECTORY --admit-only` for a
   read-only admission checkpoint. Remove only `--admit-only` to execute when
   root has allocated the test slot.

The input helper's `--help` lists all exact arguments. The native and UI
compiler-proof references come directly from the build receipt; callers cannot
replace them with another retained test product.

## Actual execution and selectors

The runner clones the complete admitted app/UI products using APFS copies,
verifies their inventories, validates signature/entitlements/runtime ownership,
and admits the original companion using the unchanged `local_producer.admit`.
It creates only its own simulator and leaves it retained, including on failure.
All commands, raw logs, xcresults, enumeration, summaries, attachments and actual
test counts are retained under its own output directory.

| Order | Target | Exact method |
| --- | --- | --- |
| 1 | AnytypeTests | PinkhaMiniAppsNativePreparationTests/prepareMiniAppsDocument() |
| 2 | PinkhaStage1AcceptanceUITests | MiniAppsNativeAcceptanceUITests/testNativeEditorPickerTextStudioReturnAndColdReopen |
| 3 | PinkhaStage1AcceptanceUITests | MiniAppsNativeAcceptanceUITests/testDuplicateCallbackDoesNotInsertAgain |
| 4 | AnytypeTests | PinkhaMiniAppsNativePreparationTests/verifyReturnedNativeDocument() |
| 5 | AnytypeTests | PinkhaMiniAppsNativePreparationTests/applySelectedTextAndPreserveNewerNativeContent() |
| 6 | PinkhaStage1AcceptanceUITests | MiniAppsNativeAcceptanceUITests/testNativeFilesRoundTripColdReopenCancelAndReplay |
| 7 | PinkhaStage1AcceptanceUITests | MiniAppsNativeAcceptanceUITests/testPendingReturnsRespectEngineAndAccountAcrossColdReopen |
| 8 | AnytypeTests | PinkhaMiniAppsNativePreparationTests/verifyEngineAccountIsolationNativeHeartReadback() |

Every command must enumerate exactly its selected original method and produce
one actual passing case, zero failures and zero skips. Native Swift Testing
selectors retain their required `()`. The original five and FileWorkshop
assertions remain unchanged. The native adapter method uses its own newly
created Page; it does not change the original Heart fixture. FileWorkshop adds
two file blocks while preserving the original/warm/cold text, which the
isolation readback checks alongside the new Heart text.

The new isolation UI creates two native Any accounts through normal UI in the
disposable simulator. It verifies Heart return after switching to Any, then
delivers account A's actual pending return while account B is selected. The
result must remain unacknowledged before and after a cold reopen in B. Both raw
original false-ACK records and their SHA256 are retained. After selecting A,
the result must apply once and retain the same block IDs through callback
replay and another cold reopen. Two genuine FileWorkshop read/cancel probes
confirm B's account/Space/document text, blocks and native version are unchanged.
Final native Heart readback and both engines' actual journals bind these UI
observations to the original native writes.

The script never seeds an Any native database, synthesizes these four isolation
requests/results, or marks them acknowledged. The original adapter test remains
separately identified as a native adapter check with zero companion round trips.
Native mutation/journal/bridge ACK are explicitly not claimed to be atomic.

The success label `PASS_EIGHT_ORIGINAL_MINIAPPS_METHODS` is emitted only after all
eight actual method results, original bridge/native receipts and unchanged
source/product checks pass. Failed commands still report actual counts from any
retained xcresult summary. A missing original summary is reported separately
instead of being presented as zero executed tests.

## Original companion and explicit handler qualification

At preparation, the existing product pin is producer
`86a6dde354947be9329fe1e8f4d45a433fe488c4`, manifest
`a46fa7e5196e2a66ad7c0126302b390d400cbc6dca84e96d697fa9bf3cb10b25`.
The runner reads the pin from the exact admitted product source, not this prose.

The SDK owner reports that full-graph producer 9565 predates the explicit-handler
fix; a86 adds the fix without changing the four 9565 package graphs but its first
stage failed before compilation; c34 has an actual handler test pass but a
different incomplete consumer graph. No one of those facts qualifies a
different companion automatically. Root and the SDK owner must provide a
compatible, actually built companion and source pin before claiming the combined
explicit-handler acceptance. This control milestone changes no producer pin.

## Controls and original evidence

- `receipt-controls-attempt1`: 29 fixture-only controls passed against the initial
  schema model. It is retained unchanged.
- `receipt-controls-attempt2`: 34 controls passed after reviewing the actual
  producer: original Git omitted-file binding, root admission and APFS same-file
  checks were added. One control reads real disposable Git blobs; none compiles
  or runs an Apple application. Receipt SHA256:
  `d85182c55575c693183a78aa2d6c690ac37dcc96ae499dd79736b8946d116fcf`.
- Source syntax parse passed. These controls do not qualify the application
  or the not-yet-produced shared build.
- The 8 original queue helper tests remain under `queue-attempt1` with their
  original Swift Testing XML and log.

## Retained Otzaria 5,000 evidence audit

The original archives were opened read-only at these exact locations. Whole-file
hashes were checked before and after, original member manifests/logs/reports were
read, and no archive or native account database was extracted, copied or changed.

| Archive under /mnt/development/projects/evidence/otzaria-shared-agent1-20261126/ | Whole archive SHA256 |
| --- | --- |
| anytype-original-app-sqlite-5000-c15e148e-evidence.tar.gz | b7563a1034766a62e0872905d79d72409cc69c4c96e13f74c0d03b68d669c69f |
| anytype-original-four-workspace-editor-reopens-8bcf64b8-evidence.tar.gz | ee38dffc6b47528622af878010acb8711befa27cc61e451bb0c5f33441871250 |

The first retains Apple summary
`60573981c99a0aa3148dd0a25607b8458d90b58991b4359ab104a4c3e32cb956`:
one passed, zero failed/skipped, actual iPad Pro 13-inch M5 arm64 OS 27.0/24A434.
Its original test source is Maktabah
`c15e148ed11bfdc03dea4119ac49672fa86253b2`; the receipt records test source
SHA256 `ebd7eb6ce028bc40358ff064a15e619805e7fc24ef019a5238290a9cb9ffbb63`.
The retained product advanced 4162→5000 native rows, with 5000 distinct identities
and revision sum 5000 (min/max 1). The actual XCTest log includes original
read-only cold observations for rows 1, 2500, 5000.

The second retains a passed original XCTest log and xcresult for source
`8bcf64b839b30a9e27a5683380fce8fdfa86f9f7`. Its report SHA256 is
`faa8c90502266d7db2cd5f8ebfc8f21a0bba5617074eef8ee1144c40748d28b9`;
the report references original summary
`d6b252e9754ccb41f6d51025faaa3099af3aff8a16df0b7ecddb4a550a7cdad0`.
That separate summary is not a standalone member of this archive; this audit
read the original report/log and preserved xcresult, without inventing a fresh
summary export. Four actual editor readback rows are 2, 379, 2407, 4163. Profile
counts 378 + 2028 + 1756 + 838 total 5000 across four retained workspaces.

Both exact GitHub test bodies were reviewed: ordinary preparation/conversion,
no bootstrap bypass, UUID/text/revision/body checks, actual process cold reopen,
and normal original expanded-editor rendering. The index
`retained-otzaria-5000-audit.json` records all archive members and their hashes,
the original reports/commands and readback observations. Its SHA256 is
`477a3845cf3fa15708f0bb127880afb26e8813f7de36405f63db2fed14c93fdb`.

This is verified retained evidence for those original Otzaria products. It is
not a new 5000-row run, a claim of 5000 rows in one workspace for the four-workspace
test, or qualification of the changed f145/bfc SDK, current Pinkha, remote sync,
physical device or TestFlight. New SDK/Host source remains with the Otzaria
owners; this lane has not duplicated their implementations.
