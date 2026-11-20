# Read-only review of the retained Windows Property15 auth timeout

**Conclusion: no root cause or supported production transport fix was established.**
This is a review of current frozen source and an already-completed diagnostic trace.
No new HTTP request, runtime experiment, native source change, timeout/header change,
toolchain installation, or retry was performed. Historical failures remain failures.

## Exact retained failure

The timestamp-only diagnostic recorded GET /v1/auth request
737A8849-8A6B-454E-B66F-E2FE6F56A64E beginning at
2026-11-20 04:50:30.560 UTC. Its entire URLSession.data(for:) await ended
with NSURLErrorDomain -1001 at 04:51:00.573 UTC, reported monotonic elapsed
30,016 ms. Wall-clock and monotonic offsets are retained separately.

There were seven raw auth awaits active at that begin. All six others returned
HTTP200 within 6–10 wall-clock milliseconds of it. Another 34 requests began and
41 responses completed before the failed await ended; the last completed at
+42ms. The trace totals are 778 begins, 777 responses, 1 error. PropertyProbe
contains no SSE subscription. These facts do not support a whole-session serial
queue deadlock or sustained occupancy by seven unfinished business requests.

## Client control flow

AnyHTTPClient.requestJSON performs a raw account check, cancellation checks,
the caller's authorization closure, the business raw request, then another raw
account check. checkAccount calls raw(GET auth) directly; it does not call
requestJSON recursively. The configured request timeout is 30 seconds.

AnyApplicationSession's lease validation checks activity, awaits a health
request, then checks the same generation again. That health request has the
default empty authorization closure. Its auth→health→auth chain therefore
terminates; it does not re-enter lease validation. Actor calls suspend at await,
and the reviewed path has no semaphore or synchronous wait for its own child.
No revoke/drain or session invalidation was observed in the failing business
path. Cleanup follows the error.

PropertyStore.catalog intentionally evaluates type proofs in batches of at
most 8 tasks. Each proof performs lease checks, which explains parallel auth
requests. The count 7 alone is not evidence of a connection-limit defect.
The HTTP client owns one private ephemeral URLSession; its redirect delegate
immediately refuses redirects. No explicit invalidation, custom data callback,
shared app lock, or manual response parser surrounds raw(data(for:)).

PropertyStore.apply retains the native accepted fence, then attempts a full
readback. A failed readback cannot produce verifiedCurrent or an Undo receipt.
The observed exact-version-readback assertion failure is consistent with that
honest uncertainty; it is not evidence that the already-acknowledged native
property mutation failed.

## Native auth and response boundary

The managed authStatus handler reads accountID through a short engine-gate
counter admission, constructs a small response, and returns c.JSON. It does not
take authMu, boot an account, enumerate stored accounts in managed mode, query
the SDK, or access document storage. The auth route is exempt from the
long-lived request gate and its teardown write-deadline callback. The gate
mutex is released by enter/leave; close returns its drain channel without
holding it. No circular lock wait was found in this path.

Echo 4.13.4 serializes JSON through json.NewEncoder(c.Response()).Encode.
Response.Write forwards to Go's ResponseWriter. This can accept the small
body into buffers. httpLogMiddleware logs status/duration after the handler
returns, but before Echo ServeHTTP returns to net/http. Go 1.27.1 then executes
finishRequest: mark handlerDone, flush the response buffer, close chunk
framing if applicable, and flush the connection writer. Its small-body path
can derive Content-Length from the buffered bytes after handlerDone.

Therefore an Info log 200—even with a near-zero duration—is handler/encoder
completion evidence, not proof of completed socket flush, byte delivery, or
URLSession completion. The retained native metadata has 32 auth 200 candidates
near this begin, including one at the same millisecond, but no shared
client/server request identity establishes which one belongs to the failed
await. The failed await itself yielded no response headers/body to the trace.
The completed nearby auth replies used Content-Length 187; that cannot be
transferred to the unseen failed response as a proved framing fact.

## Bounded classification

No application-level recursive authorization, actor/lease wait cycle,
concurrent SSE cancellation, malformed custom auth framing, or native
storage lock has been established as the cause. The remaining boundary
includes scheduling/dispatch of this individual URLSession task, its
connection and response delivery, and completion processing. The retained
trace and source do not distinguish these alternatives.

The installed FoundationNetworking binary is fingerprinted in the earlier
runtime receipts, but an exact corresponding source revision has not been
proved. Do not call an upstream networking source reading a binary pin or
attribute the failure to libcurl. Do not remove account/lease checks, weaken
verified readback, add mutation retries, disable keepalive, or extend timeouts
from this evidence.

See source-manifest.json for exact reviewed file hashes and anchor lines,
and trace-reduction.json for the deterministic reduction. This review does
not convert the Windows workflow into PASS or substitute for the separately
registered original 15 Apple-hosted assertions.
