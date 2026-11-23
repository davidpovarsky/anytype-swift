# Separate original-Products Release preflight lifecycle

This adds only a downstream prepare/cleanup adapter and its new controls.
The original preflight.py, pair selection, batch cleanup, App and product
sources remain unchanged. Base: e4f9523be8b0c4fdcaf7727b60a55a5229ad990a.
Current upstream develop was read through the repository API as
d857b23ea540be33d6faab4f7a7a1a260ab578c1. No upstream source is edited.

Commands, from the exact current controller checkout:

    python3 -B Tools/PinkhaSimulatorGate/coherent_original_preflight.py prepare --control "$CONTROL" --evidence "$EVIDENCE"
    python3 -B Tools/PinkhaSimulatorGate/coherent_original_preflight.py cleanup --control "$CONTROL" --evidence "$EVIDENCE"

The workflow owns the outer evidence directory and may open its tee log first.
Prepare creates an exclusive preflight/ subtree and writes its initial receipt
before host/source/worker setup. GITHUB_SHA, GITHUB_RUN_ID and GITHUB_RUN_ATTEMPT
bind the current controller. The later immutable App remains the separate d254
original-Products origin; it is never substituted into the actual preflight SHA.

Prepare reuses preflight.select_pairs unchanged. It saves the complete original
baseline and both exact run-owned names, types and runtimes before creating
either device, and refuses preexisting planned names. Existing batch-compatible
names remain Pinkha-UI27-<run>-iphone/ipad. Each per-device marker precedes its
create command. The original log/command record and returned nonbaseline UUID
are persisted before owned-group finalization. The first original create/setup
error remains primary. The selected map is checkpointed after each UUID; only
complete success exports both environment variables. The total preparation
deadline is 360 seconds; each command also retains its bounded worker and the
qualified coherent group-quiescence profile.

The always-cleanup command preserves the preparation receipt. Before any device
lookup it verifies this journal's current controller/run/attempt, original
baseline bytes, planned pair, started commands and available original UUID
proofs. If creation never started, it reports NO_OWNED_CREATION without a
simulator scan. A marker without an original command log does not admit cleanup.
Baseline or inconsistent UUIDs and changed ownership are refused.

Fallback cleanup directly reuses the unchanged batch.cleanup_owned policy and
its coherent 180-second deadline, scoped queries and exact name/type/runtime
checks. Its report lives under preflight/lifecycle/ and cannot overwrite the
batch's original root batch-cleanup.json. A full current batch intent, execution
receipt and matching PASS cleanup report may prove the exact journal-owned IDs
already absent/deleted; only then are all new cleanup commands skipped. Status
alone, stale source/attempt or a different UUID cannot establish that proof.
Original failures and every fallback/admission decision remain explicit.

Seven new controller methods cover successful incremental ownership, a second
create failing after the first succeeds, a returned UUID before later process
finalization failure, baseline/preexisting refusal, exact prior-cleanup admission,
failures before creation and unknown partial-create identity checks. These are
synthetic controller controls only; actual Mac preflight and product execution
are NOT_RUN until their original execution receipts exist. No old control
suite or product tests are rerun for this change.
