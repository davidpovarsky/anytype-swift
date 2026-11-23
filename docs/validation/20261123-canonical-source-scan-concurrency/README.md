# SDK06: concurrent fresh source inventories

## Actual failure retained

GitHub run [45181802668](https://github.com/davidpovarsky/anytype-swift/actions/runs/45181802668), attempt 1, consumer source `1f56bc4fbb2b51790d309d593aa8e70936410c50`, used Hanlin `32da9e314e22bbf22391fcf8902302acfbb281e2`. Its original preparation method and original native UI method each passed (1/0/0), with all 22 native receipt checks true. The overall route failed because the same-process runtime observation did not complete.

The authenticated original observer saw `AWAIT_READ_CONSENT` from PID 74038. Its fresh installed/build inventory step took **63.220237625 seconds**, exceeding the existing 60-second mapping window before the subsequent process query could start. Both trees had 112 carriers and 812,517,040 executable bytes; their original hashes matched. There was no successful ps/vmmap observation in that journey. The source scan stage duration includes lookup, traversal and hashing; it does not separately measure those costs.

Artifact 14826745894, 16,607,730 bytes, SHA256 `5cd72a268e7fec21907cfd82a2fe0353daf58e0b8aaa3936a6703a28a9b47ed8`; inner ZIP SHA256 `e782784146f3e2efe28a526255ada00dafc6a112c8afbeba527a658804798278`. Both archives passed CRC validation. The full raw originals and all 177 member hashes remain in this worktree's ignored `build/sdk06-live-observer-45181802668/`; this directory retains the original observation and exact result summary.

## Scoped correction

The existing `installed_runtime_source` function now executes its two independent `code_carriers` scans concurrently through a two-worker executor. It reads both inventories afresh and joins both workers on success or error. The canonical inventory function, classifications, alias checks, per-file hashes, main executable checks, equality comparisons and output manifest are unchanged. No cached hash substitutes for either scan.

The native observer is byte-identical to 1f56bc4f: the 60-second mapping window, 420-second total window, command timeout, fixture/session/PID/process-start validation, native receipt checks, original UI method and final hierarchy validation are unchanged. Production app, native Heart and SDK sources are unchanged.

The before/after control tests prove overlap and exact manifest equality on an actual 112-carrier filesystem fixture; they do not measure Apple performance. Native success requires the original UI/runtime conjunction to execute again.

## Executed controller evidence

- New overlap control: sequential original failed with `BrokenBarrierError`; the corrected two-control selection passed **2/2** in 0.746 seconds. It verifies complete fresh manifests, changed bytes, escaping carrier rejection, and zero remaining source workers.
- Affected existing `ExistingProcessMappingControls`: **7/7** passed in 0.045 seconds. These cover bounded no-launch observation, original probe behavior, wrong PID/missing entrypoint, executable/process-start replacement, altered binary/marker, actual UI boundary PID and changed post-UI code.
- Admission controls: **2/2** passed in 1.356 seconds. Current provenance reconstructs the exact previous source; changed source, named result or trace cannot inherit the proof.
- Other **62/69** original native controller methods retain their existing source-bound evidence; they were not rerun. The catalog now points the affected seven to their new actual log. Historical timing/diagnostic qualification remains separately identified.

`qualification.json` binds the new source and test declarations to original logs and exact inverse changes. `admission-readback.json` is a readback of this evidence gate, not test execution. The existing workflow, branch admission and Apple selections are unchanged.

## Native disposition

Current corrected native runtime acceptance: **NOT_RUN** until the one existing `hanlin-native` route executes on this source. Historical UI/preparation PASS remains valid for its source and scope. It cannot qualify a missing mapping after the original process has exited. No task completion, release, provider/model, physical-device or every-launch acceptance is claimed.


## Source preservation

The staged source-retention gate passed against its pinned baseline `586c98bcc17dee425664224e508fc0e8df277678` (checked tree `3f1a556cc6c87fcee197bc292aadb70803f455ef`): 5,790 baseline protected files, 6,275 current files, 5,692 baseline files unchanged, zero inventory errors and zero unreviewed changes. The existing reviewed extraction mappings remain valid. The new change contains only downstream controller code, focused controls and evidence; app, native UI tests, Heart, Hanlin SDK lock and live observer source are byte-identical to `1f56bc4f`.
