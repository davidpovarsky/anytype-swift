# Native generated-byte Space.Close proof

This lane retains the existing unmodified four-process account-wire baseline,
then runs two additional processes against one separate disposable account.
It leaves product composition `16b7493fa05bdc3abbae190c6e6c364c81874eea`, the
previous three-race fixture, and the App capability (`OFF`) unchanged.

## Actual native boundary

The first process creates an account using the original native local-only
Wallet/Account RPCs. Before any race barriers are installed, it waits for the
actual account notification service's `LoadFinish` channel. Its bounded startup
wait uses the native ACL notification component's existing one-minute startup
budget; no timer stands in for readiness. The subsequent race retains its
original 90-second context, 30-second event waits and 40-second gate bounds.
It creates one private operations history through generated
protobuf bytes, then forwards one second generated append. Test-only observation
gates pause that append after the real settings/target/private-tree locks are
held and before the original native validator takes its final ACL lock.

Original cache removals put both the target and private object entries in
`Closing`. An exact already-loaded Space controller then receives its original
`Close` once. The unchanged cache's original ten-second deadlines expire for
both entries. The test requires the original settings object's `SyncTree.Close`
to remain behind the same settings lock, with physical native store close not
yet reached. No native lock, return value, context, authorization decision or
write is replaced by the observation helper.

After releasing the append gate, the original native transaction commits. A
second observation gate reads the actual three-entry signed history while the
settings fence still excludes teardown. Both original signed entries must be
byte-identical; one real new head must be present. The original append response
must be `CREATED` with the expected complete claim. The original cache removals
and controller close then finish, and an actual read transaction after physical
store close must be denied while the probe context is still live.

The second process recovers the same disposable wallet, selects the existing
account and opens the same Space. It requires all signed history bytes, both
canonical claims and the verified local head to survive. It forwards the exact
retained original request bytes once: the native result must be
`ALREADY_EXISTS_SAME_PAYLOAD`, with no new change ID and no change to history or
the entire read protobuf, including its local watermark.

## Source and execution identity

The source composition contains five Heart observations, two observations in
the actual selected `any-sync v0.13.8` module and three new test-only Go files.
The original Heart, module-cache files and original account fixtures are never
overwritten. Go forbids compile overlays beneath `GOMODCACHE`. The controller
copies the complete selected module into its owned build directory, verifies
every file against the original cache, and selects that copy through one
version-scoped replacement in a separate test-only `go.work`. The original
workspace is unchanged. Go receives a compile overlay against the copy and
Heart; an empty helper package directory permits discovery. The module version,
checksums from pinned Heart's unchanged `go.sum`, original source bytes and
selected module paths, complete copied source tree and both workspace files
are checked before use and after execution.

The instrumented binary links its exact composition SHA alongside the existing
Heart, registration, account fixture and generated RPC schema identities. It
must differ from both original baseline binaries. Each phase uses a separate
PID and nonce. The controller requires the exact named Go test, original logs,
fifteen correctly ordered native event observations, eight in-process pointer
identity checks, complete phase reports, and the matching original history.

Native launch failures, nonzero exits, cancellation and timeouts retain their
observed launch/PID/exit state. The controller does not promote a source check,
controller unit test or incomplete phase to native acceptance. It preserves the
primary error if cleanup or source verification also fails.

## Disposable data and retained evidence

The lane creates only a fresh owned synthetic account directory. Its ownership
token and directory identity must still match before removal, and every started
process must have an observed exit. The private account key, mnemonic, raw
account directory and private cross-process state are never uploaded. Only
allowlisted original phase reports and logs that pass the synthetic-secret
scan join the artifact. If the secret inventory is missing, native phase output
is withheld. A changed owner or directory identity prevents cleanup.

## Limits

This proves only the explicitly instrumented native close/durable-write/cold-
reopen boundary. It does not assert response-return ordering relative to close,
duplicate-close joining, settings deletion, account switching, new-engine
parity, two App clients, iOS UI acceptance or full T2 release acceptance. Those
claims remain separate. The original three lifecycle races remain unchanged
and are not rerun by this lane.

## Startup precondition correction, 21 November 2026

Run [44939797011](https://github.com/davidpovarsky/anytype-swift/actions/runs/44939797011)
compiled the instrumented binary and passed all four original baseline native
processes. The separate race failed before its first cache-deadline observation;
cold reopen did not run. The original log reported `common.components.aclnotifications`
still closing at ten seconds, then 29,612 ms spent in that component before the
client Space was reached. Pinned native account notification discovery itself
has a 30-second peer deadline, and ACL notification teardown waits for its
startup channel. The earlier fixture had started its controlled race during
that unrelated startup. Waiting on the real readiness channel before installing
barriers removes that setup overlap without replacing the owned controller,
changing native cache deadlines, or weakening the fifteen event and eight
same-instance checks. This correction is not a native PASS claim.
