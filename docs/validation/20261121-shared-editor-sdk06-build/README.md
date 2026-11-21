# Reuse the SDK06 build for pending editor and table cases

## Scope and existing evidence

Original editor source baseline: c6ecc8ae89891b335434faec36f40b3b63e79334.
The earlier retained run 44942212731 never reached any of its ten selected
methods: AnytypeTests linking failed on three missing package products.
Commit c6ecc8ae fixes those explicit target dependencies. That failure remains
preserved in ../20261121-retained-test-linkage.

The table extension is based on b47b528a3addbe46b17304cf0e583441b0645f0b,
including the reviewed shared_table_profile.py and eleven actual UIKit handler
methods introduced by 0c582d. No previously passing component suite is selected.

| Component | Selected methods | Required actual cases |
| --- | ---: | ---: |
| Retained shared editor | 10 | 15 |
| Table persistence and commands | 11 | 14 |
| Combined component invocation | 21 | 29 |
| Native text acknowledgement, subsequent separate invocation | 7 | 7 |

The explicit `hanlin-native-shared-editor` lane uses the same job's SDK06
Debug application, test bundle and xctestrun for both editor and table groups.
It then executes the existing seven native acknowledgement methods, creates the
original SDK06 native fixture and runs its UI journey. It adds no application
build. The default `hanlin-native` and optional `hanlin-native-text-ack`
lanes retain their existing selections.

## Compiled selection before execution

The focus suite contains seventeen declarations, of which only ten belong to
the pending profile. Selecting its whole suite would run seven unrequested
methods. Selecting bare Swift Testing method names previously selected zero.
The wrapper therefore performs these steps without executing test bodies:

1. Derive an owned sibling copy of the existing v2 xctestrun. Retain the actual
   AnytypeTests target and all its product/environment settings; remove other
   targets only from the copy and set its target-relative OnlyTestIdentifiers
   to the two suites. Enumerate this copy in flat JSON. Require the exact twenty-eight source declarations: seventeen focus methods
   and eleven table methods, with no missing, repeated or disabled declarations.
2. Take the twenty-one approved full identifiers, including their Swift
   signatures, directly from that original enumeration.
3. Derive a second owned sibling copy containing those twenty-one target-relative
   full signatures in OnlyTestIdentifiers. Preserve any original
   SkipTestIdentifiers. Enumerate this selected copy and require exactly the
   twenty-one enabled methods before executing that same selected copy.

The two original enumeration files and command receipts remain in the evidence
directory, including on failure. Empty, erroneous, ambiguous or changed
enumeration schemas fail before component execution. The returned full
identifiers become both the selected copy's OnlyTestIdentifiers (without the
already-bound target prefix) and explicit `-only-testing:` arguments. No
arbitrary method list is exposed as a workflow input. Both copies stay beside
original Build/Products metadata, so __TESTROOT__ still resolves to the same
products. The original file is never modified. Unsupported versions,
multiple configurations, duplicate/disabled target entries and existing skips
of requested methods fail before execution.

Apple documents enumeration of an existing xctestrun and flat identifiers for
subsequent xcodebuild invocations in the
[Xcode 15 release notes](https://developer.apple.com/documentation/xcode-release-notes/xcode-15-release-notes).
Swift Testing identifier support in `-only-testing` and `-skip-testing` is
documented in the
[Xcode 16.3 release notes](https://developer.apple.com/documentation/xcode-release-notes/xcode-16_3-release-notes).
The flat JSON reader preserves enabled and disabled inventories separately and
does not convert an unavailable enumeration into permission to run a suite.
The exact schema is captured in a primary project's
[Xcode 27 fixture](https://github.com/AndreasSko/meh.md/blob/1b1ae8f18778387484113a3170995eda8ed33d4c/scripts/fixtures/ui_enumeration_xcode27.json)
and in an independent
[original SDK enumeration](https://github.com/Joncallim/mostlytext/blob/f11c75c549cf786972e2a372a84fd0f4501dd5e4/planning/downstream/evidence/critical-sdk-discovery-2026-11-07/actual-discovered-tests.json).
The latter also records Swift Testing parameter signatures and warns that CLI
filters alone did not restrict its enumeration. The owned xctestrun copies
therefore supply target selection directly instead of depending only on those
flags. Apple's installed `xcodebuild.xctestrun(5)` manual documents
OnlyTestIdentifiers as target-relative class/method identifiers; its v2
TestConfigurations/TestTargets structure is validated before creating a copy.
These references establish the format, not product acceptance for this app.

The native acknowledgement source was also checked: it contains exactly seven
nonparameterized methods. Its existing `run_selection` implementation selects
that complete suite and requires those seven actual named results. It has no
extra declarations and does not use the failing bare-method selection.

## Result and source binding

Both original argument contracts remain unchanged:
`Tools/Hanlin/shared_editor_profile.py` and
`Tools/Hanlin/shared_table_profile.py`. Their validators receive the original
case nodes partitioned from the combined xcresult. Fifteen editor cases and
fourteen table cases must be present individually. The raw combined summary
may report twenty-one methods or twenty-nine invocations, but neither total
substitutes for the actual parameter nodes. No per-group summary is invented.

The wrapper verifies the actual SDK06 application path, freezes application,
test executable and xctestrun hashes, and checks both test sources and all
three frozen files plus the selected copy after enumeration and after execution. It rejects stale
evidence. Its combined success label is
`SHARED_EDITOR_TABLE_COMPONENT_PASS`; this component result does not claim
native persistence, SDK06 UI acceptance or full application acceptance.

## Focused controller verification

Windows / Python 3.12, 2026-11-21T22:04:59Z–22:05:01Z:
`py -3.12 -m unittest -v test_shared_editor_existing_build`, from
Tools/PinkhaSimulatorGate.

**11 controller methods passed**, job `job_69ade8c16a9f`, exit 0.
The controls cover exact compiled selection and original 15+14 argument
evidence, discovery failure/empty/missing/duplicate/disabled/signature drift,
unrequested execution, source and product mutation before and after execution,
stale evidence, and the actual tracked table/editor/acknowledgement inventory.
Synthetic enumerations and result trees are controller fixtures only.

The earlier seven-method wrapper controller result (job_52a31614adf8,
2026-11-21T20:47:39Z) applies to the original editor-only wrapper. It has not been
relabelled as table evidence. Actual Apple execution of the pending twenty-one
methods / twenty-nine cases remains **NOT_RUN** until the new SDK06 job provides
its own enumeration and original xcresult. Existing passing product suites
were not rerun.

### Scoped xctestrun follow-up

The concrete CLI enumeration caveat above led to a follow-up, not an expanded
product test scope. Windows / Python 3.12 ran the same affected controller file
after adding the owned-copy implementation:
**14 controller methods passed**, job `job_9798d5940ac2`,
2026-11-21T22:10:45Z–22:10:49Z, exit 0.

The enumeration fixture deliberately ignores CLI filters and derives enabled
methods from the copied target's OnlyTestIdentifiers. New controls reject an
ambiguous/disabled/unknown original configuration, preserve original skips
instead of silently re-enabling them, and reject mutation of the selected
copy before or after execution. Original app, test executable and xctestrun
binding remain enforced. No Apple test body or additional application build
ran during this controller check.

### Cached-copy collision prevention

Review identified that a cached Products directory can retain previously owned
UI27 xctestrun copies. The discovery/selected pair now shares one fresh UUID
nonce, recorded with both paths and hashes. Old copies are neither overwritten
nor deleted. The original xctestrun and all product bindings remain unchanged.

Only the two affected controls were executed for this follow-up:
`test_fresh_owned_nonce_preserves_cached_other_run_configuration_files` and
`test_selected_configuration_mutation_before_or_after_execution_is_rejected`.
Both passed in job `job_c9057128b7be`,
2026-11-21T22:13:19Z–22:13:23Z, Python 3.12, exit 0. The previous fourteen-control
result remains evidence for the unchanged selection, argument and source gates;
those cases were not repeated.
