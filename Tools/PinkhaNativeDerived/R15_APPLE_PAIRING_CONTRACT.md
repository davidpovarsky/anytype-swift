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
