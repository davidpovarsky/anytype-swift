# Owned T5 command process boundary

The combined Release candidate will execute T5 commands inside the existing
bounded Wave15 worker. T5's command executor previously created a separate
process group but did not drain it after a normal parent exit. Terminating the
outer worker group therefore did not establish that nested compiler/test
processes had stopped before the next command or cache publication.

`run_t5_apple_pair.run_logged` now reuses the existing
`wave15_batch.run_worker_command` executor and
`run_owned_single_lane.verify_owned_group_stopped`. It latches SIGTERM/SIGINT,
drains only the newly created command group, and records its actual quiescence
before returning. Original argv, output path, command timeouts, return codes,
failure types and credential-debug suppression remain. The executor's raw
metadata is retained in a distinct `*.owned.command.json`; the existing T5
metadata records that original's hash and the quiescence observation. Cleanup
failure cannot qualify a command as successful or replace an original command
exception with a fabricated pass.

## Actual local verification

Three new POSIX process controls passed in 10.703 seconds. They launched actual
owned child processes, including a child that ignores TERM after its parent
exits, a timed-out command, and a cancelled controller with a separately owned
control process that remained alive. These are process-controller proofs, not
native/Swift/Apple acceptance.

A subsequent source review restored the original failed-Popen metadata shape:
`controller_process_id` remains absent when no process started. This changes
only the no-process branch; the three already-passed process-started controls
were retained without replay. The three affected original process controls
then passed in 3.346 seconds on the final candidate: SIGINT interruption,
timeout with a parent that exits on TERM, and failed process creation. The
initial attempt to invoke those controls lacked the test module in the local
source-only fixture and executed no test bodies; its original import-error log
is retained. The exact current test file was then retrieved and the selected
three controls ran once.

`QUALIFICATION.json` records source hashes and the explicit input-impact
boundary. No historical native/runtime/Swift/UI test was re-executed. No CI,
App build, simulator command, native binary or shipping configuration changed
as part of this proof.
