# Future Native accessibility tests — source preparation only

This isolated test-only tranche appends two methods to the exact current
`NativeApp/UITests/NativeLaunchTests.swift` donor. It does not change the App,
native contract, SDK, existing 19 test methods, their assertions, the shared
8f2c retry, or any current validation controller. No compiler, simulator,
VoiceOver service, accessibility audit, or device test has run for this tranche.

## Source boundary

The immutable base is `c95395aec96214dfabd73d55755baa95689cc6d3`. Its NativeLaunch
file has SHA256
`31c64474cebf4890050f9077d3c44fac63264d878a77bd6f55811cc407e02422`
and 214,858 bytes. The candidate preserves that entire file as an unchanged
prefix. Removing one appended suffix restores it byte for byte, including all
19 existing methods. `source-proof.json` records the exact suffix and candidate
digests. The existing 80d82 NativeUI preparation remains separately frozen and
does not admit this candidate by source override.

The parent reported the current warm retry source
`8f2c11713fb8a40ae13444104723666ffef68afe` as a documentation-only child of
c953, retaining the same 31c NativeLaunch donor. This future branch is not part
of that retry. A later explicit test-source freeze and closed consumer profile
must qualify any use of these added methods.

## Installed API observation

Read-only inspection found Xcode **27.0 / 27A266a**, the iPhoneSimulator **27.0**
SDK, and these actual XCUIAutomation headers under:

`/Applications/Xcode.app/Contents/Developer/Platforms/iPhoneSimulator.platform/Developer/Library/Frameworks/XCUIAutomation.framework`

| Surface | Installed declaration and limit |
| --- | --- |
| `XCUIDevice.voiceOverService` | Main-actor service, available on iOS 27; no simulator exclusion appears in these headers. |
| Service state | `isEnabled`; throwing public `enable()` and `disable()` methods. |
| Speech/navigation | Throwing `currentSpeech()`, `moveForward()`, `moveBackward()`, plus container movement APIs. |
| `XCUIVoiceOverService.Output` | Only `utterance: String`; it does not expose the focused accessibility identifier. |
| Service errors | Start, not-running, no-speech, and stop failures; no public per-operation timeout parameter was observed. |
| Accessibility audit | `.all` includes iOS Dynamic Type, text-clipping and traits in addition to the other audit categories. Returning `true` from its issue handler suppresses the issue; the candidate always returns `false`. |
| `simctl help ui` | Supports both `large` and `accessibility-extra-extra-extra-large`; help was read without setting or querying a live device preference. |

`installed-sdk-api-manifest.json` retains exact header/interface/API-notes paths,
lengths and SHA256 values. Complete vendor header text remains in the private
inspection record and is not published in this repository.

**The Swift importer is still unverified.** The actual arm64 and x86 Simulator
Swift interfaces do not list VoiceOver refinement wrappers, while the headers
mark speech/navigation as refined for Swift. The inspected API-notes files have
no additional VoiceOver mappings. The draft uses Apple's documented public
Swift methods. A real future NativeUI compilation must resolve this discrepancy;
there is no private importer name, Objective-C runtime dispatch, dynamic selector
fallback, or assumed successful typecheck.

Official API references consulted:

- https://developer.apple.com/documentation/xcuiautomation/xcuivoiceoverservice
- https://developer.apple.com/documentation/xcuiautomation/xcuivoiceoverservice/output
- https://developer.apple.com/documentation/xcuiautomation/xcuivoiceoverservice/moveforward()
- https://developer.apple.com/documentation/xcuiautomation/xcuivoiceoverservice/currentspeech()
- https://developer.apple.com/documentation/xcuiautomation/xcuivoiceoverservice/enable()
- https://developer.apple.com/documentation/xcuiautomation/xcuivoiceoverservice/disable()

The installed API declarations establish a supported API surface, not that the
selected shared Simulator runtime can operate the service. A bounded metadata
lookup found no runtime plists at the inspected locations; that does not prove
the runtime is absent or VoiceOver is unsupported.

The separate `VoiceOverPublicAPICompileProbe.swift` contains one uninvoked
function that references precisely the public API needed by the future method.
It has no test case, top-level call or entry point. Wave3 must first run an
actual `swiftc -typecheck` check with the selected Simulator SDK/target and an
owned module-cache path, retaining the exact source hash, invocation, compiler
identity, stdout/stderr and exit status. This is a compile-only gate and must
not link or execute the probe, launch an App or change VoiceOver settings.
Neither a successful probe nor this preparation establishes UI acceptance.

## Two future methods

| Selector suffix in `PinkhaAnyNativeUITests/NativeLaunchTests/` | Scope and evidence |
| --- | --- |
| `testNativeLibraryAndEditorAccessibilityAuditAtRequestedContentSize` | Creates one real disposable native account/Space/document through the existing UI helpers; retains saved body and block identity; runs the original `.all` accessibility audit on Library and the reopened editor; keeps all XCTest issues and JSON/AX/PNG evidence. |
| `testNativeVoiceOverTraversalSpeaksCurrentNativeContent` | Creates the same small fixture; requires VoiceOver initially off; enables the public service; records actual utterances while moving forward to the fixture phrase, confirms current speech, moves to another utterance, returns backward and confirms the phrase again; disables VoiceOver and fails cleanup errors. |

Each method has a finite 900-second XCTest allowance, including account and
fixture setup. VoiceOver's traversal permits at most 24 search-forward moves,
one additional forward move, one backward move and three current-speech reads:
29 speech operations in total. It checks a 60-second traversal budget before
and after each synchronous operation. The API has its own non-configurable
operation timeout; this code cannot interrupt a blocked service call. The
future controller must enforce the XCTest allowance and retain timeouts as
failures. Speech exceeding 16 KiB in one output fails with a hash/length
diagnostic rather than being accepted after truncation.

The comparison matches a phrase that exists only in the newly created paragraph.
The trace is evidence of actual VoiceOver navigation and speech for that
fixture text. It does not claim that `Output` identified an accessibility
element, that generic `XCUIElement.hasFocus` proves VoiceOver focus, or that
rotors, activation, audio quality, touch exploration or manual use passed.

Both methods register final diagnostic capture before App launch. Before App
termination they retain one bounded private AX tree, one actual screen PNG and
the exact invocation context, including if startup, onboarding, fixture setup,
navigation or an audit fails. This last capture intentionally has no completed-
onboarding precondition. Its contents can include the disposable account's
onboarding screen and must remain private; publish only hashes and structural
metadata, never its raw AX or PNG contents. Capture/termination errors fail.

The audit method is intended for a separately scheduled `large` versus
`accessibility-extra-extra-extra-large` comparison using the same agreed device,
language and appearance. The VoiceOver method currently accepts the `large`
cell only. Scheduling these cases does not replace the separate cross-language,
device and appearance matrix or physical/manual device acceptance.

## Required closed invocation and result envelope

The candidate fails before App launch unless its runner has
`PINKHA_SIMULATOR_UI_DISPOSABLE=1` and a complete
`PINKHA_NATIVE_ACCESSIBILITY_CONTEXT_JSON`, with a matching SHA256 in
`PINKHA_NATIVE_ACCESSIBILITY_CONTEXT_SHA256`. The JSON contains exactly:

`schema`, `runID`, `appSourceCommit`, `uiSourceCommit`, `simulatorUDID`,
`ownedScope`, `method`, `appLanguage`, `osLanguage`, `contentSize`, `appearance`,
`deviceFamily`, `settingsReadbackSHA256`.

The schema is `native-accessibility-invocation/v1`. Identifiers and hash shapes
are checked; the exact selected method is checked; the runner's observed
`SIMULATOR_UDID` must equal the bound device. The account fixture uses the
specified owned scope in the existing `--native-ui-test-scope` launch argument.
App language is either the original Hebrew configuration or its exact English
counterpart with the same owned flags. No product instrumentation is added.

This parser is an integrity check, **not independent source or OS attestation**.
Before any execution, the future controller must:

1. Admit the real App/UI products, native/SDK/source identity and actual compiler
   inputs through an exact reviewed profile. If App and test source differ,
   require an explicitly reviewed source closure; do not use a source override.
2. Create and own the disposable device and scope, retain actual language,
   appearance and content-size readbacks for that exact UDID, then hash the
   retained settings record into the invocation. Read them again after the
   selected case and compare; the current large-only RTL profile stays intact.
3. Bind the exact invocation to the original test descriptor, one-method
   enumeration, actual test launch, XCTest result and exported attachments.
   Verify that the runner supplies `SIMULATOR_UDID`; missing identity fails.
4. Preserve actual audit failures, service errors, timeouts, cleanup errors and
   unsupported-runtime results. No skip, ignored audit, fake service, or retry
   that discards a previous failure is allowed.
5. Export and inspect the typed JSON/AX/PNG evidence, bind it to the same device,
   scope and selected method, and complete visual review before claiming
   visual acceptance. The original XCTest result remains the case authority.

No such consumer or runtime result is supplied by this preparation. Physical
device and manual VoiceOver acceptance remain separately **NOT_RUN**.
