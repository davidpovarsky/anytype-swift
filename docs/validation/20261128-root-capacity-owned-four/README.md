# Finite Oracle ROOT ownership observation

This is an evidence-only record of one completed read-only ownership review on the established Oracle host. It is separate from W3's Mac cleanup: Mac reclaimed bytes are not Oracle ROOT capacity.

## Result

The observation reported **1,322,082,304 bytes available on Oracle ROOT**. It established **no safe candidate of at least 600 MiB** for disposal or relocation within its four-directory, direct-entry scope. No deletion, relocation, copying, native invocation or compiler invocation occurred.

The three old Files native producer directories no longer contained their `any` executables. Both comparer archive leaves were already symlinks and were not followed. Direct regular-file allocation across the four directories was **909,312 bytes**, consisting of retained source controls, manifests, receipts and logs. This is not a recursive allocation total and is not disposable capacity.

## Exact observed scope

- `/var/lib/pinkha-c-filesv2-20261126/lan-progress-native1`
- `/var/lib/pinkha-c-filesv2-20261126/readguard-native1`
- `/var/lib/pinkha-c-filesv2-20261126/final-authority-native1`
- `/var/lib/pinkha-w1-closed-comparer-root-custody-20261127/attempt1`

The observer enumerated only direct entries, using anchored no-follow directory access and `O_NOATIME`. All four complete directory identities were unchanged before and after. It read exactly two already-pinned public custody receipts, requiring complete stable metadata and byte/hash equality: the original comparer custody receipt `6b176cc1…` and final-authority native custody receipt `121542a2…`.

Source trees, generated-output descendants, toolchain records, unique evidence, accounts, current native products, pending caches and other lanes were not admitted for disposal. No recursive census or process/PID probe occurred. Symlink targets were not read.

## Bounds and provenance

- Actual tool job: `6602d97e136f451c92831c116a24130f`; exit 0; tool duration 0.05 seconds.
- Observer duration: 0.008823 seconds; 28 direct entries; errors empty.
- Fixed bounds: 10 seconds, 256 direct entries, 32 KiB output, 128 MiB address space, zero regular-file/core output allowance.
- The exact script is retained as `observe_owned_root.py`; publication does not authorize rerunning it.
- Tool transport created and cleaned its normal temporary script workspace. The observer created no project artifact and changed no reviewed source, account, cache or evidence path.

## Exact artifacts

| Artifact | Bytes | SHA-256 | Git blob |
|---|---:|---|---|
| `observation.json` | 17,742 | `7a320e75d326da64ac109204433684fe6e407aa3e6828cbbb56ef7b4971c204e` | `94c798ee523eca03047e22372d820db61673f213` |
| `observe_owned_root.py` | 6,226 | `3774c4725ee8517a5551470595ee3cd245d1ec7c669ffce083da3c36266acac4` | `5635125e38a867098f9f5977e95b0ff5b806b447` |

The raw observation is published verbatim, including its original integer nanosecond fields. It is not parsed and reserialized for publication.

## Limits and unchanged gates

This establishes the absence of an **admitted recovery candidate in the stated finite scope**, not a global claim about filesystem contents or every possible owner. The observed free-space number is historical and grants no present runtime admission. No storage-reserve, process-lifecycle, source, account, compiler, native or quota gate was changed. The earlier source carriers, selected unrun tests, geometry observations and other branches remain untouched.
