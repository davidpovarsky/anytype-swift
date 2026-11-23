# Canonical Anytype observer diagnostic repair — 2026-11-23

## Actual native evidence remains separate

The original run [45163976036](https://github.com/davidpovarsky/anytype-swift/actions/runs/45163976036), source `aefb9740c0ac8d52aa2dbd89d389930851396104` with SDK `d49a4fd4115b8335105d2991bf74ab4d7f6aad2d`, built the real app successfully. Its original native preparation case passed, its original UI case passed, and all 22 native behavior checks were true. The runtime observer failed separately. Complete original receipts and custody are retained in [the preceding readback](../20261123-canonical-native-pass-observer-failure/README.md).

The mapping-stage timeout occurred before the final native phase and before the UI passed. Its archived evidence has no completed `live-runtime-vmmap.log`, process-start identity, final runtime mapping, or qualification. It therefore cannot establish the missing same-instance loaded-module proof. This diagnostic repair does not turn that failed observation into a pass.

## Concrete defect and narrow repair

A recovered data-container query timed out earlier in the same observation. The original global `first_failure` correctly retained that first error. When the later mapping stage timed out, the per-stage record retained only its failed status and duration, so the final report could not identify whether the fatal command was a process-identity query or `vmmap`.

The production change is exactly three added lines in `Tools/PinkhaSimulatorGate/hanlin_ui_runtime.py`. Each existing fixed-size stage record now retains its latest already-sanitized failure fields, the attempt number, and the elapsed stage duration. A later successful attempt does not erase the earlier failure: the attempt number and current stage status distinguish a recovered error from a terminal one. The global `first_failure`, command bounds, exception propagation, execution, retries, deadlines, source checks, process identity, module assertions, and authority checks are unchanged. Command output and arbitrary exception text remain excluded.

Removing those exact three lines reconstructs the complete prior production source byte for byte:

| Source | SHA-256 |
| --- | --- |
| Prior observer | `65f4607ed9dd82fb7842398f4cc62ad2ec3b8ff8c5498b25f50f62ebefef6e02` |
| Observer with bounded stage failure | `b3e17426b4d2c00bce4164ebb19ba484e00507fe1a24f937ac95f22d63a7306e` |
| New focused control | `3eb4eac113272431a04993ec1b56fa8e0966778d6315710afa7e74e071b30f75` |

## Focused execution

One new controller method runs two deterministic cases against the complete actual observer and the unchanged original fixture helpers. The original fixture test methods are not executed. Both cases recover from the original polling timeout and then inject a fatal timeout into the mapping operation, once with a `vmmap` command and once with a process-identity command. These cover both commands that the original failure artifact could not distinguish; they do not assert which command failed on the Apple runner.

The exact method is `CanonicalObserverDiagnosticTests.test_recovered_poll_preserves_the_later_terminal_mapping_failure`.

- Before the change: one method, two failed cases, 0.517 seconds. Both failures identify the missing later diagnostic.
- After the change: one method, two passed cases, 0.514 seconds.
- Each case still rejects qualification, preserves the same terminal exception, performs exactly three data-container queries and one mapping attempt, and performs zero extra launches.
- The original first failure and recovered polling status are retained. The new mapping record exposes the bounded fatal command without private stdout or stderr.

These are deterministic Python controller checks, not Apple, runtime, or UI acceptance. No original controller method, previous timing control, or native case was replayed for this repair.

## Exact source qualification

`diagnostic-qualification.json` binds the production source, unchanged fixture, new control, the actual named test log, and all four before/after case traces.

The existing source-retention verifier first validates this new qualification and reverses only the exact diagnostic insertion. It applies the original imported source closure and timing evidence to that reconstructed prior source. The final source-input receipt still reports the actual current observer hash. The older 68 unchanged methods, one previously requalified method, and two existing timing methods/five cases retain their original source-qualified receipts; their evidence is not relabeled as newly executed.

The initial qualification metadata used a numeric duration while the original named-outcome parser preserves the log duration as a string. The verifier rejected that metadata. Correcting the receipt to the exact original `"0.514"` representation resolved the mismatch without changing or rerunning the test. Original before/after logs are unchanged.

## Remaining native contract and necessary next journey

[SDK06 story 1220719505176298](https://app.asana.com/0/0/1220769818981326/f) requires mapping during the actual UI journey. The observer requires the same fixture, session, PID and process-start identity, with mapping completion inside that native journey's start/finish window, followed by original entry/final hierarchy and source continuity.

There is no existing observer-only dispatch that can repair the old UI instance. The lower-level mapping helper can inspect an already-owned PID, but other routed runtime probes launch a new process. The independent SDK06 original-products continuation remains frozen to App source `75bd6d7af18dfd511e85582ce7f994d2801b7703`; its current controller does not rebuild that App. It cannot qualify the canonical SDK32da App.

A necessary fresh preparation1 plus original UI1 journey with the original observer attached is therefore the current-source conjunction still required. Its source will use the already installed and verified canonical SDK `32da9e314e22bbf22391fcf8902302acfbb281e2`. The original authenticated runtime producer remains `45091223011`. This is not a replay of the SDK06 owner's 23/32 plus ACK selection, and does not weaken the observer contract. No new native run is claimed by this diagnostic receipt.

## Supplemental original-image review

The root reviewer independently opened the already extracted original PNGs through Oracle, with no transformation, new extraction, or download:

- `EE85F541-3EAE-4A87-938B-345864EAF924.png`: original UI27 blank Page and matching A40F4C37 fixture body after return. SHA-256 `f79471c24ea454460d25868a047ddc753f3f01c7cca5597b34a8baf0bd0304dd`.
- `03DB6F5B-AA16-4A68-9A40-A968CD21838D.png`: original Anytype authentication/entry screen with the `NATIVE_ACCEPTANCE_PASS` diagnostic banner after logout. SHA-256 `517c8df83b7720b125866ac6f4a873837428de82565e9801364a1f3169d3668a`.

The existing diagnostic overlay overlaps part of the header. The images establish the observed screen state; authorization and all 22 behavior checks are established by the original assertions and receipt.
