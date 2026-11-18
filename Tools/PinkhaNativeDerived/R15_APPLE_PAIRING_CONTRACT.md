# T5 r15 Apple runtime and later application-pairing contract

## Prepared build-only lane

The new reusable workflow `.github/workflows/pinkha-t5-r15-runtime.yml` builds the
exact r15 patch `5a0906158569d47642d9fc978932cdf254550a31c864a1fb34bd1f8e4e7c10f2`
on Heart `d98420b1113536afd08cde6de9a5816f6d27ffff`. It loads the unchanged patch and
inventory from reviewed source `947fbde24d5657d0e1229f45bb3993648884a8a1`. All build
directories are isolated by GitHub run and attempt. The parent dispatcher owns
selection and dispatch; this source does not edit it, the r14 workflow, or its builder.

`build_t5_r15_runtime.py` reuses the existing source preflight, verified Tantivy
download/extraction, and per-architecture inspection functions from
`build_custom_heart.py`, bound to Git LF SHA-256
`0ebbe2f6227418eac2c532b0058290158319ba9f786baaf445de444887e8c669`.
The separate wrapper follows that builder's original gomobile + iosrepack pipeline,
using Go 1.26.5 on actual ARM64 macOS and the Xcode 27 SDK lane. It links the full
derived-property and T5 capability version string into every device/simulator
architecture. Source, patch, inventory, tool/dependency identities, original commands,
original generated go.mod text, and binary slice hashes are retained.

The original r14 builder links only the derived-property marker. It cannot be called
unchanged to produce the r15 runtime version expected by the Swift capability gate;
this is why the wrapper is separate. No global/product app flag is set here.

## Generated Go module provenance

Heart pins `golang.org/x/mobile v0.0.0-20250218173827-cd096645fcd3`. Its original
gomobile creates one temporary gobind module per Apple architecture and copies the
effective dependency replacements from the native module graph. Those generated
modules must run with GOWORK=off; a fixed native-only workspace would exclude them.

The build-local launcher `r15_runtime_go.py` records each command and explicit scope.
Only commands in the owned Heart source use the temporary workspace with the already
reviewed root genproto replacement
`v0.0.0-20241021214115-324edc3d5d38`. Commands in the owned generated-module directory
use GOWORK=off. Before each generated archive build, the launcher uses the original
Go executable to verify that the selected native module resolves to the exact Heart
checkout and that the selected genproto resolves to the reviewed version and both
known h1 checksums in both the effective selection and the cached module download.
The launcher hydrates the reviewed module from the cache before listing the selected
graph; missing or different selection checksums fail validation. GOPROXY is off after
the pinned dependency download. Downloading the correct cached version alone cannot
conceal a different selected version or checksum.

This does not patch Heart go.mod, gomobile sources, global Go settings, or the r14
builder. The original generated go.mod text and hash remain in the receipt even after
gomobile removes its temporary work. The framework cannot pass without three distinct
successful generated-module build proofs.

Inspected primary sources are pinned, not latest:
- https://raw.githubusercontent.com/golang/mobile/cd096645fcd3/cmd/gomobile/bind_iosapp.go
  — SHA-256 `17cb5ce95d4194126099c94613f4f2769a7ede696f0b36f062ed985d7245e977`.
- https://raw.githubusercontent.com/golang/mobile/cd096645fcd3/cmd/gomobile/bind.go
  — SHA-256 `f9039cc240190ee7cabd2a89f3b7d479d51bd40a18e79f1a032177ce803b64b0`.

## Artifact contract

| Item | Requirement |
| --- | --- |
| Artifact name | Pinkha-Universal-Verified-Heart-r15 |
| Device | Original ios-arm64 framework; arm64 slice verified |
| Simulator | Original ios-arm64_x86_64-simulator framework; arm64 and x86_64 slices independently verified |
| Version binding | Each thin slice contains the exact full expected runtime version and exact Heart SHA |
| Archive | Lib.xcframework plus PinkhaNativeHeartBuild.json; original file and slice hashes retained |
| Receipt | Build-only success; app_get_version_status=NOT_RUN_BUILD_ONLY, zero native test invocations in this lane |
| Application acceptance | swift_pairing_status=NOT_RUN, full_F10=NOT_PROVEN, product enablement disabled |

Binary marker inspection is not an executed AppGetVersion RPC. A produced artifact
must be installed only by a later explicit test pairing route with run ID, archive
hash, receipt hash, and selected slice identity verified before building the app.

## Later same-source Swift application proof

The later pairing must build the same exact application source and dependency locks
twice, changing only the linked r14 versus r15 runtime. If the test configuration uses
PINKHA_NATIVE_T5_LOOKUP_V1, the exact same test-only setting must be present in both
app builds. The product configuration remains unchanged.

Both application builds use one disposable simulator and the same bundle/container.
Do not uninstall or erase it between old-create, new-upgrade, old-edit, and new-recover.
The synthetic account ledger must bind the original account, Space, object and block
IDs across all four processes. Keys stay inside the private test container and never
enter logs, receipts, or uploaded artifacts.

At every phase, read actual AppGetVersion from the running framework. The production
AnytypeT5NativeRelatedLookup.current() must derive capability from that response.
Fixture-provided role strings or persisted private version fields cannot grant it.
The old binary must remain unavailable even after new private cache rows have existed
in that same account. The new binary must return the actual expanded document/block/
sourceQuote results with exact current-Space and fresh ObjectShow identity checks.

The r14-scoped TorahWave1IntegrationTests expectations for indexedDocumentsOnly and
NotIndexed are not r15 acceptance. A focused r15 test must assert the expanded
indexedTargetsOnly coverage and its explicit incompleteness disclosure. Arbitrary
external-write freshness and spaceWide completeness still require separate proof.

Actual application startup, UI navigation/acknowledgment, permissions, cancellation,
and physical-device acceptance retain their own gates. This build-only route does
not turn those requirements into passes.

## Offline Apple workspace after the first r15 build failure

Actual run44225433140 (source c727575ad67c83ec96c3178ab926681fbba22ae9) failed at gomobile init after compiling both pinned tools. Its original log records an attempted `go install golang.org/x/mobile/cmd/gobind@latest` while GOPROXY=off. No Heart slices or App tests had executed.

The pinned upstream source explains this exactly: [init.go at cd096645fcd3](https://github.com/golang/mobile/blob/cd096645fcd3/cmd/gomobile/init.go) unconditionally installs latest gobind. [bind.go](https://github.com/golang/mobile/blob/cd096645fcd3/cmd/gomobile/bind.go) resolves gobind from PATH, and [env.go](https://github.com/golang/mobile/blob/cd096645fcd3/cmd/gomobile/env.go) initializes the Apple toolchain directly from buildEnvInit. The remaining optional init work builds Android OpenAL.

This Apple-only wrapper therefore prepares a fresh job-owned GOPATH/pkg/gomobile directory and uses its already compiled, hash-verified pinned gobind. It queries and preserves the original GOMODCACHE explicitly before switching GOPATH. PATH must resolve to that exact binary, and both GOPROXY=off and GOFLAGS=-mod=readonly remain mandatory. It records this preparation separately before bind and in the final runtime receipt. Existing workspace reuse, a different/changed gobind, absent module cache, or network-enabled resolution fail before build. The original r14 helper, Heart sources, native inventories, x/mobile revision, and generated-module genproto constraints are unchanged.

Source blobs reviewed: init.go48642e22b3afaf45c2542144f34e6d4ab891b6de; bind.go4e1c453f418589afc1576045140946fb878a3868; env.go320597994e7c7cfef14fc295a074700fee0ca02b. This is a build-input correction; a successful Apple runtime build and the same-source four-process Apple pairing still require actual execution.

## Pinned tool dependency cache after the bind attempt

Actual run 44235484816, source
793d09a8d3e22c3ce29cc94e16c614f476cb73d8, passed the owned Apple workspace
preparation and compiled both pinned tools. It then failed during the generated
modules' offline `go mod tidy`: the native workspace's lazy graph had cached MTL
revision 2019, while the pinned mobile tool's Shiny dependency requires MTL
`v0.0.0-20221208032759-85de2813cf6b`. All three architecture tidies returned 1.
This attempt produced no verified runtime slices or AppGetVersion/Swift evidence.

The required version is already declared by the selected
`golang.org/x/exp/shiny v0.0.0-20230817173708-d852ddb80c63`, which is required
by pinned mobile cd096645fcd3. Its primary go.sum supplies the archive and go.mod
h1 checksums. This is a tool dependency cache gap, not a requested native/tool
revision upgrade.

The wrapper now verifies the selected mobile version and both h1 hashes, then
copies its exact go.mod/go.sum bytes to an owned dependency seed directory.
Those primary file SHA-256 values are hard-bound in the wrapper. It runs
`go mod download -json all` from this isolated seed with GOWORK=off before
switching the native build to GOPROXY=off. The native workspace, native go.mod,
and cached source files are unchanged. The resulting download receipts must
include the exact Shiny and MTL revisions and both expected h1 checksums;
duplicate, missing, failed, or mismatched receipts fail before bind.

A bounded real cache experiment on Windows Go 1.25.6 downloaded the declared
14-module tool graph and successfully read it back with GOPROXY=off. Its owned
122,281,825-byte cache was removed after the experiment. This is dependency
cache evidence only: Apple still requires the actual Go 1.26.5 macOS build.

Primary declarations and immutable blob/hash provenance are preserved in
`docs/validation/20261118-t5-r15-runtime/44235484816/dependency-source`.
Original failed-run evidence is preserved beside them. Controller rejection
tests, actual cache readback, and actual Apple runtime acceptance remain
separate receipts.

## Generated-module closure after runtime attempt 44240654969

The latest actual Apple attempt is preserved under `docs/validation/20261118-t5-r15-runtime/44240654969`. Its pinned mobile dependency preparation succeeded, including all 14 modules and the authoritative MTL checksums. All three generated architecture modules then failed `go mod tidy` offline on `git.sr.ht/~sbinet/gg@v0.6.0`. There is no accepted r15 framework artifact and no Apple/Swift runtime execution from that attempt.

The pinned `cmd/gomobile/bind.go` function `getModuleVersions` copies every original `go list -m -json all` module into a direct generated requirement, except replacements and the local main module, whose exact replacement declarations are copied. That creates a distinct generated module graph. The observed original graph contains 882 modules and gg v0.3.1; the same original graph includes gonum v0.17.0, whose authoritative module declaration requires gg v0.6.0. The original native graph and generated graph must be retained as separate inputs and must never be conflated with an intentional native source/dependency revision.

The builder now mirrors this exact pinned generator into a fresh owned `generated-dependency-seed`, verifies both relevant mobile source files by SHA-256, and records the original native graph hash and unmodified seed go.mod. It hydrates the generated graph before the offline boundary with `go mod download -json all`, then records the selected module list. The public checksum authority must be enabled; no disabled checksum database or private bypass is silently accepted or changed. Selected graph identities and downloaded archives must agree on effective path, version, module h1 and go.mod h1. The observed gg v0.6.0 hashes are independently bound to gonum v0.17.0's primary go.sum.

Every actual generated module must match the parsed seed declarations before its own tidy. After tidy and again before compilation, the launcher reads the effective module graph with `GOWORK=off` and `GOPROXY=off` and checks it against the hydrated graph. Only removal of unused seed modules is permitted; a different path, logical/effective version, replacement or checksum fails. Full pre/post-tidy module text and identities remain in evidence. The separate exact native Heart directory and selected/downloaded genproto h1 guards remain mandatory. All three architecture modules must have both original-input and successful pre-build receipts.

This changes owned build/cache preparation only. The native checkout, native go.mod/go.sum, mobile revision, Go 1.26.5 requirement, r14 builder helper, r15 patch/inventory and runtime markers remain unchanged. No product capability flag is enabled. Local checks are controller validation and a small Go 1.25.6 metadata probe; full generated-graph hydration, Apple build and runtime pairing remain **NOT_RUN locally**. They are acceptance gates for the next reviewed CI run.

Primary sources:

- https://github.com/golang/mobile/blob/cd096645fcd3/cmd/gomobile/bind.go
- https://github.com/golang/mobile/blob/cd096645fcd3/cmd/gomobile/bind_iosapp.go
- https://github.com/gonum/gonum/blob/v0.17.0/go.mod
- https://github.com/gonum/gonum/blob/v0.17.0/go.sum
- https://go.dev/ref/mod#go-mod-tidy
