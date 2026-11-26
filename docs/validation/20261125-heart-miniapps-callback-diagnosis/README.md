# Heart MiniApps callback diagnosis

The retained original warm-Return result is not available after an observed storage loss.
The account seal contains hashes and account bytes, not the original XCTest log/xcresult.
Do not reconstruct or count a PASS from that seal.

Source inspection identified two distinct hypotheses requiring actual reproduction:
1. A returning scene may not yet be foregroundActive, so an existing editor is not selected.
2. A cold URL can arrive while the account/lifetime is not ready, and the current handler consumes it.

This change only records opt-in simulator lifecycle/routing/application phases. It does not
change any route, account check, result, ACK, callback, native operation or assertion.
It records process identity and booleans, no source content, account/space/object IDs or URLs.
The bounded private JSONL is under the actual app cache/PinkhaMiniAppsCallback/observations.jsonl.
The next original warm/cold test uses the other owner's real OS URL delivery and PID assertions.
Native/UI verification is NOT_RUN for this instrumentation until the next original app build.
