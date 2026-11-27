# Bookmark6 exact stager and input payload

**Prepared locally for source review. No upload, remote materialization, compiler invocation or runtime lease has occurred.** The execution inputs remain exactly packet `2341bdb226521d368b37f37c402c83b6bb20ae1db6efe4d7f65938198f5f1353`, runner `3729eed7d91e3400c19137420df96465d4785c0bd9587d81553864e1041f176c`, and Package `e030600787c19dee1002c8223b34fe499e5832d213259c8796eb164fb3ed83be`.

## Fixed artifacts

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `materialize_and_exec.py` | 9,969 | `0a4d01543136969aeb363bd56d0b87716fc25dab302b5580932740cefc28a548` |
| `bookmark6-inputs.json.gz` | 389,854 | `14e9844ac5959bb70537d4b366c9a64cc7f7f9f955c7ccb5b28ed2ae52b60a23` |
| `bookmark6-inputs.json.gz.base64` | 519,809 | `6054954a308a8e7584dac640f1ced00a7cb49ab52f273171e3f5a798616077f7` |
| Decoded transport JSON | 1,839,657 | `8d37c7881f66b902f7f7c137a981eff1e2073e627b9e2739ee96d6c149aeef2e` |
| `stager-derivation.json` | 12,972 | `d995018c6ffd1821d41be0678678479406ca7df033d6cb1f02c0991c56445ac4` |
| `transport-manifest.json` | 1,620 | `0c9bf26dac72e6c63f8becd48ab78df19f4c582a595231b780557f055efd0d1f` |
| `one-shot-invocation.json` | 2,201 | `0bb5d9bfbcb869b3ce27f02c640aa600ff5fba1daf84ed1cabba30db73bb490f` |
| `payload-readback.json` | 26,602 | `7292cf8ba947e69edb75a64a54398b14e406bb2398761720dee9df9f3c9ae1e6` |

The deterministic gzip contains the complete, unchanged 28,662-byte input packet and **90 exact input files / 1,344,177 file bytes**. Every embedded file was decoded and compared with its existing input bytes, SHA-256 and Git blob ID. No second uncompressed source tree was created. The payload contains the Crypto manifest, not the 102 dependency artifact bodies; those remain subject to fresh physical and alias qualification during a future owned attempt. Outer reviews, toolchain provenance and historical source v1 are outside the runtime payload.

The reviewed component declares four XCTest methods and two Swift Testing methods. The 17 Host fixture scenarios are not 17 enumerated test cases. The original seven Host and 27 Integration methods remain unselected. Actual mixed-framework discovery, all six method outcomes, nine compiler/link groups, 84 whole original Swift sources and four generated support sources remain unobserved for this candidate. Neither the published Bookmark source nor the donor's earlier component result supplies that evidence.

## Complete inverse to the executed donor

The donor is the 9,998-byte hierarchy stager `b3cfea8a789c4abae7f2f2b8aa3202dc7cf2725a5fae2438eb5c5c9d6342f7eb`, published in preparation commit `8b70497157758f3ae8148842f1236d215d6d2d50`. Its exact actual launcher and completed component review are retained in the local hierarchy custody folder; actual-result publication `0b748192d230966160df010b93987638f5e161b9` preserves the separate executed result.

`stager-derivation.json` contains every literal replacement plus full bidirectional byte hunks. Reversing those hunks reconstructs the complete original donor. The six helper bodies—`sha`, `now`, `physical`, `budget`, `mkdir_owned` and `crypto_sources`—are byte-identical. Only fixed source/root/review/payload pins, schema labels, sizes and counts differ. Original admission, path validation, physical custody, exclusive creation, partial-failure retention, cwd/PWD and exec behavior remain unchanged.

The new stager binds Root's execution-source review `4e829323bf17271712bfbb8696ed832d621be8ca3a6e794c2bcae5b21d44e8f0`; peer review `b9b104c5f9ab799c0f191746b50a745821607d55f4b29e1146c148fd30291329` is recorded in the derivation. These source reviews grant no runtime slot. Execution source v1, the product-bound read correction, and both reviews remain untouched.

One retained toolchain metadata label is imprecise: the original `PackagePIFBuilder.swift.primary.json` field `originalUTF8Bytes` records 36,142 characters; the actual retained body is 36,172 UTF-8 bytes with its exact original Git identity. Root's v2 review documents this. No retained primary metadata was silently rewritten here.

## One fixed future namespace

```
/mnt/development/projects/evidence/pinkha-wave2-bookmark6-20261127
```

The future upload names are exact content-bound paths:

```
/var/lib/sentinelx/uploads/pinkha-wave2-bookmark6-stage-0a4d01543136969a.py
/var/lib/sentinelx/uploads/pinkha-wave2-bookmark6-inputs-14e9844ac5959bb7.json.gz
```

These are preparation locators. Their current presence or capacity was not queried. The original code requires a physical existing parent and rejects an existing root, including a symlink. Before creating that root it verifies the physical payload, its stable identity, exact compressed and decoded lengths, hashes, packet, complete finite path set and the original 102-file source/alias closure.

Only fresh owned `0700` directories and exclusive owned `0600`, one-link regular files are created. Each file is fsynced and read back. The completed staging root must contain only `inputs/`, with the exact 90 files and no symlinks. The original Crypto sources are checked again and must have unchanged physical identity/content and alias targets. Existing dependencies are read only; no access-time preservation or cache-warmth claim is made.

Any failure retains the partial owned staging namespace and fails the attempt. There is no overwrite, retry, alternate directory or cleanup of historical evidence. No old process or group is queried by preparation.

## Original admission and command limits

| Boundary | Unchanged requirement |
| --- | --- |
| Before and after staging: root free space | 2 GiB + 32 MiB = **2,181,038,080 bytes** |
| Before and after staging: Development free space | 512 MiB floor + 256 MiB containment + 32 MiB margin = **838,860,800 bytes** |
| Runner live root / Development floors | 2 GiB / 512 MiB |
| Runner memory floor | 512 MiB |
| Whole owned execution allocation cap | 256 MiB, including the original 1 MiB final-evidence reserve |
| Swift command / outer job deadline | 300 seconds / original 360-second envelope |
| Parallel jobs / automatic retries | 2 / 0 |

The 256 MiB cap is containment, not a forecast that the larger graph will fit. Fresh admission remains mandatory; this preparation does not lower a gate or establish current capacity.

Before exec, the stager sets and verifies its actual cwd and `PWD` to ROOT. The unchanged runner's SwiftPM subprocess cwd remains `ROOT/component`; actual compiler working directory must be ROOT. The stager replaces itself through the original `os.execv` and creates no extra controller child or process manager. The original owned-process helper remains `58624c3f6eae79e5417576ba88d24fe15919681ca6ac112e14e664b9ab12b924`.

`PASS_EXACT_INPUTS_MATERIALIZED_PENDING_EXEC` describes staging only. Actual test and compiler qualification remain the separate runner's responsibility.

## Review and execution remain separate

`one-shot-invocation.json` supplies an argv prefix that requires one actual 16-digit coordination story. The argument records external scheduling and grants no authority. Root remains the sole remote execution owner. The exact stager/payload review, separately approved publication and upload readback, W1 owner release, genuine coordination and fresh original source/dependency/resource predicates must all precede invocation.

This preparation performed local byte assembly, gzip readback, Python AST inspection and complete inverse verification. It did not import or execute the stager or runner, add or replay synthetic controls, query a host, upload files, create a Git object, request a runtime window or execute tests.
