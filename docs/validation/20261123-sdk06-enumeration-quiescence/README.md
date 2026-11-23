# SDK06 enumeration: bounded owned-process quiescence

## Observed original boundary

Run 45107006017 at 1e9ee4de8ac2051020d9fd0cb181b8f68498e184 restored the pinned original SDK Products and created its owned simulator. The original bootstatus command returned zero, but the following numeric process inventory exhausted its existing 10-second quiescence budget. The recorded final ps timeout had 0.459156 seconds remaining. Neither proposed selector variant started.

The original shutdown and delete commands subsequently each reached their unchanged 30-second timeout. Final source-integrity inspection also timed out after 30 seconds. All those failures remain failures. Restored bytes and successful earlier commands do not establish final cleanup, integrity, SDK acceptance, or product behavior.

Original artifact 14788672678 is 511,990 bytes with SHA256 acd637db484b1272b76a80e4d26e3115c80ea1c53d55503d22ec4ce01f7246be. Exact original receipt and three affected command records are preserved under original-45107006017. The complete downloaded original remains in the Oracle diagnostic folder recorded by the source review.

## Scoped correction

The SDK Commands adapter opts into the named sdk06-enumeration policy. That policy uses the already implemented explicit Apple-consumer process inventory rule: a probe may use the remaining portion of the same total 10-second budget. Only this new explicit profile is added to the existing allowlist. Ordinary callers still use their original 2-second probe limit.

The command adapter also preserves timeout_observations and quiescence_observation from a cleanup exception. An earlier actual command exception remains primary. Successful quiescence still requires an actual zero-live-member observation by the original deadline. A late zero-member result, a process still alive at the deadline, and an inventory timeout all remain failures.

The simulator command limits, final integrity limit, 600-second per-enumeration limit, 2,400-second enumeration total, both unexecuted CLI variants, exact 23-selection validator and runtime-normalizer function are unchanged. The source review records exact unchanged normalizer bytes for downstream pin review. No mounted-contract pin, workflow, App, package, native source, or original receipt is edited.

## Actual verification

Only the three new controls in test_sdk06_enumeration_quiescence.py ran. They passed in 0.013 seconds:

1. The actual supervisor observes a live member first, then zero members, using only the remaining 10-second budget.
2. Live-at-deadline, timed-out inventory, late zero-member observation, and an attempted larger budget are rejected.
3. The adapter preserves the original command timeout as primary while retaining the subsequent cleanup observations.

The exact three source files were archived before this run. Their pre/post hashes are identical. Existing controls were not rerun. No Apple product tests, selector enumeration, compilation, or CI dispatch occurred. The original incomplete cleanup and final-integrity failures remain explicit; actual Apple continuation is still unexecuted.

All modified production files are downstream-owned Pinkha tooling. Standing owner authorization and the root agent's scoped assignment authorize this isolated correction. Fresh upstream/develop reference d857b23ea540be33d6faab4f7a7a1a260ab578c1 was observed; no upstream source was fetched or modified.
