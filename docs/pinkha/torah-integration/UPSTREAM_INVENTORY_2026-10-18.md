# Upstream inventory — 2026-10-18

This is the read-only inventory captured before merging the official Anytype
Swift upstream into the Pinkha T2-Unblock line. It records the immutable inputs
used by the isolated candidate; it is not a promotion decision.

## Exact refs and ancestry

| Ref | Exact commit |
|---|---|
| Fork source, `origin/pinkha/torah-integration-t2-unblock` | `13d7577bca9c2ed9848a6a46eac49461a9e1c0d7` |
| Fork predecessor, `origin/pinkha/torah-integration-t2` | `813f6b6c8824125f5244ff1d4b7db4a3c81b39cd` |
| Fork `origin/develop` at inventory time | `50bba7deb59ecb76d20ace5312f0343c9256bf84` |
| Official `upstream/develop`, pinned for this integration | `d5650321577a209505a3277c8437b7608cff1cb9` |
| Merge base of source and pinned upstream | `325b60bcecd1119121093761e45ae24ab2eeb82e` |
| Official Heart tag `v0.51.7-nightly.20261014.1` | `d98420b1113536afd08cde6de9a5816f6d27ffff` |
| Previous Heart tag `v0.50.21-nightly.20260824.1` | `7e8f5535add386ff5f7573cde47e095c867ab724` |
| `TorahInspectorKit` package pin | `e8aefc626350c8ee0df9daf8d7de7e1dcd0ea418` |

The official remote was already configured as
`https://github.com/anyproto/anytype-swift.git`; it was verified rather than
repointed. `git fetch origin --prune` and `git fetch upstream develop --no-tags`
completed before resolving these IDs.

`git rev-list --left-right --count` reported 53 fork-only commits and 13
upstream-only commits. From the common base, the fork changed 128 paths and
upstream changed 192 paths. The path sets overlap in exactly two files, leaving
126 fork-exclusive and 190 upstream-exclusive paths.

## Official 13-commit review

The delta is a release-family chain. No commit can be removed while retaining a
coherent `Libraryfile`, generated protobuf, service and feature implementation
tuple.

| Commit | Upstream intent and dependency | Decision |
|---|---|---|
| `70a4316` | Quick Capture feature flags and middleware `v0.51.3` adoption. | `take-with-reconciliation`: feature and middleware boundary must remain paired with later generated updates. |
| `64b3383` | Regenerated protocol bindings for the `v0.51.3` family. | `take-with-reconciliation`: generated output, reviewed as part of the release tuple. |
| `301f619` | Merge of [anytype-swift PR #5118](https://github.com/anyproto/anytype-swift/pull/5118), Quick Capture and `v0.51.3`. | `take`: traceable official merge commit. |
| `cfd96f7` | Native DNS-SD discovery implementation. | `take-with-reconciliation`: requires Info.plist, service wiring and regression tests. |
| `7d1ae86` | Local Network denial retry behavior and DNS-SD test fixes. | `take-with-reconciliation`: functional correction inseparable from the previous commit. |
| `b7e6ba8` | Adds generated `export_report` protocol output. | `take-with-reconciliation`: generated artifact in the selected protocol family. |
| `df23dde` | Merge of [anytype-swift PR #5121](https://github.com/anyproto/anytype-swift/pull/5121), native discovery proxy/DNS-SD. | `take`: official merge, paired with Heart PR #3317. |
| `66e749e` | Follow-up build fixes for the integrated upstream changes. | `take`: required build correction. |
| `5339672` | Middleware `v0.51.6` and PubSub protocol/service generation. | `take-with-reconciliation`: ABI/protocol boundary for chat activity. |
| `a99cfa1` | Chat live typing and agent/tool activity implementation and tests. | `take-with-reconciliation`: depends on PubSub and new generated models. |
| `7924dc3` | Enables `chatActivity` feature behavior. | `take-with-reconciliation`: must be tested with the implementation it exposes. |
| `5cc05e4` | Merge of [anytype-swift PR #5122](https://github.com/anyproto/anytype-swift/pull/5122), chat activity and `v0.51.6`. | `take`: official merge; upstream discussion notes tombstone UI follow-up. |
| `d565032` | Merge of [anytype-swift PR #5123](https://github.com/anyproto/anytype-swift/pull/5123), official `v0.51.7` middleware bump. | `take`: exact pinned integration target. |

The reviewed PRs were all merged: #5118 on 2026-09-24, #5121 on
2026-10-12, #5122 on 2026-10-13 and #5123 on 2026-10-14. This candidate pins
the reviewed commit rather than following a moving `upstream/develop` ref.

## Path and conflict inventory

### Overlapping paths

1. `Modules/Loc/Sources/Loc/Resources/Workspace.xcstrings`
2. `Modules/Loc/Sources/Loc/Generated/Strings.swift`

The catalog had a real content conflict. The generated Swift file auto-merged,
but was still checked against the integrated catalog. The fork added 19
`Pinkha.*` keys with Hebrew and English values. Upstream added 18
`Chat.Activity.*` keys. The added namespaces had zero key collisions and no
keys were removed. The expected union contains 580 keys.

Upstream contains three renames in the delta and the fork contains none. The
renames are generated protobuf/type transitions and were retained with their
official similarity history:

- `Anytype_Rpc.ObjectType.Relation.swift` to
  `Anytype_Rpc.ObjectType.Property.swift`;
- `Anytype_Event.Account.LinkChallengeHide.swift` to
  `Anytype_Event.Account.JsonApiStatus.swift`;
- `Anytype_Event.Account.LinkChallenge.swift` to
  `Anytype_Event.Account.LinkApprovalRequest.swift`.

### Whitespace baseline

The premerge cross-ref `git diff --check` was not clean because official
generated protobuf output contains trailing spaces (and the compared histories
also contain workflow whitespace). The integrated staged diff narrowed this to
16 warnings, all in official generated protobuf files. These were not manually
rewritten because doing so would make generated output diverge from the exact
official release family. The warnings are listed in the merge report.

## Version and package graph

| Component | Fork source | Integrated upstream selection |
|---|---|---|
| Anytype Swift | `13d7577bca9c2ed9848a6a46eac49461a9e1c0d7` | merge with `d5650321577a209505a3277c8437b7608cff1cb9` |
| Heart / middleware | `v0.50.21-nightly.20260824.1` / `7e8f553…` | `v0.51.7-nightly.20261014.1` / `d98420b…` |
| Protocol Swift generation | old pinned middleware family | official files committed with `d565032…` |
| Services | old Services surface | official PubSub and discovery proxy additions |
| `TorahInspectorKit` | `e8aefc626350c8ee0df9daf8d7de7e1dcd0ea418` | unchanged exact pin |
| `PinkhaKit` | local Swift package linked into Anytype | unchanged package and product linkage |

The dependency boundary is:

```text
Anytype app target
  ├─ PinkhaKit (local package)
  │    └─ TorahInspectorKit @ e8aefc626350c8ee0df9daf8d7de7e1dcd0ea418
  ├─ Services
  │    ├─ ProtobufMessages (official generated v0.51.7-family surface)
  │    └─ Middleware binary selected by Libraryfile
  └─ upstream feature code (Quick Capture, DNS-SD, chat activity)
```

`Libraryfile` selects `v0.51.7-nightly.20261014.1`. The official Heart tag and
Heart `develop` both resolved to `d98420b1113536afd08cde6de9a5816f6d27ffff`
at audit time. That Heart release contains PR #3327, which bumps `any-sync` to
0.13.8 and `any-store` to 1.0.3.

## Protected Pinkha inventory

| Protected area | Premerge inventory | Integration requirement |
|---|---:|---|
| `Modules/PinkhaKit/**` | 62 files | Byte-identical unless an intentional compatibility patch is documented. |
| `Anytype/Sources/Pinkha/**` | 15 files | Preserve bootstrap, manifest, hierarchy, home and navigation behavior. |
| `docs/pinkha/**` | 20 files before this report set | Preserve all plans, ADRs and negative evidence. |
| Pinkha workflows | 3 registered workflow files | Preserve fork tests, validation and customized IPA flow. |
| Xcode linkage | `PinkhaKit` references/product linkage in `project.pbxproj` | Keep package and Anytype target relationship intact. |
| Installed native hooks | `ActiveSpaceManager.swift`, `HomeWidgetsView.swift` | Preserve the two installed hooks; do not infer planned hooks. |
| Pinkha localization | 19 generated accessors and 19 catalog keys | Preserve Hebrew and English values and generated symbols. |
| Manifest/schema | `PinkhaSpaceManifest` v1 | No schema bump, rewrite or destructive cleanup. |

The installed native hook inventory comes from code, not merely from
`docs/pinkha/UPSTREAM_HOOKS.md`: Space activation bootstraps Pinkha, and Home
widgets render the Pinkha section. No editor/T3 hook is installed.

## Untested and deployment risks at inventory time

- Heart #3195 remains open and describes replay divergence between mixed
  versions. Old/new Heart interoperability and downgrade safety cannot be
  inferred from a successful compile.
- Heart #3311 introduced layout migration behavior. No personal or production
  Space may be used to test this candidate.
- DNS-SD depends on Local Network/Bonjour declarations, denial/retry state and
  real network behavior; unit tests and compilation do not replace a device
  acceptance pass.
- Chat typing/activity introduces PubSub, journal and tombstone behavior. The
  official tests must compile/run with the new service/protobuf tuple.
- Quick Capture must remain feature-flag coherent with the middleware release.
- The Windows host cannot run Apple SDK builds. Registered macOS 26 / Xcode
  26.1 workflows are authoritative for package and unsigned device build proof.
- The Heart update does not itself repair T2's rejected block-journal semantics.
  B04 (silent different-payload replacement) and B06 (removed-anchor loss)
  remain functional blockers.
- Real migration, downgrade, signed-device, real middleware reopen and
  two-client/offline behavior need authorized disposable fixtures. They are not
  promoted to PASS by source audit, unit tests or an unsigned IPA.
