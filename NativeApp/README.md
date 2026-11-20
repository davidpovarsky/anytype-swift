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

After installing that verified artifact in a clean checkout:

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
| Production Swift property service | Earlier v6 15/15 remains historical; current v9 plain Windows attempt failed with an uncertain response | V8 exposed the missing serialized apply sequence, now fixed in v9. The v9 timestamp-only diagnostic isolates a 30-second GET/auth timeout; root cause remains open. The unchanged fifteen-check workflow is now also a hosted Apple test, execution pending. |
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
| New native application acceptance at d58b6a0 | All 5 methods executed and failed at real Keychain access | Standalone package XCTest received `unavailable(-34018)` / `secureStorageUnavailable`. Hosted signed simulator execution is being configured without changing the five tests or substituting storage; next Apple acceptance remains open. |
| Native AnyUI execution at d58b6a0 | 108/108 passed on arm64 iOS Simulator 27.2, zero skips | Source-bound xcresult includes the required focus 6 and marked-text 5, activation 4 and portable 93 cases. Evidence: `apple-d58-patched-runtime-v1/MANIFEST.json`. Executable interaction remains separate. |
| Separate executable acceptance | 7 XCUITests written; d58 executed zero because its app build selected x86_64 against an arm64 dependency | Real onboarding, Hebrew edit, Hanlin read consent, hierarchy/property workflow and live source Inspector quote/Note flow. The two later source-ready scenarios cover explicit direction/alignment and real hierarchy drag/drop across cold reopen. No executable acceptance is claimed yet; seven scenarios do not cover every implemented UI operation. |

At published commit `57c116e02ee6dbce21f3bbffcc297841d2bd1235`,
[Apple run44673740725](https://github.com/davidpovarsky/anytype-swift/actions/runs/44673740725)
has [sealed official embedded-library3/3 acceptance](../docs/any-engine-port/evidence/20261120/apple57-official-runtime-v1/MANIFEST.json), with no failures or skips. The patched v8
lifecycle step failed; protected Hanlin recovery and UIKit steps passed. The
hosted application gate is still running, and retained-consumer compatibility is queued. The precise lifecycle failure awaits the completed log.
This run does not include the local v9 receipt fix or the new presentation tests.

Current UI source fixes prevent delayed reads from replacing acknowledged
properties/text or erasing Undo, and retain newer typing/composition while a
native autosave is in flight. Seven property-model tests and three actual-native
editor tests are source-ready. Their Apple semantic/runtime execution remains
required; parser and structural receipts are not behavioral acceptance.

Read the source-bound receipts rather than adding these counts together: scopes,
versions and fixtures differ, and later features are not certified by an older run.
The detailed current capability table is
[CAPABILITY_STATUS.md](../docs/any-engine-port/CAPABILITY_STATUS.md).

## Scene and test isolation

Like the retained application, the executable explicitly disables simultaneous
scenes in its Info.plist. One root presentation owns the single managed native
runtime. CI checks the generated app bundle's actual scene declaration and
prefers an available iPad simulator on iOS 27 or newer.

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
