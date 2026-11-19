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

H1 now presses the production **Return to document** action after its read/create
checks. A queued request completes while the SDK session is current; the native
Close path then revokes that execution authority. The driver only observes the
separate native metadata receipt after the real UIKit dismissal and its native
mount validation. It never calls `acknowledgeMounted`, constructs a navigation
result, or supplies a presentation callback. XCTest requires the exact original
editor to be hittable, and new read/create requests must be denied by that closed
host. The same XCTest then exercises three further actual product
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

H1 read/create denial is checked again after H4's fresh consent and closure,
before source locks, Space changes or logout can explain that denial. H1's
original return metadata must remain unchanged across these later presentations.
This fixture deliberately has no selected blocks: the new return check proves
document return only. Actual selected-block return remains **NOT_RUN**.

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

Native UI22 execution remains **NOT_RUN**. Canonical Hanlin is pinned at
`116cc6be0654a5d11bc56ba00e0310031107ee36`; its earlier WebKit API correction is
documented in `CANONICAL_PIN_UPDATE.md`. Later SDK run `44238998798` failed during
Debug test-host compilation because a canonical limits initializer in the test
helper lacked `try`; `f048a33718506763b8097255a98ef742e445cfd3` corrects that exact
line. Its original build receipt and diagnostics are retained separately.
The next SDK run `44245129998` was cancelled while queued after an independent
Release run exposed shared quote-test compilation errors. Root repaired those
in `d325987d1fe721938d8991b2e086cb0de6adcfd3`. Cancelled runs are not functional
failure or test acceptance. The next UI22/SDK runs must use a source containing
those corrections and the native return implementation
`9f6c786263d6cc4a72b715a7212ccd8f964bf47a`. Source controls are separate from actual
Apple test execution. Selection entry still needs its own native UI evidence.

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
Create page, Return to document, and Close actions, then Home/activate and the existing object route.
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
**exact set of 22 keys**, each true, with no missing/extra keys:

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
native_return_mounted_original_document
```

`navigationContext` is captured from H1's actual host context before the Return
button is pressed. Its exact keys are `app`, `account`, `workspace`, `space`,
`sceneID`, `generation`, `objectReference`, `selectionReferences` and
`sourceRevision`. Require app `anytype`, the original fixture account and Space
(both workspace and space), original source object, valid scene/generation UUIDs,
an empty selection array, and the native 64-character lowercase revision hash.
Scene/generation are host context identities; they are not OS scene identifiers.

`nativeReturn` is absent before the user action and required in the final receipt.
Its required keys are `requestID`, `queuedRequestID`, `sessionID`, `context`,
`objectReference` and `presentationAcknowledged`; optional `blockReference` may be
absent or null in this whole-document fixture. The actual presented request ID
must equal the original queued destination ID, the session must equal H1, and the
observed returned context must exactly equal `navigationContext`. Require the
original source object, no block target, and acknowledgement exactly true.
Unknown or missing schema fields, a queued/unmounted response, mismatched
request/context/target, or absence of the existing closed-host denial check fail
validation. A valid receipt still does not replace actual passing XCTest and
source/executable identity checks.

The driver reads `handoff.destination` and `handoff.receipt` produced by the
native Return action, validates the real result against the real queued request,
and independently checks the original editor after dismissal. The diagnostic
does not mint or replay a mount acknowledgement. The Python validator reports
`scope=originalDocumentOnly` and `selected_block_ui_verified=false`.

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
The sum of the two disjoint deltas must be bounded by its total count. The background cycle requires
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

## 2026-11-19 follow-up: finish the original logout route

The original22-check run44437308455 at833dddee4d5c4e6cd0f89354e5a73096750d8e77 passed its native method and receipt checks. Its final screenshot still showed WorkspaceService.workspaceOpen panic recovered (unknownError), with later bootstrap/catalog activity after middleware logout. Those original observations remain preserved; they are not reclassified as a clean full-app logout.

Source review found that the diagnostic driver called the real authService.logout but omitted the next action performed by SettingsCoordinatorViewModel.onLogoutConfirmTap: applicationStateService.state = .initial. The original app's InitialCoordinator then selects the actual next root. The diagnostic now performs that same existing route transition after successful service logout and observes .auth without directly setting it. Its window-attached receipt adds logoutRootState; all22 original checks, authority denials, original journal identity and UI interactions remain mandatory.

The same original XCTest additionally requires both real PrimaryAuthView controls with their exact English source labels (I already have a key / I am new here) to be unique and touch-ready, and requires the former SpaceHub/NewSpaceButton and original editor to be absent. It does not activate either auth button. The existing final screenshot therefore records the actual logged-out root, while raw logs and previous screenshots remain available. The Python validator rejects absent or non-auth root state and still states that UIKit/XCTest evidence is required separately.

This diagnostic correction does not establish which asynchronous task caused the original banner. ActiveSpaceManager task cancellation and Pinkha bootstrap account lifetimes are separate unproven gaps; their production behavior is unchanged. App Group source8b79d35cf35dd7feef5d0a3021c9fef13e0cc8c2 is retained. Native results for this follow-up, physical device protection, provider networking, clean arbitrary account switching and release acceptance remain pending until separately verified.
