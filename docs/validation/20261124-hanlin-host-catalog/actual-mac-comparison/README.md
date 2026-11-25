# Actual Hanlin catalog continuation and cancellation comparison

The original production engine reproduced the missing second provider request in one actual Swift Testing method. The reviewed candidate then passed that same unchanged method and a second cancellation method on the Scaleway Mac. This is component evidence; the original Native App Hanlin journey is still a separate acceptance gate.

## Exact source and execution

- Baseline: f48bfc6596eebe491c982bbecbd01939bbce1ed1, original production 116cc6be0654a5d11bc56ba00e0310031107ee36, only the regression test added.
- Candidate: 6bd6036dbca16c969689a5722550a54bebc1e851. Only the reviewed engine file and the new cancellation test were applied after the original baseline completed.
- Original regression file SHA256: 1f5f18df56420a7b9b41acfb67f9995d8c4596cc42609c75337f542fcf1de65a; unchanged in both runs.
- Apple Swift 6.4 / Xcode 27.0 (27A266a), arm64 macOS. A separate tiny test harness imports the original HanlinChatCore product with all seven declared AISDK products intact. The original Platform package is unchanged.
- Exact four dependency pins and the complete 222-file baseline / 223-file candidate source census were checked before and after. The four existing setup files are separately bound by exact path and SHA256. No broad generated-file exclusion was introduced.
- One owned swift test -j1 command at a time, bounded runtime and memory monitoring. No simulator, App, production-provider request or native write was involved. Both commands exited; the final process scan found no owned process.

## Actual result

Baseline completed at 21:45:39 UTC on 24 November 2026: exactly one original method, failed as expected, zero skips. It observed one request, one tool execution, two catalog lookups and only step 0, rather than continuing the original empty tool result to step 1.

Candidate completed at 22:03:24 UTC: exactly two methods passed, zero failures/skips:
- restoredCatalogContinuesTheOriginalEmptyToolResult()
- cancellationDuringFinalCatalogLookupStopsBeforeAnotherProviderStep()

The cancellation control requires cancellation during the final catalog lookup to stop before another provider step. The unchanged regression checks original tool call identity, empty result fidelity, a single tool execution and both step indices.

The first fixed preflight rejected four pre-existing local setup files before applying any candidate or compiling. That failure is retained in fixed-preflight-failure.json; the corrected controller binds those four exact bytes. The original failed baseline XML, log and receipt remained unchanged through the fixed run.

Original XML/receipts, exact source and harness manifests, controller sources and verbatim test log excerpts are retained here. Full verbose original logs remain in the custody directory recorded in summary.json; custody.json binds their hashes. No old failed App workflow or passing SDK06 acceptance result was rewritten.
