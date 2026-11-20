# Original Anytype editor: actual Apple component acceptance

## Verified result

[Run 44722898086, attempt 1](https://github.com/davidpovarsky/anytype-swift/actions/runs/44722898086) completed successfully at **2026-11-20 11:56:23 UTC**. Its immutable checkout is **11bfb0db63d7d446be01d0b2b70ac9cadc471a7f**, on `codex/otzaria-original-editor-apple-reviewed-20261120`; application/test source is **67a23f718548ee80dbb084e57933115a07601ea3**. Root independently verified the retained evidence at **12:34:01 UTC**.

The original **Debug-Anytype** app and test target built, strict simulator-app codesign verification returned 0, and **16 distinct component methods passed, with 0 failures, 0 skips and 0 expected failures**. Exact source declarations, raw xcresult summary and all individual test leaves agree. There are no missing, extra or duplicate methods.

| Original suite | Actual passing methods |
| --- | ---: |
| PreparedEditorPageDocumentTests | 6 |
| TextServiceHandlerInjectionTests | 5 |
| EditorLocalEventPublisherTests | 5 |
| Total | 16 |

The execution used the actual **ARM64 iPad Pro 13-inch (M5) simulator**, **iOS 27.0 build 24A434**, **Xcode 27.0 build 27A266a** and **Apple Swift 6.4**. Build-for-testing ran 11:10:42–11:54:34 UTC; test-without-building ran 11:54:39–11:55:36 UTC. The exact command receipts are inside the retained artifact.

These are component methods in the original application target, using explicit controlled document/service fixtures. They do **not** establish an original block-editing UI journey, Maktabah embedding, durable annotation graph, live account/Space operations, an iPhone test, physical-device acceptance or Release acceptance. The owned iPhone simulator was created and cleaned up; tests executed only on iPad.

## Original inputs and host controls

Root checked all five application trees against the frozen application source, all three test-source hashes, and all **44 original package pins** against the actual resolved pins. The canonical original Hanlin source is **116cc6be0654a5d11bc56ba00e0310031107ee36**; its actual receipt inventories 407 files.

The original verified Heart artifact came from run **44203168617**, artifact **14383247626**, producer **b5dc53b799a70269b8082734106d8cd30a99fc44**. Its recorded GitHub ZIP hash is **7ac88836edc2ee9ff0c7d8cb8943b8e968f0c73b2b94752ba27cebc241c69996**. The Apple consumer verified archive CRC/hash, installed the original slices and verified the expected patch **fb96818eb57bd9e0be8da90a11831bcccc7ca8e72cc0a4e9a065500feb7cc077** against Heart **d98420b1113536afd08cde6de9a5816f6d27ffff**. The app and test-host embedded runtime copies have identical hashes and the expected marker. These are the actual Apple receipts; this evidence collection did not rebuild Heart or claim its separate native build tests ran.

All **74 Python host-gate controls passed on macOS**, including both process-control tests that were skipped in the earlier Windows run. Their authentic job-log lines and exact completed receipts are retained. No Windows skip is relabeled as a Windows pass.

## Complete retained evidence

GitHub artifact **14626073558** contains the nested original evidence archive:

| Bytes | Exact SHA-256 |
| ---: | --- |
| Outer GitHub ZIP: 740,218 | `59ff3051e4036168d5c7d77475a8225d75ef71543e8ca9797fee2aaf6bc77a82` |
| Nested evidence ZIP: 766,479 | `5cc72e5f02bb57c6e76a46c061cf582e2dfd90bbf615b95c06dd3dbe719faa8c` |

The outer ZIP is retained byte-for-byte. Its nested archive contains **all 86 files**, including the full original xcresult, 12 MB build log, test log, command receipts, source selection, raw summaries, package pins, Heart receipts and preflight evidence. Both archives passed complete CRC checking. The exact file inventory, original GitHub run/jobs/artifacts responses, complete job log, and both finite watcher lifecycles are retained separately.

The original `execution.json` has one stale explanatory sentence beginning “Eleven”. It is preserved unchanged. The gating source profile, selection, raw summary and all unique leaf results correctly require and report **16**. Only the wording for a future source revision should be corrected; the historical artifact must not be rewritten.

The first read-only job-log collection attempt rejected a literal step-title string that the API log did not contain; it executed no tests and preserved no claimed result. The second download retained the authentic 178,617-byte job log, SHA-256 **0c5eef357b5ffe26f55345d104d7f3810d606491bc6a9dc00407b6fd0a93004b**, and verified the source and all 74 controls.

## Recheck the evidence

`python docs/cross-app-original-editor-apple-result-44722898086-20261120/verify-evidence.py --git-ref HEAD`

The verifier checks retained bytes and recorded results. It does not run an Apple build, simulator or test. The old frozen ref remains unchanged. Later ownership, lifetime, table and host-update source changes need their own fresh Apple execution; this result cannot be transferred to them.
