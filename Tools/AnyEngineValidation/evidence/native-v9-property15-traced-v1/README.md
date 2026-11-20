# Property workflow: current v9 diagnostic

The unchanged strict Host property workflow did not finish. The reviewed timestamp-only Engine copy recorded 778 requests: 777 responses and one GET /v1/auth timeout (NSURLErrorDomain -1001, 30,016 ms). No business-check count was emitted, so this receipt is a failure without an inferred partial pass count.

Seven client awaits overlapped the failed request's beginning. The native Info log has 32 auth-200 completion candidates in the selected 105 ms window, including one at the same millisecond. The logs lack a shared request identifier; they cannot establish that a specific candidate is this response, or that bytes reached the socket/client. The failure boundary is identified at the client's response await, but the cause remains unresolved.

All other completed responses were at most 108 ms. Of them, 776 had Content-Length and the 204 cleanup response had no such header; none reported chunked framing or a Connection header. This property workflow creates no SSE subscription. The trace therefore does not require a live-stream cancellation to reproduce the timeout.

The dedicated applySeq field is present in v9 and covered by its native serialized-response regression. The earlier v8 missing-field failure, the plain-v9 failure, and this diagnostic remain separate evidence. No client acknowledgement check, request timeout, header, retry behavior, native write authority or original property assertion was changed. Apple-hosted execution of the same 15 business assertions is a distinct pending gate.
