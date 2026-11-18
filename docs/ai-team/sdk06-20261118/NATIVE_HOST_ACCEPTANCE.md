# SDK06 real native read/create acceptance lane

## Scope and current evidence

This adds a narrow opt-in native integration lane. It complements, and does not
replace, the four SDK component suites. The supported write is creation of a
new standard Page with its title only. Existing document edits, body insertion
by Hanlin, external models, provider configuration, release builds, and user
accounts are outside this lane.

The fixture preparation writes a known paragraph through Anytype's real native
block service into a freshly created disposable Page. The tested Hanlin host
reads that paragraph only after the XCTest presses its existing native consent
alert. The XCTest then cancels one real create-page prompt and approves another.
It never constructs `PinkhaHanlinCreateApproval` or changes a production gate.

The app driver is compiled only for `DEBUG && targetEnvironment(simulator)`.
It is activated only by the exact opt-in environment and a recent single-use
fixture, bound to the actual local account, original Space, mounted editor,
unselected document, presentation session, CI SHA, run ID and attempt. It starts
after the actual host installation. An invisible or ambiguous document, existing
result, wrong account, nonlocal server, configured provider, or mismatched fixture
fails setup. A small diagnostic label exposes metadata and phases to XCTest.

The canonical `HanlinHostDispatcher` calls the installed production
`PinkhaHanlinReadWriteHost`. Its forwarding observer records call identities and
counts without changing context, catalog, approvals, results or cancellation.
The actual shared native write journal supplies the created object's opaque ID;
that ID is used to read back the actual Page. Native exact-title search is used
only to detect duplicates and an unwanted cancelled page, never to infer which
object the write created. Normal 30-second host invocation limits remain intact.

After the product Close action, new read and create requests must be denied by
that closed host. The same XCTest then exercises three further actual product
presentations, all in the original process and disposable account:

* H2 opens through the existing Hanlin button, obtains native read consent, and
  successfully reads the prepared document before `XCUIDevice.press(.home)`.
  `app.activate()` returns the same process to the foreground. The original H2
  host must then reject new reads and creates; activation cannot restore consent.
* H3 opens with no inherited read grant. Its actual read-consent alert remains
  pending while `XCUIDevice.shared.system.open` opens the Page created by H1.
  The ordinary SpaceHub object route dismisses existing presentations. XCTest
  requires the exact new editor to be hittable and the old prompt to disappear
  without pressing Allow. H3 must still deny reads and creates.
* H4 opens after XCTest returns to the original document. It must require new
  consent, then read the original native body after an actual Allow action.
  Its native index check must still find exactly the one originally created Page.

The driver observes scene/application notifications and first production
presentation-invalidation call sites; it never posts lifecycle notifications,
supplies an approval, or changes navigation. Scene inactivity can itself revoke
the host before a background event. Therefore the H3 receipt records all six
event deltas and distinguishes navigation with/without a scene transition. This
is evidence that old consent is rejected after navigation, not a claim that the
document fence was the sole cause. The recorded invalidation cause is the first
observed presentation call site, not an inferred hidden fence origin.

Three distinct fresh native authority objects then first validate,
then must reject after a real source lock, real Space change, and actual logout
of this disposable account. Each negative case has its own initially valid
authority, so the previous revocation cannot make the next case pass. These
three checks exercise the native authority boundary directly; they do not claim
three separate approved host writes. The original committed metadata must still
be readable from its original journal after ordinary logout.

Native execution is pending the focused Apple lane after Startup smoke. The
preceding four-suite SDK Apple run `44209702553` stopped at TEST BUILD FAILED:
canonical Hanlin `OpenUIBlock.swift` lines 55/115 pass completion closures to
`WKWebView.callAsyncJavaScript` that the selected Xcode 27 API does not accept.
No SDK test cases ran. This dependency compilation failure must be resolved
before the new native lane can execute. The minimal published correction is now
pinned at `116cc6be0654a5d11bc56ba00e0310031107ee36`; its Apple build is pending
(see `CANONICAL_PIN_UPDATE.md`). Source parse evidence is separate and
is not native acceptance. The later run `44217294617` was cancelled before any
completed SDK case evidence; the corrected source-bound SDK run is
`44227955159`. Neither run is evidence that this UI lifecycle extension passed.
Selection entry still requires its own native acceptance evidence.

## Build and preparation contract

Use a **fresh disposable iOS 27 simulator per device/lane**, the reviewed exact
integration commit, the pinned Hanlin bootstrap before SPM, and rebuilt Heart
artifact `Pinkha-Universal-Verified-Heart-r14` from run `44203168617`.
Use `Debug-Anytype` for the app, app-hosted tests, and UI test project with
`PINKHA_NATIVE_DERIVED` and `DEBUG` in active Swift compilation conditions. The
diagnostic is intentionally absent from `Release-Anytype`. Do not mix binaries
or fixtures from the existing Release UI lane.

First run exactly:

```
AnytypeTests/HanlinNativeAcceptancePreparationTests/prepareRealHostFixture()
```

For Swift Testing selection, selecting the suite
`-only-testing:AnytypeTests/HanlinNativeAcceptancePreparationTests` is sufficient;
the result must contain **exactly one passed preparation case** and no failures
or skips. This method invokes the existing native
`SimulatorAcceptancePreparationTests.prepareRealUIFixture()` as an ordinary
function; do not separately schedule that suite, or preparation will execute
twice against the same fixture.

Inject these environment values into the actual app-hosted test target in the
generated `.xctestrun`, following the existing native preparation path:

```
PINKHA_HANLIN_NATIVE_PREPARATION=1
PINKHA_SIMULATOR_ACCEPTANCE_PREPARATION=1
PINKHA_SIMULATOR_UI_DISPOSABLE=1
PINKHA_HANLIN_NATIVE_SOURCE_SHA=<exact checked-out integration SHA>
PINKHA_HANLIN_NATIVE_RUN_ID=<actual GitHub run ID>
PINKHA_HANLIN_NATIVE_RUN_ATTEMPT=<actual GitHub run attempt>
```

Preparation rejects an existing account or fixture, turns off middleware
request logging through the existing feature setting and actual message handler,
and calls the existing local-only account/Space preparation. It adds the known
body block through the real native service, verifies its readback, creates a
separate disposable alternate Space, restores the original Space, and writes:

```
<actual app data container>/Library/Application Support/pinkha-hanlin-native-fixture.json
```

Obtain the **actual** app data container with the existing `simctl get_app_container`
route for `io.anytype.app`. Read this JSON from that exact container and verify
its SHA/run/attempt against the runner's independent values. The file contains
only disposable object metadata and test text, no wallet/credential material.
It expires after one hour and cannot overwrite an earlier fixture or result.

## UI selection and environment

Run exactly this one method in the separate existing UI test project:

```
PinkhaStage1AcceptanceUITests/HanlinNativeAcceptanceUITests/testRealNativeConsentCreatePageAndAuthorityRevocation
```

Inject into the UI test runner's `.xctestrun` environment:

```
PINKHA_HANLIN_NATIVE_UI_TESTING=1
PINKHA_SIMULATOR_UI_DISPOSABLE=1
PINKHA_HANLIN_NATIVE_FIXTURE_JSON=<unmodified actual fixture JSON>
PINKHA_HANLIN_NATIVE_SOURCE_SHA=<exact checked-out integration SHA>
PINKHA_HANLIN_NATIVE_RUN_ID=<actual GitHub run ID>
PINKHA_HANLIN_NATIVE_RUN_ATTEMPT=<actual GitHub run attempt>
```

The test cold-launches `io.anytype.app` with the exact fixture nonce and CI
identity, `PINKHA_HANLIN_NATIVE_UI=1`, and `PINKHA_UI27_ROUTE_OBSERVATION=1`.
It requests English app labels and portrait orientation. Actual device language
must be observed separately if reported; this is not Hebrew UI acceptance.
It waits for the actual SpaceHub/NewSpaceButton Home control after cold launch,
then uses XCUIDevice.shared.system.open for the fixture's exact native object
route, requires its actual mounted
editor diagnostic, and taps the production Home-panel Hanlin entry while that
editor remains mounted. It presses the existing Share context, Allow, Cancel,
Create page, and Close actions, then Home/activate and the existing object route.
Every create prompt must show its exact title
and original Space. Provider configuration and model invocation never occur.
This lane does not claim reuse of an earlier Inspector process.

The new file `PinkhaStage1Acceptance/Tests/HanlinNativeAcceptanceUITests.swift`
is registered in that project's existing Sources phase. It does not change the
older Stage1 acceptance class or the root-owned Python/workflow dispatcher.

## Result guard

Require exactly one actual passed XCTest method, zero failures/skips, and a
nonempty matching `.xcresult`. Preserve actual simulator UDID, model, OS and
architecture, source SHA, resolved package identities, executable identity,
preparation result and UI result. Do not count the diagnostic label alone as
success.

The app atomically writes metadata after each phase to:

```
<actual app data container>/Library/Application Support/pinkha-hanlin-native-result.json
```

Require `phase == NATIVE_ACCEPTANCE_PASS`, no `failure`, nonempty
`createdObjectID`, `finishedAt`, `providerConfigured == false`, positive process
ID, and the exact independent fixture ID, SHA, run ID and attempt. Require this
**exact set of 21 keys**, each true, with no missing/extra keys:

```
middleware_logging_disabled
read_denied_before_native_consent
real_native_context_text_read
native_cancel_prevents_write
native_confirm_creates_exact_page
created_page_read_back_by_journal_id
replay_does_not_create_duplicate
cancelled_title_absent_from_native_index
no_provider_configuration
closed_presentation_denies_read_and_create
native_source_permission_change_denied
native_active_space_change_denied
native_account_logout_denied
original_commit_metadata_survives_logout
background_presentation_had_live_read_access
native_background_foreground_observed
backgrounded_presentation_denies_read_and_create
pending_read_consent_dismissed_on_document_exit
departed_document_presentation_denies_read_and_create
fresh_presentation_requires_new_native_consent
fresh_presentation_reads_original_document_only
```

Require four distinct UUIDs: the original `sessionID` and the new
`backgroundSessionID`, `staleConsentSessionID`, and `freshSessionID`. The original
session field remains H1; the process must stay unchanged across Home/activate
and the document routes. `invalidationCauses` must have exactly these four UUID
keys. Its values are existing observed call sites: `nativeAuthorityChanged`,
`presentationRemoved`, `interactivePresentationDismissal`, or
`explicitCloseOrOwner`.

`sceneEventCounts`, `backgroundCycleSceneDelta`, and `documentExitSceneDelta`
must each have exactly these six keys with nonnegative integer values:
`sceneWillDeactivate`, `sceneDidEnterBackground`, `sceneWillEnterForeground`,
`sceneDidActivate`, `applicationWillResignActive`, `applicationDidBecomeActive`.
Every delta must be bounded by its total count. The background cycle requires
positive `sceneDidEnterBackground`, `sceneWillEnterForeground`, and
`sceneDidActivate` deltas. `documentExitAttribution` must equal
`navigationWithSceneTransition` if any document-exit delta is positive, and
`navigationWithoutSceneTransition` otherwise. Do not relabel the former as an
isolated document-fence test or discard the early inactivity counters.

The XCTest independently checks these invariants and the exact check set,
preserves the process across the close/revocation sequence, and attaches metadata JSON
and screenshots of the actual prompts and final state. An uncertainty, invalid
context, native write mismatch, absent prompt, deadline expiry, unavailable
index or missing evidence fails this lane. Acceptance remains open until the
actual Apple results satisfy these conditions on the requested devices.
