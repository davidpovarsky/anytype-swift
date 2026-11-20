"""Read-only analysis of already-retained source and trace; never issues HTTP requests."""
from __future__ import annotations
import collections, datetime, hashlib, json, pathlib, subprocess

APP = pathlib.Path(r"C:\Users\DAVID\Code\anytype-swift-any-engine-20261119")
ANY = pathlib.Path(r"C:\Users\DAVID\Code\any-pinkha-runtime-20261119")
MOD = pathlib.Path(r"C:\Users\DAVID\go\pkg\mod")
OUT = pathlib.Path(__file__).resolve().parent
TRACE = APP / "build/any-engine-port/native-v9-property15-traced-v1/run/stderr.log"
CORRELATION = TRACE.parent.parent / "native-http-metadata.json"
NATIVE_SPEC = APP / "Tools/AnyEngineValidation/evidence/native-property-receipts-v9-source.json"
FAILED_ID = "737A8849-8A6B-454E-B66F-E2FE6F56A64E"

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def dump(name: str, value: object) -> None:
    path = OUT / name
    if path.exists():
        raise RuntimeError("Refusing to overwrite retained evidence: " + name)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

specs = [
    ("app", "Modules/PinkhaAnyEngine/Sources/PinkhaAnyEngine/AnyHTTPClient.swift",
     ["public struct AnyHTTPClient", "URLSessionConfiguration.ephemeral", "requestJSON(", "func checkAccount", "func raw", "request.timeoutInterval = 30"]),
    ("app", "Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyApplicationSession.swift",
     ["struct AnyHostLease", "actor AnyApplicationSession", "verifyRun", "func perform", "func validateCurrentRun", "func revokeAndDrain"]),
    ("app", "Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyNativePropertyStore.swift",
     ["func catalog", "stride(from: 0", "withThrowingTaskGroup", "func read(", "func apply(", "let readback = try?", "static func acceptedFence", "func typeProof"]),
    ("app", "Modules/PinkhaAnyHost/Sources/PinkhaAnyHostProbe/PropertyProbe.swift",
     ["static func", "catalog(", "property native acceptance lacked exact version readback"]),
    ("any", "internal/server/handlers_auth.go", ["func (d *deps) authStatus", "if d.cfg.Managed()"]),
    ("any", "internal/server/handlers_meta.go", ["func (d *deps) accountID"]),
    ("any", "internal/server/gate.go", ["func (g *engineGate) enter", "func (g *engineGate) leave", "func (g *engineGate) close"]),
    ("any", "internal/server/routes.go", ["func buildEcho", "case \"/v1/health\"", "v1.Use", "SetWriteDeadline"]),
    ("any", "internal/server/server.go", ["func RunWith", "net.Listen", "e.Start"]),
    ("any", "internal/server/logger_echo.go", ["func httpLogMiddleware", "err := next(c)", "lg.Info"]),
    ("any", "internal/server/control.go", ["func (d *deps) requireControl", "func (d *deps) capabilities"]),
    ("any", "internal/server/pinkha_gateway.go", ["func (d *deps) pinkhaMobileManagedGateway"]),
    ("module", "github.com/labstack/echo/v4@v4.13.4/json.go", ["func (d DefaultJSONSerializer) Serialize"]),
    ("module", "github.com/labstack/echo/v4@v4.13.4/context.go", ["func (c *context) json(", "func (c *context) JSON("]),
    ("module", "github.com/labstack/echo/v4@v4.13.4/response.go", ["func (r *Response) WriteHeader", "func (r *Response) Write("]),
    ("module", "github.com/labstack/echo/v4@v4.13.4/echo.go", ["func (e *Echo) ServeHTTP"]),
    ("module", "golang.org/toolchain@v0.0.1-go1.27.1.windows-amd64/src/net/http/server.go",
     ["if w.handlerDone.Load() && !trailers", "func (w *response) finishRequest", "serverHandler{c.server}.ServeHTTP(w, w.req)", "w.finishRequest()"]),
]
roots = {"app": APP, "any": ANY, "module": MOD}
before = []
for kind, relative, anchors in specs:
    path = roots[kind] / relative
    data = path.read_bytes()
    lines = data.decode("utf-8").splitlines()
    before.append({
        "scope": kind, "path": relative, "absolutePath": str(path),
        "sha256": sha(data), "bytes": len(data),
        "anchors": {s: [i + 1 for i, line in enumerate(lines) if s in line] for s in anchors},
    })

trace_bytes = TRACE.read_bytes()
correlation_bytes = CORRELATION.read_bytes()
native_bytes = NATIVE_SPEC.read_bytes()
assert sha(trace_bytes) == "f7050aa7de1fa05144cff4cd4b76acbe8501fa411b4ebb27f21c79659784f27c"
assert sha(correlation_bytes) == "f01d12a0c8e3d3477552dd1be0eb714ce3fd831f8541b6895443f67474edacb6"
assert sha(native_bytes) == "15906eb27afea68cc7ec99242bffd6a8ea69517edb608a4421cce90c9a99a070"
metadata = json.loads(correlation_bytes)
events = []
for line in trace_bytes.decode("utf-8").splitlines():
    if line.startswith("ANY_HTTP_TRACE "):
        event = json.loads(line[len("ANY_HTTP_TRACE "):])
        allowed = {"elapsedMs", "id", "method", "path", "phase", "timestampUnixMs", "framing",
                   "status", "errorCode", "errorDomain"}
        assert set(event).issubset(allowed)
        events.append(event)
begins = {e["id"]: e for e in events if e["phase"] == "begin"}
terminals = {e["id"]: e for e in events if e["phase"] != "begin"}
start, finish = begins[FAILED_ID], terminals[FAILED_ID]
assert start["path"] == "/v1/auth" and start["method"] == "GET"
assert start["timestampUnixMs"] == 1795150230560
assert finish["phase"] == "error" and finish["errorCode"] == -1001 and finish["elapsedMs"] == 30016
t, end = start["timestampUnixMs"], finish["timestampUnixMs"]
active = []
for entry in metadata["clientActiveAtFailedBegin"]:
    terminal = terminals[entry["id"]]
    active.append({
        "id": entry["id"], "method": entry["method"], "path": entry["path"],
        "terminalPhase": terminal["phase"], "status": terminal.get("status"),
        "reportedMonotonicElapsedMs": terminal["elapsedMs"],
        "terminalWallOffsetFromFailedBeginMs": terminal["timestampUnixMs"] - t,
    })
other = [e for e in events if e["phase"] == "response" and t <= e["timestampUnixMs"] < end]
assert len(active) == 7
assert sum(e["terminalPhase"] == "response" and e["status"] == 200 for e in active) == 6
assert len(other) == 41
assert max(e["timestampUnixMs"] - t for e in other) == 42
assert sum(e["phase"] == "begin" and t < e["timestampUnixMs"] < end for e in events) == 34
source_stable = all(sha(pathlib.Path(x["absolutePath"]).read_bytes()) == x["sha256"] for x in before)
assert source_stable
head = subprocess.run(
    ["git", "--no-optional-locks", "-C", str(APP), "rev-parse", "HEAD"],
    check=True, text=True, encoding="utf-8", capture_output=True, timeout=15
).stdout.strip()

reduction = {
    "status": "READ_ONLY_RETAINED_TRACE_REDUCTION",
    "noNewRuntimeExecution": True, "noHTTPRequests": True,
    "trace": {"path": str(TRACE), "sha256": sha(trace_bytes)},
    "correlation": {"path": str(CORRELATION), "sha256": sha(correlation_bytes)},
    "failure": {"begin": start, "terminal": finish},
    "allBegins": len(begins), "allResponses": sum(e["phase"] == "response" for e in events),
    "allErrors": sum(e["phase"] == "error" for e in events),
    "concurrentAwaitTerminals": active,
    "otherResponsesBeforeFailure": len(other),
    "lastOtherResponseWallOffsetMs": 42, "newBeginsDuringStall": 34,
    "nativeCompletionCandidateCount": len(metadata["nativeAuthCompletionCandidates"]),
    "uniqueClientServerRequestJoin": False,
    "failedAwaitFramingObserved": False,
    "serverFinalFlushObserved": False,
    "scope": "One exact Windows Property15 failure, not a new behavior acceptance run.",
}
dump("trace-reduction.json", reduction)
dump("source-manifest.json", {
    "status": "READ_ONLY_SOURCE_MANIFEST",
    "capturedAtUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "appHEADAtReview": head, "sourceStable": source_stable,
    "nativeSourceManifest": {"path": str(NATIVE_SPEC), "sha256": sha(native_bytes)},
    "nativeBinarySHA256FromFrozenManifest": "4b110906ccecca3cc15a22a66caeeabea82b3cc44e25fe94a911a23a878da361",
    "foundationNetworkingSourcePinAvailable": False,
    "moduleSourceScope": "Local pinned Echo 4.13.4 and Go 1.27.1 source; not a FoundationNetworking binary-source equivalence claim.",
    "files": before,
})

review = """# Read-only review of the retained Windows Property15 auth timeout

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
"""
(OUT / "review.md").write_text(review, encoding="utf-8")
archive_files = []
for path in sorted(OUT.iterdir()):
    if path.is_file() and path.name != "archive.json" and ".bak." not in path.name:
        data = path.read_bytes()
        archive_files.append({"path": path.name, "bytes": len(data), "sha256": sha(data)})
dump("archive.json", {
    "status": "READ_ONLY_ANALYSIS_SEALED_NO_ROOT_CAUSE",
    "scope": "Exact source and retained trace review; no runtime or fix claim.",
    "files": archive_files, "productionCodeChanges": False,
    "newNetworkRequests": 0, "newRuntimeExecutions": 0,
})
print(json.dumps({"status": "READ_ONLY_ANALYSIS_SEALED_NO_ROOT_CAUSE",
                  "directory": str(OUT), "sourceStable": source_stable,
                  "files": {x.name: sha(x.read_bytes()) for x in sorted(OUT.iterdir())
                            if x.is_file() and ".bak." not in x.name}}))
