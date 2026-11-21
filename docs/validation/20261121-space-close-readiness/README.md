# Space.Close startup precondition and compiler-cache correction

## Original evidence

Run [44939797011](https://github.com/davidpovarsky/anytype-swift/actions/runs/44939797011)
used app source `a03a834d8fb399978b49408a5f4a8c60b221203a`.
The immutable Go module overlay setup now succeeded. The instrumented native
binary compiled, and the unchanged baseline completed four native processes
and eight exports. The separate Space.Close race failed after 30.84 seconds;
its cold-reopen process was not started.

The original race log reported the ACL notification component still closing
at ten seconds. Final teardown statistics reported 29,612 ms in
`common.components.aclnotifications` before reaching the client Space.
The original trace contained the settings lease, paused append, and both
cache entries entering Closing, but neither cache deadline.

Pinned Heart `d98420b1113536afd08cde6de9a5816f6d27ffff` explains the setup
overlap: `notificationService.loadNotificationObject` uses a 30-second peer
discovery deadline, and the owned Space controller closes ACL notifications
before the client Space loader. ACL notification processing first waits for
the global service's `LoadFinish` channel, with its own one-minute startup
budget. Starting the controlled close race immediately after AccountCreate
therefore consumed its 30-second event wait on unrelated account startup.

## Correction

The native fixture obtains the actual account notification service and waits
for its original `LoadFinish` channel before creating race objects or installing
barriers. The startup wait is capped by the existing native ACL one-minute
startup budget; it does not sleep or manufacture readiness.

All original race requirements remain:

- Original owned controller receives exactly one Close.
- Original native cache deadline is ten seconds.
- Race context remains 90 seconds; event waits remain 30 seconds and gates 40 seconds.
- All fifteen native events and eight exact live-instance comparisons are required.
- Native storage remains open across the original durable commit and then closes.
- A distinct process must cold-reopen the same account and retry original bytes without changing history.

The source-bound race receipt must now include actual startup readiness.
Timeout errors identify the awaited stage. No production source or response
is replaced, and this correction does not claim native acceptance.

## Avoiding repeated dependency compilation

Job `136954274862` reported a cache miss for the pinned musl/toolchain key
and every compatible fallback. Its native step occupied approximately
12.6 minutes. The combined cache action's post step was skipped when native
assertions failed, losing the newly compiled dependencies.

This workflow now separates cache restore and save. Saving requires this
run's successful observed compiler exit, the exact current app/run identity,
matching build/source inventories, and a successful post-execution source
integrity check. Only the existing `go-mod` and `go-build` directories may
exist in the cache root. Native-work binaries, accounts, phase outputs,
receipts and acceptance status are outside it. The changed fixture is still
compiled and its exact linked identity verified on each run. Native failure
remains failure regardless of cache saving.

## Targeted validation

- 20 native evidence/materializer controls passed: 18 directly, then the two
  byte-pinned fixtures from an LF Git archive to avoid Windows checkout CRLF.
- Seven cache eligibility checks passed: a successful compiler plus failed
  native race remains eligible; failed compiler, changed source, foreign run,
  foreign app, unexpected cache content, and missing build are rejected.
- YAML and embedded Python parsed successfully.
- The fixture passed `gofmt`; `git diff --check` passed.
- Native compile and both real native phases on the corrected source remain
  for the next original CI execution. Prior three lifecycle races were not rerun.
