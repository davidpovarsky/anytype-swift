# Forward warm staging from the retained 8f2 checkpoint

**Status: local source proposal; staging, build and runtime activation are closed.**

This packet prepares a forward transition of the existing physical App source and DerivedData. It does not claim that the target source has been published, that the current Mac has capacity, or that any new Apple test has run. Root remains the sole staging/build dispatcher.

## Actual starting point

The retained root observation at 2026-11-27 15:45:40 UTC identifies:

| Input | Observed identity |
| --- | --- |
| Source | `/Users/m1/development/anytype-d-active-20261125/main14/source` |
| Source HEAD | `8f2c11713fb8a40ae13444104723666ffef68afe` |
| Source tree | `7bcaa6e1b6eadf42eaaaebcb75aab84686aa1f9a` |
| Worktree status | Clean |
| Canonical SDK | `38528941720d9b4f2da8dce7afbc788c2e554a0c` |
| SDK marker | 170,264 bytes; `b10eb0805789a04f9f48721230961e45ba6a93ceb5d95cb90437a59c87ae9528` |
| Main resolved lock | 15,183 bytes; `e22368e522ac795253935b0a31e39d1b36bd9043ef2ed1014845927914527ccd` |
| App DerivedData | `/Users/m1/development/anytype-d-active-20261125/main14/app-derived` |

The original response is retained under `originals/root-warm-source-1545.sentinel-response.json`. Its free-space and process rows are historical observations, not a present resource admission. The new controls never probe those historical process identifiers.

The original failed 6aab App build, original App15 source/products, and actual 8f2 predispatch checkpoint remain distinct. The old warm stager is retained as evidence and is not invoked: it was specific to 6aab and its old process groups.

## New source files

| File | SHA-256 | Purpose |
| --- | --- | --- |
| `after/stage_wave3_forward_warm.py` | `f7ff8cc492918d7e77686d408f430ee0c39647ee3fb3bdd353f14168fc84bec7` | Bound forward source staging, preservation, exact SDK/Kit transition, and a fresh ready-false cache/build draft |
| `after/wave3_forward_warm.py` | `80c9d213ba95072125bf863917b1f98e4db24fa174cf170e743c66c124d2f245` | Forward cache admission and reversible expansion of the original producer |
| `after/priority-runtime-selection.closed.json` | `9d4ec5c867a9d03f6d0d41d5c52c7faaafc6116e09c0c135cd3790c76940d170` | Exact original focus22/34 and editor4 selection, with runtime activation closed |

The original d77 adapter is `47c66dde…`, and the original 204f producer is `9b1405ea…`. Their complete bytes are retained. The expanded producer will still require a complete inverse to the original 204f bytes and exact original `run_phase` and `source_state` function bodies. No expansion or hash is claimed before the target admission is concrete.

The adapter has seven literal inverse operations to the retained c4b warm adapter. The dedicated stager has a complete positional byte inverse to the retained e6f stager. Six original warm declarations are unchanged, including the strict package checkout and shared-writer checks. These are source proofs, not execution results.

## Finite staging sequence

1. Require a separately hash-bound root plan with `readyForStaging: true`, the exact published target commit/tree, immutable Git bundle, final SDK revision/reader/marker, native receipts, complete compiler-source inventory, toolchain observations, and a finite root-coordinated owner window. The included proposal keeps the target values null and the ready flag false.
2. Recheck the original physical source/DerivedData, clean 8f2 identity, untouched 8f2 predispatch output paths, original App15 retention, full failed-6aab retained node manifests, and unchanged original failure evidence.
3. Run the original all-host census and shared-cache writer check. Require no matching heavy compiler/copy process or queued launcher, and sufficient staging capacity. This is a cooperative owner-window admission plus fresh observations; it is not a global atomic lock across unrelated owners.
4. Create a fresh owned `main16-wave3-forward-*` root. Preserve the complete current source, current App Products, and prior Kit checkout using actual APFS clones. Compare every original/clone/original-after inventory entry: kind, mode, timestamp, link target and file content. No full-copy fallback is allowed.
5. Verify the Git bundle and target tree, prove the current source is an ancestor, inspect the exact target lock, then perform one normal fast-forward. There is no reset, rebase, forced ref movement or cache cleanup.
6. Move the already preserved SDK385 materialization into the owned retention root and invoke the exact target source's original `prepare_sdk.py` against its explicitly supplied immutable Git reader. Require the full resulting marker hash and the unchanged target lock bytes.
7. Resolve only the exact lock using the existing source/DerivedData/SourcePackages paths, with the original selected Xcode environment and a 600-second owned command. No App compilation or test execution is selected in staging. Recheck all 56 real checkout HEADs, workspace states, and nonignored untracked-file status.
8. Verify that the exact native framework already installed in the source matches the supplied qualified two-slice assembly and inventory. This route is reuse-only; it does not replace the framework, build native code, or promote a new native manifest.
9. Check every selected App-hosted and complete Stage1 UI source against the final source-bound inventory. Clone the untouched 8f2 UI cache into the new root using APFS, retain the exact original lifecycle helper, and produce new staging/cache receipts plus `build-admission.draft.json` with `readyForBuild: false`.

Every new external command uses the unchanged original73bb process owner behind a barrier. The next command cannot start while an owned group is unresolved. Terminal failure handling preserves the first failure and performs only evidence writes; it starts no Git command, process probe, cleanup or simulator action.

## Package transition and unresolved inner manifest

The two retained main locks contain exactly 56 identities. The only allowed row change is:

| Identity | Before | After |
| --- | --- | --- |
| `torahinspectorkit` | `9058b489e9acc271b4f8ef69e2ed24648f93b4ed` | `26beca175d64a4d34e3567f2bbb4bf308d714478` |

The target lock's reviewed hash is `4065a37e9e6dd3c117bd72bec90c2039108a0985df6989f9dc66b0f47840f689`. All 55 other pin objects are unchanged. The actual checkout set and every unchanged path/revision/state must remain equal before and after resolution; only the Kit checkout revision may move. The four canonical SDK package paths remain at their existing source-root locations.

Root reported a separate source issue: `Modules/PinkhaKit/Package.swift` still requests the old Kit revision while the outer lock selects Kit26. The SDK owner is checking this exact mismatch. This packet does not edit that file or reinterpret successful locking. Root must supply a coherent published source before admitting resolution. A resolver failure is retained as an actual failure, not converted into permission to rewrite locks.

## Build resource policy

| Phase | Own growth allowance | Live emergency floor | Concurrent allowance | Total admission |
| --- | ---: | ---: | ---: | ---: |
| Source staging | 536,870,912 | 2,147,483,648 | Included in finite source window | 2,684,354,560 bytes |
| App | 6,442,450,944 | 2,147,483,648 | 536,870,912 | 9,126,805,504 bytes |
| Complete Stage1 UI | 1,073,741,824 | 2,147,483,648 | 536,870,912 | 3,758,096,384 bytes |

The App and UI phase monitors retain the original four-job scheduling, original 7,200-second phase bound and original live own-process emergency-floor behavior. The 6 GiB App growth allowance is the retained conservative estimate, not a newly measured peak. The final native producer's 24 GiB policy and the hosted cold-build policy remain separate.

The build adapter re-reads the new cache and baseline-preservation receipts, current package checkouts and SDK identity, captures a fresh all-host census, and requires the full App admission. An earlier source-stage success or earlier free-space number cannot authorize compilation.

## Priority runtime scope, now source-bound

The primary queue at commit `2519140dd1966cedc4403b74f0f00479e9bd289f` is retained exactly: 16,946 bytes, SHA `55486639642fdf24a02f963b79683941fb46f4229884d1e0ecde90b417aec00b`.

### Focus lifecycle

The original `focus_lifecycle_profile.py` is 6,213 bytes, SHA `c495985b9afc278c13ec8900049f9835cee5fd74fc368e2e7b264ecf718c5812`. Its full Swift source is 44,681 bytes, SHA `2b1d3dbe3ad8c1e6e262eeea15a99e0c292dd693118f926c893f7bf9dfc8ac0b`.

The plan is `focus-lifecycle-only`, lane `focus-lifecycle`, stage `native`, original target `AnytypeTests`. The complete suite invocation is `AnytypeTests/TextBlockFocusLifecycleTests`; the exact 22 named methods and 34 literal cases are in the closed selection JSON. The original source declaration, compiled-enumeration, named-result and literal-argument validators remain unchanged. Enumeration is 180 seconds, per-method allowance 300 seconds, and the whole suite command 600 seconds.

### Four original editor UI journeys

The `first-editor` plan first invokes `AnytypeTests/PinkhaStage1AcceptancePreparationTests/prepareRealApplicationState()`. Its original state-save call creates the fixture read by the controller as `pinkha-stage1-acceptance-state.json`. The test source delegates the filename to the original state type; the filename is not duplicated as a literal in that test file. A first local source-inspection assertion that expected a duplicate literal is retained under `proof/priority-intake-attempt1.json`; no candidate source changed.

The original editor lane's first three methods plus the original combined controller's explicit fourth are:

- `testAppWideDirectionPersistenceAndInteractiveBack`
- `testMultiBlockEnterCreationAndTypingLifecycle`
- `testDocumentSourcesEntryOpensExistingSearch`
- `testUnifiedEngineSwitchRetainsHeartDocumentAndColdReopen`

All four remain in the original `PinkhaStage1AcceptanceUITests` source/target. The original budget function assigns 300 seconds to each of these methods: 1,200 total method seconds and the original 300-second command overhead. Preparation has its own original bounded stage. Actual opposite simulator/app languages, fresh preparation, original startup prerequisites, result/attachment preservation and screenshot evidence remain required. Device family, language and appearance are unbound here.

Historical focus21/32 acceptance does not qualify focus22/34. Core16 plus RTL6 is a separate22/26 profile. The original failed editor preparation and its uninvoked UI methods remain separate retained evidence.

## Execution interface after root binds the actual inputs

The command tokens are retained in `after/commands.unbound.json`; no supplied command is ready to invoke. The forward stager interface is:

```text
python3 -B <exact stage_wave3_forward_warm.py>
  --plan <exact source-staging.approved.json>
  --plan-sha256 <actual approved-plan SHA256>
  --accepted-source <actual published target commit>
```

The build adapter keeps the original CLI: `--admission`, `--admission-sha256`, `--accepted-source`, `--original-adapter`, `--original-producer`, `--output`, and optional `--execute`. Root first needs the concrete expansion and full inverse for review, then separately owns effective admission and supervised dispatch. The included build draft has no target source or effective approval.

This producer compiles the original App and complete Stage1 UI phases. It does not compile the separate two-source Native UI target. A consumer requiring61/10/2 receipts still needs that separately reviewed third compiler phase. The two priority plans above use the App-hosted focus/preparation tests and Stage1 UI target, but their original App15/source/native admission must still be bound through a reviewed current-product consumer. This packet supplies selection and staging source; it does not waive those runtime guards.

## Remaining concrete inputs

- Actual published App commit/tree and immutable transport after the queued integration work, with the inner/outer Kit declarations reconciled.
- Actual final SDK revision, complete marker, exact materializer and an immutable local Git reader with that revision's required objects.
- Root's exact native choice and physically present qualified framework/receipt tuple. No unknown future native may be substituted.
- Complete final compiler-source inventory and actual source hashes, without substituting a historical43/57/61 count for enumeration.
- Fresh same-environment toolchain originals, finite owner window and fresh source/cache/resource observations.
- Exact physical control/output paths and the actual source-stage/cache/preservation receipts.
- A reviewed current-product runtime consumer and device/configuration admission for the exact focus22/34 plus editor4 plans.

Source-only checks performed here were byte hashing, AST/literal inspection, inverse reconstruction and original-source comparison. No candidate module was imported; no Apple command, test, simulator, account operation or remote source mutation was performed.
