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

1. Enumerate the two compiled suites in flat JSON using the existing xctestrun.
   Require the exact twenty-eight source declarations: seventeen focus methods
   and eleven table methods, with no missing, repeated or disabled declarations.
2. Take the twenty-one approved full identifiers, including their Swift
   signatures, directly from that original enumeration.
3. Enumerate this exact identifier selection again. Require exactly those
   twenty-one methods before allowing the single component execution.

The two original enumeration files and command receipts remain in the evidence
directory, including on failure. Empty, erroneous, ambiguous or changed
enumeration schemas fail before component execution. The returned full
identifiers become the actual `-only-testing:` arguments; no arbitrary method
list is exposed as a workflow input.

Apple documents enumeration of an existing xctestrun and flat identifiers for
subsequent xcodebuild invocations in the
[Xcode 15 release notes](https://developer.apple.com/documentation/xcode-release-notes/xcode-15-release-notes).
Swift Testing identifier support in `-only-testing` and `-skip-testing` is
documented in the
[Xcode 16.3 release notes](https://developer.apple.com/documentation/xcode-release-notes/xcode-16_3-release-notes).
The flat JSON reader preserves enabled and disabled inventories separately and
does not convert an unavailable enumeration into permission to run a suite.

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
three frozen files after enumeration and after execution. It rejects stale
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
