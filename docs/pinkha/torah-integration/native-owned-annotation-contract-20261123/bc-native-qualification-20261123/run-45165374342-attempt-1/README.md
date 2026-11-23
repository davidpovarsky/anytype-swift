# Native9 continuation: declared-source coverage failure before compilation

Run [45165374342](https://github.com/davidpovarsky/anytype-swift/actions/runs/45165374342), attempt 1, at `ce1e78576de6a3d586e849d5990d008944ff2777` acquired runner `1000024627`. Its full source tree is identical to the preceding zero-runner source: `5ad7c12f9244e168b618189682cf6413672cd312`. The actual workflow and native-gate job ended failure; this time checkout, toolchain setup and the gate did execute.

## Actual boundary

The original Go1.26.5 darwin/arm64 toolchain and Xcode27.0 were observed. All eight commands exited0 with their owned groups drained. The final command was `go list -deps -test -json ./core/application`; it returned0 and declared1,481 package variants. Exactly86 of the frozen87 required source paths are in that declaration. The only missing path is the original r14 `core/details.go`, in the root core package, which is not a dependency of application. The driver refused that incomplete coverage before invoking the Go compiler.

The original error is preserved: `declared closure omits/differs from reviewed product/test input: core/details.go`. This is a gate/package-selection mismatch, not a Go compiler diagnostic. No export fixture, original import operation or selected native leaf ran. Exact native status: **0 PASS / 0 FAIL / 0 SKIP / 9 NOT_RUN**.

## Authentic evidence

The original artifact is1,781,934 bytes with SHA256 `79d683c0f22ef9a0624e4329bc6a7362520be9c99c93067697d38cf2bb1a7415`, matching the GitHub artifact digest. All22 unique safe ZIP entries passed CRC and all21 indexed payload byte counts/SHA256 values were independently verified. The full15.8MB original Go declaration output remains inside this ZIP. Its compact path/variant diagnosis is copied into observations; it is not described as compiler execution. All85 composed native source hashes match the frozen control manifest.

The driver's actual finally block passed its available checks:85 composed sources,11 original model/proto/RPC inputs, module checksums, actual Tantivy link inputs and exact control source. Declared full dependency closure and a compiled native binary were unavailable, and their checks are explicitly false/zero in the retained result. Native temporary data was removed; no account fixture had started. The sole observer ended normally, its process was absent and its lock was independently acquirable.

`observations/RUN.json` is the original observer's normalized complete API object, not a byte-identical HTTP body. Direct JOBS/ARTIFACTS response files are preserved exactly. All other original artifact entries remain unchanged in the ZIP.

## Minimal next source correction

Root authorized preparing a gate-only correction that declares the actual root core package and produces a separately identified original core compilation output without executing its tests, then compiles/runs the unchanged application binary/selector once. All87 required inputs, original85 composed sources, finally checks and nine native assertions must remain. This packet does not alter the driver, product, fixture, workflow or failure and activates no retry.

The earlier hosted-allocation failure stays retained in `run-45159946802-attempt-1`. These are distinct run IDs with the same source tree; neither is a native pass.
