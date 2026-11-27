# Current Properties display lifecycle

This separate Wave 2 core-source tranche prevents a native Properties panel from retaining an earlier readable snapshot and Undo after the current read fails or the mounted owner deactivates. It is based on `c95395aec96214dfabd73d55755baa95689cc6d3`; the frozen shared Apple source `8f2c11713fb8a40ae13444104723666ffef68afe` is unchanged.

## Behavior

A current, correctly owned read failure clears displayed values and Undo and requires explicit review. Deactivation also clears the previous displayed snapshot and Undo. The existing epoch/request guards still prevent late old reads and write completions from changing the new owner. An already-dispatched uncertain edit is retained until a successful current review; this change does not retry, abandon or duplicate a native write.

Derived Source, Topic and Word rows now require active, reviewed ownership. With a configured native property store they remain hidden until a current snapshot exists, so discarding a failed snapshot cannot reveal a previously hidden derived field. The existing source-only workspace fallback remains when no native store is configured.

The native store, engine/Host contracts, three distinct chiddush/article/research Types, original property definitions, Tag values and canonical associations are unchanged. The original native Properties view and document constructor remain the shipping path.

## Exact source and regression scope

`source-inverse.json` binds both original and candidate files and restores their original bytes. The seven existing test journeys remain; the old reactivation expectation now requires `snapshot == nil`, because the prior owner's values must disappear before the next read. Two new Swift Testing methods cover read failure (typed403 and changed-document scenarios in one internal loop) and deactivation/reactivation. This is nine framework methods, with three new internal scenarios, not three independently enumerated new tests.

Independent Torah and editor source reviews found no remaining concrete lifecycle blocker. The retained review receipt is source review only. The actual staged source-retention gate passed all129 unchanged mappings; its full original report and logs are retained. Source retention does not establish runtime behavior.

## Current validation status

At this source publication, the new component tests, Apple compilation, actual native service/UI and visual acceptance are **NOT_RUN**. The exact component input custody was read successfully on Oracle at `2026-11-27T04:35:33.616735+00:00`: all370 dependency source files, original Add-block source copies/results and the resolved dependency graph matched. That does not execute any tests.

The planned finite component phases are the two new regressions against the original model, then all nine methods against the fixed model. They reuse the already-qualified Add-block dependency cache sequentially; its two accepted methods are not selected again. The runner requires the coordinated2GiB live disk floor plus a conservative256MiB incremental allowance, uses one compiler job, and records actual command, process, source envelope, output and before/after dependency custody. Current free disk is below that admission. No component compiler has started.

The Linux preparation removes only the SwiftUI availability/import envelope and the two document-bound convenience constructors; it compiles the actual Foundation/Observation state model and typed injected operations against the complete original Engine/Host/Integration/Kit packages. The unchanged production error-description enum is copied exactly. This is a declared component envelope, not a fake SwiftUI implementation or full Apple compilation. App lockfiles remain untouched; the component's actual ASN1 resolution is recorded separately.

The runner and preparation helper are under `Tools/PinkhaDualEngineRuntime/property_lifecycle/`. Existing private inputs and future original evidence are under `/var/lib/pinkha-wave2-property-lifecycle-20261127`; the handed-off cache is `/var/lib/pinkha-wave2-native-block-menu-20261127`. No native account is opened by these component phases. Original failure attempts will be retained in separate evidence directories.

## Remaining acceptance

Actual two-regression baseline and nine-method fixed results must be recorded. The next matching Apple build must compile/enumerate the changed suite and exercise real Properties open/add/edit/Undo/reopen and ownership/permission changes. Native ACL and persisted values, all three document Types, UI appearance and physical-device acceptance remain distinct gates. No Release or full-core acceptance is claimed by this commit.

## Runner review before actual model execution

Five concrete controller findings were corrected before any Properties model test started: guaranteed cleanup after post-launch exceptions, exact production Error enum and original dependency closure pins, complete physical dependency input sets, truthful classification of baseline failures pending inspection of their intended expectation issues, and positive process-group absence. The historical Add-block process ID is never probed again; its original pinned owner handoff remains the evidence.

The final runner is 99dcacdacace01b4b7c0646c09dafb45c9b8d167781043542bc6c0ed2a7103e2. The original two runner revisions, both reviews and exact final inverse are retained under runner-review/. A single genuine local Python process probe completed in 0.151 seconds: the leader exited, its child remained, the actual cleanup helper delivered TERM, the child was reaped, and a signal-zero group observation returned ESRCH. Later cached calls issued no further group probe. The deliberately failed original phase stayed FAIL with its exact exception while cleanup was recorded separately as PASS. SIGKILL escalation and permission-error branches were source-reviewed only.

This probe did not run Swift, a Properties model test, Native, an App or UI. The planned two-method original-model and nine-method corrected-model phases remain NOT_RUN pending the same host disk admission; none of their outcomes is inferred from controller or source checks.
