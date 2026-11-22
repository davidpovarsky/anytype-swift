# Coherent worker teardown boundary

This is controller/process evidence, not native, App, or Simulator acceptance.

The original outer supervisor allowed five seconds after TERM while its inner owned command could itself need five seconds before KILL. The exact new cancellation control reproduced that race: one error after 5.523 seconds because the outer process died before the inner original command receipt was written. The original failure log is retained.

The candidate-only `run_nested_worker_command` keeps the execution cap unchanged and reserves 25 seconds before outer KILL: inner TERM5, final wait5, quiescence10, and receipt5. Its final post-KILL wait remains5. It delegates final owned-group termination and quiescence to the unchanged existing helpers. Ordinary SDK/package executors are unchanged. This commit defines the new executor but does not select it for any existing profile.

Two new controls initially passed in 5.798 seconds: cancellation through the outer supervisor, and rejection of a nominal successful command without its original owned-group receipt. After the teardown accounting included the existing inner final wait, only the affected outer control ran again: one PASS in 5.799 seconds. The unchanged missing-receipt control was retained. The earlier three new and three affected command controls are also retained without repetition.

The original logs and exact source/function bindings are in QUALIFICATION.json. Normal/timeout/cancelled command receipts, original exceptions, specific command PGIDs and unrelated process isolation remain mandatory. The new executor writes its original command receipt and verifies its own group is quiescent before allowing downstream cache admission. The eventual combined profile must independently validate its complete worker conclusion and cleanup receipts.
