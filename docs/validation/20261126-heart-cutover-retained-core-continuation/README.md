# Same-source core continuation

The third real compile stopped at the unchanged 2 GiB emergency floor after 320.086 seconds. Its owned process group is absent, its complete 4,879-file source is unchanged, and it produced no test binary or account invocation. The original outcome remains FAIL.

The successor reuses that exact materialized source and warm cache. Only new compiler scratch, output binary and the later fresh test account use a distinct root filesystem directory. It requires independent initial allowances of 768 MiB for cache growth and 1,280 MiB for scratch/binary growth, in addition to an unchanged 2 GiB floor on each filesystem. Estimates are not measured peaks and do not admit execution when current headroom is insufficient.

Three actual bounded guard controls passed: secondary-volume preflight refusal starts no child; a later secondary-volume floor stops only the current owned child; a failed second-volume observation also stops that child rather than leaving it running without its floor. Original child exit and log remain preserved, all owned groups are absent, and no historical process group is signalled.

The complete original native invocation and outcome-validation block is byte-identical (2,318 bytes, SHA256 92228e3ab9fdea8ec4b11c28e9ba4cedf521a50a0ceddf457381b39032c40010). The prior failures, original full source and original empty private directory are independently admitted. This checkpoint executes no Go test, native account operation, App or slice build.

A separate go -n diagnostic printed the remaining 93 Go and 104 native compile commands. Its actual child exited zero with an absent process group, but its outer reporting script called an unavailable cleanup method and remains a collector failure. It is only planning evidence and grants no native acceptance.
