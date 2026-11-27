# Exact hierarchy rename stager and transport

**Frozen for separate source review. Not uploaded, staged, executed or admitted to a runtime window.** The hierarchy runner/input tuple remains exactly `f63adbdf…` / `ed3ef9bf…`. Root's completed source-only execution review `e152db9ef0e57c44206497b73b2bdfb726e5d83fe942ec3f4f8bb369a968aab8` is bound in the new staging receipt metadata.

## Fixed artifacts

| Artifact | Bytes | SHA256 |
| --- | ---: | --- |
| `materialize_and_exec.py` | 9,998 | `b3cfea8a789c4abae7f2f2b8aa3202dc7cf2725a5fae2438eb5c5c9d6342f7eb` |
| `hierarchy-rename-inputs.json.gz` | 229,322 | `b4ef0e166fe306118eeb099df5781451fc0716134ba382c9d8803861459c95b3` |
| `hierarchy-rename-inputs.json.gz.base64` | 305,764 | `e6a019df2e2cd8de564379a3cbb3d3ece73ae397d167d14ef18b72e32e10bc17` |
| Decoded transport JSON | 1,068,552 | `ec0c1a2e04af03cac8e85cc6c7d726c74897768a31825819744e6914dc8016a6` |
| `stager-derivation.json` | 12,077 | `e4c20e6a17e65a3a41be31fe85b579ab1e6e3381f61fdd1b9a4e958d8e139de0` |
| `transport-manifest.json` | 1,736 | `e6316b9b58cc502b401a88de9d6c26770edc8d6ed7da45f3c427b5eccd56e4df` |
| `one-shot-invocation.json` | 1,642 | `1681f9fb7908222e22bdfe86927d0c91645cea599296a6846d3e8709acbe2bb3` |
| `payload-readback.json` | 15,539 | `235ce44de367dbba431cabe38012cc3646bdc82b5c5670a27a26accdbe26f173` |

The payload contains the exact original input-packet JSON plus **61 input files / 781,373 decoded file bytes**. Every file was decoded and compared against its original local input bytes and SHA256. The deterministic gzip has mtime0. The payload does not contain outer review/docs files or copies of the 102 Crypto dependency artifacts; it contains their unchanged exact manifest, which governs future read-only validation and private copying.

## Complete inverse to the proven stager

The donor is Property4 `materialize_and_exec.py`, 9,982 bytes, SHA256 `2a7ef1c0d7f5957ef1194b27d34a5456d254b1d077f6e3eceda628925f236a1b`. The derivation records all 18 exact replacement rules and complete bidirectional byte hunks. Reversing those hunks restores every original byte.

Six helper bodies remain identical: `sha`, `now`, `physical`, `budget`, `mkdir_owned`, and `crypto_sources`. The only main-function changes are fixed root, source/review/payload pins, schema labels, sizes and file counts. No lifecycle, exception, directory creation, path validation, dependency comparison, resource or exec logic changes were introduced.

The one future root is:

```
/mnt/development/projects/evidence/pinkha-wave2-hierarchy-rename-20261127
```

The exact future uploaded payload path is:

```
/var/lib/sentinelx/uploads/pinkha-wave2-hierarchy-rename-inputs-b4ef0e166fe30611.json.gz
```

The future stager path is pinned by its content hash in `transport-manifest.json`. These are preparation locators; no upload or remote path creation occurred.

## Retained staging and command boundaries

The inherited code rejects an existing root, including a symlink; validates the exact physical payload, size, SHA256 and stable file identity; validates the embedded packet and every canonical relative path; and refuses traversal, absolute names, duplicates or unlisted entries. It creates only fresh physical owned0700 directories and exclusive owned0600 regular files with one link, fsyncs each new file and verifies its bytes and the complete final inventory. Failures retain the partial owned directory and the original failure; there is no overwrite, cleanup retry or automatic namespace change.

The exact original Crypto102 source/copy/alias checks occur before and after staging. Their physical contents, identities and hashes must remain equal. Existing source/reference files are read only. Their current availability has not been inspected here, and no access-time preservation or cache-warmth claim is made.

The original pre/post staging resource gates remain **2GiB root +32MiB margin** and **512MiB Development floor +256MiB containment +32MiB margin**. The inherited runner retains its memory gate, whole-owned allocation cap with1MiB final reserve, jobs2,300-second Swift deadline and original owned cleanup helper. No larger limit or alternate execution path is introduced.

Before exec, the stager changes its actual cwd to ROOT, sets `PWD=ROOT`, verifies both and records them. It then uses the original `os.execv` to replace itself with the fixed reviewed runner. It creates no controller child or additional process manager. The runner captures and owns the single Swift command, preserves its first failure, and requires original terminal-group proof before qualifying release. No historical PID or group is queried by this preparation.

`PASS_EXACT_INPUTS_MATERIALIZED_PENDING_EXEC` would describe staging alone; it is not a test PASS. The actual component receipt must independently qualify all four methods/eight cases and actual compiler closure.

## One-shot handoff remains closed

`one-shot-invocation.json` supplies an argv prefix requiring one actual16-digit coordination story. That argument documents external scheduling and grants no slot. Root remains the sole remote mutation/execution owner. Exact source review, future upload/readback, W1 owner release, genuine coordination and fresh unchanged resource/dependency admission are required before invocation.

Preparation performed only local byte assembly, complete payload readback, Python AST inspection and inverse verification. Neither the stager nor runner was imported or executed. No compiler, Swift tests, host/cache probe, upload or runtime-window request occurred.
