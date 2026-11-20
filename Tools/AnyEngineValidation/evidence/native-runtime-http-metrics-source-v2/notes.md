# Runtime HTTP metrics revision 2: callback performs no diagnostic I/O

Revision 1 is preserved under native-runtime-http-metrics-source-v1. Root
review identified that writing stderr synchronously inside didFinishCollecting
could itself delay URLSession completion when log-sink blocking is among the
unresolved failure boundaries. Revision 2 removes that observer dependency.

The callback captures its own timestamp and copies only allowlisted scalar
values into a RuntimeCollectedMetrics value. RuntimeMetricValue is an explicit
Sendable enum of integer/double/bool/string/missing, with no Foundation object
case. A short lock protects the callback count and one retained snapshot,
bounded to 16 transaction records. The callback performs no JSON conversion,
output, await, new task scheduling, or session operation. It retains no
URLSession, URLSessionTask, response or metrics object.

After the original shared-session await returns or throws, finished/failed
copies count and snapshot together under the lock, releases the lock, then
converts and emits one terminal record. Callback timestamps remain separate
from terminal/log timestamps. A callback still in progress, absent, or arriving
later remains unknown at that observation. There is no callback wait or extra
async task to force metrics delivery.

Output schemaVersion 2 keeps the PINKHA_RUNTIME_HTTP_METRICS prefix. Start and
end/error records are emitted by the helper; there is no callback-emitted
metrics phase. The terminal record has metricsAvailableAtEmit, the coherent
metricsCallbackCount, and a metrics value or null. Stored snapshots include
total and omitted transaction counts. No headers, URLs, content, tokens,
account data, or NSError descriptions/userInfo are logged.

The original test source is exactly restored by removing the helper and
reversing the one call-site wrapper. The call-site is unchanged from revision 1:
same URLSession.shared, URLs, headers, default timeout, default authentication
and redirect handling. All 3 test names and 27 original XCT calls remain.
No native engine or production Swift source changed.

Validation: full test iOS-target syntax parse exit 0 in 0.25 seconds (expected
Windows-sysroot warnings); exact primitive observer Swift 6 typecheck exit 0 in
16 seconds with no diagnostics. Source remained unchanged. Actual Apple SDK
compilation/runtime is pending.

Diagnostic pre-request and post-await output can still perturb workflow
timing; this change specifically removes logging from the URLSession callback.
No instrumented success may erase the historical Apple57/Windows failures or
be called their root-cause fix. No HTTP/native execution was performed here.
