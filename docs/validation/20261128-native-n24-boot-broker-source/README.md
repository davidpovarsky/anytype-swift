# Native source composition: N24, boot/lifecycle 33, and broker 7

**The complete source maps and 64-event selection are checked. Compilation, native execution and all 64 selected events remain unrun.** This additive carrier combines the accepted source packets into one explicit prospective graph. It changes no native test controller or active application source.

## Exact graph

| Full input map | Files | SDK projection | SHA-256 |
| --- | ---: | ---: | --- |
| Production | 1,648 | 755 | 437ded56616ae2c342076aaad30e8bf56c0a6d5e2033a9146de1676985027c66 |
| Qualification | 1,657 | 757 | 0b581b558f1750e62aeb3eb5aa1370fcced7aff03d2613085406ca7a05db4d14 |
| SDK production projection | 755 | 755 | 95f841431592083020a4ec0d3283f475e4cdb0b45dbe8c3b3ad44b24be75f096 |
| SDK qualification projection | 757 | 757 | 0f9600abbc7bc4ebab349e4e49704471f0f6f5bafc5cf34c2350dee4006fa5de |

The [production](../../../Tools/AnyEngineValidation/native_n24_boot_broker_composition_20261128/maps/native-production-source.json) and [qualification](../../../Tools/AnyEngineValidation/native_n24_boot_broker_composition_20261128/maps/native-qualification-source.json) maps include every file and mode inherited from the original Runtime18 input graph. Here, “production” means that the new qualification-only test overlays are omitted; unchanged original test files and other original compiler inputs remain in the complete map. Their presence does not select them for replay. The [SDK production](../../../Tools/AnyEngineValidation/native_n24_boot_broker_composition_20261128/maps/sdk-production-source.json) and [SDK qualification](../../../Tools/AnyEngineValidation/native_n24_boot_broker_composition_20261128/maps/sdk-qualification-source.json) maps are exact projections with the SDK prefix removed.

The source order is:

1. Original Runtime18 base: 1,638 files, SHA 3552d6f65350c1eba2e9763c7f9a9daa64ada0335f64020ad585fff4a0e286e4.
2. N24 carrier 94fd763d459210b496557894628333d466abae73: 1,645 production and 1,649 qualification inputs.
3. Root's boot and lifecycle source, ending at 584d8eb7423e61823aa67c173312b742d540a27f: 1,648 production and 1,656 qualification inputs. The full original Root maps are retained unchanged under inputs/.
4. Broker carrier dae5c971f61eda51e497df21a974b1c7fad29184: replace only the broker production row with fe698597 and add test 35453146 only to qualification.

This uses the 3552 Runtime18 base and its exact N24 successors. The historical 8ac manifest named by an older boot source packet is not substituted for that base.

## Whole sources and complete inverse

The [ordered overlay manifest](../../../Tools/AnyEngineValidation/native_n24_boot_broker_composition_20261128/ordered-overlay-manifest.json) contains 31 operations over 30 unique paths. The repeated path is internal/embedded/embedded.go: the lifecycle source explicitly succeeds the boot-binding source. There are 21 final production paths and nine new qualification test paths.

The [source origins](../../../Tools/AnyEngineValidation/native_n24_boot_broker_composition_20261128/source-origin-manifest.json) name exact full bodies, Git blobs, native modes and paths for all 30 final sources. Twenty N24 sources and two broker sources remain at their unchanged inherited carrier paths. Eight final Root source bodies are copied byte-for-byte under root-overlay/; the original embedded source and intermediate boot version are also retained. All 31 ordered after-images and all 12 complete replacement before-images were matched to their full held/read-back bodies. Git artifact modes remain 100644; prospective native modes are separately recorded.

The [inverse manifest](../../../Tools/AnyEngineValidation/native_n24_boot_broker_composition_20261128/inverse-manifest.json) requires each exact after-image before reversing its operation. Both complete final maps recover the exact full Root maps, then the exact N24 maps, then the original 369,957-byte Runtime18 map. Every undeclared path and mode participates in these complete byte comparisons. The eight unchanged quota/upload/queue dependency rows are still exact.

The [pure derivation module](../../../Tools/AnyEngineValidation/native_n24_boot_broker_composition_20261128/derive-source-composition.mjs) and [argument bindings](../../../Tools/AnyEngineValidation/native_n24_boot_broker_composition_20261128/derivation-inputs.json) make this computation reviewable. The module has no filesystem, network, process, compiler or native entrypoint. Its input JSON and raw map text must first match the declared immutable identities. The [source composition proof](source-composition-proof.json) records the actual in-memory result, whole source bindings and all inverse checkpoints. A first in-memory draft rejected N24's original qualification-test kind; that source and diagnostic remain under preparation/, followed by the explicit two-kind normalization. No input source or map was changed to accommodate the parser.

## Exact unrun test union

| Source selection | Parents | Children | Total events |
| --- | ---: | ---: | ---: |
| N24 bound HTTP, LOCAL mutation and typed ACL errors | 9 | 15 | 24 |
| Root boot/lifecycle, including four affected original parents | 17 | 16 | 33 |
| Broker cancellation, including three affected original quota parents | 5 | 2 | 7 |
| **Disjoint union** | **31** | **33** | **64** |

The [full selection](../../../Tools/AnyEngineValidation/native_n24_boot_broker_composition_20261128/test-selection64.json) gives every parent, child, package, build tag and original group. Both global test names and package/event pairs are disjoint. TestStartAddressStop occurs once. Each child belongs to a declared selected parent. No old C13 or Runtime18 method is added, and no untouched network, migration or Files cohort is selected for replay.

These are source selections, not execution receipts. The broker source's two actual pinned stdin formatter successes remain in the parent carrier and do not count as tests. The Android gomobile and Linux iOS-core selections do not establish a generated Apple ABI, framework or Apple runtime result.

## Controller and runtime boundary

[CONTROLLER_BOUNDARY.json](CONTROLLER_BOUNDARY.json) identifies the unchanged N24 controller ownership and E's frozen boot33 module/plan/graft. The E package at source commit 5f86ea97cd4a9aee102163a5d7ff59b796e4c381 excludes broker7 and does not admit these newly composed maps. Neither it nor any N24 controller is rewritten here.

A separately reviewed N-owned controller successor must adopt this exact graph and selection, bind fresh source/toolchain/product identities and preserve owned process cleanup, deadlines and resource gates. Actual E97 then Swift23 completion and the explicit cache handoff remain separate prerequisites. This commit does not grant runtime or cache use. It contains no compiled native product and no generated ABI.

The [retained Files acceptance matrix](../20261128-native-quota-broker-source/FILES_ACCEPTANCE_MATRIX.md) continues to distinguish the completed original LAN/range/resume/offline and authority proofs from current quota, the two pending originals' cloud custody, and consumer/Apple integration. No earlier product proof is relabeled as an execution of this new graph. The retained-account quota observer remains unrun.

## Delivery

This is a normal additive child of broker commit dae5c971f61eda51e497df21a974b1c7fad29184 on the N-owned broker source branch. Existing source packets, active paths and test controllers remain unchanged. [FILES.json](FILES.json) identifies every new carrier file; the publication checks read every added blob whole and preserve every undeclared parent-tree entry. No Oracle project allocation, native startup, compilation or unit-test execution is part of this source publication.
