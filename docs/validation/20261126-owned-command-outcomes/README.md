# Owned command outcomes: exact App14 controller successor

The original frozen App14 controller is SHA256 59a9d5627bf0f2144d1d4f73d044c8e2b0b5156cd2c2f2e580be5667f62605de. The separately named successor is 73bb6a4f6dde58faa723c38fddd322b6a6ff356fbbee44ecdeb949a77d358e1a. It does not replace or reinterpret any original command, App, XCTest, fixture, or account receipt.

The observed infrastructure defect was a post-exit group query raising PermissionError before result.json was written. A separate timeout path could also lose its original interruption when cleanup raised. The successor writes an exclusive process-exit.json containing the original exit code, log identity and interruption before any post-exit group query. A timeout records its first error before signaling and bounds the waits used to reap its own Popen child. A signal failure is retained independently.

Post-exit observation sends only signal zero. Actual ESRCH is the sole absence proof. Permission denial and positive presence are observed for a bounded interval and remain failure if unresolved. checked=False does not waive the ownership gate. Once ESRCH is observed that historical group is not queried again. New Popen generations clear any historical absence for a reused identifier. The main cleanup loop separately records each group observation error so one error cannot prevent the final failure receipt from being written.

All admission, source, product, selection, native semantic, stage and result predicates remain byte-identical. The source inverse replaces only Commands and the exact per-group cleanup exception block; it reproduces the full original59 file.

## Actual qualification

- Linux:12 focused controls PASS,0failures,0skips. These include actual zero/nonzero/spawn outcomes and timeout reaping, plus explicitly labeled injected post-exit permission/presence failures and signal denial. Positive cases ultimately use actual kernel ESRCH. Result02a6fd1a0a8a15d568855e4d3ef6b18bb9d4da92bf352cbe69a53b3c90e0716c.
- Darwin:3 actual tiny command cases PASS: exit0,exit7,and a real timeout with SIGTERM exit-15 and child reaping. All created groups were positively absent. Result10746f31ca05035c6439ebfafd01df8c4d2c6c9f9e83c9a3fbffddf7c0981c2a.
- The first portable run remains FAIL:11 process controls passed but the exact inverse exposed one missing class-boundary newline. The original newline was restored; command ASTs were unchanged. The final complete12-control run used the final exact73bb bytes.
- Root independently reviewed the full59→73bb delta and reported no blocker before adoption. This is source review plus command-controller qualification, not application acceptance.

Zero App builds, native builds, Simulator calls or application test invocations were performed for these controls. The original59 consumers and their failures remain unchanged. A new consumer must explicitly pin this successor and retain its own original product and account admission.
