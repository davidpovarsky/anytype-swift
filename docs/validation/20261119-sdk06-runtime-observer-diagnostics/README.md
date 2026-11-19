# SDK06 runtime observation diagnostics, revision 2

Original run `44602685274` at `c787745ad99348aa198b91be0c672f5a9ba2fbda`
passed its build, one preparation method, one actual UI method and all 22 native
checks. Its actual-UI runtime observer raised `TimeoutExpired`, so runtime
binding and full SDK06 acceptance failed. The original artifact did not retain
the failing command/stage or an in-flight native receipt. It does not establish
which simulator lookup or process-mapping command timed out.

The two changed Python files add bounded diagnostics. Each fixed stage retains
its attempt count, latest status and elapsed stage time. A subprocess failure
retains its bounded argv and command timeout or exit code, without command
stdout/stderr or arbitrary exception text. Validated native phase bytes and
already collected source/runtime metadata survive a later observation failure.
These are partial observations and cannot satisfy runtime qualification.

Independent review reproduced two revision-1 gaps: final receipt-export failure
and UI-boundary qualification failure updated in-memory diagnostics after the
last saved snapshot. Revision 2 now persists the final diagnostic snapshot on
those paths and updates the execution receipt. Secondary diagnostic-write
failure preserves the original error; it cannot produce a qualification PASS.
A previously failed stop write is not retried.

The root independently ran all 62 relevant controller tests: 42 observer
controls, including the original 30 plus 12 new diagnostic regressions, and 20
unchanged native-evidence controls. Local tests used the current committed
dependencies, including the already published Properties controller updates.

This changes no simulator command retry policy, app launch, native fixture, UI
method or qualification condition. Original command/observation/mapping/stop
bounds remain 10/420/45/15 seconds. The runtime remains the original r14 input.
The next actual Apple run must either satisfy the original runtime-binding gate
or provide localized original diagnostics for the remaining failure. Source and
controller passes alone do not complete SDK06.
