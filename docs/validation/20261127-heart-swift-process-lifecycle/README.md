# Actual owned-process lifecycle qualification

The five real Python controls passed on Oracle on 2026-11-27, job `job_be3a8fe2bbdc`. The control sequence took 0.778 seconds and the controller exited zero. This qualifies command ownership and cleanup for the isolated Swift generation and client controllers; it makes no native-engine, Swift-client, or Apple acceptance claim.

The exact controller and helper are already published in commit `26d48284e4476a52e5d8c2135e442485891c6849`. Their SHA-256 pins and the original immutable receipt location are recorded in `source-pins.json`. `result.json` is an unchanged copy of the original receipt, SHA-256 `040ffa3fcf93094369e24928732aeba9eb10fdb673db76ab7540a887748aa27d`.

| Actual control | Required observation |
| --- | --- |
| Normal child with inherited blocked termination signals | Child received unblocked SIGTERM/SIGINT and exited zero without forced cleanup. |
| Started-journal write failure | Original injected OSError retained; only the owned group terminated. |
| Leader exits with a live descendant | Original residual-descendant error retained; the descendant was closed before the leader was reaped. |
| Controller SIGTERM | Original signal-15 error retained; owned child terminated. |
| Controller SIGINT | Original signal-2 error retained; owned child terminated. |

All five process groups were positively absent at completion, and every command had an empty cleanup-error list. The failed child scenarios are deliberate negative controls: their original errors and termination signals remain visible in the receipt. No compiler, native account, or engine was invoked. Runtime resource floors remained root 2 GiB and development 512 MiB.

The canonical generator and the seventeen Swift client methods have separate receipts and acceptance gates. This control result must not be represented as their execution or as validation of the separate FullSpace source checkpoint.
