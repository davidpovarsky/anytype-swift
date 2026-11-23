# Native9 attempt 1: hosted runner allocation failure

The actual GitHub run 45159946802 / attempt 1 at source `1ec511b046fff1c46aaeb8425b98932a19400ad2` ended **failure**. Its one job was **cancelled**, with `runner_id = 0`, no assigned runner name, zero steps and zero artifacts. The original check annotation is preserved byte for byte in `raw/CHECK_ANNOTATIONS.json`:

> The job was not acquired by Runner of type hosted even after multiple attempts

No checkout, producer, Go compilation, original import execution, fixture leaf or final stability check ran. The new native scope is **0 PASS / 0 FAIL / 0 SKIP / 9 NOT_RUN**. The 87 compiler inputs remain a reviewed source requirement, not an observed compiler closure. There is no native artifact ZIP to authenticate or restore. This is an infrastructure allocation result and supplies no reason to change the native source.

## Authentic evidence and ownership

`raw/RUN.json` is the sole observer's normalized complete API object. `JOBS.json`, `CHECK_RUN.json`, `CHECK_ANNOTATIONS.json` and `ARTIFACTS.json` preserve the original successful API response bytes. Acquisition receipts bind the direct queries and hashes. The observer ended normally at 11:07:19 UTC after seeing the actual failure; its process was absent and its exclusive file lock was independently acquirable. The active source worktree remains clean at the immutable failed source.

The copied `source-review/` records concern source admission and preactivation reviews only. They are not native test or runtime results. No previously passed 36-leaf archive selector, endpoint or lifetime component was replayed. An initial docs-only worktree population assertion and its narrow index initialization are retained in `raw/RESULT_PREPARATION.json`; no native source or raw evidence was changed by that preparation.

## Continuation boundary

The frozen job condition admits only `github.run_attempt == 1`. An ordinary attempt 2 cannot be treated as a supported continuation. `RETRY_SOURCE_POLICY.md` records the exact condition and the smallest proposed source-identical continuation for root review. No continuation commit, branch activation, redispatch or rerun was performed while sealing this packet. The original failed run remains retained and linked.

Run: https://github.com/davidpovarsky/anytype-swift/actions/runs/45159946802
