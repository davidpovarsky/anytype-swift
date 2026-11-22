# Genuine framework install-name correction

## Observed defect and exact source change

The unchanged, authenticated signed consumer from `45054111060` contains an absolute framework identity, `/Library/Frameworks/AnytypeOriginalEditor.framework/AnytypeOriginalEditor`. The actual `OriginalEditorConsumer.debug.dylib` has the same absolute dependency. The app embeds that framework under its own `Frameworks` directory. The entry executable strongly loads the debug dylib. All three complete Mach-O load-command prefixes, original file sizes and hashes are retained in `fixtures/INSTALL_NAME_BINARY_EVIDENCE.json`; the original archives and signatures have not been edited. This is a concrete relocation defect, without a captured native crash report establishing it as the exclusive cause of the observed launch failure.

The project change adds `LD_DYLIB_INSTALL_NAME = @rpath/$(EXECUTABLE_PATH)` to the four configurations belonging only to the new `AnytypeOriginalEditor` framework target. Removing those four lines reproduces the old project exactly. No original app target, 2,254 original Swift files, 51 package pins, 12 facades or original product source/resource tree is changed.

The new byte reader checks actual thin arm64 Simulator files. It requires the framework's unique `LC_ID_DYLIB` to be `@rpath/AnytypeOriginalEditor.framework/AnytypeOriginalEditor`. It follows the executable's exact strong debug-dylib edge when present, checks that real file and its identity, and requires a reachable strong framework load with the same relocatable identity. Missing, malformed, foreign-architecture, wrong-platform, weak, duplicate, absolute and unused-decoy inputs cannot qualify. Existing signature and runtime gates remain separate. Raw `otool -l` results for the actual entry executable and debug dylib are retained before the consumer check.

## Runtime evidence and preservation

The runtime entry adds only the installed tool's advertised stdout/stderr redirects to each original launch. On launch or observation failure, a bounded helper takes one read-only snapshot of output and strictly attributable crash reports. Native bundle identity, process name, complete installed executable path and attempt timestamps must all match. No matching report remains inconclusive. Capture or diagnostic-recorder failure cannot replace the original launch/observation error. The original en/he nonce, resource oracle, validation and acceptance logic are preserved.

The producer retains its newly signed consumer before boot through the unchanged, previously reviewed archive function. A new narrow adapter authenticates the original successful signature command and its streams; it explicitly makes no extra process-group-drain assertion. Both the framework source and consumer control identity refer to this genuine producer. The separately uploaded app archive remains unqualified and preserves bytes and modes. It is never substituted for an SDK qualification.

Boot status retains its 180-second budget. Installation remains a single attempt and uses the already reviewed 300-second budget. The authentic earlier app had 642 files and 500,498,107 bytes; its successful install took 40.694 seconds in run `45054111060`, while the original producer's 60-second install timed out in `45041382512`. The budget change grants no success or retry authority. The two distribution artifact uploads now include manifested hidden files, preserving the two exact resource members previously omitted by transport.

## Historical and current test scopes

The 245 original source-control results and 38 actual public/SPI requirements remain bound to `edce5b975b173059522f90adb71271fb95adf963`, run `45041382512`. The workflow no longer invokes the full 245-control suite. The new admission verifies that exact retained raw result and original source inventory, then compares all current source inputs against the original inventory plus an explicit reviewed path/hash ledger. It rejects any unreviewed addition or mutation and preserves the original Swift/facade/product tree membership. It executes only eight original flow cases that reach the changed packaging/consumer boundaries. The two flow cases that stop before those changes are retained. Those eight current cases have not been executed locally.

All ten old flow test bodies remain byte-identical. Only their explicit native-binary/archive boundary doubles are added. Their historical passes do not qualify the new binary reader, new archive adapter or actual Apple products.

New local executions are recorded separately:

| New control group | Passed once | Scope |
|---|---:|---|
| Install-name/parser/project and initial fixture boundaries | 28 | Includes authentic failed-prefix rejection and synthetic positive/negative binaries. |
| Original-error wrapper integration | 4 | Executes the actual new driver AST with explicit command/validator doubles. |
| Signature/provenance archive adapter and final fixture inverse | 8 | Includes a real small archive of explicitly non-native fixture bytes. |
| Exact-app failure helper, owned by the StageB agent | 19 | Filesystem/command fixtures; no simulator or subprocess execution by the helper. |
| Failing diagnostic-error recorder | 1 | The later guarded-write path; the earlier four were not replayed. |
| Retained-source admission | 11 | Raw-result/source-ledger rejection boundaries and an actual isolated Git dirty-input check. |

These are 71 source-scoped local control outcomes, not Apple or native runtime acceptance. The executed earlier control scripts and relevant source slices are retained. `SOURCE_PRESERVATION.json` explains the exact later guard/fixture deltas and inverses; `SOURCE_MANIFEST.json` indexes operational files and hashes.

## Remaining actual gates

No Apple activation belongs to this source packet. Root must review the final neutral source/head and source-profile rebind before one producer push. That producer must pass the historical admission/current eight selected cases, genuine original framework compile, actual public/Clang collector, strict signatures and binary load checks, then the original separate en/he resource observations. Existing unqualified products and failures remain independently retained. The original producer's command/cleanup/acceptance functions are unchanged by this correction; no additional cleanup guarantee is inferred from this packet.
