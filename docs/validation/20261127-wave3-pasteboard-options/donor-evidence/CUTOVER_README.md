# Exact SDK Pasteboard source cutover and original fresh-run plan

## Observed result

The authorized source cutover completed once on 2026-11-27 at 12:28:01 UTC, Sentinel job `job_7ddaa069608f`, exit 0. The original Scaleway SDK checkout `/Users/m1/builds/otzaria-wave1-sdk-20261127/source` fast-forwarded from `1be970356c655bcef3688ddf1d129d5029bbc533` to `d6090c03b9ac4e5760941e34f4c04478db4ae59f` on the unchanged `codex/anytype-wave1-sdk-admission-20261127` branch and remained clean. The exact old source is retained at `refs/otzaria-preserved/sdk-before-pasteboard-options-20261127`.

`actual-cutover/CUTOVER_RESULT.json` is the actual 4,248-byte receipt, SHA256 `277a572634499e1498614d9c7a313a2853cea0884f881e3b81edfe6934176e88`. All three original Git steps exited 0. No reset, branch replacement, hook disabling, build, simulator test, signing or upload occurred in this cutover.

## Narrow source and provenance review

The independently read six-file candidate contains one product change: `Anytype/Sources/ServiceLayer/Block/Pastboard/PasteboardHelper.swift` passes the required `options: []` to `PropertyListSerialization.propertyList(from:options:format:)`. Its 6,271-byte candidate SHA256 is `0eee42f7036e43d74d82088b2bd21696dc3b248f4430e4c9dfc887bbbc1a60d9`. All existing pasteboard selection, optional decoding and failure behavior stays in the original source. The existing 93,575-byte upstream exception register prefix is byte-identical; the remaining changes append its source exception and four provenance files. No driver or acceptance predicate changed.

The exact 6,489-byte bundle SHA256 `830388532b1a69e7549a9075f0777da1253b16e95d51292c2ba1f2108cc3054d` was verified against the existing parent before import. All seventeen original guard files were checked against their committed candidate bytes and the live checkout before and after the fast-forward. The complete six-file hash list and preserved reference operations are in the actual precheck/result. The effective hooks directory contained no executable hooks; none was disabled. All four new Work/Evidence/ABI/Macro roots and both new source refs were absent before the operation.

Root's exact upstream graph proof remains `/home/ubuntu/.codex/artifacts/otzaria-wave3-sdk-pasteboard-fix-20261127/GRAPH_PROOF.json`, SHA256 `36773db7263b89fb52d61d524b79b8bbce93e61772e58550bd7d497d577cdb78`. The observed upstream develop was `d857b23ea540be33d6faab4f7a7a1a260ab578c1`, the original source blob was `995df1ccf9a3131919d89bb398bed38594cb47f8`, and the actual common ancestor was `d5650321577a209505a3277c8437b7608cff1cb9`. This is a source/provenance review; the correction is not compiler-qualified by this packet.

## Fresh original execution remains separately gated

The prepared original supervisor SHA256 `4720728f67862a003ed527a56ef1164eae6e063509eb3b619f7a26b346f6be2b` and recipe `677c18318f52912e188c8c48501333462932a330ef7584160adb2f8fb2566490` retain the original execution body, runstep implementation, timeouts, sampled 2,415,919,104-byte stop reserve, all seventeen source guards and mandatory macro restoration. Configuration changes bind d609 and genuinely new absent output roots. The genuine new descriptor/UUID and ABI receipt must be produced by the original tools. The actual failed local-ad6e descriptor/cache is not reused, and `continue_verified_framework.py` is not eligible or invoked.

After reviewing this exact plan, root conditionally authorized one original run only when the checkout is still clean d609, all guards/fresh roots and the exclusive compiler slot remain valid, and actual available Mac storage is at least **15,032,385,536 bytes (14 GiB)**. The owned launcher and watcher both check this admission. The original lower sampled stop reserve still governs the running original supervisor. No completed corrected framework-plus-consumer peak is known; the admission does not imply sufficiency or acceptance. The observed post-cutover free sample was 11,385,499,648 bytes, and the later samples in this packet fluctuate. No SDK run was launched while preparing this packet.

The exact owned launch envelope is staged at `/Users/m1/builds/otzaria-wave3-sdk-pasteboard-launch-20261127.oyteucez`. It preserves original PID/process-group/start observations and the single completion watcher. Its only additional operational gate is the root-required fourteen-GiB admission and read-only exclusive compiler check; it issues no foreign-process signals. All original framework, binary-consumer, runtime, source, ABI, resources and ownership acceptance requirements remain mandatory.

The initial `COMPLETE_PLAN.json` direct supervisor argv omitted the required execution switch. This documentation error is preserved and explicitly corrected in `plan/RUN_ARGV_CLARIFICATION.json`; the unchanged supervisor rejects the incomplete argv, while the actual original watcher already includes `--execute-reviewed-proposal`. No execution was attempted with the incomplete illustration.

## Evidence and limits

Every file in `PACKET_INDEX.json` is byte-bound. Raw scripts and captured logs are stored as lossless gzip, with both compressed and original hashes; trailing spaces and original line endings were not trimmed. The historical failed compiler run and its preservation/retirement packet remain immutable at source commits b16d3c305be3d54706f032b11cac442d6075d7ad and 929f5fc2b4f0e7d60c15e3bef829ecf7807e38ef. This packet changes documentation only. New framework/app/native/physical acceptance and TestFlight uploads: **0**.
