# Prepared migration: one actual Apple runtime journey

This opt-in reusable workflow builds the distinct native candidate and runs
one new XCTest through the actual Any C runtime, managed HTTP transport and
production prepared-migration client. The existing native, portable and
product suites are retained at their original evidence scope. The workflow
does not rerun them.

## Entry point and exact inputs

Workflow: `.github/workflows/pinkha-prepared-migration-apple.yml`.

| Optional string input | Meaning |
| --- | --- |
| `native_artifact_run_id` | Original run that produced the native artifact |
| `native_producer_commit` | Exact original producer source commit |
| `native_artifact_run_attempt` | Exact original producer attempt |

Leave all three empty for a new native build. Reuse requires all three
explicit values; partial input refuses before download. No `source_sha` or
`source_ref` input is required: both jobs check out immutable `github.sha`
and pass that exact value to their controller. The root-owned manual route
can call this workflow as `prepared-migration-apple`.

The artifact name is
`Any-Prepared-Migration-Native-<run>-<attempt>-<producer-commit>`.
It is unique to an attempt; the upload never overwrites earlier evidence.
The overall original run may have failed because its consumer failed, but
the original native producer job must independently be complete and
successful. The controller reads the exact attempt's GitHub run and job API
responses and preserves those original responses.

## Producer and reuse boundary

`build.py` requires an actual Darwin ARM64 host and the Xcode 27 runner.
It selects the frozen native source manifest explicitly, applies both full
patches to the exact Any/SDK upstream pins, and invokes the unchanged original
`scripts/build-xcframework.sh dist`. The script's original Git blob is
`4ebea60454865884284a6c34a903de00e2f0e53f` at Any
`88fae2e5ae7d0f46d6707567a3123081faa8de9a`:
https://github.com/anyproto/any/blob/88fae2e5ae7d0f46d6707567a3123081faa8de9a/scripts/build-xcframework.sh

The explicit version is `v0.5.0-pinkha.prepared.1`; both iOS device and
simulator slices are ARM64 with minimum deployment version 18.4. The existing
`prepare_native_runtime.py --manifest ... apply/record/install` contract
verifies source paths, Git blobs, staged source trees, archive hashes,
platforms and C ABI headers. The producer uploads the archive and immutable
source/build receipts before the consumer job can start.

The source manifest SHA-256 is
`bff726fc54530af8f3cc0361b5a041d1c46019a5584e877303ef88aaf60c9c44`.
Any and SDK upstream pins, full patch digests and native source trees are
defined by that manifest. The new controller does not select the default
v9 runtime or mutate its manifest.

Reuse verifies original run ID, attempt, repository, workflow path, commit,
successful producer job, original command evidence and archive/build receipt
hashes. The existing installer additionally requires the original producer
to be an ancestor and all native manifest/patch bytes to remain unchanged.
Producer-recorded source hashes are checked against their original Git
commit. Swift-only consumer corrections may reuse the exact native artifact;
they do not relabel any old XCTest result.

## Actual consumer execution

The selected method is exactly:

`PinkhaAnyRuntimeTests/AnyPreparedMigrationRuntimeTests/testManagedPreparedObjectAndBlockSurviveOrderlyReopenAndRejectRevokedOwner`

The test source SHA-256 is
`ba446f2a78f475517439111169cd6d4c33541bff470d848e63b7bf6207d0818f`.
Its package is evaluated with explicit
`PINKHA_ANY_NATIVE_ARTIFACT=verified-prepared-v1`. Combining it with the
authorized-read candidate flag is refused. Native source, runtime enum,
Package flag and the new XCTest are root-owned inputs; this controller
does not edit them.

The original shared `simulator_selection.choose_pair` selects an explicitly
compatible installed iPad / iOS 27 / ARM64 runtime and device type. The
controller creates a fresh UUID-named device and records its exact UDID.
One `build-for-testing` overlaps cold boot; a separate bounded `bootstatus`
must then succeed. Only then can `test-without-building` run the single
selector, with parallel testing disabled and a 900-second method allowance.
Fresh derived data and source-package checkout directories belong to this
attempt. No retained product method is selected.

Current tracked module/controller/helper/workflow sources are hashed before
and after execution. Extra untracked files under product `Sources` or
`Tests` refuse the source closure. The actual resolved dependency revisions
and tracked checkout states are checked before and after execution, as are
all installed native archive members. The retained Swift dependency pins
are TorahInspectorKit `511454e...`, swift-crypto `e8d6eba...` and swift-asn1
`917b472...`; their full revisions are in `contract.PINS`.

## Acceptance and evidence

PASS requires all of the following together:

- Original xcresult summary: exactly 1 test, 1 passed, 0 failed and 0 skipped.
- Exactly one original named terminal for the selected method, on the owned
  UDID with actual iOS 27 / ARM64 metadata.
- Exactly one bounded native observation attachment from that fresh result
  bundle, with completed disposable-account/Space cleanup.
- Six distinct runtime and application-owner generations, exact stage order,
  stable account/Space/store/plan bindings, stable intent fingerprints and
  specification hashes, and the required signed root/bootstrap/block IDs.
- Exact UTF-8 current and historical name/body hashes; original native change
  author and touched-record identity; one current block after retry; unchanged
  native history/readback after the last reopen.
- The explicit retired application-owner refusal and all original untested
  scope labels preserved.
- Unchanged sources, exact dependency/binary identities and completed cleanup
  of the controller's owned simulator.

An attachment alone is explicitly observations-only and cannot supply PASS.
The frozen XCTest does not include a run nonce. Its attachment is therefore
bound through the fresh owned result bundle, exact named execution and UDID,
frozen executed source, native artifact hashes and distinct native generations.
The controller does not invent a nonce or a stronger claim.

Original build/test xcresults, summary/tree export logs, attachment exports,
command timings/PIDs/hashes, original producer API responses, artifact receipts
and source snapshots are uploaded, including failed attempts. The wrapper is
the retained `run_account_lifecycle.run_process`, which terminates only its
owned process group on timeout or cancellation.

The first failure is recorded before bounded result export or simulator
diagnostics. Both owned-device shutdown and delete are attempted with their
own 30-second limits; cleanup/diagnostic errors cannot replace the original
failure. General application stdout or containers are not separately dumped.
The test attaches no recovery phrase, authentication response or managed
token. Commands never log the environment or bearer credentials.

## Scope that remains open

This method exercises orderly native SDK/store reopen inside one XCTest OS
process. It does not inject an OS crash or lost HTTP acknowledgement, test
native ACL mutation or network synchronization, expose inline-file HTTP,
or perform a complete Space import. `file=0`, `networkVerified=false` and
full migration acceptance remain unchanged. The producer builds shipping
candidate native code, while Apple qualification is supplied only by a new
original successful consumer result.

The local `test_controls.py` suite contains only new synthetic controller
controls. Its passing results are not Apple or native product execution.
