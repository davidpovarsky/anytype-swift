# Original network conditional revision acceptance — 25 November 2026

**Actual result: PASS, SentinelX job \`job_7b2ad6b09e9d\`.**

The immutable native input is \`50426b5010576f6467b5a7baca0fe897447b41dd\`; the test harness is \`d436092383e2a9289760d039571c095060d262d9\`. This is a real native Go application test on the Scaleway Mac, with the original default Anytype network and LAN synchronization disabled. Two independent original account repositories were reused. No account or object was created to replace the retained fixture.

## What passed

- The producer and receiver processes (PIDs 53575 and 53576) opened the same original account, Space, Annotation UUID and native root.
- The receiver observed the producer's actual rich block change through its own original native read. The coordination files contain hashes/round markers, not a transferred native body.
- The old receiver token was refused after that remote change, with no native Apply attempt, no observed write, and unchanged current root/Archive witnesses.
- An explicit resolution used a fresh original token and performed an actual conditional replacement of the same root. The genuine native readback matched the complete intended block inventory.
- The producer subsequently observed that replacement through its own native read, independently of the receiver's local mutation receipt.
- Both original accounts stopped, with actual \`AccountStop\` return and application absence. Two new processes (PIDs 53665 and 53666) reopened their retained repositories, read the same final root and Archive witness, and stopped successfully.
- Six actual restriction controls passed: the parent normalization control and five nonzero native restriction flags. The test reuses the original \`Base.Diff\` empty-restriction normalization on comparison copies; it does not ignore restrictions. Complete rich mark tuples and child order remain significant.

The final original root digest is \`68a3aeaf9d700d6501750b6fe14ef03904b9d8b463ce056c89e893d71ef45fdc\`. Exact object IDs, native heads, Archive heads, response hashes, process IDs and Stop receipts are in \`RESULT.json\` and \`OBSERVED_NATIVE_RECEIPTS.json\`.

## Input and execution evidence

The complete original Native66 composition is identified separately from its shallow upstream checkout: canonical tree \`4b1ce2b7629974eb2bff91155f66b03122548aa6\`, actual shallow HEAD \`d98420b1113536afd08cde6de9a5816f6d27ffff\`. All 112 composed input files and all 14 native overlay preimages were checked before and after. These are not represented as the same commit.

Compilation took 18.143 seconds; the focused restriction process took 3.034 seconds; the live and fresh-process network sequence took 37.255 seconds. Every phase exited zero without a budget stop or forced termination. The actual test binary SHA-256 is \`90b2aca95feb936573a63bdde1043bc923f7c773665fb058116adcfd60d3508f\`. Maximum child RSS was 1,953,808,384 bytes; the retained owned attempt occupied 190,214,969 bytes. Source and original donor bytes remained unchanged.

\`REMOTE_CAS_PUBLIC_EVIDENCE.tar.gz\` contains the same public receipt set. Its SHA-256 is \`b26012263d46bb433adf4923f394278c5fba313e098fc262148fd7d5edbea1fd\` (24,390 bytes). \`PUBLIC_FILES.json\` authenticates the public members; \`RAW_ARTIFACT_HASHES.json\` authenticates all 109 retained raw evidence/peer files.

Full original responses, ZIP bodies and execution logs remain private at:

\`/Users/m1/builds/anytype-original-network-acceptance-20261125/revision-cas-50426b50-d4360923/attempt-1\`

The public native receipt projection omits only the native ZIP body, retaining its exact original hash, byte count and source-response hash. Account repositories and the recovery phrase are never included. The public files were checked against the test-owned recovery phrase in memory before packaging.

## Scope and retained failures

This proves independent original network replicas on the same physical Mac, including forward/reverse rich change observation, observed-remote stale-token refusal, same-root conditional resolution and fresh-process persistence. A local native receipt is never called a remote server ACK. A receiver-observed native revision is the separate transport evidence.

This does not qualify ordinary Maktabah UI, physical-device behavior, offline simultaneous multi-peer conflict convergence, archive/restore/promotion, SDK ABI/release packaging, or the 5,000-native-note batch. Those have separate owners and acceptance gates.

Historical \`job_09fe7fb07354\` remains a failed old-contract attempt: its exact six-block comparison exposed only the original nil-versus-empty restriction representation. Its reverse/cold path is not retrospectively marked passed. The original failed evidence and correction rationale remain in the parent source checkpoint.
