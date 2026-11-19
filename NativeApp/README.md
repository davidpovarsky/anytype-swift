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
      CODE_SIGNING_ALLOWED=NO

The project requires Xcode 27 and iOS 27. The separate native package acceptance
suite uses Modules/PinkhaAnyNative, scheme PinkhaAnyNative.

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

The complete default overlay is native v7, manifest
`Tools/AnyEngineValidation/evidence/native-document-metadata-v7-source.json`.
It includes the v5 creation/claim fences and v6 document/property policy.
Its exact 85 changed files were reapplied to disposable clean Git indexes.
Do not stack historical v1–v6 patches on top of this overlay.

| Execution scope | Latest completed result | Boundary |
| --- | --- | --- |
| Swift Integration | 107 tests in 9 suites, source stable | Domain and adapter tests; no UIKit execution |
| Production Swift canonical archive against native v5 | 16/16 checks | Association history/payload export, explicit ID mapping, native import/retry; not full Heart body/file migration |
| Production Swift guarded creation against native v5 | 14/14 checks | Real native object/block creation; this probe uses an in-memory metadata journal |
| Production Swift property service against native v6 | 15/15 checks | Type preservation, typed values, membership, hidden fields and conditional Undo |
| Native v6 definition/property policy | 4 SDK tests, 19 top-level HTTP tests / 31 cases, and 11 two-peer checks | Actual storage, signed claims, sync, definition removal and cold reopen |
| Native v7 independent document metadata | 4 focused native tests and 7 real HTTP/cold-reopen checks | Fresh editor policy before claims installation; exact Type/target dependencies |
| Final v7 native regression | 64 top-level tests / 134 including subtests, no skips | Exact current SDK guards, claim contracts and HTTP routes; source and binary stable |
| Final v7 two-peer object workflow | 16/16 actual runtime checks | Verified network partition/reconnect, global collision closure, scoped SSE, orphan/bin refusal; optional 10,001-claim scale check was not repeated |
| Live Sefaria through the original production facade | 7/7 real network checks, source stable | Hebrew reference/text/version, commentary, hierarchy, topic search/resolve and word context; no mocked provider |
| Apple package execution at a5a4a6 | Engine 67; Integration 107; Host 55 XCTest + 11 SwiftTesting; Hanlin 28; PinkhaKit 217 | All passed on macOS/Xcode 27; the same run's Presentation and AnyUI dependency compilation failed on the shared Sendable contract |
| New native application acceptance | 5 real AnyLib/Keychain/journal tests written | Includes the full T5/quote/reopen path; Apple execution pending |
| Native AnyUI composition and focus | Dedicated UIKit acceptance suite written | Pure composition checks passed separately; actual UIKit execution remains pending |
| Separate executable acceptance | 5 XCUITests written | Real onboarding, Hebrew edit, Hanlin consent, hierarchy/property workflow, live source inspector quote/Note flow, background and cold reopen pending Apple execution |

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
