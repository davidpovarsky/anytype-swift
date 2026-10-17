# Upstream merge report — 2026-10-18

Candidate branch: `pinkha/upstream-sync-2026-10-18`

Merge commit: `acbd2b242f07a271f983f59c9eba44e4e9d717ea`

Merge parents, in order:

1. Pinkha source: `13d7577bca9c2ed9848a6a46eac49461a9e1c0d7`
2. Official upstream Swift: `d5650321577a209505a3277c8437b7608cff1cb9`

Final status: **UPSTREAM INTEGRATION PARTIAL / BLOCKED**. The merge, Pinkha
tests and unsigned app/IPA build pass, but the official AnyTypeTests regression
suites for the newly integrated Chat Activity, DNS-SD and Quick Capture paths
were not executed by the registered workflows. The candidate is not approved
for promotion or personal-Space use.

## Merge execution

The branch was created from the exact remote source with:

```text
git switch -c pinkha/upstream-sync-2026-10-18 origin/pinkha/torah-integration-t2-unblock
git merge --no-ff --no-commit d5650321577a209505a3277c8437b7608cff1cb9
```

The merge reported one conflict,
`Modules/Loc/Sources/Loc/Resources/Workspace.xcstrings`. It was manually
reconciled as structured JSON. No blanket ours/theirs strategy was used. The
18 upstream `Chat.Activity.*` keys and all 19 fork `Pinkha.*` keys/localizations
were retained. The resulting key set exactly matches the mathematical union:
580 current/expected, zero missing fork keys, zero missing upstream keys and
zero unexpected keys. Fork values are byte-equivalent; upstream-only values
match upstream. JSON parses and no conflict markers remain.

`Modules/Loc/Sources/Loc/Generated/Strings.swift` auto-merged. It was audited
against the catalog and contains all 18 Chat Activity and 19 Pinkha generated
accessors. No generator was run on Windows because the already integrated
official and fork symbols were complete and a platform generator could add
unreviewed churn.

No compatibility patch to Pinkha production code was necessary. All official
upstream code/protobuf/service changes were retained as the coherent
`v0.51.7-nightly.20261014.1` family.

## Static/source gate

| Check | Result | Evidence |
|---|---|---|
| Merge ancestry | PASS | Merge commit has the two exact required parents. |
| Unmerged entries / markers | PASS | Zero unmerged paths; repository scan found no merge markers. |
| Protected production trees | PASS | `Modules/PinkhaKit/**` and `Anytype/Sources/Pinkha/**` are byte-identical to the source parent. |
| Pinkha docs/workflows | PASS | Existing `docs/pinkha/**` and three fork workflows are retained; only candidate evidence docs are added/updated. |
| Xcode package linkage | PASS | `PinkhaKit` package/product references and Anytype target linkage remain present in `project.pbxproj`. |
| Native Pinkha hooks | PASS | `ActiveSpaceManager.swift` and `HomeWidgetsView.swift` hook content is unchanged from the source parent. |
| Localization | PASS | Structured union is 580 keys; all Pinkha en/he values and generated accessors retained; all upstream additions retained. |
| Kit pin | PASS | `TorahInspectorKit` remains exactly `e8aefc626350c8ee0df9daf8d7de7e1dcd0ea418`. |
| Middleware tuple | PASS (source) | `Libraryfile` selects `v0.51.7-nightly.20261014.1`; official generated protobuf, Services/PubSub and discovery adapter are from the same upstream commit chain. Build proof is recorded below. |
| T2 negative evidence | PASS | T2 remains blocked; B04/B06 are not reclassified; no adapter or T3 code added. |
| User-data safety | PASS | No app was launched against a user Space; no database/reset/migration operation was executed. |

`git diff --check` reports 16 trailing-whitespace warnings in the exact official
generated protobuf output. They are confined to:

- `Anytype_Rpc.AI.ListModels.swift`;
- `Anytype_Rpc.Account.RecoveryState.swift`;
- `Anytype_Rpc.Object.ImportRunList.swift`;
- `Anytype_Rpc.Object.ImportRunStatus.swift`;
- PubSub publish/subscribe/unsubscribe command and envelope files;
- account link-approval/recovery and import-statistic event files;
- PubSub message/event files;
- account app-grant and membership fetch-state/revision model files.

These are inherited upstream generation artifacts, not conflict residue. They
were recorded rather than manually altered independently of the generator.
All non-generated candidate documentation and reconciliation changes pass
`git diff --check`.

## Compatibility audit

- Quick Capture: feature-flag and middleware changes are preserved as one
  upstream chain. No Pinkha routing or editor hook was modified.
- DNS-SD/LAN: native discovery proxy, service wiring, retry behavior, tests and
  Local Network Info.plist declaration are retained together.
- Chat activity: PubSub protocol/service, journal, typing/activity state,
  presentation and official tests are retained together. This does not resolve
  the separate tombstone/product follow-up discussed upstream.
- Pinkha host: package link, bootstrap/manifest, hierarchy and Home hooks are
  unchanged. There were no upstream API conflicts in those paths.
- Heart: the source branch remains reproducible at the old pin. The candidate
  selects `d98420b…`; mixed-version Space and downgrade safety remain unproved
  and must use disposable fixtures only.

## Deterministic checks and CI

The Windows host can perform portable parse/static checks but has no Apple SDK.
Authoritative macOS package and app results are appended here after explicit
workflow dispatch on the candidate ref.

| Validation | Status | Exact evidence |
|---|---|---|
| Apple toolchain diagnostic | PASS / platform limited | `apple-doctor --json`: Windows, portable Swift 6.3.3 available, Apple SDK unavailable. |
| Package resolution | PASS | `swift package --package-path Modules/PinkhaKit resolve --verbose`; workspace state resolves `TorahInspectorKit` exactly at `e8aefc626350c8ee0df9daf8d7de7e1dcd0ea418`. The command-created untracked package lock was removed rather than added to the candidate. |
| Portable Swift parse | PASS | `swiftc -frontend -parse` passed all 74 PinkhaKit production/test Swift files. |
| Localization/Info.plist | PASS | Catalog parses as JSON: 580 keys, 19 Pinkha keys with en+he, 18 Chat Activity keys; Info.plist parses and includes `_anytype._tcp` and `_pulse._tcp`. |
| Local Swift package test | BLOCKED (host) | Build reached the exact Kit checkout, then Windows failed on unavailable Apple module `CoreTransferable`; no product failure inferred. |
| Upstream changed-source parse | PASS | `swiftc -frontend -parse` passed all 187 upstream-changed Swift files, including seven added Chat Activity/DNS-SD test/fake files; four existing Quick Capture test files also parse. This is syntax evidence, not test execution. |
| `pinkha-tests.yaml` | PASS | Run [39076635946](https://github.com/davidpovarsky/anytype-swift/actions/runs/39076635946) at exact SHA `ac7abb29e94f332e3d4ea3c080ddb3fef5eb4e94`: 125 tests in 15 suites, zero failures. |
| `ipa.yaml`, release | PASS | Run [39076638187](https://github.com/davidpovarsky/anytype-swift/actions/runs/39076638187) at the same exact SHA: 125/125 tests, middleware `v0.51.7-nightly.20261014.1` download, full unsigned iOS device build, packaging and upload all succeeded. |
| IPA artifact | PASS | Artifact `Anytype-Hebrew-Unsigned-Device-IPA`, ID `12118300198`, 155,114,954 bytes, SHA-256 `a7223b409a65a323f26cb01696a87cb6a1f3b909e82ddf0c755a9c606c964bdf`, expires 2026-10-24. |
| Official upstream feature tests | BLOCKED | `pr_tests.yml` has both `Run unit tests` and its preceding notification step guarded by `if: false` because tests hang on CI. The two mandated candidate workflows do not build/run `AnyTypeTests`; no compilation or app-build result is misreported as execution of Chat Activity, Bonjour/DNS-SD or Quick Capture tests. The raw fallback harness also lacks the repository's required middleware/dependency preparation and is not an equivalent test path. |
| Real device / migration / downgrade | BLOCKED | No authorized disposable device/Space fixture in this assignment. |

## U01–U16 acceptance matrix

No row is inferred merely from Git's successful merge. U10 remains a material
test-execution gap, so the overall Track A decision is `PARTIAL/BLOCKED` even
though the registered Pinkha and unsigned-IPA workflows are green.

| ID | Status | Evidence / remaining proof |
|---|---|---|
| U01 | PASS | Exact fork, upstream, Heart, Kit and merge-base commits recorded and independently resolved. |
| U02 | PASS | New isolated branch; source T2 branches and fork `develop` were not checked out, reset or updated. |
| U03 | PASS | All 13 upstream-only commits reviewed and classified in the inventory; coherent release chain selected. |
| U04 | PASS | Single catalog conflict manually reconciled; auto-merged generated accessors verified against the union. |
| U05 | PASS | Protected Pinkha production files and prior portable tests/fixtures are byte-identical; required docs retained. |
| U06 | PASS | Xcode package/product link, target relationship, Services code and two installed Pinkha native hooks are intact. |
| U07 | PASS | All Pinkha en/he keys/accessors plus upstream Chat Activity keys/accessors verified. |
| U08 | PASS | Official Libraryfile, middleware version, generated protobuf, PubSub/Services and discovery adapter are a single upstream family; full app compilation passed. |
| U09 | PASS | Run `39076635946` passed 125 tests in 15 suites at `ac7abb29e94f332e3d4ea3c080ddb3fef5eb4e94`; IPA run independently repeated 125/125. |
| U10 | BLOCKED | All changed sources and official new test files parse and the app compiles, but the registered `pr_tests.yml` explicitly disables unit-test execution; Chat Activity, DNS-SD/LAN and Quick Capture `AnyTypeTests` were not run. |
| U11 | PASS | Run `39076638187` compiled the full unsigned iOS device app and uploaded artifact `12118300198` at exact SHA `ac7abb29e94f332e3d4ea3c080ddb3fef5eb4e94`. |
| U12 | PASS / device gap BLOCKED | The 125-test run includes Pinkha bootstrap/manifest/hierarchy/reconciliation coverage and the host app compiles with the unchanged hooks; interactive editor/Home/Hierarchy device behavior was not exercised. |
| U13 | PASS / device gap BLOCKED | No user data or Space touched and no destructive migration performed; real migration/downgrade/device proof unavailable. |
| U14 | PASS | B04/B06/T2 blocked status retained; no unsafe adapter, Heart/protobuf implementation or T3 work. |
| U15 | PASS | Inventory, research, report and evidence-ledger updates are committed only on the isolated candidate. The final post-CI commit changes documentation only. |
| U16 | PASS | Only `pinkha/upstream-sync-2026-10-18` was pushed, without force; trusted branches remain at their recorded refs. Final documentation HEAD is supplied in the handoff. |

## Original-branch immutability and limits

The recorded remote source remains
`13d7577bca9c2ed9848a6a46eac49461a9e1c0d7`; the predecessor remains
`813f6b6c8824125f5244ff1d4b7db4a3c81b39cd`. No trusted branch is a target of
this work and no force push is allowed.

An unsigned IPA proves compilation and packaging, not installation, signing,
real-device LAN behavior, real middleware persistence, migration/downgrade or
two-client convergence. Those limits remain explicit even if CI is green.

The CI-validated implementation/report SHA is
`ac7abb29e94f332e3d4ea3c080ddb3fef5eb4e94`. The subsequent final evidence
commit changes only this report, the inventory/research documents and
`PROGRESS.md`; `git diff --name-only` between the tested SHA and final HEAD is
recorded in the handoff so the distinction is auditable.

## Decision gate

- Track A: `PARTIAL / BLOCKED` because U10 is BLOCKED. Keep the candidate
  isolated; a separate reviewer may provide/authorize a working focused
  AnyTypeTests path and then reconsider promotion.
- Track B: `PARTIAL / BLOCKED`; Tier C and Tier D are both BLOCKED and no T2
  adapter exists.
- No merge into a trusted branch, no personal-Space migration, no Heart/protobuf
  implementation and no T3 work are authorized by this report.
