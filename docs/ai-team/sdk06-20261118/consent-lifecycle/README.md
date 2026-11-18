# Supported native consent lifecycle ? SDK06

## Observed Apple result

Run [44253632413](https://github.com/davidpovarsky/anytype-swift/actions/runs/44253632413) used App source `f0e0165d3396f933a14cd755312b836b60643623`, the verified r14 Heart from run `44203168617`, and a disposable iPad Pro 13-inch (M5) simulator on iOS 27.0 (24A434).

The App built. The actual native selected-block preparation passed (1 test, 0 failures, 0 skips). The selected-block UI method failed (0 passed, 1 failed, 0 skipped): it performed the real long-press selection and Share action, displayed native consent, and tapped ?Allow for this presentation? at XCTest time 37.00 seconds. Subsequent accessibility output showed ?Access to the current source was not allowed.? while Chat remained mounted with one selected block. The pre-Allow screenshot shows the actual consent sheet and no denial banner.

The driver retained only three completed checks: middleware logging disabled, actual single-block selection context, and read denied before native consent. It timed out awaiting the successful-read/Return phase. There is no selected-read or native-return PASS. Provider configuration remained false.

These observations prove denial after the real Allow action. They do not identify whether the old disappearance observer or a subsequent authority validation produced the denial. This change is therefore a source-contract repair that still requires a new actual Apple UI run.

## Source repair

The previous read and create prompts inserted an observer UIView into UIAlertController's private view hierarchy. Apple documents that this hierarchy must not be modified. A presentation-controller delegate alone cannot replace that observer for programmatic dismissal because its dismissal callback does not run for programmatic dismissal. The existing Anytype navigation API can dismiss just the top child prompt while leaving Chat alive.

Anytype now owns a small native UIKit permission controller with actual accessible labels and Cancel/Allow buttons. Allow validates and completes its exact pending decision before dismissal. Child-only programmatic disappearance denies only a still-pending decision; a completed Allow is not overwritten. Interactive dismissal is disabled, with no grabber, so a cancelled swipe cannot finish a decision while leaving a dead prompt visible.

Read retries receive a fresh decision object. Each callback retains only that exact prompt's identity; a delayed old Allow cannot resolve a replacement request. Terminal owner, task, account, Space, scene and stale-context checks remain in force. Read validation also runs after awaiting consent. Create retains its separate title/Space confirmation and native write-readiness checks. Chat's owner-disappearance hook preserves the native Return completion and does not invalidate merely because the permission sheet covers Chat.

The UI22 driver already waited for `presentedViewController == nil` after read permission and again after cancelled create; those waits are preserved. Successful decision resolution does not bypass the no-covering-presentation readiness gate. UI22 remains 22 checks and selected-block UI remains 9 checks, with new stable identifiers for the actual owned prompt controls. No consent, selection or native mount is fabricated by the driver.

The app's existing file-system-synchronized Sources group includes the new controller without a project-file rewrite. Canonical Hanlin remains the only AI/chat implementation.

## Focused verification

All 10 changed Swift files passed `swiftc -frontend -parse -swift-version 6 -D DEBUG` under the installed Windows Swift 6.3.3 toolchain. This is syntax verification only; Apple typechecking, UIKit runtime behavior, native creation, and the new component tests remain NOT_RUN at this source handoff.

The adapter suite now declares 35 methods. The four required new or renamed regression methods are:

- `nativePromptAllowsBeforeDisappearanceAndRevalidatesOwner`
- `nativePromptProgrammaticDismissalDeniesPendingAllow`
- `oldNativeAllowCannotResolveReplacementPrompt`
- `taskCancellationWinsBeforeQueuedNativeAllow`

They exercise the production owned controller's real UIControl actions and supported appearance lifecycle, including both permission purposes, stale validation, reentrant revocation, explicit Cancel, programmatic disappearance, old-prompt identity, and task cancellation. Modal-interaction policy assertions are inside the existing helper, with no extra method or parameter. These component controls are not a substitute for an actual account/UI run.

The source-bound SDK profile must require 70 methods / 71 argument runs (the existing two-budget method is unchanged). The root-owned combined profile must require 121 methods / 140 argument runs. Root owns those runner/profile changes. This commit does not alter the journal's protection or durability requirements.

## Evidence and provenance

`raw/` contains selected original artifact bytes, not a rewritten diagnostic result. `origin-manifest.json` maps each retained file to its original archive member, size and SHA256. The complete artifact was verified in memory and was not committed or copied to Scratch.

Artifact `14409657321`: 44,499,470 bytes; SHA256 `18d0277a900bb119beae00a5267ed00e7af5b4a412cbda7e2c1813e74e5a3471`. Nested evidence ZIP SHA256: `94b9ca3ccc15abdb476206474b3a8f510dc5db6dcedcad4870cdb63106726fff`.

Local attributes preserve raw bytes across Windows checkouts. Source base and all 10 resulting file hashes are in `source-manifest.json`; parse arguments, source hashes and limitations are in `swift6-parse.json`.

Apple references:
- https://developer.apple.com/documentation/uikit/uialertcontroller
- https://developer.apple.com/documentation/uikit/uiadaptivepresentationcontrollerdelegate/presentationcontrollerdiddismiss(_:)
