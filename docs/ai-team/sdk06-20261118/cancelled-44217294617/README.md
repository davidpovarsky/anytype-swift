# SDK06 Apple cancellation evidence and controller repair

## Observed attempt

Run [44217294617](https://github.com/davidpovarsky/anytype-swift/actions/runs/44217294617)
used source `c8e5a0e148021662dd943f93faeb3195c6086888`, attempt 1,
job `134510204281`, and ended **CANCELLED**. It is neither a passing acceptance
run nor a demonstrated compiler or functional failure. The four SDK suites
(57 expected source methods) remain **NOT_RUN**.

The exact public Hanlin revision `116cc6be0654a5d11bc56ba00e0310031107ee36`
was checked out and materialized successfully. The verified Heart artifact from
run `44203168617` was installed successfully with archive SHA-256
`7aa836e081740b99e7e26485fd7f1845fc3ea99fa2331b2ab99330675a4c590f`.

UTC events preserved in the raw job log:

| Event | Time |
| --- | --- |
| Job started | 01:45:46 |
| Build/test controller step started | 01:46:47 |
| `build-for-testing` launched | 01:50:27 |
| Only recorded Xcode output, `Command line invocation:` | 01:51:04 |
| GitHub reported `The operation was canceled.` | 02:01:40 |
| Evidence artifact uploaded successfully | 02:03:34 |
| Runner cleanup terminated orphan `xcodebuild` / Python | 02:04:54 / 02:05:16 |
| Job completed | 02:05:19 |

The original `execution.json` is preserved without rewriting its outcome. It
remained at `phase=BUILD`, `build_succeeded=false`, and
`test_command_exit_code=null`, with no xcresult. Its `status=FAIL` was the old
controller's initial value, not evidence that a compiler invocation failed.
The artifact's build log `command-02.log` was zero bytes despite the raw job
log containing Xcode's opening line.

Artifact [14390092827](https://github.com/davidpovarsky/anytype-swift/actions/runs/44217294617/artifacts/14390092827)
has original ZIP SHA-256
`cc2ec3c796acd17548aeb0a55c46ef7bc4e6d9dc46275be4ba92ece0abac85a4`.
The preserved raw execution receipt SHA-256 is
`3c0ed5ee93eac3eb43673dbf342224cd713985dcc8c75adbd9927c6943e99865`.
`evidence.json` records hashes of the retained original files.

## Cancellation cause and runner comparison

Neither the run API, check-run output nor its annotations identifies who or
what requested cancellation. The exact caller and reusable SDK workflow have
no `concurrency` / `cancel-in-progress` declaration. The cancellation occurred
before their configured 100-minute step and 120-minute job limits. **The
cancellation cause is unverified.** No unchanged retry was launched.

The SDK runner ID was `1000020792`; the concurrent startup run `44216444722`,
job `134507358447`, reported a different runner ID, `1000020789`. Both were
GitHub hosted `xcode-27` runners. This does not establish shared physical hardware
or resource contention. The SDK recorded image `xcode-27-arm64`
`20261104.0337.1`, macOS 27.0.1, Xcode 27.0 build 27A266a, Swift 6.4, and arm64.
The available preflight records do not contain CPU, free RAM or disk-pressure
measurements. Capacity or toolchain waiting is an unproven possibility.

## Narrow repair

`Tools/Hanlin/host_command.py` now gives the SDK controller its own command
runner. Every output line is flushed to the raw log immediately. Each command
has a separate JSON receipt recording start, PID, its newly created process
group, actual exit code, completion or cancellation, and bounded cleanup.
SIGINT/SIGTERM stop only that command's owned new process group, reap the child,
and preserve remaining output. No process discovery or unrelated-job termination
is performed. Completed command receipts remain distinct from a later cancellation.

The SDK execution receipt starts as `RUNNING`, records simulator boot and build
separately, and reports `CANCELLED` on interruption. It starts no new simulator
cleanup commands during cancellation; the disposable runner tears down those
simulators. A hard kill cannot run a Python signal handler, so the last durable
`RUNNING` receipt must still be interpreted with GitHub's actual conclusion.

The shared `run_xctest` wrapper accepts an optional command runner, preserving
its existing default for other callers. On KeyboardInterrupt it retains any raw
xcresult but starts no further diagnostic commands. Ordinary nonzero test exits
still export their available result diagnostics and still fail acceptance.

A focused control rerun also exposed an existing path-validation defect:
random temporary paths containing `__` were mistaken for Xcode placeholders.
Validation now checks placeholder tokens in the original xctestrun template
before expanding filesystem paths. Unknown tokens, path escape, missing bundles
and unsafe executables remain rejected.

## Verification boundary

The Linux control run passed all **20** tests, including real child-process
cancellation, a TERM-resistant descendant, preserved live output, and a separate
process that remains alive. It also checks ordinary exit failures, cancellation
classification, default/injected XCTest runner behavior, and exact product paths.
The source-bound Windows run passed **18** portable controls and skipped the two
POSIX process tests. The earlier failing placeholder-control run is retained
separately; it is not counted as passing evidence.

These are controller tests, not Apple application acceptance. No new Apple run,
provider call, live account operation or release occurred during this repair.
Actual SDK compilation, all 57 host test methods, and the separate native
consent/create/read/lifetime UI lane remain open.

## Cleanup cancellation review follow-up

Independent review reproduced a second cancellation path: SIGINT/SIGTERM during
simulator cleanup could escape before the final receipt was written. The narrow
follow-up also catches that interruption, reports CANCELLED and finished_at, and
preserves build/test results that completed before cleanup. It does not convert
those facts back into a preflight failure or overall acceptance. The focused
source now passes all 21 Linux controls; Windows passes 19 with the same two
POSIX tests skipped. Original and follow-up logs remain separate in
`controls-cleanup-linux.*` and `controls-cleanup-windows.*`. No new Apple run is
represented by these controller results.
