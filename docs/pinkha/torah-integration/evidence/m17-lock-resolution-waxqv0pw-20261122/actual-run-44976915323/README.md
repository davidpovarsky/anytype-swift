# Actual M17 strict resolution result

**Verified component outcome: PASS for the original Maktabah CocoaPods workspace at `813fbe79c1b325ee21a8c2be78bb86577f44bf6c`. No package-lock repair was required.**

The single push-triggered run was [44976915323](https://github.com/davidpovarsky/anytype-swift/actions/runs/44976915323), attempt 1, workflow checkout `0c183ed56c24ba3db34a6e11a52504b89efd9db0`. Its only job, `137068759064`, completed successfully at 2026-11-22 02:41:52 UTC. The dedicated trigger ref stays at that exact checkout; later evidence publication uses only the neutral draft ref.

## Actual execution

| Boundary | Observed result |
|---|---|
| Original preparation | Existing Hanlin, React and CocoaPods preparation completed in 175.24 seconds |
| Apple toolchain | Xcode 27.0, build 27A266a; original SDK 27.0 |
| Original strict resolver | `xcodebuild -resolvePackageDependencies -workspace Maktabah.xcworkspace -scheme Maktabah-iOS -clonedSourcePackagesDirPath <owned>/build/SourcePackages -onlyUsePackageVersionsFromResolvedFile` |
| Strict invocation | Exit 0 in 62.4408 seconds; no timeout |
| Automatic resolution / second strict pass | Neither was executed; the first strict operation succeeded |
| Original lock | All five retained copies are byte-identical: schema 2, 17 pins, no `originHash` |
| Lock Git blob | `99a5b952aab40cb3d5ffe03153c9cf8c07ed341b` |
| Lock SHA-256 | `722609bb6b71362aee5e7f401246edcd037a2d1815c2fc4704bf93830d9f5530` |
| Actual package checkouts | All 17 materialized at the exact locked revisions; no additional untracked checkout inputs admitted |
| Workspace closure | All 268 retained configuration inputs are unchanged after resolution; both Maktabah and Pods projects are present |
| Package ownership | All 36 app package objects and seven project/target owner records, including attachment arrays, remain exact; Pods introduces no Swift package objects or attachments |
| Hanlin source | All 424 original Git input records match before preparation, after preparation and final verification at `e00498e33f106cc43be0476ffa2e09329c8ca300` |
| Source provenance | Immutable source HEAD/tree unchanged; 23 input blobs were independently compared to actual Git objects at `813fbe79` |

The actual CocoaPods preparation produced only its reviewed project and privacy aggregation changes in the fresh CI checkout. Original source and generated configuration evidence are retained. Nothing was copied back over application source, and the original project lock needs no update.

## Retained evidence

The original artifact is `artifact-original.zip`, GitHub artifact `14736187053`, 313,527 bytes. Its SHA-256 is `d6a20ad46fdc0ca33d21bd310c0aed9b0b2777ee0f15b70210a04ac0b585ae81`, matching GitHub's artifact digest. CRC verification passed for all 61 members, which are also extracted under `evidence/` without modification.

`INDEPENDENT_ARTIFACT_AUDIT.json` records the direct command/log/lock/workspace checks. `COMMITTED_SOURCE_VERIFICATION.json` records the separate actual `git cat-file --batch` comparison. `ROOT_ARTIFACT_REVIEW.json` is the independent parent review against the same already-downloaded artifact. `audit_archived_resolution.py` reproduces the archive checks without executing preparation, Xcode or tests.

The single Sentinel observer `job_6ef549c63ea5` ended naturally after observing the successful terminal state. No process-stop command, replacement observer, CI cancellation or repeat dispatch occurred. The retained observer used a finite custom status reader; a subsequent guidance review selected native `gh run watch --exit-status --compact` for future runs. By that point this run was already complete, so no second watcher was needed.

## Qualification and later reuse

This is genuine Apple package-resolution evidence for the original generated CocoaPods workspace. It is not application/framework compilation, editor rendering, Native acceptance, provider execution or a completed integration task. No application or framework build and no test suite ran in this lane.

The result is bound to `813fbe79` and its original preparation closure. A newer consumer can reuse the result only after an explicit comparison of its package requirements and owning attachments, all 17 full pin objects, local manifests, original preparation code/inputs, and actual Hanlin source. A newer application SHA alone neither invalidates nor proves this identity. Do not replace a newer generated project with the archived project, and do not fabricate an `originHash` for this valid schema-2 lock.
