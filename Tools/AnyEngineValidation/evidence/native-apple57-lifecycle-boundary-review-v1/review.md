# Apple57 lifecycle timeout: exact read-only boundary review

**The patched Apple runtime acceptance failed. No root cause or supported
production fix has yet been established.** This review preserves that failure;
it does not reinterpret it as a Windows-only problem or infer one common
mechanism from similar timeout errors.

## Exact workflow and source

The inspected app source is commit 57c116e02ee6dbce21f3bbffcc297841d2bd1235.
The Runtime test SHA is 45751cc8c2c1c46245e5a2c663fdaf7acd449df57a8f95e4c2761555dfd22989.
Its native source is the sealed v8 manifest 484d377a; all nine reviewed
native files match that manifest or its unchanged pinned upstream source.

The closed Apple job 136080515969 ran three Runtime tests and recorded one
unexpected failure. The failing task was the sequential, unauthenticated
GET /v1/pinkha/capabilities in lines 29–34. Line 86 only rethrows after cleanup.
The test uses URLSession.shared directly, with no AnyHTTPClient, Host lease,
catalog fan-out, SSE, or application property operation.

The prior authenticated health/auth requests returned 200; unauthenticated
health/auth/spaces returned 403. The capabilities request then timed out with
NSURLErrorDomain -1001. Native event time was 04:37:32.359 UTC for its 403 log;
CFNetwork's error timestamp was 04:38:32.397310 UTC. No exact client request-start
timestamp is available. The native line is interleaved with CFNetwork stderr,
and Actions collection timestamps lag these events.

## Lifecycle paths excluded by execution order

The failure occurs before any shutdown request, second runtime start,
generation change, emergency-stop call, account creation, or Space mutation.
The assertion just before the loop confirms authorized=false.

Native Start copies the C strings into Go and creates a context derived from
context.Background. Its lifetime persists after the Swift start call returns.
The Swift registry installs the generation but does not schedule automatic
cancellation. The first explicit stop on this failed path is catch cleanup.
No source-supported dangling caller context, early stop, or stale-generation
teardown was found for this occurrence.

## Denial and response path

The mobile managed-token gateway is outside the engine/tech-space guards.
Missing-token denial returns before the capabilities handler executes.
The reached chain is requireControl → writeError → c.JSON, then outer
middleware and Go HTTP completion. There is no document/claim/property/SDK
read in this denied path.

One concrete observability limitation matters: requireControl discards the
error returned by writeError and reports false; the gateway returns nil.
Thus the outer HTTP 403 log cannot certify that the JSON write itself
succeeded. This differs from Windows authStatus, which returns c.JSON's error.

Independently, the access logger runs synchronously after the handler but
before Go net/http finishRequest flushes the buffered response and connection.
A slow or blocked logging sink can therefore delay response flushing by code
order. The torn log line does not prove that the sink blocked: collection can
interleave streams after their writes, and no sink/write/flush timestamps
were measured. This is a bounded source-based possibility, not the diagnosis.

## Cross-platform interpretation and remaining evidence gap

This target-platform occurrence rules out treating a Windows-specific
FoundationNetworking issue as a complete explanation of all retained failures.
It also shows the application account/lease checks, parallel catalog proofs,
and SSE are unnecessary for at least this occurrence.

Both observed paths eventually use the native Echo/Go JSON response lifecycle,
but one is a denied mobile request on Darwin and the other an authorized
Windows readback request. Equal error names do not establish equal causes.

The missing evidence is completion of the specific response write/final flush
and the client's receipt/completion on that connection. No timeout increase,
keepalive change, token-check weakening, retry, native patch, or new run was
performed or justified by this review. This remains an acceptance blocker
until the actual required Runtime gate passes with an understood disposition
of the retained failure.

The receipt binds the closed log without copying it, records allowlisted
metadata only, and pins all reviewed source. No credentials or private
account data are included.
