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
