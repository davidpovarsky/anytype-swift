# Coherent Heart native evidence audit

**PASS_SCOPED_ARCHIVED_NATIVE_EVIDENCE** — run [45026227924](https://github.com/davidpovarsky/anytype-swift/actions/runs/45026227924), attempt 1, app `b2fc3804426067dd1ec8318d6ea92a4bcb8e9545`.

This audit only reads and hashes the original artifact. No Go, Swift, simulator, or native product tests were rerun.

## Verified evidence

- Archive SHA256 `52f293d77c7d1bcf9b94c0c0cd0cf0a2cbb8cdeca7a83ab5dde1506635b12783` matches the GitHub artifact digest; all 43 extracted originals match ZIP bytes.
- 42/42 independent evidence checks passed. Raw logs contain 9 component methods/18 terminal events and 1 actual account method: **10 methods/19 terminal events, 0 failures, 0 skips**.
- Owner and Reader protobufs decode as complete successful snapshots; their canonical operation bytes, target, author and native provenance are byte-identical. The authority snapshot token changes after downgrade.
- Removed-member protobuf contains permission error 4, fixed denial label and protocol version only. It contains no snapshot, canonical operation, claim, or synthetic body payload.
- T2 and T5 share account, Space, object, process, nonce and runtime identities. The real native ACL reports removal, read-key rotation and a populated cache; T5 Search reports error 2/zero rows/zero total, and Show error 2/no ObjectView.
- All 139 native source hashes and 314 controller source hashes match before/after. Patch inventory and snapshots agree for all 139 paths; 99 newly added patch files were reconstructed and rehashed. Frozen controller and both account fixtures were independently fetched at exact `b2fc380` and match recorded hashes.
- All 11 distinct archived-file hash references match. The audit JSON records hashes for every original.
- Original AccountStop, graceful shutdown and final named test PASS remain in the native log. Existing warning/error diagnostics are retained.

## Scope and limits

- iOS/Apple acceptance NOT_RUN. This is one Linux native run; no iPad, UI, release, or fresh iOS process proof.
- Network ACL transport NOT_RUN: real signed records were delivered locally through native validation/update code.
- Automatic T2-to-T5 projection NOT_PROVEN. T2 immutable operation bytes and T5 canonical association property are distinct fixture writes on the same native target.
- Full T5, offline unknown revocation, mixed clients, and full T2 acceptance remain unproven.
- T2 response protobufs are archived and independently decoded. T5 Search/Show raw protobufs are not in this ZIP; T5 denial is supported by original observation, source-bound require assertions, and the passing native log.
- The native executable is not archived. Its recorded binary SHA256 and before/after execution check can be audited in the frozen controller, but the binary digest cannot be independently recomputed from this artifact.
- 139 native and 314 controller source guards are verified through before/after snapshots. Two account fixtures and controller were separately fetched at exact b2fc380 and rehashed. Existing changed files are not full snapshots in the ZIP; their complete base+patch content was not reconstructed here.
- Original credential scanning is recorded by the controller and hash-bound export. Disposable wallet secrets are deliberately absent, so this audit cannot independently repeat the original exact-secret comparison.

## Artifact identity

- Native patch SHA256: `2e898ac9aac29c0f53dd777492be6b47f14784949313364ff47439de93cd3c00`.
- Native inventory SHA256: `05ee31723508599e228d28e132ce5b89af886f5095c908362b2348d07c80d0f0`.
- Artifact ID: 14756266358. Original receipt status: `PASS_COHERENT_SIGNED_AUTHORITY`.
- Retained prior unaffected scope: 67 T2 terminals and 2 current-read components, without reruns. Those retained counts are not added to the 10/19 newly executed count.

See `AUDIT.json` for individual checks, raw-wire summary and original-file hashes.
