# Hosted native application tests

The d58 standalone package run actually executed all five native application tests and failed at real Keychain access with error -34018. Its original evidence is retained in [the patched-runtime archive](../apple-d58-patched-runtime-v1/MANIFEST.json).

The new `PinkhaAnyNativeHostedTests` scheme references the same three files in `Modules/PinkhaAnyNative/Tests/PinkhaAnyNativeTests`. It uses a separate empty SwiftUI application, `PinkhaAnyNativeTestHost`, as `TEST_HOST`; `BUNDLE_LOADER` points to that executable. The host never starts an Any runtime. Each original test still owns its real runtime lifecycle. All thirteen directly imported library products are explicit test target dependencies.

The host declares its own application identifier and matching private Keychain access group, using Xcode's actual `AppIdentifierPrefix` and bundle identifier. No team identifier, production access group, credentials, mock vault or fallback storage are introduced. Original test sources, original method names, acceptance thresholds and the NativeLaunch scheme are unchanged.

## Apple configuration contract

Use Debug with the patched artifact environment, `ARCHS=arm64 ONLY_ACTIVE_ARCH=YES`, `CODE_SIGNING_ALLOWED=YES CODE_SIGNING_REQUIRED=YES CODE_SIGN_IDENTITY=-`, and `-parallel-testing-enabled NO`. The root workflow supplies the existing simulator destination. Inspect the resulting signed host entitlements and run all five unchanged tests; source configuration is not evidence of Keychain success.

## Primary documentation and repository precedent

- [Apple build settings](https://developer.apple.com/documentation/xcode/build-settings-reference.md): `TEST_HOST` selects the executable receiving the test bundle; `BUNDLE_LOADER` binds bundle loading to its executable. The entitlement-file and base-entitlement settings configure signing.
- [Apple errSecMissingEntitlement](https://developer.apple.com/documentation/security/errsecmissingentitlement.md): required entitlement absence and default Keychain group selection explain the observed failure class.
- [Apple Keychain access groups](https://developer.apple.com/documentation/bundleresources/entitlements/keychain-access-groups.md): documents the access-group entitlement.
- Existing `Anytype.xcodeproj/project.pbxproj` already uses `BUNDLE_LOADER = $(TEST_HOST)` and an application executable as `TEST_HOST`. The exact source hash and matching lines are captured in [result.json](result.json).

The Windows check parses the complete OpenStep project and XML, verifies all references and package paths, compares original source hashes, and validates that the host does not boot a second runtime. **Xcode semantic compilation, real signing, and hosted Keychain execution remain pending Apple CI.**
