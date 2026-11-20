# Original editor framework v3: build succeeded, exporter failed

Actual run [44797902550](https://github.com/davidpovarsky/anytype-swift/actions/runs/44797902550), attempt 1, finished **FAILURE** at exact source `a75443e4244762051cb0a99367188dc35645bfbf`. This packet preserves the complete original artifact and nested build xcresult; it does not transfer any later candidate result.

## Actual results

| Boundary | Actual outcome |
| --- | --- |
| Original framework build, Debug-Anytype, simulator arm64 | Exit 0, BUILD SUCCEEDED, 19:00:21–19:19:10 UTC, original 6000-second bound |
| Source controls on the actual Mac runner | 54/54 passed: original 44 plus 10 v3 flow controls |
| Original source/package/SDK inputs | 23 canonical input files; 2237 original Swift paths; 44 pinned package revisions; original 407-file Hanlin snapshot |
| Exporter | Failed with `Missing or ambiguous genuine framework products` |
| Symbol graph / external consumer / simulator boot and runtime | NOT_RUN |
| Editable editor mount / original app runtime / Native UI | NOT_EXPOSED / NOT_RUN / 0 |

The actual build used Swift 6.4 (`swiftlang-6.4.0.34.1`), Xcode 27.0 and iOS Simulator SDK 27.0. All original source/resource trees, compiler settings, verified Heart producer, SDK snapshot and source-before/source-after records were preserved. The full logs retain **1298 warning lines** and **five Internal Error / corrupted-JSON diagnostics**. They did not turn the actual framework command into a failure: its recorded exit is zero. This is not a claim that those diagnostics are harmless in other runs.

## Concrete exporter cause and limit

The unchanged exporter rejects any duplicate framework basename. The actual build log contains two `ProcessXCFramework` operations from the same verified `Dependencies/Middleware/Lib.xcframework`, to `Lib.framework` and `PackageFrameworks/Lib.framework`. These are the only duplicate framework destinations identified from that log. This establishes the strict exporter's source/setup conflict. **It does not establish byte equivalence of those two built products:** the failure artifact does not contain them. A new route must compare both complete closures, including relative paths, kinds, bytes, modes and literal symlink targets, before admitting only this exact pair.

The driver also reported a complete 2238-file original compiler closure (2237 original Swift paths minus the sole AppScene entrypoint, plus original AssetConstants and the inspection facade) and one generated Swift file. However, the original generic packager omitted the raw `.SwiftFileList` and three generated `.swift` bundle accessor copies. The current artifact contains their original digests and validation report, not those four raw proof files. Independent raw file-list replay is therefore unavailable for this historical run. The proposed retention repair uses `.txt` copies without changing compiled inputs or the original packager.

## Evidence and replay

`artifact-14661426349.zip` is the unmodified 1,620,390-byte GitHub artifact, SHA256 `508d94841af15124cb87580ac87829973e7d8aceae75e3ffb1948db74e761cdf`. It contains the complete nested 34-member evidence ZIP, including all seven xcresult members (six Data entries plus Info.plist). Every ZIP CRC was checked. Both owned simulators remained shut down; shutdown returned 149 and both exact owned delete operations returned zero.

`canonical-api-and-log.zip` preserves complete canonical run/jobs/artifact/commit metadata and the full workflow log, the canonical Git tree subset, exact source binding and original ZIP inventories. The failed direct-job metadata request is retained separately inside that ZIP as a collection error, not a test failure. `canonical-source-inputs.zip` contains all 23 original input bytes plus the original 44-pin Package.resolved. Signed storage download URLs and credentials are excluded.

Run `python3 VERIFY_PACKET.py .` from this directory. It only reads the sealed artifacts and canonical source bytes. It does not rebuild, rerun a test or contact Apple/GitHub. A successful verifier result confirms an authentic failed workflow with a successful original framework build; it does not qualify a consumer, runtime resource loader, editor UI, account, codec, annotation integration or live exchange.
