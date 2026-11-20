# Framework v3: preserve the simulator destination and compile before owned boot

The seven-file candidate is committed as `35dbb7bf54b18a8974d4c1bc820fe7d95ecb26e6` on the authoring branch `codex/otzaria-original-editor-framework-v3-preparation-20261120`. Its parent is the complete attempt2 evidence commit `1ca44c0bd885ab696afebd79e9e1f7b6e2bd491f`; the earlier frozen source `dc3ac07cec63692c8b84877a56e3e3fd60a4c667` and its branch remain unchanged. The separate reviewed route is prepared for `codex/otzaria-original-editor-framework-v3-reviewed-20261120`. This authoring task did not create or activate that reviewed ref.

## Actual evidence and the narrow correction

Both original Apple attempts stopped at the same 180-second `simctl bootstatus` bound before the framework compiler ran. The complete attempt2 artifact, all 28 nested members, cleanup and the exact attempt1 comparison are sealed in the parent packet `original-editor-framework-44781744925-attempt2-20261120`. That failure is retained; neither attempt established a framework compiler or consumer runtime result.

Source inspection additionally found a concrete variable collision: copying at least one dependency license reassigned `destination` to the license output path. The later external-consumer build then received that filesystem path as its `-destination` argument. The new whole-driver controls execute that notice-copy path and reproduce the wrong argument on the unchanged old driver. This is not described as an observed Apple compiler failure because the two Apple attempts stopped earlier.

The driver now uses `notice_destination` only for the four license-copy statements. The original simulator destination remains unchanged. The exact existing boot and bootstatus calls move together to immediately before installation, after the genuine framework build, source and dependency proofs, public symbol graph, independent consumer build, signature and exact embedded-framework inventory checks. Their 60/180-second bounds, selected device and arguments remain unchanged. This ordering allows compiler evidence to be retained if the later owned boot fails; the overall result remains failure and the distributable qualification is absent unless both actual language/resource executions finish successfully.

## Source preservation

| Path | Bounded change |
|---|---|
| `Tools/OriginalEditor/run_framework_acceptance.py` | Four license-target renames; move the two unchanged boot calls. |
| `Tools/OriginalEditor/framework_profile.py` | Exact new reviewed branch and installer inverse anchored to the prior framework branch. |
| `Tools/OriginalEditor/framework_profile.json` | New reviewed branch; canonical prior installer blob `89efc7695c5bbbc87b3e0fd10f65300dd1bfdd58`. All product/resource/package pins unchanged. |
| `Tools/PinkhaNativeDerived/install_verified_heart.py` | Append exactly the v3 reviewed branch; preserve every prior choice and the default. |
| `.github/workflows/pinkha-original-editor-framework.yml` | Only the three exact reviewed-branch literals. Original permissions, immutable dependencies, source admission, evidence handling, concurrency, 140/120-minute bounds and success-only distribution upload remain. |
| `Tools/OriginalEditor/test_framework.py` | The existing installer control's single branch literal follows the newly added v3 choice. Its assertions and all 44 original IDs remain. |
| `Tools/OriginalEditor/test_framework_flow.py` | Ten added whole-driver controls with explicit Apple/source boundary doubles. |

Every existing file has a complete exact inverse. All original `command(...)` expressions, including compiler arguments, SDK selection, runtime commands and budgets, have identical ASTs independent of ordering. No original Anytype source, module, resource, project, package version, Heart source, SDK source, public inspection facade, consumer Swift source or product setting is changed.

## Actual Python RED and GREEN

| Run | Original controls | New controls | Total | Errors |
|---|---:|---:|---:|---:|
| Authenticated dc3 driver with the added controls | 44 PASS | 1 PASS / 9 FAIL | 45 PASS / 9 FAIL | 0 |
| Candidate with the identical added controls | 44 PASS | 10 PASS | 54 PASS | 0 |

These runs occurred on Linux. All 24 input files per run were hashed before and after and remained identical. The complete stdout/stderr, first case-ID parse, normalized exact leaves, source projections and ten structured flow traces per run are retained. The first metadata parser appended a method suffix already present in Python's qualified name; that metadata was corrected from the unchanged raw log, with its first output retained. It was not a test or source failure.

The controls execute the complete original `execute` and `main` bodies, actual filesystem exports, original notice copying, consumer project generation, inventories, failure handling and cleanup. Apple commands, platform identity, original source/dependency admissions, Heart/Hanlin and original resource-oracle input are explicitly synthetic boundaries. No Swift compiler, simulator, framework binary or native UI executes in these controls. Even successful mocked build steps retain an overall failed synthetic flow that stops before installation; no `QUALIFICATION.json` is produced. The original command timeout and nonzero-process controls still execute their real bounded subprocesses.

The source review by B covered the complete changed driver sequence and found no concrete blocker. That review adds no execution credit.

## Replay and limits

Run `python3 VERIFY_PACKET.py` in this packet directory. It reads the sealed archive only, validates all member hashes and CRCs, authenticates the 23 original input blobs from the recorded canonical source, checks the seven candidate blobs, replays complete inverses and unchanged command expressions, and verifies actual 54-leaf RED/GREEN logs and all synthetic flow boundaries. It does not rerun Python tests, build software or use the network.

Apple execution of v3 remains **NOT_RUN**. In particular, a successful future framework compiler would still not prove an editable editor mount, Maktabah consumer integration, original application runtime, live writers, account isolation, device builds or physical-device behavior. The existing strict two-language external-resource runtime gate remains required for this framework prerequisite's final success.
