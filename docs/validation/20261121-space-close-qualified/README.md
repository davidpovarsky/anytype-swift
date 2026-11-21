# Qualified generated-byte Space.Close and cold reopen

Run [44943962391](https://github.com/davidpovarsky/anytype-swift/actions/runs/44943962391) passed at application source `4ee2d7fd9f8acd74f51cbb2236d08f55a93af08b`, retaining native product baseline `16b7493fa05bdc3abbae190c6e6c364c81874eea`. Original artifact `14723536481` has ZIP SHA-256 `a58cc7c2999d509e832cea8f7234d5423c82c7858dbe5c1987408d97f4033f77`. The exact original source-bound receipt is retained in `space-close-receipt.json`; `qualified.json` records the independent artifact checks without account payloads.

## Verified scope

The native fixture executed one actual Space.Close race and one separate-process cold reopen of the original disposable account/Space. Both original phase logs have exactly one named PASS, no FAIL/SKIP, matching phase nonce and process exit. Phase-report hashes match both original result and receipt. Account, Space, target, block, request, original state, committed claim and change identities agree across the two phases. The two process IDs and nonces differ.

All 15 race observations and eight pairs of live native instances were present. Both original cache entries entered closing, and their unchanged 10-second deadline paths ran. The actual settings close attempt preceded durable commit, while native storage close followed durable commit and target/settings release. The original generated-byte append was forwarded once. No gate timeout, cancellation or overflow was recorded.

The corrected fixture waited for the real notification-service LoadFinish before installing race barriers. It did not widen the existing event/gate/cache bounds. The failure of run 44939797011 remains historical: its race budget overlapped unrelated notification startup. This source-bound corrected result resolves that fixture blocker.

The committed signed history grew from two to three raw changes, preserving both original byte hashes. The cold reopen saw the same durable raw changes and heads. Forwarding the identical original request returned ALREADY_EXISTS_SAME_PAYLOAD without a new change ID; the read remained protobuf-equal, including the local watermark. Reads after physical close were denied with a live probe context. Original account shutdown and owned disposable cleanup were verified.

The unchanged four-process generated-byte account baseline also passed with four named invocations and eight ordinary exports. Existing three-race acceptance was not rerun. Original source/build bindings were recomputed from the artifact; source inputs match before and after execution, with zero product-source or module-cache mutation. Both evidence secret scans passed. The CI controller suite reported 70 controls passing; these controls were not rerun during artifact qualification.

The compiled dependency cache was saved after its source-bound compiler-success qualification. Only Go module/build cache directories were eligible; account data, product binaries and test results were not cached by that step.

## Limits

This proves the particular native Space.Close race and original-store cold reopen. It does not assert response-return ordering relative to close or completion of duplicate close calls. Settings deletion, actual account switching, two iOS applications, Any-engine parity and full T2 acceptance remain outside this result. App capability remains OFF. No rerun is needed for this accepted scope unless a relevant product or fixture dependency changes.
