# Original shared App and complete UI on hosted ARM64

This change prepares an alternate build route after repeated actual resource
refusals on the shared Scaleway Mac. It does not execute a build, repin a native
runtime, qualify application behavior, sign a Release archive or upload to
TestFlight. The existing Mac source at `8f2c11713fb8a40ae13444104723666ffef68afe`
and its SDK385/native8ac inputs remain separate and untouched.

## Two concrete routes in the existing dispatcher

The already registered `.github/workflows/torah-inspector-ipados27.yml` gains
two additive choices. All earlier choices, inputs and jobs remain unchanged.
The new reusable workflows are called by that dispatcher; neither depends on
registering a new standalone manual workflow on the default branch.

| Choice | Runner | Work performed |
| --- | --- | --- |
| `wave3-native8ac-export` | Existing `pinkha-scaleway-mac` self-hosted ARM64 runner | Read, package and independently rehash only the already built native8ac inputs; publish one Actions input artifact and its original export evidence. No native compiler runs. |
| `wave3-hosted-shared-build` | Existing hosted `xcode-27` ARM64 label | Admit exact native input artifact, materialize the exact canonical SDK, run the original combined App and complete UI build once, preserve the complete original Products and source. No XCTest invocation or simulator mutation. |

Both use two new dispatcher string inputs: `shared_build_plan_json` and
`shared_build_plan_sha256`. The former is the exact UTF-8 JSON body, including
any final newline. The latter hashes those exact bytes. The controller never
evaluates that string as shell code. Root supplies the exact executing control
commit, compiled App commit/tree, canonical SDK revision, complete compiler
source hashes, all native pins and exact artifact identity. No branch-tip
selection is accepted.

`readyForBuild` and `readyForExport` are independent and false in a prepared
draft. The sole integration owner finalizes the appropriate actual plan and
dispatches the existing workflow. These flags represent the owner's concrete
source/resource decision; they are not a request for additional user consent.

## Original producer and truthful hosted intake

The executed compiler program is derived from the unmodified original
`build_wave2_app16_compiler_qualified.py` at commit
`204f8fbb25c3b21f419fc1a8818eb46ed492e561`, SHA256
`9b1405ea44ba9cce3fca47a88127fc798fedab3d1b05f6e3728da3597d19929c`.
It uses the unchanged original Wave3 compiler-proof adapter, SHA256
`47c66dde6122d19b12e5206a4a5f0b1841a026fb8088aa4bdb2c69d6a657cfcd`.

The expansion produces a complete reversible delta. Reversing the hosted
changes and then the original Wave3 changes must restore every original byte.
The original `run_phase`, `source_state` and focused native compiler assertion
remain byte-identical. The original four-job commands, source snapshots,
complete framework checks, exact runtime qualification, SDK verification,
generated complete UI target, actual `swiftc`/`SwiftFileList` witnesses,
complete Products inventory, 7,200-second phase deadlines and bounded owned
process-group cleanup are retained.

The historical Mac staging/cache block and its warm-cache narrative are
replaced explicitly. A fresh hosted checkout cannot truthfully claim that
App15 products or the Mac's caches were reused. The new source and cache
receipts say respectively `PASS_FRESH_HOSTED_SOURCE_NATIVE_AND_SDK_NOT_BUILT`
and `PASS_EMPTY_HOSTED_COMPILER_PATHS_NOT_BUILT`. Both precede compilation and
claim zero builds/tests. Every locked actual package checkout must also have
the exact revision and a clean status including nonignored untracked files
after App compilation and after UI compilation.

The root-derived producer admission retains the existing schema and fixed
original lineage. Its actual expanded producer hash, source/native inputs,
original native transport receipt, source/cache receipts and all compiler
proofs are bound to the final original build receipt. The terminal original
success remains `PASS_COMBINED_MAIN_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE`.

## Exact native8ac transport

No r14/r15 artifact is substituted, and no new native implementation is built.
The exporter verifies the exact source manifest
`8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b`,
all 4,868 original source files, both original slice receipts/commands/logs,
both binary hashes, the complete original framework file inventory and the
original combined assembly receipt. The original `runtime_identity.py`
validator is executed without alteration. The payload records bytes, modes
and timestamps and rejects symbolic links, unexpected files, duplicates,
case collisions, traversal paths and oversized input. Original inputs are
rehashed after packaging; the compressed archive is independently streamed
and verified before it can be uploaded. Original sources and products are
never deleted.

The original binary closure is:

| Input | SHA256 |
| --- | --- |
| Combined assembly receipt | `c9c90e3a12868bcedf5f0a4f116c4dc1c388bdcddd0e9f0170c047684c500231` |
| Full framework inventory | `fa999a27c00bfb572cf91ddd65b30e1b7618827c75631f0ee0546748c83f7dbf` |
| Simulator receipt | `946fe141ee4fa1c1fa8ceafc9060d9d9eedb0d546360140eadaf5ecf1f264f9b` |
| Simulator binary | `f94079de9eeb9e2e869f02bd1dda93fcd272e3191b2417ca4b4657cae5dc6763` |
| Device receipt | `c5237b26fe0a1ab7fe3c373aed50a34a0a6f65c306ed47918b4e4b54a9245208` |
| Device binary | `8592fb526b8796b3e118f1a18bacc276e89894459207d5df294b17b0c3859c50` |

The hosted consumer requires the exact same-repository Actions run ID,
attempt, export control commit, successful terminal run, artifact ID/name,
unexpired state, ZIP byte count/digest, inner payload byte count/digest and
payload manifest digest. It checks all these facts against the actual API
responses and downloaded original bytes. The archive contains no account,
simulator, signing material or credentials. Only the automatic read-only
Actions token is used to fetch the artifact; it is removed from the SDK and
compiler child environments. No repository credential is copied.

No qualified native8ac Actions artifact existed in the audited original
metadata. The source archive on Oracle is real and verified, but the earlier
simulator offhost-retention receipt explicitly records a failed binary
retention attempt. That failure is not represented as a successful backup.
The new export route is the concrete missing transport operation.

Known original export paths, to be reverified by the actual exporter, are:

```text
appSource:
/Users/m1/development/anytype-d-active-20261125/main14/source
materialization:
/Users/m1/development/anytype-d-active-20261125/main16-wave2-20261127/native-materialization-8ac
framework:
/Users/m1/development/anytype-d-active-20261125/main14/source/Dependencies/Middleware/Lib.xcframework
nativeSource:
/Users/m1/development/anytype-d-active-20261125/native-permission8ac/pinkha-dual-native-v1-8ac407e75a4b-simulator/source
```

The retained export App identity is separately bound through
`exportAppSourceSHA`/`exportAppSourceTree`; it must not be rewritten to the
future compiled App identity. The original native source and binary pins
remain the same regardless of which compatible Swift source root selects.

## Toolchain and resource admission

The workflow explicitly selects `/Applications/Xcode_27.app/Contents/Developer`.
Before compilation it retains original outputs of `xcodebuild -version`,
`xcrun swift --version`, and the simulator SDK build-version command. It
requires Xcode27.0/27A266a, the original Swift compiler identity
`swiftlang-6.4.0.34.1 clang-2100.3.34.1`, and SDK24A430. A newer default Xcode
does not satisfy these guards. An already installed native ARM64 Python3.12
is selected without downloading a runtime.

The cold App estimate is 16GiB, followed by a separate 2GiB UI estimate. The
original 2GiB live emergency floor, 512MiB concurrent allowance and four-job
limit remain. This estimate is informed by the actually recorded retained
Mac allocations: intermediates3,670,495,232B, Products2,973,990,912B,
SDK modules1,403,154,432B and package sources5,391,351,808B. It is **not** an
observed hosted peak or a reuse claim. Native download/extraction headroom is
admitted in addition before intake. Original result archival has a separate
bounded 8GiB envelope and a live free-space check.

The original phase monitor stops only its owned compiler group on deadline
or emergency floor. No queue silently waits for capacity and retries. Every
new workflow run/attempt has fresh output paths and refuses existing output.
The Mac export also uses a unique checkout/output for that run and attempt;
it does not clean an occupied project worktree or change global Git settings.

## Original source and product retention

The result tar retains the full actual compiled source including Git
identity, complete App/UI Products, generated UI source/project, original
compiler logs and xcresults, compiler FileLists, both native input receipts,
source/cache admissions, exact expanded producer and byte inverse, and
executed control source. Before/after node inventories and archive member
content checks accompany the tar. Compiler caches and intermediates are not
presented as application evidence. No input or product is deleted.

The existing receipt-admission769 validator is compatible with the hosted
producer's new source/cache receipts and paths while those original paths
exist. It requires canonical original paths, real Git identity, exact source
bytes and `samefile` compiler witnesses. A later import onto another machine
therefore needs a separately reviewed custody/relocation layer, or a retained
gate result produced at the original hosted paths. Rewriting absolute paths
in original receipts is not unchanged admission. In particular, this build
does not qualify the retained Mac T5 account or any UI journey.

The separate `NativeApp/UITests/NativeLaunchTests.swift` runner and its 23
selected methods are outside the combined App/Stage1 UI target compiled here.
They require their own original target/compiler evidence and scoped runtime
receipt. Selecting every Stage1 UI file does not count that different target
as compiled or executed.

## Preparing a source-only draft

Run on the authorized source host, using explicit immutable commits and the
original canonical SDK object store:

```bash
python3 -B Tools/PinkhaDualEngineRuntime/hosted_shared_build/run.py draft \
  --source /path/to/anytype-repository \
  --source-commit EXACT_ROOT_SELECTED_APP_COMMIT \
  --hanlin /path/to/original-hanlin-repository \
  --control-commit EXACT_EXECUTING_CONTROL_COMMIT \
  --output /fresh/path/hosted-plan.ready-false.json
```

The draft reads committed Git blobs even when the source reader is sparse;
it never modifies or trusts uncommitted source. It enumerates every original
`AnyTypeTests/Pinkha` Swift file, the four explicitly hosted package-test
sources and every original Stage1 UI Swift file. It derives the canonical
SDK materialization marker using the original materializer's exact path
ordering. Compilation must later prove the entire selected source set was
actually used. The root owner can generate a new draft for the upcoming SDK
union without changing this route or silently advancing a branch tip.

After root finalizes an exact plan, the `dispatch-request` subcommand writes a
reviewable JSON request without contacting GitHub. It preserves the plan's
final newline; shell command substitution would silently remove that newline
and break the exact hash binding.

```bash
python3 -B Tools/PinkhaDualEngineRuntime/hosted_shared_build/run.py dispatch-request \
  --plan /exact/root-plan.json --plan-sha256 EXACT_PLAN_SHA256 \
  --ref ROOT_VERIFIED_EXISTING_BRANCH \
  --route wave3-hosted-shared-build --output /fresh/dispatch-request.json
```

The root owner may then submit that exact reviewed file to the existing
workflow ID `389936648` using the authorized GitHub API. Preparation never
submits it. The running workflow independently checks that `GITHUB_SHA`
matches `controlCommit`, so a moved branch fails closed.

## Evidence and remaining work

The route feasibility audit binds actual hosted runs, image metadata and
original logs. The hosted Hanlin proof used run45942933110/job140321092861,
image`xcode-27-arm64/20261123.0387.2`; its original job log is
5,144,427B/SHA256`f045646db95f0b17fe4f7a00f45d9a6102a724ce087c3cd280a6b8b2c336b7e0`.
It failed during a separate NativeScript artifact-preparation route; it is
runner evidence, not current Anytype acceptance. The image's original
readme identifies the required27.0/27A266a installation. An older Anytype
hosted NativeApp job137474299509 at run45108211949 completed
`TEST BUILD SUCCEEDED`; that is a distinct historical source/target, not the
combined App requested here.

Portable tests exercise immutable admission, actual original byte inversion,
archive corruption/link/traversal/duplicate rejection, metadata roundtrip,
and a real temporary Git checkout with an injected untracked Swift source.
Their result is control-code evidence only. Actual native export, hosted
App/UI compilation, test discovery/runtime journeys, physical-device
acceptance, Release signing and TestFlight remain pending their own original
source-bound receipts.
