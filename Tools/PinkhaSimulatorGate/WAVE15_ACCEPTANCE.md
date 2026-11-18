# Wave-15 existing UI acceptance lanes

This controller runs the existing application and existing XCTest methods on a disposable OS27 simulator. It is used only after the focused Home/document smoke is working. It creates real local-only fixtures through the existing native test suites.

| Lane | Native preparation | Named UI methods | Language currently supported |
| --- | --- | --- | --- |
| inspector | SimulatorAcceptancePreparationTests | 5 comprehensive search/Inspector/property methods | en |
| properties | TorahNativeDerivedProductIntegrationTests | 5 native property, picker, source header and Set methods | en |
| editor | PinkhaStage1AcceptancePreparationTests | 2 direction and five-block Enter methods | en / he |

The former canonical-property test expects removed legacy rows, and the former document-sources entry method expects a source header on blank Note/Page fixtures. Both need ports to the current native property and source-attachment behavior; they are excluded from this initial selection and their acceptance remains open.

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
