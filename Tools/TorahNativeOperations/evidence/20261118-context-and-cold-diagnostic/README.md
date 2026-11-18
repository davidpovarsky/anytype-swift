# T2: native context proof and separate cold-client failure

The two runs below test different sources and hypotheses. The context-preservation fix passed actual native tests. The cold-client diagnostic still failed and did not prove the underlying target-load cause.

## Context-preservation proof

- Source commit: `ad51263f31aaeaa8d9605394db4961fd64ba54b8`.
- Exact integration: `09e4287e78fb79937a83f5ed50b5d34800bc50f6`.
- [Run 44282367113](https://github.com/davidpovarsky/anytype-swift/actions/runs/44282367113), attempt 1, completed successfully at 2026-11-18 10:14:48 UTC.
- Registry: **63 PASS = 25 top-level + 38 subcases; 0 FAIL, 0 SKIP**. All three new context methods and their two subcases appear in the original Go event log.
- Component: **68 PASS = 23 top-level + 45 subcases; 0 FAIL, 2 helper SKIPs**. The skipped entry points are `TestNativeTreeProcessHelper` and `TestCommittedProcessExitHelper`; they are not passing tests.
- Both original receipts bind inventory `14261dcc974addb60664772d75be12f63f96ea5768bd245b803d522e17575642`, exact source, and the reviewed overlay hashes.

The original request context reaches the native target loader. A legacy contextless loader is rejected, load errors keep their identity, and a cancelled callback checks cancellation before reading the target. Native SmartBlock locking remains noncancellable. This is neither atomic logout nor two-account synchronization acceptance.

## Cold-client diagnostic

- Source commit: `225cb5075b9c91dc92e4634ee47b063a5c4bae63`.
- Exact integration: `743ae42f7b8ec8181efe5e87f3bb5ccbc1b4ad63`.
- [Run 44280905417](https://github.com/davidpovarsky/anytype-swift/actions/runs/44280905417), attempt 1, failed at 2026-11-18 10:08:19 UTC.
- Preparation passed 35 Python controls, 13 native boundary terminal cases, and all four same-account baseline phases. Those preparation results are not concurrent-client acceptance.
- Creator A reached ready. Recovered B failed its private read after 2.60 seconds. There were **zero passing concurrent-client phase tests and zero final receipts**.
- The original failure reported `wire_code=1`, `wire_issues=[ISSUE_UNKNOWN_INTERNAL]`, and `snapshot_present=false`.
- The subsequent diagnostic reported `target=false`, `private_root=false`, and nil errors for both local `HasTree` calls.

The storage observations occurred after the failed read. They establish local absence at that later time, not the cause of the original wrapped error. The strict read assertion remains fatal; no arbitrary INTERNAL_ERROR retry, error reclassification, history injection, or capability enablement was added. Owned cleanup and secret-scanned allowlist publication passed.

## Evidence and remaining scope

`verified-summary.json` records original artifact IDs, ZIP/receipt/log hashes, source identities, exact categorical diagnostic lines and actual terminal counts. Original ZIPs and raw private logs remain in GitHub Actions; this commit contains only a small metadata summary. The component log includes a non-JSON toolchain preamble; counts use actual Go JSON test terminal events, not text mentions of PASS.

App capability remains OFF. Concurrent native accounts remain blocked at bootstrap; offline convergence/restart, two iOS applications and full T2 acceptance remain unproven. The DoCtx proof does not establish a fix for the separate B failure.
