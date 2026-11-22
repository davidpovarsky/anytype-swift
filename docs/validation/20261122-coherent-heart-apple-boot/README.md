# Coherent Apple cold-boot continuation

The original run `45043203916` at
`e5f4697c9e8cbda7448e9cba59e64de5535ec28e` verified the two original framework
artifacts from build `45035194823`. It selected the compatible iPad mini A20 Pro
and iOS 27.2 pair, created the owned simulator and requested boot successfully.
Readiness failed before any XCTest. The original bootstatus log is empty; the
controller did not record that command's error. A subsequent shutdown timeout
replaced it in the final receipt. The first failure's exact cause therefore
cannot be recovered from that receipt.

The original 113-file proof ZIP has SHA-256
`6de35e17b02a028451e365705cbc0f11813d0050200add6e4eed74b285749f66`.
Its original files remain failure evidence. They do not prove Apple execution.

## Narrow orchestration repair

The host now requests boot, performs the required current Swift harness
`build-for-testing`, gates readiness once with the existing 180-second command
allowance, then invokes the one selected XCTest with `test-without-building`.
The build and test use the same scheme, destination, derived-data directory,
dependency cache and selected test method; their result bundle paths are
distinct. No XCTest runs during the build. No boot retry, new simulator fallback
or original Go framework rebuild is introduced.

This ordering follows the already successful Any bootstrap in run
`45031455896`: its same iPad mini/iOS 27.2 simulator was requested before the
required App build, and its later original bootstatus output reports an already
booted device. That evidence supports overlapping the necessary compilation
with cold boot. It does not prove the next boot will succeed or establish why
the previous readiness command failed.

Every command now records its allowance, start/finish timestamps, elapsed time,
error type/message, and original log length and digest, including empty logs.
On failure, bounded device-state and owned-UDID system-log diagnostics run before
cleanup. Shutdown and delete are each attempted independently with 30-second
command allowances, using the existing owned-process-group termination helper.
That helper has its own bounded termination waits. Diagnostic or cleanup errors
cannot replace the primary error. Cleanup outcomes are recorded separately as
complete or incomplete and never imply that an unobserved device deletion passed.

Admission requires the sole successful selected test, its exact preceding
successful build command, and the ordered boot/build/readiness/test sequence on
the actual owned destination. Original framework receipts, binary hashes,
native139 source, shared Swift modules, assertions, proof replay and all other
admission gates remain unchanged. The legacy combined `xcodebuild test` branch
remains available with its original checks.

## Evidence retained and new controls

`new-orchestration-controls.log` is the original output from **two new Python
controls, both passing once**, with zero failures or skips. Apple subprocesses,
Mach-O inspection and xcresult replay are substituted in these controller
checks. They are not actual simulator, native or Apple acceptance.

The first new control injects a readiness timeout plus failures in both
diagnostics and both cleanup commands. It proves that the primary error and
empty-log digest survive, build precedes readiness, no test or retry starts,
and both bounded cleanup attempts occur. The second exercises the new admission
branch positively, then rejects another build output directory, wrong order,
wrong destination, failed build, extra test method and a Boolean test count.

`new-orchestration-controls.json` binds the exact tested source/dependency bytes
and the eight immutable native input files used only as synthetic-controller
fixture inputs. Existing controller methods, Go tests and XTests were not rerun.

The original ten Python controls remain retained with their original report and
raw logs. `orchestration-review.json` pins the exact two changed file hashes and
checks their original dependency scope:

- For `run_host.py`, imports, top-level declarations and the complete executed
  `fields`/`qualify_t5_wire` dependency AST remain identical. Only bodies outside
  the old controls' execution scope changed.
- For admission, the newly added `test-without-building` branch is projected to
  its unchanged legacy `else` statement. The entire resulting module AST equals
  the original. The four retained controls use the legacy `xcodebuild test`
  input; their full executed branch remains unchanged.

All other original dependencies and inputs retain their exact hashes. The three
previously reviewed Git-versus-tested terminal-LF pairs remain the only newline
exceptions. The new controller test ran with those original tested bytes; final
retention verification also succeeded with their exact canonical Git bytes.
`retention-verification-tested-inputs.json` and
`retention-verification-canonical-git-inputs.json` distinguish those observations.
`retention-negative-checks.json` records six additional static rejection checks,
including changed old dependency ASTs even when a synthetic candidate digest is
adjusted. These are verifier checks, not repetitions of the test suites.

The CI retainer verifies the original ten and these two new raw method results
without executing them again. The existing selector's five previously observed
controls remain explicitly labeled as an observation without a raw unittest
log. Actual compatible boot and the new one-method XCTest are still required.

## Acceptance boundary

No production or fixture framework was built by this repair. No simulator was
created by the new local controls. No new Apple method has executed yet. Native
production139 proof and both separately built binary artifacts retain their
original origins; the next current host run must supply the real execution
proof before admission or task completion.
