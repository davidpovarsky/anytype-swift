# Passive Runtime denied-read metrics

The sole modified application-repository source is the Runtime test file.
Its four original denied reads use the same URL expression and
URLSession.shared.data(from:) operation with the API's optional per-task
delegate. No session/configuration/timeout/header/authentication policy is
changed. All three test names and all 27 original XCT calls are retained;
the original test prefix is restored byte-for-byte by reversing that one
call-site replacement and removing the appended helper.

The observer implements only didFinishCollecting. It does not implement
authentication, redirect, response-disposition, byte-delivery, or completion
callbacks. A strong local variable spans the await, success/error reporting
and defer. The observer retains no session/task. Its sole mutable state is
a counter protected by a short NSLock; no lock spans output or suspension.
The concrete helper passed Swift 6 typechecking against installed
FoundationNetworking declarations without diagnostics. The full test passed
iOS-target syntax parsing with the expected Windows-sysroot warnings.
Actual Apple SDK compilation and Runtime execution remain pending.

Output prefix: PINKHA_RUNTIME_HTTP_METRICS. Each minified JSON line contains
a fixed route label from the four tested paths, an observation UUID, phase,
absolute/monotonic timing and metrics callback count. Metrics add
transaction timing, normalized protocol, reuse/proxy flags, numeric fetch
type, byte counts, status, and expected content length. At most 16 transaction
records are emitted, with total/omitted counts explicit. The success event
records only returned Data length. Errors expose only a whitelisted domain
label and numeric code. No request/response headers, URLs, body content,
tokens, account identity, or NSError descriptions/userInfo are emitted.

A missing metrics callback is unknown, not proof of absent response headers.
A metrics responseStart date is first response-byte timing, not by itself
complete headers. Negative/unknown byte lengths retain their native value.
Transfer byte counts include encoding/framing and are not asserted equal to
decoded bytes or expectedContentLength. The raw observations are evidence;
they never decide or relax an original assertion.

Synchronous diagnostic output adds overhead and can perturb timing. A
passing instrumented run does not by itself explain or erase the retained
Apple57/Windows failures. No runtime or network attempt was made by this
source validation. Native engine and production Swift sources are untouched.
