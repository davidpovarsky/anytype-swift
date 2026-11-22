# SDK06 original result: build passed, selection stopped before tests

Run [45047827580](https://github.com/davidpovarsky/anytype-swift/actions/runs/45047827580), attempt1, executed source `58b9de8f7a26d798e18e301ad1ed8be14f2a8c14` on the shared branch. Its actual job137286199026 completed **FAILURE**. The original Debug app/test build produced `TEST BUILD SUCCEEDED`; the shared-editor component phase then stopped at its enumeration precheck. No current consumer product test executed.

## Original evidence

Artifact14765919670 contains56 original files. Its outer ZIP is2,433,954bytes, SHA256 `7ebc72520f55608edf3855f5cea5e861334fec3d4c64fe00446c9220c201e618`. The inner evidence ZIP SHA256 is `677469e491b5cc8cfc09737c1bedd65cdb8f5976cf9526a7133ff8999c0156f6`. `retained/ARCHIVE_RETENTION.json` records every exact file digest and size. The read-only `audit_original.py` rechecks all56 files, both archive digests, GitHub artifact/job metadata, source declarations, original enumeration commands/results, cleanup and build inventory. It runs no product tests.

The actual suite discovery returned all30 source-declared methods in the three reviewed suites. The requested selection contained23 methods and32 declared argument cases. The next enumeration enabled the15 zero-argument methods and disabled all8 requested parameterized methods. It enabled no extra method. The eight exact missing signatures are in `ORIGINAL_RESULT_AUDIT.json`.

Both `shared-editor-components/command-00.json` and `command-01.json` contain `-enumerate-tests`; their exit0 and `TEST EXECUTE SUCCEEDED` log text describe enumeration, not test execution. The component receipt retains `FAIL / ENUMERATION_PRECHECK` and the original refusal. The parent receipt retains `FAIL / SHARED_EDITOR_COMPONENTS`.

| Current consumer scope | Result |
|---|---|
| Editor/table/authority23 methods,32 cases | NOT_RUN |
| Acknowledgements7 methods | NOT_RUN |
| Native preparation1 method | NOT_RUN |
| Mounted SDK06 UI1 method | NOT_RUN |
| Full acceptance / release acceptance | False |

The `heart/` replayed xcresult belongs to the already qualified coherent producer. Its fixture/Swift-codec success is upstream evidence and contributes zero current consumer methods.

## Reuse and cleanup boundaries

The original app/test build is successful evidence. The archived product manifest explicitly states that it is an observed inventory rather than verified build provenance; all reuse flags are false. The archive contains no app/test executable or original `.xctestrun` bytes. Its executable hashes therefore do not, by themselves, qualify exact binary reuse. GitHub's compatible compilation-cache save step completed successfully and can assist the next source-bound build.

The owned worker group was quiescent, both disposable simulators were deleted, packaging and artifact upload passed, and the original failure remains unchanged. No cleanup failure obscures the selection diagnosis.

## Bounded repair

The original result directly demonstrates that the parameterized full signatures were not accepted as selectors. The proposed repair sends a method-level selector for only those eight methods, preserves the15 successful nonparameterized selector strings, and keeps full signatures for source, enumeration and terminal comparison. Apple documents the method selector shape as `test_target/test_type/test_function` in [Running tests and interpreting results](https://developer.apple.com/documentation/xcode/running-tests-and-interpreting-results.md).

The corrected grammar still needs actual Apple enumeration to return exactly the23 requested signatures before any test can execute. Exact parameter arguments,23 method terminals,32 case terminals, actual simulator identity and zero failed/skipped results remain required afterward. Local synthetic controls cannot establish this Apple outcome.
