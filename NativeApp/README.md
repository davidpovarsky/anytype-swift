# Pinkha on the Any native engine

This is the separate iOS executable for the new-engine port. Its process links
AnyLib and the new Host/UI packages. It does not instantiate the retained
Heart application. The retained application continues to compile against the
shared Torah and Hanlin implementations through its existing wrappers.

## Build the pinned native code first

Use the branch workflow .github/workflows/pinkha-any-engine-port.yml.
It checks out the exact Any/SDK base commits, applies the complete overlays
named by Tools/AnyEnginePort/prepare_native_runtime.py, verifies every
changed Git blob, and builds device and simulator XCFramework slices.
The installer binds the archive and all members to the application commit
and the native source manifest before enabling the local binary target.

The complete native overlay replaces the earlier foundation overlay.
Do not stack the historical patches.

The canonical Hanlin source must also be materialized with
Tools/Hanlin/prepare_sdk.py at the revision recorded by the workflow.

After installing that verified artifact in a clean checkout, and preparing the
owned Hanlin fixture/test-runner environment as the workflow does:

    export PINKHA_ANY_NATIVE_ARTIFACT=verified-v1
    xcodebuild test \
      -project NativeApp/AnyNative.xcodeproj \
      -scheme PinkhaAnyNativeApp \
      -destination 'platform=iOS Simulator,id=<owned-simulator-udid>' \
      -parallel-testing-enabled NO \
      ARCHS=arm64 ONLY_ACTIVE_ARCH=YES \
      CODE_SIGNING_ALLOWED=YES CODE_SIGNING_REQUIRED=YES CODE_SIGN_IDENTITY=-

The project requires Xcode 27 and iOS 27. The account acceptance suite uses five test sources from
Modules/PinkhaAnyNative in the `PinkhaAnyNativeHostedTests` scheme of this
project. A minimal simulator app hosts those tests with its own Keychain
entitlement. It does not start the product runtime; each test owns the actual
AnyLib lifecycle. The original five tests remain unchanged; three native editor publication tests and the original fifteen-check property workflow add four hosted methods. The named gate requires all nine. Standalone Swift package XCTest cannot certify Keychain access.

## Ownership and recovery

The executable declares an HTTP exception only for the literal `127.0.0.1`
address used by its embedded Any server. The built-bundle gate verifies that
exact transport configuration; ordinary provider connections keep the default
ATS policy. The runtime's per-boot control token and account/run checks still
apply to every native request. See Apple's
[IP-address exception contract](https://developer.apple.com/documentation/bundleresources/information-property-list/nsapptransportsecurity/nsexceptiondomains).

The app owns one managed runtime generation, one authenticated account and one
active Space. The Keychain service is specific to this executable. Recovery
phrases are handed only to explicit backup/recovery UI; control tokens are
opaque transport capabilities and never written into receipts.

A failed secure credential save revokes native authorization and blocks document
access. A known generated credential remains available to the explicit recovery
flow, which must save the same account before continuing. Background shutdown
revokes the presentation, drains owned work, then stops the matching runtime
generation. The expiry hook cannot stop a subsequent boot.

Object and block creation share a protected metadata journal. Intent identities
survive reopen; lost replies do not trigger a new create. A native partial root
response retains its original Space/object ID as uncertain recovery metadata.
Hanlin retains its original journal format and records known partial IDs in an
additional metadata-only sidecar; incomplete creation is never a committed receipt.

## Acceptance status

The source-bound component and native-engine receipts are in the module
Evidence directories and Tools/AnyEngineValidation/evidence.
The new UIKit graph, native account package and executable have their own Apple
CI steps. Parser checks and Windows package tests do not certify those steps.

This checkpoint does not claim complete original-application parity, a signed IPA,
physical-device validation, or completed Heart-data migration. The detailed
capability inventory and open Asana work items remain the acceptance authority.

## Current acceptance evidence

The complete default overlay is native v9, manifest
`Tools/AnyEngineValidation/evidence/native-property-receipts-v9-source.json`.
It includes v8 caller-captured property sequence checks and explicitly validated
conditional no-ops. V9 returns the actual SDK apply sequence in the dedicated
property receipt, alongside the exact property version and engine run. The
strict Swift client requires all three before accepting a write or its Undo.
The generic stock response contract is unchanged.

Its exact 90 changed files (49 Any and 41 SDK) were reapplied to disposable clean
Git indexes. Each resulting full tree equals `testedEffectiveTree`; the older
`testedLocalCommit` is explicitly the local parent. The manifest records the
uncommitted v9 overlay separately. Artifact installation verifies the exact
patches, file blobs, effective trees and application commit. Apply this complete
overlay once.

| Execution scope | Latest completed result | Boundary |
| --- | --- | --- |
| Swift Integration at published57 | 126 tests in 10 suites, source-bound Apple PASS | Domain and adapter tests; no UIKit execution |
| Production Swift canonical archive against native v8 | 16/16 checks | Current unchanged workflow: association history/payload export, explicit ID mapping, native import/retry; not full Heart body/file migration. `native-v8-archive16-v1/` |
| Production Swift guarded creation against native v8 | 14/14 checks | Real native object/block creation with an explicitly in-memory metadata journal. `native-v8-creation14-v1/` |
| Production Swift property service | The unchanged fifteen-check workflow passed in actual hosted Apple execution at c8, in28.568 seconds | [Exact hosted archive](../docs/any-engine-port/evidence/20261120/apple-c8-hosted-application-v1/MANIFEST.json). The previous Windows GET/auth timeout remains a preserved failure with unresolved cause; this Apple pass does not erase it. |
| Native v6 definition/property policy | 4 SDK tests, 19 top-level HTTP tests / 31 cases, and 11 two-peer checks | Actual storage, signed claims, sync, definition removal and cold reopen |
| Native v7 independent document metadata | 4 focused native tests and 7 real HTTP/cold-reopen checks | Fresh editor policy before claims installation; exact Type/target dependencies |
| Current property-fence components | Integration 35/35 and Host 23/23 passed against their exact source and dependency receipts | Includes original property operations/Undo, captured sequence/run propagation and archive no-op request contracts; native runtime acceptance is separate |
| Native v8 conditional property implementation | SDK17/29 and HTTP19/47 passed; full regression64/140 and real hierarchy20/20 passed | No skips. Original assertions cover no-op, captured sequence/run, ABA, competing writers, safe folder removal and native live updates. `native-final-v8-go-regression-v2/` and `guarded-hierarchy-native-v8-v1/` |
| Native v9 property receipt | Actual HTTP19 top-level/47 cases and pinned native build passed | Only the dedicated receipt gains the real SDK sequence; generic routes and all SDK sources are unchanged from v8. Full clean effective-tree and four-file delta review are preserved in `native-property-receipts-v9-wire-review/`. |
| Native v9 two-peer object workflow | 16/16 actual runtime checks | Verified network partition/reconnect, global collision closure, scoped SSE and bin restore. A bounded read-only convergence barrier precedes the original single peer-B append. No write retries or assertion relaxation; all owned firewall rules/processes removed. `native-final-v9-object-runtime-v1/` |
| Live Sefaria through the original production facade | 7/7 real network checks, source stable | Hebrew reference/text/version, commentary, hierarchy, topic search/resolve and word context; no mocked provider |
| Apple package execution at d58b6a0 | Engine 67; Integration 107; Host 55 XCTest + 11 Swift Testing; Hanlin 33; TorahPresentation 1 XCTest + 10 Swift Testing; AnyUI 4 XCTest + 93 Swift Testing; PinkhaKit 217 | All passed on macOS/Xcode 27. The earlier split-surrogate recovery failure and its fix are preserved separately. Exact source-bound evidence: `apple-d58-packages-v1/MANIFEST.json`; this does not execute UIKit or the native app. |
| Apple package execution at57c116e | Engine67; Integration126/10; Host65 XCTest+11 Swift Testing; Hanlin33; TorahPresentation1+10; AnyUI4+93/16; PinkhaKit217/29; live Sefaria7 | All passed with zero failures/skips. [Exact archive](../docs/any-engine-port/evidence/20261120/apple57-packages-v1/MANIFEST.json); these counts exclude the later v9/property/editor changes. |
| Official and patched v7 AnyLib | Each passed 3/3 lifecycle/control tests at 27b4b2c and again at d58b6a0 | Actual arm64 iOS Simulator 27.2. Both source-bound named-execution archives are complete; the patched job's later application gates failed separately. These lifecycle tests do not certify the app or protected journals. |
| Historical native application acceptance at d58b6a0 | All 5 methods executed and failed at real Keychain access | Standalone package XCTest received `unavailable(-34018)` / `secureStorageUnavailable`. The original methods subsequently passed in the real signed simulator host at57, as recorded below. |
| Hosted native application at57c116e | All original5/5 passed, zero failures or skips | Real AnyLib/account/Keychain/editor/creation/association tests. Later publication and property execution is recorded separately at c8 below. |
| Native AnyUI execution at d58b6a0 | 108/108 passed on arm64 iOS Simulator 27.2, zero skips | Source-bound xcresult includes the required focus 6 and marked-text 5, activation 4 and portable 93 cases. Evidence: `apple-d58-patched-runtime-v1/MANIFEST.json`. Executable interaction remains separate. |
| Separate executable at57c116e | Actual2/7 passed and5 failed, zero skips | Every failed scenario stopped at backup acknowledgement before Space/editor assertions. The recorded outer Switch row contained a distinct physical child Switch; all five remained off after the outer-row tap. The corrected helper taps that observed child once and requires0→1 while retaining the Continue enabled guard. Its Apple execution remains pending. |
| C8 runtime diagnostic | All original3 methods explicitly passed in the closed log | [Safe source-bound archive](../docs/any-engine-port/evidence/20261120/apple-c8-runtime-metrics-v1/MANIFEST.json). Four denied reads returned403; no timeout recurred. The final xcresult/destination gate is still separate. |
| C8 UIKit test target | Build cancelled with exit65; zero tests executed | [Exact compiler failure](../docs/any-engine-port/evidence/20261120/apple-c8-ui-compile-failure-v1/MANIFEST.json). Two helper calls passed a mutating dictionary expression directly to a Testing macro. The follow-up evaluates the removal first and retains the same non-nil requirement and resume behavior. |
| C8 hosted native application | Actual9 executed:8 passed,1 failed, zero skips or unexpected failures | [Exact closed-log archive](../docs/any-engine-port/evidence/20261120/apple-c8-hosted-application-v1/MANIFEST.json). Account/recovery3, creation1, property1 and Torah1 passed; publication2 passed and1 failed four immediate readback/focus assertions. |
| Empty native paragraph correction | All16 Host creator component tests passed against the corrected production source | [Exact source and component proof](../docs/any-engine-port/evidence/20261120/native-empty-paragraph-fix-v1/MANIFEST.json). The native engine omits the text field for empty paragraphs; successful creation now accepts only that absent-field representation for an empty intent. Explicit null/wrong types, nonempty intent, identity/type/style/parent/position and journal checks remain strict. This component archive predates the separate actual-native result below; corrected Apple execution remains pending. |
| Corrected production creator on native v9 | Original14 plus2 sparse-empty/exact-retry checks passed, zero failures | [Exact native16 proof](../docs/any-engine-port/evidence/20261120/native-empty-paragraph-runtime-v1/MANIFEST.json). A new synthetic Space, unchanged plain transport and original30-second request timeout; stable source/native binary, preserved ID/version/history on retry and synthetic-object cleanup. The in-memory metadata journal does not certify protected Apple persistence. |
| Retained application compatibility | The57 build failed before test execution because its create-page wrapper omitted the existing shared module import | [Failure](../docs/any-engine-port/evidence/20261120/apple57-retained-consumer-failure-v1/MANIFEST.json) and [one-line import correction](../docs/any-engine-port/evidence/20261120/retained-hanlin-platform-import-fix-v1/MANIFEST.json). No SDK/API duplication, dependency change or test change; the retained Apple build and its five suites still require execution. |
| Current executable scenarios | Ten business XCUITests plus one separately classified picker observation required | Original9 bodies/helpers remain unchanged. Added selected-context Hanlin with separate create consent and cold reopen; the picker observation is diagnostic only. Registration, syntax and saved-response decoding do not certify mounted behavior. |

At published commit `57c116e02ee6dbce21f3bbffcc297841d2bd1235`,
[Apple run44673740725](https://github.com/davidpovarsky/anytype-swift/actions/runs/44673740725)
has [sealed official embedded-library3/3 acceptance](../docs/any-engine-port/evidence/20261120/apple57-official-runtime-v1/MANIFEST.json), with no failures or skips. The
[completed patched archive](../docs/any-engine-port/evidence/20261120/apple57-patched-runtime-v1/MANIFEST.json)
records Runtime2/3, Hanlin36/36, UIKit108/108, hosted application5/5 and executable UI2/7, all with zero skips.
The runtime failure was an initial unauthenticated GET `/v1/pinkha/capabilities`
timeout before shutdown/restart. A native403 log does not prove socket delivery;
no transport root cause is claimed. The current test collects bounded passive
URLSession metrics and emits them after the awaited read completes or fails.
It keeps the original session, URLs, request order, default timeout and assertions.

The five executable failures share the observed backup-toggle boundary described
above. Full recovery-screen AX/video/ZIP data stays outside the published evidence;
the archive contains screened control metadata and exact source/result hashes.
Retained-consumer compatibility subsequently failed during build-for-testing,
before any test began, because the create-page wrapper used
`HanlinToolInvocationID` without importing its existing `HanlinPlatformContracts`
module. The explicit import is corrected in this checkpoint; its original body,
dependencies and tests are unchanged. This historical run predates the
published v9 base checkpoint `2dca5f6c1c64ab96d5fd32abb7d8628d919543ec`
and does not certify its property/editor changes or the follow-up test corrections.

The [two-helper macro correction](../docs/any-engine-port/evidence/20261120/native-property-require-macro-fix-v1/MANIFEST.json)
keeps all seven property scenario bodies and their assertions unchanged. It fixes
test-target compilation; actual Apple UIKit behavior remains to be executed.
The [source identity receipt](../docs/any-engine-port/evidence/20261120/apple-c8-runtime-current-source-binding-v1.json)
confirms that the production modules and runtime test source were identical
between c8 and the published Hanlin checkpoint ddff3d3. The new mounted UI and
provider fixture still require their own run. Runtime diagnostic intervals
include synchronous output and scheduling; they do not establish a cause of the
previous timeout or pure network latency.

Current UI source fixes prevent delayed reads from replacing acknowledged
properties/text or erasing Undo, and retain newer typing/composition while a
native autosave is in flight. The three actual-native editor publication tests
executed at c8: two passed and the third exposed a valid empty paragraph being
rejected by creation readback. Its immediate assertions remain unchanged. The
narrow production correction passed sixteen component tests and the original
fourteen real-native creation checks plus two sparse-empty/retry checks. Corrected
hosted execution and the seven property-model UIKit tests remain required.

Read the source-bound receipts rather than adding these counts together: scopes,
versions and fixtures differ, and later features are not certified by an older run.
The detailed current capability table is
[CAPABILITY_STATUS.md](../docs/any-engine-port/CAPABILITY_STATUS.md).

## Mounted Hanlin and archive observation

The ten business XCUITests now include the ordinary Hanlin Configure, Send and
consent interfaces. The new journey denies source sharing first, then grants
only the selected block, cancels one create request, approves a separate request,
and checks exactly one empty page in the original Space after a cold reopen.
It also verifies that the original source blocks, identities and text remain intact.

CI prepares a finite HTTPS/SSE provider from the pinned canonical Hanlin fixture
builders. It creates a private temporary CA, installs its public root only in
the simulator whose UUID, runtime, type and run-specific name were verified,
and supplies configuration to the test runner. The app receives the endpoint,
model and synthetic key through the existing configuration UI. No provider
credential or control token is committed. The native application keeps its
existing ATS policy and URLSession transport. Cleanup proves the owned child
and listener stopped before removing private files; deleting the owned simulator
removes the temporary trust. Actual default-URLSession trust and mounted behavior
are checked by the Apple run, not inferred from the Windows fixture checks.

The separate `archive-picker-observation` profile requires
`testObserveCanonicalArchiveSystemPickers`. It captures the real Export/Import
system-picker accessibility surface and screenshot for the next implementation
step. It does not save, import, map IDs or certify a writable Files provider.
Its private xcresult attachments must be screened before publication. Full
canonical archive transfer through the mounted interface remains open.

Pre-publication evidence is source-bound: [fixture controls and lifecycle](../Tools/AnyEngineValidation/HanlinProviderFixture/evidence/20261120-v1/MANIFEST.json),
[exact Swift consumer and source retention](../docs/any-engine-port/evidence/20261120/native-hanlin-and-picker-ui-v1/MANIFEST.json),
[CI ownership/schema review](../docs/any-engine-port/evidence/20261120/native-hanlin-ci-orchestration-v1/MANIFEST.json)
and [named-result gate controls](../docs/any-engine-port/evidence/20261120/native-apple-execution-gate-controls-v9.json).
The 35 fixture controls, ten lifecycle checks, seven original Swift response
vectors, nine saved-response decodes, 18 schema controls and 14 gate controls
cover different boundaries and are not a combined count of Apple app tests.

At 2026-11-20 07:21 UTC, the published c8
[Apple run44682744488](https://github.com/davidpovarsky/anytype-swift/actions/runs/44682744488)
had completed its patched job with failure: Runtime and protected Hanlin steps
passed, UIKit failed compilation, hosted application passed8/9, and executable
UI failed with detailed results under review. The official-runtime job passed.
The package job was still running and had failed its live Sefaria step; no
package-wide success is claimed. That revision predates the mounted Hanlin and
picker additions and cannot certify them. The published macro correction at
3d9932 and the new empty-paragraph/import corrections need their own Apple run.

## Scene and test isolation

Like the retained application, the executable explicitly disables simultaneous
scenes in its Info.plist. One root presentation owns the single managed native
runtime. CI checks the generated app bundle's actual scene declaration and
prefers an available iPad simulator on iOS 27 or newer.

Each workflow revision has its own concurrency group, immutable checkout and
owned simulator/data directory. A newer revision can validate while an older
retained-consumer job finishes; no test or signing gate is removed.

Debug-only UI tests use a UUID-specific data directory and Keychain namespace.
Reusing that exact test UUID permits a cold-process reopening test. Native Space
creation uses the real configured network; an empty node configuration is not
treated as a proven offline Space-bootstrap implementation.

Saved text is verified after process termination. Unsaved draft recovery is
currently bounded, account/Space-scoped memory retained across background
runtime replacement. Every recovered draft obtains a fresh native snapshot;
a late matching native confirmation is reconciled without another write, and
remaining changes require review. This is not process-persistent unsaved-draft
storage.
