# Upstream U10 Native Regression Validation — 2026-10-18

## Scope and status

This report is limited to U10: actual execution of the focused native
`AnytypeTests` regressions added or affected by the integrated upstream Chat
Activity, DNS-SD and Quick Capture work. It does not promote a branch, close
the real-device U12/U13 gaps, change T2, or authorize T3.

Final assessment: **U10 PASS (focused native regressions)**. The isolated
macOS Actions run executed all 15 required suites: 197 named test cases and 229
concrete parameter executions passed, with zero failures, skips or timeouts.
The overall Actions job is red only because the post-test count validator used
an incorrect pre-run minimum; the three `xcodebuild` test steps and their
independent `.xcresult` bundles are green. The cause and correction are
recorded below without spending another native run.

## Immutable inputs

| Item | Exact value |
|---|---|
| Trusted source | `pinkha/torah-integration-t2-unblock` at `13d7577bca9c2ed9848a6a46eac49461a9e1c0d7` |
| Upstream candidate | `pinkha/upstream-sync-2026-10-18` at `5641eab469141bf99133cd42eb9cdea7113f12bc` |
| Official Swift input | `d5650321577a209505a3277c8437b7608cff1cb9` |
| Merge commit | `acbd2b242f07a271f983f59c9eba44e4e9d717ea`, ordered parents source then official |
| CI-validated candidate code | `ac7abb29e94f332e3d4ea3c080ddb3fef5eb4e94` |
| Validation branch | `pinkha/upstream-u10-validation-2026-10-18`, created at exact candidate SHA |
| Validation/tested SHA | `0a7db261a922f1e17762861bf497e2713ee216ce` |
| Heart | `v0.51.7-nightly.20261014.1` / `d98420b1113536afd08cde6de9a5816f6d27ffff` |
| TorahInspectorKit | `e8aefc626350c8ee0df9daf8d7de7e1dcd0ea418` |

Phase-0 revalidation found the refs unchanged, the merge parents in the stated
order, and exactly four documentation paths between the tested code SHA and
the candidate final SHA. `Modules/PinkhaKit/**`, `Anytype/Sources/Pinkha/**`,
the Xcode project, Pinkha workflows, native hooks and the Kit pin are unchanged
between source and candidate where required. The 16 inherited trailing-space
warnings remain confined to official generated protobuf output and were not
rewritten.

A fresh blob comparison covered all 192 paths changed by official upstream
since the fork point. The candidate is byte-identical to upstream on 190; the
only expected differences are the reconciled localization catalog and its
generated accessors. A direct structured-catalog recheck proves the candidate
has exactly the 580-key source/upstream union, zero missing or unexpected keys,
all 19 `Pinkha.*` keys with exact source values and en/he localizations, and all
18 `Chat.Activity.*` keys with exact upstream values. This independently
confirms that the Chat Activity, DNS-SD, Quick Capture, Services, feature-flag,
Heart and generated-protocol tuple survived integration without a partial
pick.

## Registration and mixed-case checkout audit

Git contains two different root trees:

- `AnyTypeTests/`: 76 paths, including the test plan and all focused Chat
  Activity, DNS-SD and Quick Capture sources;
- `AnytypeTests/`: 13 paths, including `Info.plist` and legacy tests;
- the two trees have zero colliding relative paths.

The scheme references
`container:AnytypeTests/AnytypeTests.xctestplan`, while the
`PBXFileSystemSynchronizedRootGroup` is also rooted at `AnytypeTests`. The test
plan itself registers target `AnytypeTests` (`03C5C53F22DFD90C00DD91DE`) in
addition to three package test targets. On this Windows checkout,
`core.ignorecase=true` and the two Git trees appear as one physical directory.
That is not macOS execution evidence.

The validation workflow therefore audits the two Git trees before Xcode runs,
detects the runner filesystem's case behavior, and requires all upper-tree
focused sources plus the lower-tree `Info.plist` to be visible through the
exact synchronized-root spelling. It does not copy, rename or merge either
tree. A case-sensitive clean checkout on which the scheme cannot see both
trees fails explicitly rather than silently compiling only legacy tests.
Actual suite identities are then required in the `.xcresult` output.

## Focused native test inventory

The source inventory contains 197 case-sensitive `@Test` declarations: 102
Chat Activity, 50 DNS-SD, and 45 Quick Capture. Parameterized tests increase
the concrete run count to 229. No focused declaration is disabled. The gate
requires at least those per-group named-case counts, every named suite, zero
failures and zero skips.

| Group | Exact `-only-testing` suites |
|---|---|
| Chat Activity | `AnytypeTests/ActivityJSONTests`, `AnytypeTests/ChatActivityPayloadsTests`, `AnytypeTests/ChatActivityJournalTests`, `AnytypeTests/DiscussionActivityJournalTests`, `AnytypeTests/DiscussionActivityPlacementTests`, `AnytypeTests/ChatActivityTimelineRunsTests`, `AnytypeTests/ChatActivityTextTests`, `AnytypeTests/TypingPublishPolicyTests`, `AnytypeTests/TypingRosterTests`, `AnytypeTests/ChatTypingPublisherTests` |
| DNS-SD | `AnytypeTests/BonjourDiscoveryEngineTests` |
| Quick Capture | `AnytypeTests/QuickCaptureDraftTests`, `AnytypeTests/QuickCaptureInputObserverTests`, `AnytypeTests/QuickCaptureLifecycleTests`, `AnytypeTests/QuickCaptureServiceTests` |

Quick Capture coverage is present; it was previously not run, not absent.

## Reproducible runner strategy

Workflow: `.github/workflows/pinkha_u10_native_tests.yml`. It is restricted to
the validation branch. A push is the primary trigger; a documentation-only
update to this report is ignored so observed evidence can be recorded without
spending a second test run.

The job uses `macos-26`, Xcode 26.1, the matching installed iOS simulator
runtime and a dynamically selected available iPhone simulator. It runs the
repository dependency preparation and `make setup-middle-ci`, resolves pinned
packages, executes one `build-for-testing` for target `AnytypeTests`, then
three bounded `test-without-building` commands against one DerivedData. Test
parallelism is disabled. Each group has a separate `.xcresult` and text log;
the job and steps have explicit time limits and evidence retention is 14 days.

The result validator fails on any build/test command failure or timeout, a
missing result bundle, zero/under-count execution, a missing suite identity,
any failed test, or any skipped test. The workflow never enables the dormant
all-tests step in `pr_tests.yml` and performs no signing or user-account work.

Local `apple-doctor --json` confirmed Swift 6.3.3 is available on Windows but
no Apple SDK is present. Consequently, local parsing is not upgraded into
native test evidence. As supporting historical context only, upstream run
`38506223300` successfully built `AnytypeTests.xctest` with Xcode 26.1.1 and an
iOS 26.1 simulator, but its unit-test step was skipped; it does not close U10.

## Observed run

| Evidence | Observed value |
|---|---|
| Workflow run / job | [run 39105374704](https://github.com/davidpovarsky/anytype-swift/actions/runs/39105374704), [job 117609947326](https://github.com/davidpovarsky/anytype-swift/actions/runs/39105374704/job/117609947326) |
| Tested commit | `0a7db261a922f1e17762861bf497e2713ee216ce` |
| Runner | `macos-26`; Xcode 26.1.1; macOS 26.6.2 build environment |
| Simulator | iPhone Air, iOS 26.5 (`23F77`), arm64; dynamically selected installed destination |
| Checkout | Case-insensitive filesystem; both mixed-case Git trees visible through `AnytypeTests`; test plan and all focused sources discovered |
| Build | One clean `build-for-testing`, success, 19:07; one DerivedData reused |
| Chat Activity | 10/10 suites; 102/102 named cases; 131/131 concrete parameter runs; 0 failed, 0 skipped; `xcodebuild` success |
| DNS-SD | 1/1 suite; 50/50 named cases and concrete runs; 0 failed, 0 skipped; `xcodebuild` success |
| Quick Capture | 4/4 suites; 45/45 named cases; 48/48 concrete parameter runs; 0 failed, 0 skipped; `xcodebuild` success |
| Evidence artifact | [artifact 12129625309](https://github.com/davidpovarsky/anytype-swift/actions/runs/39105374704/artifacts/12129625309), 887,777 bytes, `sha256:1c219475844ee7248553397b8ce63dd8a2c5828921de3ea843ea1f5ce6283129`, expires 2026-11-01 |
| Failures / skips / timeouts | Test execution: none. Post-test validator: false-negative count thresholds only; see below. |

The per-suite named-case counts in the emitted test identity JSON are:

| Suite | Passed |
|---|---:|
| `ActivityJSONTests` | 14 |
| `ChatActivityPayloadsTests` | 8 |
| `ChatActivityJournalTests` | 32 |
| `DiscussionActivityJournalTests` | 6 |
| `DiscussionActivityPlacementTests` | 7 |
| `ChatActivityTimelineRunsTests` | 4 |
| `ChatActivityTextTests` | 7 |
| `TypingPublishPolicyTests` | 11 |
| `TypingRosterTests` | 7 |
| `ChatTypingPublisherTests` | 6 |
| `BonjourDiscoveryEngineTests` | 50 |
| `QuickCaptureDraftTests` | 19 |
| `QuickCaptureInputObserverTests` | 4 |
| `QuickCaptureLifecycleTests` | 7 |
| `QuickCaptureServiceTests` | 15 |

All nodes above have result `Passed`. The three root `.xcresult` summaries
report 102, 50 and 45 named cases; their device/configuration summaries report
131, 50 and 48 concrete runs because seven parameterized tests expand into 39
argument runs.

### CI conclusion and bounded correction

The initial push produced [run 39105132787](https://github.com/davidpovarsky/anytype-swift/actions/runs/39105132787)
with zero jobs because `runner.temp` was unavailable in job-level `env`.
Moving path initialization to a runner step was the one causal setup
correction; `actionlint` then passed and the consolidated native run above was
issued.

All three native test steps in the real run concluded `success`. The final
validator concluded `failure` because the pre-run PowerShell inventory was
case-insensitive: its `@Test` search also counted one `@testable import Anytype`
line per source file. This inflated thresholds by exactly four Chat files, one
DNS-SD file and four Quick Capture files (106/51/49 instead of 102/50/45).
The uploaded identity JSON proves every real case and every required suite was
present and passed. The workflow thresholds are corrected to the exact
case-sensitive declaration counts on the final validation branch. No third
native run was issued merely to turn the overall badge green.

CI was therefore actually run. The run-level red conclusion is retained in
this report rather than concealed; it is an evidence-validator false negative,
not a product, test, discovery, failure, skip or timeout result.

## Assessment and boundaries

U10 is **PASS** for the focused native regressions. The candidate is technically
promotable only to a separately approved integration branch; this validation
does not itself promote it. Track A is not an unconditional pass and remains
`PARTIAL / device-gated`: U10's native execution gap is closed, while release,
interactive and real-device conditions remain.

The original `125/125` Pinkha runs remain attributable to unchanged
`PinkhaKit` and hook code. U12/U13 still retain their interactive real-device,
authorized disposable account/Space, migration and downgrade gaps. T2 remains
`PARTIAL / BLOCKED`; no association adapter, schema/Heart change or T3 work is
included.

## U01–U16 impact and promotion conditions

- U01–U09 remain PASS; this branch changes none of their product evidence.
- U10 changes from BLOCKED to **PASS (focused native regressions)** on the
  exact tested commit and run above.
- U11 remains PASS from the prior unsigned device build.
- U12 and U13 retain their explicitly blocked real-device, interactive,
  migration and downgrade portions. This simulator run does not upgrade them.
- U14–U16 remain PASS: T2 stays blocked, evidence remains isolated, and no
  trusted ref was moved or promoted.

Promotion still requires a separate explicit authorization and review of this
candidate. Real-device/editor/Home/RTL behavior, actual Local Network permission
and DNS-SD behavior, authorized disposable migration/downgrade fixtures, and
release/signing gates remain outside this result. No personal account, Space,
vault or user data was used.

**STOP: NO PROMOTION.**
