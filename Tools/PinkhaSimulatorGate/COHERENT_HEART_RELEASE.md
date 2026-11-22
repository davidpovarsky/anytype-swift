# Coherent Heart Release / T5 batch

This is a new, explicitly selected Apple acceptance profile. It uses the
existing strict Release, T5, and R07 validators. Python controller tests prove
the orchestration and rejection rules only; an actual Apple run and review of
its original evidence are still required.

## Invocation

The `wave15-acceptance` dispatcher route selects:

| Input | Value |
| --- | --- |
| `acceptance_lane` | `coherent-heart-release` |
| `runtime_profile` | `r15-attachment-authorized-current-read-v1` |
| `source_run_id` | The successful, source-bound `coherent-heart-apple` producer |
| `acceptance_device` | `ipad` |
| `acceptance_language` | `en` |

The shared UI workflow invokes `run_wave15_acceptance.py`. Its fixed batch
registry routes to `wave15_batch.py`; `coherent_heart_release.py` adds the T5
phases. No caller supplies arbitrary method selections or a previous App build.
The original runtime installer must qualify the production ARM64 simulator
artifact before this controller starts.

## Build and execution scope

One `Release-Anytype` App/native-test build and one UI-only runner build contain
the fixed union below. Every subsequent execution uses `test-without-building`.

| Phase | Actual selection required |
| --- | --- |
| Editor | Native preparation 1, existing UI 3 |
| Quote/drag | Native preparation 1, existing UI 1 |
| Properties/Set | Native preparation 1, existing UI 2, stopped-store native preservation postflight 1 |
| Pending T5 host actions | Existing named methods 11, declared cases 12 |
| R07 pending account retry | Existing pending-only method 1, observations 3, service queries 9: successful 8 and native error 1 |
| Remaining quote freshness | New native method 1: six immediate queries through one retained production service; native canonical move/restore 2 and quote-block deletion 1 |
| T5 native/UI | Fresh native preparation 1, real mutations 2 with observations 3, core UI methods 2 |
| T5 Hebrew presentation | The existing read-only method once in light and once in dark; UI executions 2 |

The UI runner compiles nine distinct methods and executes ten selections across
the whole batch because the R08 method runs in both appearances. The T5 UI
retains five actual application lifetimes. Its original snapshots, screenshots,
accessibility attachments, native receipts, and credential-scanned publication
remain mandatory.

The App and UI runner both use the existing T5 flags explicitly:

```
OTHER_SWIFT_FLAGS=$(inherited) -D PINKHA_NATIVE_DERIVED -D PINKHA_NATIVE_T5_LOOKUP_V1
ENABLE_TESTABILITY=YES
ONLY_ACTIVE_ARCH=YES
SWIFT_OPTIMIZATION_LEVEL=-Onone
CODE_SIGN_IDENTITY=-
CODE_SIGNING_ALLOWED=YES
CODE_SIGNING_REQUIRED=YES
PROVISIONING_PROFILE_SPECIFIER=
```

These receipts describe this enabled test build. They do not qualify shipping
defaults, a mixed runtime pair, VoiceOver, physical iPad behavior, or the whole
acceptance matrix. `release_accepted` and `full_matrix_accepted` remain false.

## Reuse and independent fixtures

`FrozenBuild` binds the source tree, package locks, canonical Hanlin snapshot,
runtime installation receipt, App bundle, native XCTest bundles, UI runner,
and both original xctestrun files. It verifies those bytes between phases. The
coherent profile permits its reviewed T5 build flags only for the three fixed
Release lanes. Historical presets retain their original flags.

The three Release fixtures, R07, remaining quote freshness, and T5 UI each create a separate owned simulator.
The parent records every planned name before creation and checks fresh UDIDs.
It revalidates six distinct native Spaces and separate T5/R07/freshness accounts from the
original published receipts. Host callback tests use the original preflight
simulator and do not provide native account or ACL acceptance.

The previous 36-query pagination pass remains bound to its original qualification
and immutable Swift prefix. The new route executes only the pending nine-query
tail. The historical corrected-runtime route still requires its original
producer and exact runtime. Coherent R07 accepts the new full runtime only through
an explicit profile and verified producer binding.

The separate quote freshness suite appends to the original runtime-pair Swift
file while preserving its original 41,696-byte body exactly. One new method
creates a fresh native account, Page, Note, custom Type, and sourceQuote. It
observes the original verse, moves the quote association to the next verse,
observes both, restores the original bytes, proves the other verse is empty,
then deletes the quote block and requires its exclusion using the live graph.
All six calls use the same production service, without explicit invalidation.
The native candidate index remains present after block deletion; the host must
disclose the stale candidate while excluding that block. Canonical metadata,
unknown fields, unrelated targets, titles, Types and remaining quote text are
checked against original native readbacks. This completes only the remaining
quote mutation fixture. It does not relabel the original failed r14 pair,
certify simultaneous mixed peers, or establish whole-index completeness.

## Failure, cleanup, and cache

The existing 105-minute worker and 120-minute execution-step limits remain.
Observed Release test failures retain their independent original results;
identity/setup errors abort. T5 errors retain separate host, pending-nine, core
UI, remaining quote freshness and R08 evidence. No partial result can qualify the combined profile.

The coherent worker uses the existing bounded nested teardown: inner owned
command groups drain before the outer worker retires. Parent cleanup knows all
eight owned destinations, including preflight devices and the three extra T5
devices, even if a child is interrupted after creation.

Cache publication requires terminal worker receipts, original receipt hashes,
successful owned-simulator cleanup, nested-command quiescence and outer-worker
quiescence. Failed functional tests may preserve safe compilation work; a missing
or incomplete cleanup proof prevents caching.

The coherent cache has its own namespace. A prior compatible ordinary Release
compilation cache can warm it, after which current build-for-testing commands
must run and the new products must be frozen. Cache reuse never supplies runtime,
native-test, UI, account, or acceptance evidence.

## Focused validation

`test_coherent_heart_release.py` covers the exact native/UI build union, one App
and one runner, reuse without a second UI build, source/runtime/product rejection,
explicit pending-only runtime admission without the old pagination validator,
fresh simulator ownership, exact counts, and hash-bound cleanup before caching.
Existing corrected-runtime and same-build/readiness tests remain regression
controls for the unchanged routes. These are controller tests, not Apple results.

`test_t5_remaining_freshness.py` rejects stale service identities, wrong current
run/runtime, missing or reordered observations, payload damage, reachable
deleted quotes, invented empty results, changed original pair source, and
secret-bearing publication. It also checks execution through the existing
build with no additional compile command. Actual Apple execution remains
required before any native freshness pass can be reported.
