# Conditional revision on the retained original network fixture

Status at preparation: **SOURCE PREPARED; NOT COMPILED OR RUN.** This file records the intended new regression, not a passing result.

`original_network_revision_test.go` is an external-package test of the actual original Heart application service. It uses the existing `original_network_peer_test.go` helpers and the native revision lane's `owned_annotation_revision_native_test.go` helpers. Those sources must be frozen together in the immutable Go overlay before compilation on the real Mac.

## Separate completed evidence

The earlier genuine remote roundtrip passed in `job_e8f0acde2861` and is retained under `docs/pinkha/torah-integration/original-native-network-20261125`. Its source, native binary and receipts remain unchanged. The new test does not rerun that completed case.

## New acceptance sequence

1. Recover the same development account from the two existing separate original repositories; require the same native account, Space and object. Require actual default remote network mode and disabled LAN sync.
2. Obtain genuine native revision reads on both peers and retain the receiver's old token/export.
3. Mutate a rich text block through the original producer Block service. The receiver must observe the changed canonical native root and exact text/marks hash through its own original export.
4. Send the receiver's old token to the real native conditional revision operation. Require a pre-write conflict with no native Apply, no observed write and unchanged receiver heads.
5. Make a separate explicit test resolution choice: use the receiver's own previously saved native archive with a newly observed token. Require the same root ID and accepted actual original Apply/readback.
6. Require the other process to observe the complete selected block inventory, content, formatting and child order through the genuine network. Control files convey identifiers, hashes and outcome observations; they never supply native bodies, archives or database files to the other peer.
7. Stop both original accounts cleanly. Start two fresh test processes with the same repositories, read the final native root and stop again. These reopening roles perform no object mutation.

A local `applied` receipt alone never satisfies the peer-observation check. A native refusal, incomplete readback or timeout fails the phase and remains recorded.

## Invocation contract

- `OTZARIA_ORIGINAL_NETWORK_ROOT`: the retained private fixture root containing both existing repositories and the private development credential.
- `OTZARIA_ORIGINAL_REVISION_RUN`: a new owned mode-0700 directory for this phase, outside both repositories.
- `OTZARIA_ORIGINAL_REVISION_ROLE`: `producer` or `consumer` for the concurrent pair, then `producer-reopen` and `consumer-reopen` for the cold processes.
- Execute only `TestOtzariaOriginalNetworkRevisionPeer` for this phase. The existing initial-account test must not be selected.
- The retained credential stays in its private fixture. It must never enter public logs, a transfer archive, Git, or a report.

The harness refuses a reused evidence directory instead of silently overwriting a prior run. If a trial fails, inspect its actual native state and retained evidence before adapting or resuming; do not create another account/object or blindly repeat the mutation.

The final run manifest must bind the exact native product/test overlay, prior helper bytes, Go environment, binary checksum, all process exit codes and sanitized proof hashes. No runtime or C–F acceptance is established by committing this preparation.
