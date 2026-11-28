# Queue dependency metadata — actual completed observation

**PASS: dependency metadata only. No queue build or test acceptance.**

Root's exact metadata controller completed job `job_8214c33ac02a` on Oracle from **2026-11-28 14:26:05.914727 UTC** to **14:26:11.063750 UTC**, exit 0. Its one owned command ended normally, without signals or forced cleanup, and the process group was positively absent. The result identifies **291 packages and 16 module versions** for the explicit queue source/test files. Only `runtime/cgo` and `net` appear in the reported Cgo package list.

## Which record establishes the result

`actual/qualified-controller-stdout.json`, recovered from the exact successful Sentinel notification, has `terminalReceiptQualified: true`. It joins the full hashes of the primary receipt, terminal candidate and read-only module-view receipt after the final source, resource and persistence checks.

The original `actual/result.json` remains **PROVISIONAL_NO_ACCEPTANCE**. The original terminal candidate remains **QUALIFICATION_CANDIDATE_NO_STANDALONE_ACCEPTANCE**, with its explicit requirement for exact successful controller stdout. Both files are preserved unchanged. Neither is promoted into an independent PASS record.

The directory-view receipt is similarly limited to its verified pre-exec mount boundary. Its READY status alone does not establish Go execution.

## What the completed observation established

- Exact five original inputs, ten staged inputs and four controls passed their final checks.
- The child used the fixed read-only/noatime module-cache view, with the source/view identity and mount flags qualified. The parent's mount namespace remained equal before and after the command.
- Final owned allocation, including final receipts, was **6,791,168 bytes** across **872 entries**.
- Maximum sampled group RSS was **38,817,792 bytes**. This is a sampled observation, not an unobserved instantaneous peak.
- **Zero test methods** ran. Source compilation and test acceptance were not requested or claimed. No retained account, native engine or E cache was accessed.

The exact executed controller, wrapper and two independent source peers are retained under `controls/` and `reviews/`. The controller contains its complete source packet. The original source carrier, beforeimages, adoption map and test selection remain unchanged at parent `bdc80e1ef8c4715ee215ebe48d9bb6502478fbe1`.

## Retained external evidence

The **768,258-byte** original metadata log remains at:

`/mnt/development/projects/evidence/pinkha-w1-files-queue-component-20261128-metadata1/commands/go-list/original.log`

SHA256: `208fe7fd9f48df42ddc27372fd642b337d4c6615407373987427f2bbc9233c50`.

It was not reread or copied for this publication; its hash is joined by the retained primary and qualified stdout.

Root's later, separate source/tool closure manifest remains at:

`/var/lib/pinkha-w1-files-queue-component-20261128-inputs1/source-inputs.json`

**1,142,387 bytes**, SHA256 `44e569defe3fc7e96efc3fbdc22778147484e4fdf3547d809bc43a7ab3785192`. Root reports 1,820 files / 89,923,332 logical bytes / 291 packages and no Go, compiler or test invocation for that observation. This is a locator handoff, not a fresh independent read or part of the earlier metadata job.

## Publication and acceptance limits

The three receipt files were read once through the retained bounded NOATIME/NOFOLLOW reader. Their complete raw UTF-8 bytes and nanosecond integers are unchanged. The exact notification and transport stdout are retained; large integer metadata was not regenerated from JavaScript numeric values.

This evidence is additive under this directory. All prior source, tests, beforeimages and native gates are preserved. At this metadata milestone, the six new and four affected queue methods are **NOT_RUN**, as is the baseline defect reproduction. A later component build/test result needs separate actual evidence.

This milestone does not establish cloud quota recovery, successful uploads, resumed cloud bytes, account authorization, native64 acceptance or a general filesystem sandbox. It does not execute or approve the later build wrapper/controller. Root remains the owner of that separate admission.
