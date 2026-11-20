# Apple49: actual original components and document constructors

**Verified result: 49 unique Apple test methods passed, with zero failures or skips.** The actual original application was built and tested at immutable source `e140790e9ebf03b17ce3a241e0e3197301ea1365`. The result consists of the 43 original component methods plus six additive tests of the real `BaseDocument` and `DocumentViewModelSetter` constructors. The existing Mac control route also completed all 74 original baseline-profile controls and 23 candidate gate controls.

This packet records an actual completed run. It does not replace the original preparation packet or turn its earlier `NOT_RUN` statements into historical passes.

## Source and execution identity

| Item | Observed identity |
| --- | --- |
| Repository | `davidpovarsky/anytype-swift`, repository ID `1289863025` |
| Immutable source F | `e140790e9ebf03b17ce3a241e0e3197301ea1365` |
| Source tree | `78b918354dce380b0725e2a67fa81f1ae71c339c` |
| Parent | `b4ece8c2129124f6ec8ed00143e156b9d0e11383` |
| Branch | `codex/otzaria-original-document-constructor49-reviewed-20261120` |
| Workflow | `.github/workflows/pinkha-original-document-constructor.yml` |
| Actual run / attempt | [44791343024](https://github.com/davidpovarsky/anytype-swift/actions/runs/44791343024), attempt 1 |
| Actual job | `136479505253`, `original-constructors`, completed SUCCESS |
| Job start / completion | `2026-11-20T18:17:24Z` / `2026-11-20T19:18:44Z` |
| Workflow updated time | `2026-11-20T19:18:45Z`; distinct from job completion |
| Xcode | 27.0, build `27A266a` |
| Swift | Apple Swift 6.4, `swiftlang-6.4.0.34.1 clang-2100.3.34.1` |
| Actual test destination | ARM64 iPad Pro 13-inch (M5), iOS Simulator 27.0 build `24A434` |
| Configuration | Original `Debug-Anytype` application and embedded `AnytypeTests.xctest` |

The authenticated Git API source projection and 40 retained input files bind the actual constructor sources, all eight test files, original result validators, control drivers, workflow, dependency lock, project, and relevant build/preflight helpers. Every retained file matches its canonical Git blob and byte count at F. The five original application trees match the frozen constructor manifest. All 44 original dependency pins match the actual post-build lock; the actual Hanlin and two explicitly verified Swift dependency checkout revisions are retained separately.

## Actual results and their boundaries

| Executed scope | Passed | Failed | Skipped | Qualification |
| --- | ---: | ---: | ---: | --- |
| Seven original component suites | 43 | 0 | 0 | Complete original method inventory and original validator; controlled document/service boundaries remain explicit. |
| `PreparedDocumentConstructorTests` | 6 | 0 | 0 | Real original classes, supplied dependencies, original defaults and projection behavior. |
| Original baseline-profile Mac controls | 74 | 0 | 0 | Executed against exact b4 baseline with the reviewed temporary host-dispatch overlay and verified restoration. This does not claim that the old baseline profile accepts the changed product source. |
| Candidate49 gate Mac controls | 23 | 0 | 0 | Exact candidate source, inventory, authority and result-validation controls. |

The six actual XCTest methods are:

- `testDefaultDocumentResolvesTheSameFourFactoriesOnceInOrder`
- `testDefaultSetterResolvesOneOriginalUpdaterAndKeepsOriginalProjection`
- `testExplicitNilKeepsTheOriginalDefaultConstructorPath`
- `testPreparedDocumentDoesNotResolveAnyImplicitFactory`
- `testPreparedPreviewKeepsOriginalListenerAndClosedState`
- `testPreparedSetterUsesItsActualUpdaterWithoutResolvingTheDefault`

`VERIFIED_RESULT.json` retains all 49 exact method identities, their original/new scope, and all 97 exact control identities. The raw test log separately reports six passing XCTest methods and 43 passing Swift Testing methods in seven suites. The complete xcresult summary and test tree independently contain the same 49 unique passing leaves. The original `run_host_tests.validate_results` and constructor/original component validators were replayed on those unmodified raw results and returned the same structure as the actual CI receipt. This local replay did not compile or execute Swift, XCTest, or the Mac controls again.

The build command completed in **3307.020429 seconds**. The actual test command completed in **88.989081 seconds**; the xcresult test interval was 78.572 seconds. The original signed application and test executable hashes, xctestrun hash, installed Heart provenance, and cleanup of both owned simulators are retained in `PRODUCT_IDENTITIES.json` and the complete original receipt.

### Compiler and warning limits

The build succeeded and produced the actual tested executables, but its log is not warning-free. It contains **2346 `warning:` occurrences**, or **1752 distinct exact warning lines**. These include repeated compiler context and build-tool messages and are not a count of unique defects. The raw test log contains no `warning:` occurrences, and the xcresult runtime-warning array is empty.

The successful build log also contains **three actual `Internal Error: DecodingError.dataCorrupted` messages** at raw lines 46112, 47331 and 47639, interleaved with Swift build output. Their cause is unqualified. They are preserved explicitly; they are neither omitted nor reported as failed XCTest leaves. Twelve other textual `error:` occurrences are source-code parameter context, rather than compiler error diagnostics. No primary `error:` compile diagnostic was found by the recorded classifier.

A first local collection-verifier attempt stopped while classifying those three Internal Error lines. Its exact verifier and failure receipt are retained under `verification-attempts/attempt1`; its initial descriptive reason was imprecise and is corrected by the adjacent `DIAGNOSIS.json.gz`. The final verifier reports the messages separately without changing the actual Apple logs, source, test inventory, pass requirements, or command outcomes. This was an evidence-processing correction, not an Apple retry.

## Complete retained artifact

The sole actual GitHub artifact is `14659569956`, named `Otzaria-Original-Constructors-Apple-e140790e9ebf03b17ce3a241e0e3197301ea1365-44791343024-1`.

- Original outer ZIP: **797939 bytes**, SHA-256 **`d51f5d0717c28d621e5c2a7c849967592384bc895674ad2ca9763d74d2d884d3`**. It is retained verbatim under `raw/`.
- Inner `Pinkha-Native-Derived-Evidence.zip`: **845162 bytes**, SHA-256 **`17b2f80a8a23a1eddcc8ca871db46f7b7bb4624038d45b0a5e4745381e6d9624`**. It is retained inside the original outer ZIP, not rebuilt.
- All **157 inner members**, totaling **13144491 uncompressed bytes**, passed CRC and byte-for-byte extraction verification. The complete `OriginalConstructors.xcresult`, full build/test logs, command receipts, preflight, package/Heart/Hanlin metadata and control logs are included.
- The complete job log is retained losslessly as `raw/JOB.log.gz`; its original bytes total **265345**, SHA-256 **`34ecd107d844da46b6f2ac2665cce698a027a8bd3171e4443598f24c2c5adc56`**.
- Full canonical run/jobs/artifacts/commit API receipts and the explicitly marked source-tree projection are retained in `api/`. No signed download URL is needed to reproduce this verification.

## Reproduce the result verification

From a checkout containing this packet, run `python3 REPLAY_PACKET.py --output /absolute/path/to/a/new-owned-directory` in this directory. The output directory must not exist. The script first checks every sealed payload hash, reconstructs the original source/evidence, validates all ZIP CRCs, and calls the unchanged original result/control validators on the retained actual data. It does not invoke GitHub, Xcode, Swift, simulators or live services.

`PACKET_INDEX.json` binds the packet files except itself. The result author branch adds this evidence directory only; product, test and CI trees remain exactly those of F. Root owns integration and task-tracker updates.

## Acceptance that remains outside this run

**Native UI executions: 0.** This result does not prove an externally importable editor framework, a mounted original editor, genuine object open/import/export, Heart RPC execution, live account/Space writes, Maktabah annotation persistence or CloudKit synchronization, or physical-device behavior. The constructor tests use explicit service doubles while exercising the real original classes. No acceptance is transferred to the later framework, Repository/Cloud routes, Maktabah Native116, or Release114+2 scopes.
