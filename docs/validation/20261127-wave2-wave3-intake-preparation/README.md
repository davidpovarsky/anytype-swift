# Wave3 shared producer compatibility — closed preparation

This review binds the Wave3 producer contract at `d77bc5d2cea7503c7afa012978349951f72fa295` to the existing Wave2 common intake. It does not admit a build. The actual selected App commit, source tree, canonical Hanlin revision/materialization receipt, successful App/UI receipt, and their evidence pins are still required. `wave3_intake_freeze.template.json` deliberately has `readyForRuntimeAdmission: false` and null actual-product pins.

The historical common module remains SHA256 `4ec8617c59da3183a68a53ea9f840e57738469f36f9a0bc5b5a00e806d73cd9c`, and its a089 source check remains closed. No historical admission, failed attempt, retained App15 product, source receipt, or controller is rewritten. The next common module must be materialized separately for exactly one reviewed, frozen Wave3 source; supplying a different source or dependency hash in an admission must not select a different product.

## Unchanged consumer interface

```python
source_proof, built, app = shared.admit_and_clone_products(
    admission, private_execution_root, evidence_directory, commands
)
```

`built` retains the `app` and `ui` entries, each with `products`, `inventory`, `copies`, `descriptor`, and `originalSelection`. Both complete product trees are admitted and cloned. The returned app remains the original unified `Anytype.app`; there is no new App build, Native build, source overlay, or historical-UI continuation in a consumer.

The NativeUI adapter also uses `qualify_app16_producer`, `qualify_app16_runtime`, `source_admission`, `product_integrity`, and the fixed active `APP16_SOURCE`, `MANIFEST`, `NATIVE_BINARY`, `SDK_RECEIPT`, and `LOCK` exports. A separately frozen Wave3 module can retain these compatibility names, but their current values must come from the reviewed actual freeze, not from arbitrary admission or environment values. The original a089 module and its exports remain unchanged in its own retained package. The Page154 materializer must also bind its explicit current-source guard to that reviewed module and the real canonical admission.

The original `Commands` lifecycle, descriptor binding, enumeration, XCTest result validators, source helper closure, complete product clone checks, and owned-simulator retention remain intact. Lane-specific sources and selections continue to be qualified separately. A shared producer receipt does not replace any lane's fixture preparation, exact test enumeration, execution, native evidence, or visual review.

## Concrete compatibility changes

| Boundary | Existing a089 intake | Required Wave3 admission |
| --- | --- | --- |
| Source | `a089ff29…`, tree `bf6aa5ec…` | One actual frozen source/tree; full clean before/after inventories equal; current Git bytes and ancestry still checked. |
| Builder identity | Producer `9b1405ea…`, delta `5e18f0a7…` | Exact expanded producer hash in the actual receipt, exact Wave3 adapter `47c66dde…`, frozen build-admission bytes, and its explicit reversible delta. The adapter hash is not the expanded producer hash. |
| Builder inverse | Positional inverse directly to original `617b1639…` | Two legs: Wave3 sequential occurrence inverse to `9b1405ea…`, then the original 90 positional spans to `617b1639…`. Every original byte must restore. |
| Original functions | Four verification bodies byte-identical | `run_phase` and `source_state` remain byte-identical across both legs. Runtime/dependency bodies retain their original logic via the exact inverse and reviewed input substitutions; raw equality is not claimed after those substitutions. |
| Stage protocol | a089 stage receipt `ed896be8…`, previous source379 | `pinkha-root-forward-staging-v1`; previous sourcea089; exact `planSHA256`, staged source/tree, stage script, transferred Git bundle, fast-forward-only transition, no active competing compiler, and original-preservation revalidation. `planSHA256` replaces the old stage input binding. |
| Original preservation | Receipt `11ab2f45…` | Same preserved App15 source/products receipt plus the actual `originalPreservationReverifiedSHA256`. Verify retained source, product bytes, directories, modes, and links. Keep original App15 evidence distinct from the a089 staging attempt. |
| SDK | Historical receipt `b5b2ce16…` | Actual canonical SDK revision must agree among the frozen source `Tools/Hanlin/source.json`, stage receipt, materialization receipt and original `prepare_sdk.py --check` boundaries. The retained previous SDK is separate evidence, not the active SDK. |
| Cache state | Qualification `26b16e0b…` corrects the historical warm-cache overstatement | Exact new qualification bound to the new source/stage. Intermediates and package checkouts were observed absent; Products/SDK modules present. Retain the existing 6 GiB App estimate, 1 GiB UI estimate, 2 GiB floor, and 512 MiB concurrent allowance. Do not demand pre-build absence after a completed build has populated the caches. |
| Source receipt binding | Full decoded before/after equality | Keep complete equality and additionally match the actual producer's `sourceBeforeSHA256` and `sourceAfterSHA256` fields. The entire inventories, not selected tests alone, remain authoritative. |
| Native compilation | Exact original focus/gesture rows and retained FileList | Keep that proof and additionally validate `nativeCompilationProof`, including its `originalCompilerQualificationSHA256`. Every selected native source must equal its frozen source bytes and occur exactly once in a retained target-specific FileList actually used by `swiftc -module-name AnytypeTests`. |
| UI compilation | Same-source UI copy, generator and reviewed Page154 source | Exact `originalUICopySHA256` plus `uiCompilationProof`; all copied UI Swift files, not just the requested subset, must be compiler inputs for `PinkhaStage1AcceptanceUITests`. Full copied-file set must equal the frozen tracked set. |
| Generated UI project | Original generator/copy checks | Add actual before/after project and scheme inventory equality, including file bytes, modes and directories; reject unexpected links. No regenerated substitute after compilation. |
| App/UI process outcomes | Both phase results and process-exit records | Retain both full successful `build-for-testing` outcomes, exact flags and original logs, exit0, no termination/cleanup errors, `ABSENT_ESRCH`, and owned lifecycle helper `73bb6a4f…`. A terminal marker alone is insufficient. |
| Native identity | Exact8ac manifest, consumer and two slices | Retain original manifest/source/version/date, simulator and device receipt/command evidence, full assembly/framework inventory and binary hashes/sizes, and equal runtime-identity boundaries before/after App/after UI. Do not claim Native RPC execution from these checks. |
| Product identity | Complete producer and explicit-mode consumer inventories, original descriptors and APFS clones | Keep all checks for both App and complete UI trees. The producer inventory and explicit-mode manifest must agree before cloning, after cloning, and after lane execution. No partial-product admission. |
| Final status | `PASS_COMBINED_MAIN_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE` | Same producer status, with an exact `controlAdmission` binding and all added proof pins. This status remains a build result, not functional, RTL, physical-device or release acceptance. |

## Compiler evidence checks

The new compiler proof cannot be replaced with a source declaration, a generated FileList alone, `WriteAuxiliaryFile`, a stale command, a package-test declaration, or a successful build marker. Re-read the original build log and each retained list. Check the exact target module, original list path, one-based log-line number, line SHA256 excluding the line ending, and every recorded invocation. Accept APFS case normalization only when the selected path names the same physical regular source file with the exact frozen bytes. Require each selected path exactly once.

The root's final `selectedNativeTestSources` must include the new marker and empty-paragraph hosted suites in addition to the original focus/gesture and other selected sources. Their exact test files are `AnyTypeTests/Pinkha/PinkhaTextBlockLeadingMarkerTests.swift` and `AnyTypeTests/Pinkha/AnyNativeEmptyParagraphDirectionTests.swift`. The existing hosted RTL profile SHA256 `40429e43abf2ea22874b6a9d3c796a64888581be18ae7868f3066880817b5d5b` consumes the admitted native proof and preserves its six-method/ten-case contract. The original focus22/34 gate is separate. A package source such as `AnyNativeTextRendererTests` cannot receive AnytypeTests compilation credit unless a reviewed direct-source target bridge and the actual matching FileList prove that path.

Properties, Related, Inspector, editor, Page154 and NativeUI consumers can retain their explicit source-bound checks. The common qualifier owns the complete producer proof; a lane's native proof pin must be exactly the one in that admitted receipt. Existing `rtl_hosted_profile.source_contract` is a fixed-suite verifier, not a general source-admission API. Reusing the original result validators or the producer's pure compiler-log witness semantics must not weaken each lane's source hashes or exact selection.

The additive read-only `native_compiler_witness.verify_native_compiler_sources(app, *, source_commit, native_compilation_proof, expected_sources, rtl_profile_path)` supplies a shared selected-source check for the Properties/Related profiles. It verifies the exact clean tracked source and the caller's literal source-hash map, then loads only three exact function declarations from pinned RTL profile40429e43: `sha`, `_pinned_bytes`, and `source_contract`. The compiler-witness body is unchanged; its declared selection is supplied by the already validated map. No runner, test method, selector, product admission or top-level profile body is executed. The returned record explicitly says product admission and application execution were not performed. Consumers must call it only after the shared admission and take `native_compilation_proof` directly from that producer receipt. Three portable controls cover exact selected input, wrong compiler module, and changed source/validator rejection; they are not Swift/XCTest tests.

## Actual evidence needed to freeze the next qualifier

1. The final selected App commit/tree and full source-before/after snapshots, plus the exact `readyForBuild` admission used by the producer.
2. Actual forward-stage script/plan/bundle, stage receipt, preserved-original revalidation, cache qualification, and canonical SDK materialization/check evidence.
3. Exact expanded producer, sequential delta, original9b producer and original5e delta, with all admitted input hashes and the original lifecycle helper retained.
4. The successful combined producer receipt, App/UI result and process-exit records, original logs, three runtime/dependency boundary receipts, Native assembly/receipt/command/framework records, and the canonical SDK receipt.
5. Original focused compiler qualification, new complete native/UI compilation proofs and retained lists, exact UI-copy receipt, generated project/scheme before/after inventories, and complete product inventories/descriptors with explicit modes and links.

Pin actual bytes first, then materialize the separate exact-source qualifier and canonical consumer admission. Run its portable negative controls against changed/missing evidence before any lane dispatch. Until then the old a089 qualifier must continue rejecting the future source. No accepted qualifier or arbitrary-source switch is provided in this preparation.

## Source-only verification performed

`inspect_wave3_contract_compatibility.py` reads eight exact pinned inputs. It proves that both upstream templates remain closed, the unapproved build template is rejected, the historical a089 module was not repinned, and a non-executed synthetic structural expansion reverses through both producer generations to every original617 byte. It also verifies the retained source/lifecycle functions and new compiler receipt hooks. The expanded candidate is never written or executed. The resulting `review-receipt.json` explicitly records no accepted source, no actual producer receipt, no runtime qualifier, no build, no Apple test and no simulator command.

The eight input bytes are recoverable from their stated Git revisions or the retained materialization. Wave3 files come from `d77bc5d2cea7503c7afa012978349951f72fa295` under `Tools/PinkhaDualEngineRuntime`; producer9b/delta5e from `204f8fbb25c3b21f419fc1a8818eb46ed492e561`; original617 from a089's `build_main_permission.py`; the common4ec module from Wave2 materializer `96cd2fe0fa29ed8bf5a74e5dcaa5eda2fde3d54c` and its exact retained control inputs. The inspection writes one fresh JSON evidence file and has no execution option.
