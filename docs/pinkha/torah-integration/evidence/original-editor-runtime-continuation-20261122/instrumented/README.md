# Instrumented continuation of the retained original framework

This source-only candidate follows the authenticated failure packet `e7748857b6f9f622cf1ef13b7059ebc754e54860`. The failed runtime run `45048745285` remains failed: consumer compilation/signature passed, the 180-second boot-status call timed out, no installation ran, and a shutdown timeout prevented the old cleanup branch from attempting deletion. The original framework still belongs to source `edce5b975b173059522f90adb71271fb95adf963`, run `45041382512`.

The candidate changes the runtime runner, adds one observation/retention helper, and extends only its existing workflow. It preserves the original product trees, archive, full distribution inventory, Clang import closure, 245 source controls, 38 public requirements, and both original producer roles. No framework build, previous control replay, alternate runtime or toolchain fallback is introduced.

## Runtime behavior

The runner preserves ten explicitly allowed ordinary environment variables. The four additions are USER, LOGNAME, SHELL and __CF_USER_TEXT_ENCODING. GitHub credentials remain confined to the separate GitHub command environment. The retained comparison established this environment difference but did not establish a cause for the earlier simulator stall.

Read-only snapshots record host memory/CPU/swap/disk facts, process identities without command-line arguments, the owned device's returned state and its persisted plist when readable. Each snapshot has a 35-second requested budget and each child at most eight seconds. Actual durations, timeouts and process-group drains remain recorded. Diagnostic failures cannot manufacture readiness, silently qualify a runtime, or authorize a global reset. Any unknown or incomplete owned process-group drain blocks subsequent mutation and qualification.

The actual signed consumer app is archived before boot. The archive contains all observed files, hidden files, empty directories and their file modes. Its actual code-signature command, exact input/output inventories, current control/run identity and original framework identity accompany it. It is explicitly unqualified and is uploaded as a separate artifact; its approximately 500 MB of uncompressed app bytes never enter the runtime evidence wrapper or original SDK inventory. Its exact size in the new attempt will be measured, not assumed from the failed run.

The single owned boot still uses 60 seconds for the boot request and 180 seconds for boot status. The single install still has 300 seconds and occurs only after successful readiness. The original strict en/he verifier remains unchanged. A failed runtime remains failed even if cleanup later succeeds.

Cleanup now records shutdown failure and continues to the same owned device's bounded delete and post-state request once the previous command group has drained. It makes no unrelated simulator change. Cleanup succeeds only when delete returned success, the actual subsequent list proves the owned device absent, and all relevant groups have drained. An undrained command, unknown state, failed delete or remaining device cannot qualify the run.

## Source and control preservation

All ten original top-level functions other than `main` are byte-identical. `RUNNER_EXACT_INVERSE.json` reconstructs the previous runner's complete bytes; the original filename-only inverse then reaches the exact source used by the retained 24 passing controls. Those raw results and assertions remain unchanged. The workflow verifies both inverses, the ten function definitions, all original helper hashes and the new source bindings without executing any previous test body.

Fourteen new helper boundaries executed once and passed. They use explicit process-response and code-signature receipt fixtures; actual archive creation, hidden bytes, directory/file modes, inventory hashing and helper control flow execute locally. These results establish Python boundary behavior and do not claim codesign, CoreSimulator, Apple runtime or native editor success. The raw outcomes and complete source inputs are under `controls/`.

The existing schema 2 consumer accepts the extra separate artifact and diagnostic fields while retaining its exact role identities, four required successful workflow steps and single-member evidence wrapper. The evidence wrapper still contains only `runtime-continuation-evidence.zip`. The additional consumer artifact cannot substitute for the genuine successful runtime sidecar required by StageB.

No Apple activation is performed by this candidate. The first admitted attempt must rebuild the unarchived small external consumer once; the original framework is reused. A successful signed consumer archive from that attempt would make subsequent exact-byte diagnostic continuation possible without another consumer compilation.
