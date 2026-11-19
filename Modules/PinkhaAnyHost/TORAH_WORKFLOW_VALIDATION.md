# Native T5 workflow validation

## Result and remaining issue

The production T5 workflow passed **all 19 assertions against the real native v7 engine over direct loopback HTTP** in two diagnostic runs on 2026-11-19. The first reused the same 549 compiled production dependency objects and added only eight fixed CLI progress messages. The second rebuilt an isolated Engine source copy with private timing/framing logging, retained the other 537 compiled production objects, and completed the same 19 assertions.

**Windows local HTTP reliability remains unresolved.** The unchanged original executable failed in three retained direct runs, including a later control that failed earlier in the workflow. Production timeouts, request semantics, capability checks and the 19 assertions were not weakened.

## Retained attempts

Receipt paths below are under `docs/any-engine-port/evidence/20261119/`.

| Receipt | Execution | Result |
| --- | --- | --- |
| `native-torah-workflow-20261119-201618-378627.json` | Original source-bound SwiftPM executable, direct endpoint | Build succeeded; 10/19, then request timeout. |
| `native-torah-existing-20261119-203847-902255.json` | Same executable, direct endpoint, no build | 10/19, then NSURLErrorDomain -1001. |
| `native-torah-http-trace-20261119-204337-014385.json` | Diagnostic HTTP/1.1 proxy | Inconclusive: first two native responses were promptly delivered HTTP 200, then no third request arrived before timeout. |
| `native-torah-http-trace-20261119-204615-793374.json` | Diagnostic HTTP/1.0 proxy with connection close and exact content length | 19/19 through 2,229 real requests. Several framing variables changed together; this is not proof of a particular fix. |
| `native-torah-direct-progress-20261119-205736-349784.json` | Progress-only relink, original direct endpoint | **19/19**, all four retry-phase begin/end pairs completed; sources, cached dependencies and native source/binary pins stable. |
| `native-torah-existing-20261119-210154-834308.json` | Unchanged original binary, direct endpoint, owned-process DLL inspection | 3/19, then writeUncertain during origin/quote/association setup. No blind retry was added. |
| `native-torah-direct-transport-trace-20261119-210843-392308.json` | First isolated trace build | Diagnostic driver rejected a single output path with threaded code generation; 0 native checks. Preserved and corrected only in the runner. |
| `native-torah-direct-transport-trace-20261119-211047-233388.json` | Isolated HTTP trace, direct endpoint | **19/19**, 2,229 requests and 4,458 paired trace events; no errors or unfinished requests. Production/cache/native/copy source hashes stable. |

The source-bound executable hashes are:

- Original: `38f2967726a7ffe93adeae55baaffe991ebba7b10ff5e9543d2c1f9bf73a6eb1`.
- Progress-only relink: `f404eaf1a2c8b1123d30cbba4c2d3d8c62ad3ca2d39e027fbf3f3bdcb8194c51`.
- Isolated HTTP trace: `bea0f193fae973d47b970fddcd5c4bd160270373c0c4f4db217ec88e7ab8773f`.
- Native v7: `12c7fb62164c830410331aabf616194edb0711a083250f8e8dd34c3cba52078b`.
- Native source manifest: `62a13310a474d93d728258d0631618b09056a20c4454bd7be303f3ec071fb77c`.

The control runner separately records current source and original binary source manifests. Its sole permitted delta is the exact audited eight CLI progress lines; it does not pretend the original binary contains them.

## What succeeded

The actual workflow covers native capabilities and Note-marker bootstrap, guarded canonical storage, origin/quote creation, original T5 Note creation and RTL source line, current Note classification/permissions, canonical source context and origin backlink, related/derived indexes, exact retry preserving IDs/history/claim count, a later conditional body edit, old-session revocation, reconnection using the same receipts while preserving that edit, safe unlink of both associations without deleting the Note, exact quote payload/provenance preservation, index rebuilding, prevention of an old plan resurrecting removed context, and cleanup of only tracked synthetic objects.

Both global claim snapshots around retry remain present. No snapshot assertion or expected count was removed.

## DLL observation

The final original-binary control inspected only its own newly spawned process. Actual loaded DLLs came from `Swift/Runtimes/6.3.3/usr/bin`:

| DLL | SHA-256 |
| --- | --- |
| Foundation.dll | `168aefec134849f733594b9721e6d000b8431b5a0da69c0c05c86df0eb56a574` |
| FoundationNetworking.dll | `2526b5b278644974aa9f01eb01e9152b509ea2264e01e39bc29411ad73c15c9f` |
| swiftCore.dll | `852f2e59694d89ca28a38cfe0ba97f12d45e5a5e5ae2e06830adc85fd07f14f4` |

The receipt includes the other Foundation modules and candidate DLL hashes. Neither executable directory contained Foundation DLLs. The final traced process was also inspected live and all six loaded Foundation/Swift module hashes matched the failed original control. A different runtime DLL is therefore not supported as an explanation for that pair of runs. The earlier progress-only successful process was not inspected live.

## Direct trace observations

The completed trace records 2,229 responses: 2,223 HTTP 200, four HTTP 201 and two HTTP 204. Of these, 2,185 had Content-Length, 42 used chunked framing, and the two bodyless 204 responses had neither. Every response lacked a Connection header; this successful run did not use the connection-close workaround.

With integer-millisecond observations and nearest-rank percentiles, all requests had p95/p99 of 16 ms and a maximum of 452 ms (bundle installation). The 1,486 auth requests had p95 of 15 ms, p99 of 16 ms and a maximum of 78 ms. These are diagnostic timings, not a performance benchmark; logging and scheduling can affect them. The exact aggregate and slowest normalized routes are in `native-torah-direct-transport-trace-20261119-211047-233388.analysis.json`.

No request error reproduced in this trace. The changing failure phase does not identify a blocked route or establish a Foundation cause. The successful fixed-length and chunked responses also do not establish that the earlier failures have been fixed. No production keepalive, timeout or retry change was made. The prior Windows failures remain open, and separate Apple execution remains necessary.

## Scope and reproduction

Creation receipts in this CLI probe are **in memory**. Reconnection is a new application session against the running engine, not a process restart. Protected Apple journal reopening, UIKit consent/presentation, cold app launch and live provider transport require their separate acceptance tests.

All accounts, Spaces and writes are owned synthetic fixtures. Trace output excludes authorization headers, bodies and recovery phrases. CLI progress output contains fixed phase names only.

Runners are under `Tools/AnyEngineValidation/`: `run_native_torah_probe.py`, `run_existing_native_torah_probe.py`, `trace_native_torah_probe.py`, `run_torah_direct_progress.py`, and `run_torah_transport_trace.py`. Earlier variants are retained under `evidence/native-torah-workflow-scripts/`. Rerun helpers require explicit disposable-write authorization and are confined to the assigned fixture.

The exact modified source and logging diff are archived as `AnyHTTPClient.trace-v2.swift` and `AnyHTTPClient.trace-v2.diff` under the same scripts evidence directory. `reusable-trace-engine-v2.json` binds the original/copied Engine source maps, compiler commands, traced object/modulewrap hashes and the required two-object replacement rule. These diagnostic objects may be reused only after checking the consuming executable's exact original Engine source compatibility; they do not replace production objects or settings.
