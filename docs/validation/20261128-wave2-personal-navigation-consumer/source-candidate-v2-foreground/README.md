# Personal navigation foreground successor

Status: source only; not compiled or run.

This separate successor closes NAV-CONSUMER-FOREGROUND-01. A successful read can be accepted while the real mounted surface is not foreground. The existing guard correctly declines the first observation in that state. The existing foreground notification now explicitly calls `AnyDocumentPresentation.didBecomeActive()`, which delegates to the same readiness/once guard. It preserves the mount token, attempted state, current read owner and every authority fence. It does not reload, remount, retry, manufacture an observation, or hide work inside MiniApps handling.

The complete source-candidate-v1 packet remains unchanged. Four v1 product bodies are reused byte for byte; only Document gains the lifecycle method and the original DocumentView gains one call. `literal-replacements.json` reverses these two complete successors to v1 Document and the exact current bae View. The original 26 replacements remain separate and unchanged; the coherent proposal now has six product files and 28 literal replacements in total.

The exact source base is `bae68131a20fd7ef351c2b4034ebdf520c6d3b39`. The d1 Host contract is present there. The new authoritative nonoptional Runtime `expectedNetworkID` and its bound-start native ABI are still required as an independently qualified dependency. This packet does not claim bae alone is a complete compiling/runtime tuple.

Focused consumer test source is being prepared separately in the existing hosted renderer test input. None of the five existing renderer methods is rerun or credited to this consumer. Real scene background/foreground return, Home Library read/set/unset, cold navigation, and opposite App/OS language behavior remain explicit acceptance requirements. No Package, PBX, controller, selection gate, Native contract, runtime flag, account, or final branch is changed here.
