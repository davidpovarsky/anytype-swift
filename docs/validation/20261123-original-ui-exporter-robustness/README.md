# Preserve original UI export failures and independent evidence

## Original failure remains open

Original product run 45087682296 at 7293e4fd0bcabdcdb643d5768b777b8e87ff1b73 is unchanged. The original artifact SHA256 is 6625e363c7cd9e4c256dfc116073687228db7a0564ae6f2aed8213eca089616b.

The second diagnostic export, run 45097808288, failed when the Swift process terminated with an uncaught error. Its original job 137441440808 and artifact 14784468942 remain archived under /mnt/development/projects/diagnostics/original-ui-timeline-export-20261123/watcher. The artifact ZIP SHA256 is 026947fff0c5f7e5098e2c157a58a697f13b1b44d93d60025bf20630133669e6. The old coordinator retained only the final 4000 stderr characters. That crash tail does not establish which media or time guard rejected the input. This change makes no retrospective cause claim and does not convert that failure to a pass.

## Bounded correction

The Swift renderer returns a typed JSON failure, observed recording duration, video-track start/duration/end, and each requested/actual frame time when available. Each exact frame has its own outcome. It catches an individual frame error and attempts the other original frame. The coordinator invokes each pinned recording independently, so an unsupported recording does not suppress the other recording or either sanitized backup operation.

Complete stdout and stderr are written directly to six exact owned process paths (two streams and one manifest per recording). The workflow retains these separately from selected visual evidence. Raw recordings, private render plans, backup screenshots, and full backup trees remain outside both artifact allowlists. The process manifest records byte counts and SHA256 without copying stream contents into the selected receipt.

Both original case identities, four named exact frames, and both backup groups must pass for overall export success. Missing or failed results produce FAIL while independently valid results remain inventoried. The two media processes share the original 180-second total deadline. No duration, requested/actual timestamp, safe post-onboarding window, backup sanitation, or file-size guard was relaxed. This does not choose an arbitrary nearby sparse frame.

## Actual validation and limits

Four new controls are qualified on the current source: three unchanged passing methods from attempt 1 and the one corrected timeout-fixture method from attempt 2. The initial 3 PASS / 1 FAIL log and exact original fixture source are retained. The fixture had assumed that subprocess.TimeoutExpired.timeout equals the configured 0.3 seconds exactly; Python reports the remaining wait budget after process setup. The fixture now requires the recorded budget to be positive and at most the configured timeout. Product code was unchanged between attempts, and only this failed method was rerun.

The controls execute real child processes for long stderr, invalid JSON, nonzero exit, and timeout preservation; exercise coordinator failure isolation; and reject incomplete frame or backup outcome sets. They do not claim to validate AVFoundation decoding.

Swift frontend syntax parsing passed on Oracle. AVFoundation typechecking and media execution were not performed. The five prior timeline/privacy controls and all product tests were not rerun. The unchanged functions and old test module are byte-identical to c42acd98147b54f89dba7ef615b22ad561e6f94e. The generic workflow route is also byte-identical.

No new Mac export was dispatched. Original raw recordings and numeric backup attachments were recovered independently from the original Oracle archive, so no new queue is needed merely to obtain that existing evidence.

## Read-only observer review

Commit be938dd8d860b4be3b8c8a407ba8cd22ed9a3f40 was reviewed without tests or edits. Its retry branch is limited to the exact owned simulator data-container argv and a timeout bounded by COMMAND_SECONDS. The original first failure remains recorded; the observation deadline is never reset; cancellation is checked before another subprocess; and a failed lookup never reuses a prior path. No blocking regression was found in that added branch.
