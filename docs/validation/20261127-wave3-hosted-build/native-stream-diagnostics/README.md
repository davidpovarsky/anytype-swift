# Native8ac stream diagnostics and bounded process custody

The actual fcc run 45968381393 failed before native input artifact finalization. Its original ready receipt proves the FIFO existed. No Oracle relay was invoked. The later absent output path is post-job evidence. The original first watchdog exception was replaced by a generic message, so its precise cause remains unknown.

The original terminal receipt records unresolved group 37491. A separate later read proved actual ESRCH at 08:55:07 and latched that absence; it was never probed or signalled again.

The exact runner Node executable is /Users/m1/actions-runner-anytype/externals/node24/bin/node, v24.22.1. A bounded probe imported the immutable fcc helper and spawned one owned sleep process. Original ps calls passed; immediately after SIGTERM the original helper received EPERM from kill(-PG,0), discarded the OS detail, and failed its custody check. The child close signal and later separate ESRCH observation are retained. This reproduces a cleanup defect, not the historical watchdog cause.

## Narrow source changes

The action now latches the first observed error before receipt I/O or cleanup. It retains exact typed OS fields and bounded original ps stdout/stderr, actual signal names, phase, and later events. Receipt failure cannot overwrite the first error; sanitized original observations also go to the retained job stderr. No runtime capability or signed URL is serialized.

EPERM remains indeterminate. The original 3-second drain waits may perform only read-only absence probes after indeterminate custody. No additional signal is allowed after that uncertainty; only actual ESRCH permits the absence latch, FIFO cleanup, and artifact finalization. Other OS errors still fail closed. Original 1500-second operation, 600-second FIFO, 768 MiB RSS, 3-second ps, and 3+3-second drain limits are retained.

The source-qualified continuation and original CreateArtifact await both stop when a prior error has been observed. The new focused controller proves no API call occurs for an earlier failure and no stream continuation occurs for a failure while creation awaits. The original eight diagnostic controls remain tied to aa50377; the focused boundary control is tied to the final successor source. These controls are not an upload, Mac stream test, or Apple acceptance.

The registered workflow changes only its seven literal checkout references to a fresh diagnostics-owned path. Every other job and reusable reference remains byte-identical. Original failed checkouts and receipts stay preserved. The source archive producer, Oracle relay, native/source/framework admission, original Actions library implementation, transport, and native/App inputs are unchanged.

Root reviews and publishes this source before any dispatch. The pending plan remains false-ready and binds a future immutable control commit; every other plan field is the original fcc plan. Root owns a single subsequent dispatch/ready/relay envelope.
