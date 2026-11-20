# Original editor framework — attempt 2

The actual GitHub run **44781744925**, attempt **2**, failed on the unchanged frozen source **dc3ac07cec63692c8b84877a56e3e3fd60a4c667**. Job **136464900723** ran from **17:50:44 to 18:00:17 UTC** on 20 November 2026. The same owned simulator `bootstatus` gate failed before either the genuine framework or its external consumer was compiled.

## Authenticated result and scope

Artifact **14656015255** is **70,666 bytes**, SHA256 **ddcfe0f39d63195cbdbe16379c6c858f7259189d86d9659d6ae48dc36d84d23b**. Its one outer ZIP entry and all **28** nested entries pass CRC verification. The complete original ZIP, all raw commands/stdout/stderr, execution/source reports, API metadata and full job log are sealed here. Download credentials and temporary storage URLs are excluded.

Actual Mac Python source/filesystem/receipt controls passed **44/44**. Actual Apple Swift 6.4 and simulator SDK27 were observed, original Heart producer/slices were admitted, and the original Hanlin 407-file snapshot was verified. These facts do not establish that the new framework compiled. Framework build, separate consumer build, resource-language execution, app runtime and editor UI are all **NOT_RUN**. The editable mount API remains **NOT_EXPOSED**.

The before/after source snapshots are byte-identical. Every one of their 22 source inputs matches its independently fetched canonical Git file, all 2237 original Swift source names match the Git tree, and the three original application/resource/package trees agree. The full original source list includes AppScene; the additive target's original exception still excludes that sole entrypoint. No target or source membership changed in this attempt.

## Comparison with attempt 1

| Observation | Attempt 1 | Attempt 2 |
|---|---|---|
| Frozen source | dc3ac07c | dc3ac07c |
| Job | 136445938068 | 136464900723 |
| Artifact | 14652169203 | 14656015255 |
| Owned boot command | Exit0,4.586s | Exit0,6.162s |
| bootstatus configured bound | 180 seconds | 180 seconds |
| bootstatus outcome | Timeout, return -15 | Timeout, return -15 |
| Recorded elapsed, including termination | 183.325s | 184.898s |
| bootstatus stdout/stderr | Both empty | Both empty |
| Framework/consumer compilation | NOT_RUN | NOT_RUN |
| Runtime observations | 0 | 0 |
| Owned-device deletion | Both exit0 | Both exit0 |

The source snapshots across attempts differ only in `run_attempt`. Both original inventories showed 40 shutdown devices before the new owned devices were created. This does not establish the reason for the subsequent timeout: neither artifact includes a host-load or CoreSimulator service diagnosis. The previous full 70,669-byte authenticated ZIP is retained for direct comparison, rather than borrowing a successful result from another source.

Cleanup retained the exact owned iPhone/iPad identities. The unused iPhone shutdown reported the original already-Shutdown error149; deletion then returned0. The iPad shutdown and deletion both returned0. This is evidence for those owned commands, not a host-wide process-cleanliness claim.

## Source findings for a separate candidate

The unchanged driver currently boots before compilation. Its subsequent framework build, source/dependency checks, actual public symbol graph, copied-resource verification, external consumer build and codesign checks do not themselves read an installed simulator app or data container. A narrow candidate can move the same 60-second boot and 180-second bootstatus pair to immediately before install/launch, after those compilation checks. It must keep the exact selected simulator, build arguments and all final runtime gates. This would permit independent compiler evidence to be attempted when the explicit boot gate is blocked; it does not qualify later runtime or increase the timeout.

A second deterministic source defect is independent of the timeout: `execute()` assigns the simulator selector to `destination` at line187 and uses it for the framework build. The dependency-notice copy loop reassigns the same function-local variable to a filesystem path at lines216–219. The later consumer build passes that overwritten value to `-destination` at line280. Any nonempty notice loop triggers this dataflow error. Neither actual failed attempt reached it, so this packet does not describe an observed consumer-build failure. A separate notice-output name preserves the simulator selector and original compiler arguments.

`DRIVER_REVIEW.json` records both findings. No source correction, rerun, budget change or ref rewrite is performed by this evidence packet. Root authorized preparation of a separately reviewed v3 candidate after this seal.

## Offline replay

Run `python VERIFY_PACKET.py` from any copy of this directory. It checks every sealed file, complete outer/nested archives, metadata/head/attempt/job, all 22 canonical source bytes, 44 actual Python leaves, before/after source, exact 180-second failure, owned cleanup and direct attempt1 comparison. It performs no Swift build, simulator command, network request or acceptance rerun.
