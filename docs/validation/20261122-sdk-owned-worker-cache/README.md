# SDK single-lane process ownership and compilation cache

The original SDK run [44956239736](https://github.com/davidpovarsky/anytype-swift/actions/runs/44956239736) was cancelled during Debug compilation. Its execution receipt records BUILD, with the 21 shared-editor methods and 7 acknowledgement methods NOT_RUN. No compiler diagnostic or test terminal had been observed in this SDK run. The separate Release run proved the same old table fixture's compilation defect; commit c338989d4c changes its two fixture type lines, preserving all eleven test bodies.

The cache step was green but did not save a cache. The actual gtar warning says Index.noindex changed while it was read; the save ended with exit 1. This corrects the earlier status based on the step conclusion. The three retained lines are an exact excerpt of decoded job 137004880241 logs, lines 851–853, not the entire job log.

## Correction

Only the existing hanlin-native-shared-editor lane is wrapped in a bounded, owned worker process group. It invokes the original lane with the same arguments and selection. It uses the existing batch process cleanup, writes a separate supervisor receipt, preserves execution.json unchanged, and deletes only the original preflight simulators after matching source/run identities, names, types, runtime and newly created UDIDs. The worker has the existing 105-minute budget inside the 120-minute step.

The existing process helper now also records successful owned-group cleanup on its cancellation/timeout paths; the process behaviour is unchanged. The wrapper additionally waits at most ten seconds for the owned PGID to have no live non-zombie members, using only numeric PID/PGID/state observations. A SIGKILL delivery receipt alone is insufficient. SDK cache publication requires both the hash-bound cleanup receipt and this separate process-group quiescence result. Missing or incomplete cleanup denies cache publication; cancelled or failed product tests never become passing acceptance.

The v2 cache contains Build, SourcePackages and compiler/module caches, excluding Index.noindex. Because actions/cache includes path selection in its version, an old-layout restore is attempted only if no v2 exact or prefix cache matched. The same architecture, Xcode, configuration and dependency key remain mandatory. This retains useful prior compilation work. Restore/save v2 path lists are identical. Actual future Apple cache save remains unproven until the replacement run.

## Focused verification

Linux x86_64, Python 3.12.14. Five new real-process integration controls cover success, cancellation, timeout, refusing false success and refusing cache publication without cleanup. Actual workers and TERM-ignoring descendants are stopped; an unrelated process remains alive. The original execution receipt hash is preserved.

Initial attempt: three passed; cancellation and timeout controls exposed a missing cleanup receipt field (not surviving processes). One observability line was added to the existing helper, then only the two affected failed controls were rerun: both passed in 1.356 seconds. The other three successful controls are retained from their unchanged paths. Both raw logs are preserved, including the initial errors. Peer review then identified that signal delivery alone did not prove descendant termination; the bounded PGID observation was added. Because it affects every supervisor/cache path, all five new controls were rerun once on the final wrapper: five passed in 2.068 seconds. This final original log is also preserved. Syntax and exact cache path/fallback conditions also passed. No old product/native/UI suite was rerun, and this is not Apple app acceptance.

The next SDK execution remains pending while the shared Kit authority/cache correction is integrated. Its exact lane remains editor 10 methods/15 cases, table 11 methods/14 cases, acknowledgement 7, native preparation 1 and UI 1. Broad SDK06 and full iPad acceptance stay open.
\nPrimary ps interface reference: https://github.com/apple-oss-distributions/adv_cmds/blob/main/ps/ps.1 (numeric pid/pgid/stat fields; empty headers; all-process observation).\n