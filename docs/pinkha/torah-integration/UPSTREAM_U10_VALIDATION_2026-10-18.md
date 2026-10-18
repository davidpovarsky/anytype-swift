# Upstream U10 Native Regression Validation — 2026-10-18

## Scope and status

This report is limited to U10: actual execution of the focused native
`AnytypeTests` regressions added or affected by the integrated upstream Chat
Activity, DNS-SD and Quick Capture work. It does not promote a branch, close
the real-device U12/U13 gaps, change T2, or authorize T3.

Current assessment before the isolated run: **U10 BLOCKED (execution pending)**.
Compilation, parsing, `PinkhaKit` tests, or an empty test result do not satisfy
this gate. The assessment will be replaced with the observed GitHub Actions
result after the single bounded run.

## Immutable inputs

| Item | Exact value |
|---|---|
| Trusted source | `pinkha/torah-integration-t2-unblock` at `13d7577bca9c2ed9848a6a46eac49461a9e1c0d7` |
| Upstream candidate | `pinkha/upstream-sync-2026-10-18` at `5641eab469141bf99133cd42eb9cdea7113f12bc` |
| Official Swift input | `d5650321577a209505a3277c8437b7608cff1cb9` |
| Merge commit | `acbd2b242f07a271f983f59c9eba44e4e9d717ea`, ordered parents source then official |
| CI-validated candidate code | `ac7abb29e94f332e3d4ea3c080ddb3fef5eb4e94` |
| Validation branch | `pinkha/upstream-u10-validation-2026-10-18`, created at exact candidate SHA |
| Validation/tested SHA | Pending first validation-workflow commit |
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

The source inventory contains 206 `@Test` declarations: 106 Chat Activity, 51
DNS-SD, and 49 Quick Capture. Parameterized tests may increase the executed
count. No focused declaration is disabled. The gate requires at least those
per-group counts, every named suite, zero failures and zero skips.

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
| Workflow run / job | Pending |
| Tested commit | Pending |
| macOS / Xcode / simulator | Pending |
| Chat Activity | Pending |
| DNS-SD | Pending |
| Quick Capture | Pending |
| Evidence artifact | Pending |
| Failures / skips / timeouts | Pending |

## Assessment and boundaries

Until the table above contains real executed results, U10 remains **BLOCKED**
and Track A remains `PARTIAL / BLOCKED`. A green result would close only the
focused native U10 execution gap and make the candidate technically promotable
to a separately approved integration branch; it would not itself promote the
candidate or make Track A an unconditional pass.

The original `125/125` Pinkha runs remain attributable to unchanged
`PinkhaKit` and hook code. U12/U13 still retain their interactive real-device,
authorized disposable account/Space, migration and downgrade gaps. T2 remains
`PARTIAL / BLOCKED`; no association adapter, schema/Heart change or T3 work is
included.

**STOP: NO PROMOTION.**
