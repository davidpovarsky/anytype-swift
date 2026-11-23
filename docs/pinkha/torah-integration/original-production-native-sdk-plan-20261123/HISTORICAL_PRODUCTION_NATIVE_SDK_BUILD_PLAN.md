# Production native library and original SDK build plan

Status: source preparation only. No new native framework, original editor distribution, application integration or runtime acceptance is asserted by this document. The retained original SDK continuation and its StageB consumer remain separate work.

## Exact source graph

The original Heart base is d98420b1113536afd08cde6de9a5816f6d27ffff. Both current native lanes first apply the same reviewed r14 patch, SHA256 fb96818eb57bd9e0be8da90a11831bcccc7ca8e72cc0a4e9a065500feb7cc077, whose inventory is SHA256 952073d8dccc991f21bffe5d3ded4e1d5369bb2c30f247ae5204d47cb03aee14.

PRODUCTION_NATIVE_COMPOSITION_INPUTS.json is an exact copy of ORDERED_NATIVE_COMPOSITION.json from source782d07668d2def4655bc519739f2d650cbfa2d1f. Its SHA256 is bb7e18751e1941f98644961c340f746a77d0eb1af038c533deeed08a036d82f1. It binds each installer, preimage, afterimage and actual generated artifact instead of treating a branch name as a dependency pin.

| Layer | Actual identity and state |
| --- | --- |
| Original request/mapping compatibility | Six afterimages installed by72e8154c9ad21280894d0c93f5828e33a19ed7d6 |
| Original owned import/file lifecycle | Fifteen afterimages installed by3d58f04f938f743b9c3b737cdfedcc10610cbffc, replacing the preceding processor afterimage |
| Original app/account/operation lifetime | Eight afterimages installed by455e1c55d765b25f8dd63bd472964057e5cbffc7 |
| Final mapping correction | mapping_observation.go SHA7634efc97506c1b1f4f67ecfdbd7fab919b5843986261a445e258ef39b8a3fa6; current native run45116895060 |
| Schema endpoint | Thirteen native and two proto afterimages from7496e47fa4d37b0117abeae6b35ca5f4c8eaf638; current native run45108043207 |
| Generated Go | Three genuine generator outputs from run45101449367/artifact14787700016; original ZIP SHAec13df1db9405ffa42b2ef76ec1bda7988ecee8dff1c3fcb1fd01c556a7cf80e. The fourth native generation delta is documentation, docs/proto.md. |

The final lifetime overlay has28 paths. The endpoint native/proto/generated overlay has18 paths. Their path intersection is empty; the combined execution and ABI have not been built or qualified. The lifetime lane compiles core/application, the endpoint lane compiles clientlibrary/service. Neither produces Lib.xcframework.

The generated Swift source calls Lib.ServiceAnnotationSchemaRegister(requestData). The actual generated Go source defines service.AnnotationSchemaRegister([]byte). A built and exported mobile bridge for this new call remains unqualified. Start/Observe/Cancel/Release do not exist in generated code yet. Their eventual native and protocol deltas must be added to this graph after the owned archive/graph/readback/permission contracts are implemented and reviewed.

## Reuse of the real producer

The existing producer is Tools/PinkhaNativeDerived/build_custom_heart.py, read from d1ca51352734bd21a4943e7e094ac3ae95519c1e, SHA2560ebbe2f6227418eac2c532b0058290158319ba9f786baaf445de444887e8c669. It builds the original pinned Go mobile tools, calls gomobile bind on the actual clientlibrary/service and core packages, runs original cmd/iosrepack, and verifies thin binary slices. The original tagged source, pinned Tantivy checksums, native test template, build tags and genuine Go toolchain must remain explicit inputs.

Use one fresh isolated Heart checkout to apply the exact ordered sources and produce a consolidated source diff/inventory against d984. Every composed afterimage and generated output must be authenticated. Record any materialized path not in the original tree, including generated or ignored inputs, and account for every compiled product input. No additional source may enter because it happens to be in a compiler search path.

The identity embedded into each native binary must commit to the complete composed source, not just the unchanged r14 patch. The existing builder derives its identity marker from the supplied patch hash; reuse that mechanism with the reviewed consolidated patch/inventory, retaining its r14 lineage separately. Do not preserve the old marker while replacing native product code. A source-level marker is only one part of the proof: retain full framework file hashes, architecture-specific binary hashes, actual SDK/toolchain commands, exported headers and real bridge symbols.

Review both simulator and device product coverage from the actual XCFramework Info.plist and lipo output. The existing command targets iOS and fetches the original iOS and Darwin native dependency slices. A helper looping over the files that happen to exist is not enough to prove the required slice set; expected and observed platform/architecture inventories must agree.

Do not invoke make install-middle-local against a user's existing checkout: that target removes its destination before copying. Install the accepted framework only into a new owned, empty integration build destination and retain actual source/run/artifact/signature metadata.

## Separate production admission

The retained de631 original editor distribution was built with Heart producer44203168617. Tools/Hanlin/prepare_original_editor_heart.py authenticates that exact old producer. Tools/OriginalEditor/run_framework_acceptance.py also requires installation.source_run_id44203168617, the old original-tree profile, the original facade list and exact public/SPI contract. These safeguards are correct for that historical product and must remain true records.

A later production build needs an explicit new admission/profile that records its complete reviewed diff from that original product, new native producer identity and actual final original Swift/Modules/project/facade trees. It cannot acquire qualification by replacing the old pinned hashes or by reusing a previous success label. Factor a minimal reviewed profile/receipt input boundary in the existing producer only when the final production source is concrete; preserve the original default path and controls by exact source correspondence.

Keep the original package pin closure, generated resource accessors, original localization/font/color oracles, source-input closure and signing/install-name/rpath checks. A reused original dependency stays tied to its actual bytes. The E1 four-file environment work is source d1ca513; E2 bootstrap and later closed Host/import composition remain separately reviewed pending changes. The new public facade needs its own exact public contract with private construction and real account/selection ownership; no identity string or fixture token becomes authority.

The final original framework and its consumer must use the same observed compiler, Xcode build and SDK, not merely the same runner label. Re-observe actual toolchain metadata before admitting a retained or newly built framework. Keep static distribution archives distinct from the original dynamic embed set, as proven by the original producer's actual Mach-O headers.

## Qualification order and reuse

1. Intake current endpoint5 and Heart mapping results. Retain actual prestart cancellation evidence only within its proven unchanged route. A source-only successful build does not supply the missing runtime result.
2. Complete the genuine exported annotation specimens, bounded archive admission, whole-graph disposition, native create collision, registered readback, mapping-aware body proof and actual live permission/cancellation boundaries. Generate the four import methods with the original generator only after the protocol is frozen.
3. Compose the exact native tree, build Lib with the genuine producer, verify the actual bridge/export/header/platform closure and source-bound artifact. Exercise the relevant composed native endpoint/lifetime seams; keep historical controls clearly source-bound instead of replaying unrelated suites.
4. Compose original Swift schema/bootstrap/closed Host sources with that accepted Lib, build the original framework, qualify resources/import/link and real account/Space selection under the final source. Retained de631 EN/HE runtime and its StageB saved-edit/reopen remain their own prerequisites and do not transfer to this changed product.
5. Integrate the qualified framework through the real Maktabah saved-revision/source owner. Freeze Source/Vendor/project/UItests and all dependency identities once. Native116, Release114, full-v32 Reader/Inspector/performance and final signed delivery must be tied to the corresponding exact artifacts.

Cancellation request, nil return, a complete mapping, a successful binary link, a real source substring and a private registry handle each have distinct evidence meanings. Completion requires the original operation's actual Done/Result, the qualified native readback and current closed Host save boundary. Actual persistent reopen, process restart and device acceptance remain separately reported observations.

No CI or release is activated by this plan. Current final inputs remain UNFINALIZED.
