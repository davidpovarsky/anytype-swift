"""Bind a read-only Apple57 lifecycle review to its exact source and closed job log."""
import datetime, hashlib, json, pathlib, subprocess

APP = pathlib.Path(r"C:\Users\DAVID\Code\anytype-swift-any-engine-20261119")
ANY = pathlib.Path(r"C:\Users\DAVID\Code\any-pinkha-runtime-20261119")
OUT = pathlib.Path(__file__).resolve().parent
COMMIT = "57c116e02ee6dbce21f3bbffcc297841d2bd1235"
LOG = APP / "build/any-engine-port/apple57-patched-runtime-v1/workflow-job.log"
SPEC_PATH = "Tools/AnyEngineValidation/evidence/native-conditional-properties-v8-source.json"

def sha(b):
    return hashlib.sha256(b).hexdigest()

def git_bytes(root, revision, path):
    return subprocess.run(["git", "--no-optional-locks", "-C", str(root),
                           "show", revision + ":" + path],
                          check=True, capture_output=True, timeout=15).stdout

def save(name, data):
    p = OUT / name
    if p.exists():
        raise RuntimeError("Refusing to overwrite evidence: " + name)
    if isinstance(data, str):
        p.write_text(data, encoding="utf-8")
    else:
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

source_rows = []
for rel in [
    "Modules/PinkhaAnyRuntime/Tests/PinkhaAnyRuntimeTests/AnyEmbeddedRuntimeTests.swift",
    "Modules/PinkhaAnyRuntime/Sources/PinkhaAnyRuntime/AnyEmbeddedRuntime.swift",
]:
    data = git_bytes(APP, COMMIT, rel)
    source_rows.append({"scope": "app", "path": rel, "gitCommit": COMMIT,
                        "sha256": sha(data), "bytes": len(data)})
assert source_rows[0]["sha256"] == "45751cc8c2c1c46245e5a2c663fdaf7acd449df57a8f95e4c2761555dfd22989"
assert source_rows[1]["sha256"] == "e77f1d948d22480c4e15fb647a61911db38ae3ec2029a85404dded75f8953ee2"
manifest_bytes = git_bytes(APP, COMMIT, SPEC_PATH)
assert sha(manifest_bytes) == "484d377a89b3e53ccab28bbf8defe223441e85db398c40ee5626d71ddc521289"
manifest = json.loads(manifest_bytes)
changed = {x["path"]: x["worktreeSHA256"] for x in manifest["any"]["files"]}
native_paths = [
    "internal/server/pinkha_gateway.go",
    "internal/server/pinkha_gateway_mobile.go",
    "internal/server/control.go",
    "internal/server/errors.go",
    "internal/server/routes.go",
    "internal/server/logger_echo.go",
    "internal/server/server.go",
    "internal/embedded/embedded.go",
    "mobile/ios/anylib.go",
]
for rel in native_paths:
    data = (ANY / rel).read_bytes()
    if rel in changed:
        expected, basis = changed[rel], "sealed v8 changed-file map"
    else:
        expected = sha(git_bytes(ANY, manifest["any"]["upstreamCommit"], rel))
        basis = "unchanged pinned upstream source"
    assert sha(data) == expected, rel
    source_rows.append({"scope": "native", "path": rel, "sha256": sha(data),
                        "bytes": len(data), "v8SourceMatch": True, "basis": basis})

raw = LOG.read_bytes()
text = raw.decode("utf-8")
required = [
    'NSErrorFailingURLStringKey=http://127.0.0.1:49256/v1/pinkha/capabilities',
    'Task <2213C46C-B6CE-43D9-9189-7F937C76AD91>.<6>',
    '2026-11-20T04:37:32.359Z',
    '"path": "/v1/pinkha/capabilities", "status": 403',
    '2026-11-20 04:38:32.397310+0000',
    'AnyEmbeddedRuntimeTests.swift:86',
    'Executed 3 tests, with 1 failure (1 unexpected)',
]
assert all(x in text for x in required)
source_stable = all(
    x["scope"] != "native" or sha((ANY / x["path"]).read_bytes()) == x["sha256"]
    for x in source_rows
)
assert source_stable
assert sha(LOG.read_bytes()) == sha(raw)

receipt = {
    "status": "READ_ONLY_APPLE57_LIFECYCLE_BOUNDARY_REVIEW_NO_ROOT_CAUSE",
    "createdAtUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "appCommit": COMMIT,
    "workflowJobID": "136080515969",
    "nativeManifest": {"path": SPEC_PATH, "sha256": sha(manifest_bytes)},
    "closedJobLog": {"path": str(LOG), "bytes": len(raw), "sha256": sha(raw),
                     "rawLogCopiedIntoThisArchive": False},
    "sourceStable": source_stable, "sources": source_rows,
    "observations": {
        "test": "AnyEmbeddedRuntimeTests.testRealManagedRuntimeLifecycleAndControlBoundary",
        "actualRuntimeTests": 3, "actualUnexpectedFailures": 1,
        "failingRequest": {"method": "GET", "path": "/v1/pinkha/capabilities",
                           "url": "http://127.0.0.1:49256/v1/pinkha/capabilities",
                           "client": "Darwin URLSession.shared / CFNetwork",
                           "task": "2213C46C-B6CE-43D9-9189-7F937C76AD91.6",
                           "errorDomain": "NSURLErrorDomain", "errorCode": -1001},
        "nativeLogStatus": 403,
        "nativeLogTimestamp": "2026-11-20T04:37:32.359Z",
        "clientErrorTimestamp": "2026-11-20T04:38:32.397310Z",
        "exactClientRequestStartTimestampAvailable": False,
        "nativeLogTextInterleavedWithCFNetworkStderr": True,
        "actionsCaptureTimestampsAreNotNativeEventTimestamps": True,
        "reportedTestLine86": "catch rethrow after cleanup; request await is lines29-34",
        "priorSequentialRequests": [
            {"path": "/v1/health", "authorized": True, "status": 200},
            {"path": "/v1/auth", "authorized": True, "status": 200},
            {"path": "/v1/health", "authorized": False, "status": 403},
            {"path": "/v1/auth", "authorized": False, "status": 403},
            {"path": "/v1/spaces", "authorized": False, "status": 403},
        ],
        "accountAuthorizedAtFailure": False,
        "restartControlOrEmergencyStopReachedBeforeFailure": False,
        "AnyHTTPClientOrHostLeaseUsedByFailingTestRequest": False,
        "SSEUsedByFailingWorkflow": False,
    },
    "responseBoundary": {
        "denialOccursBeforeCapabilitiesHandlerAndSDKGate": True,
        "requireControlDiscardsWriteError": True,
        "httpInfoLogPrecedesGoFinishRequestFlush": True,
        "nativeFinalFlushObserved": False,
        "failedResponseHeadersOrBodyObserved": False,
        "logSinkBackpressure": "Source-supported possibility, not established by the interleaved log.",
    },
    "classification": "Target-platform acceptance failure. Same timeout symptom as Windows does not prove a shared root cause.",
    "newRuntimeExecutions": 0, "newHTTPRequests": 0, "productionChanges": False,
    "supportedProductionFix": None,
}
save("receipt.json", receipt)
save("review.md", """# Apple57 lifecycle timeout: exact read-only boundary review

**The patched Apple runtime acceptance failed. No root cause or supported
production fix has yet been established.** This review preserves that failure;
it does not reinterpret it as a Windows-only problem or infer one common
mechanism from similar timeout errors.

## Exact workflow and source

The inspected app source is commit57c116e02ee6dbce21f3bbffcc297841d2bd1235.
The Runtime test SHA is45751cc8c2c1c46245e5a2c663fdaf7acd449df57a8f95e4c2761555dfd22989.
Its native source is the sealed v8 manifest484d377a; all nine reviewed
native files match that manifest or its unchanged pinned upstream source.

The closed Apple job136080515969 ran three Runtime tests and recorded one
unexpected failure. The failing task was the sequential, unauthenticated
GET /v1/pinkha/capabilities in lines29–34. Line86 only rethrows after cleanup.
The test uses URLSession.shared directly, with no AnyHTTPClient, Host lease,
catalog fan-out, SSE, or application property operation.

The prior authenticated health/auth requests returned200; unauthenticated
health/auth/spaces returned403. The capabilities request then timed out with
NSURLErrorDomain -1001. Native event time was04:37:32.359 UTC for its403 log;
CFNetwork's error timestamp was04:38:32.397310 UTC. No exact client request-start
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
Thus the outer HTTP403 log cannot certify that the JSON write itself
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
""".replace("commit57", "commit 57").replace("SHA is457", "SHA is 457")
   .replace("manifest484", "manifest 484").replace("job136", "job 136")
   .replace("lines29", "lines 29").replace("Line86", "Line 86")
   .replace("returned200", "returned 200").replace("returned403", "returned 403")
   .replace("was04", "was 04").replace("its403", "its 403").replace("HTTP403", "HTTP 403"))
files = []
for p in sorted(OUT.iterdir()):
    if p.is_file() and ".bak." not in p.name:
        data = p.read_bytes()
        files.append({"path": p.name, "bytes": len(data), "sha256": sha(data)})
save("archive.json", {"status": receipt["status"], "files": files})
print(json.dumps({"status": receipt["status"], "sourceStable": source_stable,
                  "files": {p.name: sha(p.read_bytes()) for p in sorted(OUT.iterdir())
                            if p.is_file() and ".bak." not in p.name}}))
