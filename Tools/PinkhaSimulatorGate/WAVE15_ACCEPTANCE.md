# Wave-15 existing UI acceptance lanes

This controller runs the existing application and existing XCTest methods on a disposable OS27 simulator. It is used only after the focused Home/document smoke is working. It creates real local-only fixtures through the existing native test suites.

| Lane | Native preparation | Named UI methods | Language currently supported |
| --- | --- | --- | --- |
| inspector | SimulatorAcceptancePreparationTests | 5 comprehensive search/Inspector/property methods | en |
| properties | TorahNativeDerivedProductIntegrationTests | 3 native property, picker, source header and Set methods | en |
| properties-set | A separate fresh TorahNativeDerivedProductIntegrationTests fixture | 2 historical Set-resume methods on still-blank universal objects | en |
| editor | PinkhaStage1AcceptancePreparationTests | 3 direction, five-block Enter and native document-source entry methods | en / he |
| canonical-properties | PinkhaStage1AcceptancePreparationTests with native properties preparation | 1 native link/unlink/relaunch method across all 3 writing types | en |

The canonical-property method now uses the actual native rows and fixed-scope picker, verifies completed mutations and persistence across cold reopen, and rejects the retired projection row. Native Stage1 preparation attaches Sources to its disposable ordinary Note/Page fixtures through the real Add Property path and verifies persisted installation. These ports were integrated at a8665d6220c016d85652a8bcf2f7bf309ee7af83; selecting them does not establish UI acceptance.

The properties and properties-set jobs must use separate fresh native preparation because the universal object method mutates the blank documents that the Set-resume methods require to remain blank. Native value selection now cold-opens the same mounted object after completed mutation on both phone and pad, removing the old iPad-only outside-popover tap. Interactive sheet dismissal is not covered by that persistence check.

Select iphone or ipad explicitly. A successful lane is LANE_PASS_ACCEPTANCE_REVIEW_PENDING, not full-matrix or release acceptance. English-label tests cannot be requested as Hebrew coverage. The editor's requested device-language diagnostic is not treated as proof of actual device-language mismatch. The real observation is retained separately.

The runner verifies the actual source/run, Kit lock and checkout, installed Heart, real preparation result, named UI results, actual OS27 destination and executable bytes before/after UI. Inspector methods also preserve the mapped process across their boundary attachments. Other lanes deliberately exercise relaunch; the runner does not misrepresent the initial process mapping as every relaunch.

Full acceptance still requires visual review and outstanding IME, Undo/Redo, quote/drop, landscape/dark/type-size/compact, failure/retry and other criteria in required-coverage.json. Adding this controller does not establish those results.

Inputs in the manual dispatcher:

- route=wave15-acceptance
- source_run_id=<successful verified r14 Heart build>
- acceptance_lane=<one lane above>
- acceptance_device=iphone or ipad
- acceptance_language=en or he (editor only for he)

Keep each job's raw xcresult, screenshots, selection plan, native fixture, actual package pins and runtime installation receipt. Failed preparation must stop UI execution. Unselected methods and configurations stay NOT_RUN.

## Hanlin native host lane

The hanlin-native lane uses Debug-Anytype for both the application and the
real UI runner, with DEBUG and PINKHA_NATIVE_DERIVED. Other lanes retain
Release-Anytype. Cache identity includes the actual build configuration and
canonical Hanlin source pin.

It executes only HanlinNativeAcceptancePreparationTests/prepareRealHostFixture
(one real native fixture), then
HanlinNativeAcceptanceUITests/testRealNativeConsentCreatePageAndAuthorityRevocation
(one real XCTest UI method). The existing simulator fixture is called normally
inside the preparation function, not scheduled as a second Swift Testing test.
The fixture requires a fresh disposable local-only account; source SHA, actual
CI run and attempt, nonce, body/title markers, distinct Spaces and creation time
are checked before any UI action. Its exact native JSON is passed unchanged.

A passing XCTest and its xcresult are required. Independently,
hanlin_acceptance_evidence.py validates the native result's 14 exact Boolean
checks, source/run/attempt/fixture identity, a distinct native created ID,
session/PID, no provider, no failure and consistent real dates. Raw native
results are retained on failure too. A status label or a complete native JSON
without the named passing XCTest is not accepted.

The component result does not claim provider/model operation, real selection
UI, background lifecycle or full SDK acceptance. The native driver and fixture
are excluded from production Release builds. The documented cold launch within
this lane does not reuse the earlier Inspector process mapping.
