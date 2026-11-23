# SDK06 original Products enumeration only

## Observed starting point

Original run [45087685319](https://github.com/davidpovarsky/anytype-swift/actions/runs/45087685319),
attempt 1 at source 7293e4fd0bcabdcdb643d5768b777b8e87ff1b73, successfully built the native App.
Admission stopped at SHARED_EDITOR_COMPONENTS / ENUMERATION_PRECHECK: actual suite discovery
enabled 30 methods, but the attempted selection enabled only the 15 nonparameterized methods.
The eight parameterized methods were disabled. No pending component test, acknowledgement test,
native journey, or UI journey executed in that run.

This diagnostic does not qualify SDK06, execute a product test, make an App build, restore an
accepted build, or permit consumers to skip their existing admission gates.

## Immutable inputs

The only accepted GitHub artifact is 14782666651,
Pinkha-UI27-hanlin-native-shared-editor-45087685319-1, 697,865,578 bytes,
SHA-256 6e22d77dcf964edef2c88a6c5d1b6375c21c9bb9213fab761e0d64b349d95450.
The source/run/attempt, artifact API digest, size and original failed-run identity must agree.

Original sdk06-early-products/BuildProducts.tar.gz is 713,955,862 bytes,
SHA-256 7a741f05df92143622a7d07b07682260c0c2281c4b700586fd80839bbc282822.
An independent Oracle streaming read verified this digest; independent-products-digest.json
records that read. The manifest is pinned to
cd9a4743f4bec103a8805c0755df680997268147147706287a9356bca75a1889.
It describes 5,007 original regular files/directories with exact size, mode and digest.
The helper restores those entries into a fresh owned directory; links, escaping paths and
extra/missing/duplicate members are rejected.

The App executable, AnytypeTests executable, xctestrun and source-input inventory remain unchanged.
The original xctestrun SHA-256 is eb7baf907400841fd1a5e7a687ad0a843e12ff6ddab958d8037fed90a7e767d1.
Before and after the probe, all imported repository Python modules are bound to their exact
current Git checkout and byte hashes. All original Products are rechecked after cleanup.

original-selection.json retains the original source inventory and actual flat enumeration
response for the focused controls, derived from original execution receipt SHA-256
2c5dd3601567cc28fd1a0f240e14da7c675d1b4653c91840cbebbada80699e01.
The live diagnostic independently reads and verifies the original GitHub bytes; it does not
use this test fixture as its admission authority.

## Bounded selector experiment

At most four variants run, stopping at the first exact result:

1. Full 23 original method identities in a sibling xctestrun copy, without CLI method filters.
2. The same identities plus separate -only-testing argument/value pairs.
3. The three exact suites minus the seven original exclusions in the copied plist.
4. A bounded syntax hypothesis appending terminal () only to parameterized signatures.
   This hypothesis is not an accepted identifier translation.

Every test action is xcodebuild test-without-building with -enumerate-tests. There is no build,
build-for-testing, scheme resolution, or actual test execution in this route. Descriptor copies
stay beside the original, preserving __TESTROOT__, App/test paths, environment and injection.
Existing disabled-test identifiers remain disabled.

A variant qualifies only if Xcode reports the original test-plan name, exactly the 23 full
original compiled identities enabled, none of them disabled, and all seven exclusions explicitly
disabled. Actual JSON, command, owned-process observation and descriptor copy are preserved for
every attempt. Success is EXACT23_ENUMERATED_PRODUCT_TESTS_NOT_RUN; it is not a test-pass receipt.

The seven exclusions, including three parameterized methods, are:

- AnytypeTests/TextBlockFocusLifecycleTests/consumedAndNewerFocusSurviveOldCallbacks()
- AnytypeTests/TextBlockFocusLifecycleTests/editingDenialCancelsPendingFocus(locked:)
- AnytypeTests/TextBlockFocusLifecycleTests/focusedTextViewDoesNotReplayResponderAcquisition()
- AnytypeTests/TextBlockFocusLifecycleTests/laterFocusSupersedesDetachedRequest(useNativeEditing:)
- AnytypeTests/TextBlockFocusLifecycleTests/nativeFocusObservationDistinguishesOutcomes(outcome:)
- AnytypeTests/TextBlockFocusLifecycleTests/pendingFocusWaitsForKeyWindow()
- AnytypeTests/TextBlockFocusLifecycleTests/refusedFocusWaitsForWindowReadiness()

One newly created, explicitly compatible iPad/iOS27 simulator is owned by the probe. Existing
simulator selection and process-group cleanup helpers remain unchanged. Every owned command
requires an observed zero-member process group. Cleanup targets only the new simulator UUID;
no unrelated simulator, process or cache is modified.

## Route and validation

The new .github/workflows/pinkha-sdk06-enumeration-probe.yml offers workflow_call and
workflow_dispatch, with no inputs. It uses xcode-27, ARM64 Python 3.12, and contents/actions
read permissions. It checks out github.sha with full source history so the three original
Swift test files can be verified from their pinned commit. The existing central dispatcher
and every existing product/controller source are unchanged in this commit.

Owned command:

    python3 -B "$CONTROL/Tools/PinkhaSimulatorGate/sdk06_enumeration_probe.py" \
      --control "$CONTROL" --work "$FRESH_WORK" --evidence "$FRESH_EVIDENCE"

Eight new focused Python controls passed on Oracle in 0.051 seconds. They cover the observed
15-only failure, wrong/extra/zero selections, artifact and run replay, changed source inventory,
exact regular-file restoration, mutation, links/traversal, descriptor injection preservation,
and the permanent enumeration-only command contract. Original controls and product tests were
not repeated. new-controls.json binds the exact source and log bytes.

Actual Apple enumeration remains NOT_RUN at this commit. Future SDK06 acceptance still requires
actual 23 methods / 32 cases, seven acknowledgement tests, native journey and UI journey with
their original source/module guards.
