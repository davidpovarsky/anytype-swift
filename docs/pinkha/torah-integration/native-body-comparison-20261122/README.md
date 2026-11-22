# Historical original-native body comparison

This isolated downstream candidate compares an intended ATOSNAP v1 body with the complete protobuf ZIP returned by an actual original `ObjectListExport` call. The call and synchronous comparison remain inside the same prepared original document Owner as the identity read. It does not grant atomic native state, a durable application receipt, a mapping write, or ACK authority. The active StageB/Auth v12 SDK and Maktabah candidates are unchanged.

## Actual source boundary

`OriginalAnnotationObjectReadback` retains the original prepared session, concrete AccountManager, BasicUserInfo account and captured account/source/document lifetime. Its new method performs original `ObjectShow`, `ObjectListExport`, and a second `ObjectShow` under one `withExclusiveRead` interval. It uses the original unfiltered protobuf export flags, including nested objects and file bytes. It records the actual export report in the newly owned directory immediately after export, so a later owner check or ObjectShow failure does not discard that evidence.

The original exporter visits collected objects through separate tasks and per-object `cache.Do` calls. This app Owner drains registered application writes; it does not suspend inbound native changes or make a multi-object export one native transaction. The nonconstructible internal result is therefore named `OriginalAnnotationHistoricalBodyComparison`. It retains the actual archive/report bytes, root/account/Space identity, object/file inventories, supported body format version and intended body digest. A digest is an audit field after comparison, not the comparison or authority. Final owner loss after synchronous consumption remains `completedWithoutCurrentOwnership`.

The existing ATOSNAP decoder validates the frame, version, complete original report, archive bounds and canonical header. Historical `capturedAgainstRevision` remains historical provenance; it is not the current exchange revision. Original `SnapshotWithType` wraps `Change.Snapshot`, which has no engine-wide version field. This code does not invent a native monotonic revision or equate an exchange revision with an atomic native snapshot.

## Complete supported export comparison

The comparator decodes the exact original wrapper messages around the existing generated `SmartBlockSnapshotBase`. It compares every emitted native object and every file byte. It keeps object/type/reference IDs exact, all 17 annotation creation/applied metadata fields, collections, ordered child IDs, relation links, file metadata, log heads, file keys and supported protobuf unknown fields. Block inventory and ZIP member order are normalized; ordered children and collection contents are preserved. No speculative import remapping occurs.

The only removed detail keys are the exact 11 UTF-8 names returned by r14 `torah.LocalKeys()` and removed by `torahvalues.ExportDetails`: `pinkhaTorahSources`, `pinkhaTorahTopics`, `pinkhaTorahWords`, `_pinkhaTorahReady`, `_pinkhaTorahLabels`, `_pinkhaTorahProjectionVersion`, `_pinkhaTorahCanonicalHash`, `_pinkhaTorahState`, `_pinkhaTorahCanonicalPropertyKey`, `_pinkhaTorahCacheIntegrity`, and `_pinkhaTorahAttachedProperties`. Unicode-equivalent alternative spellings are not removed. No general “local/derived” list or annotation-metadata exclusion is substituted.

ZIP input remains in memory; no untrusted member is extracted to a filesystem path. The bounded supported layout refuses duplicates, traversal/absolute/alternate paths, encryption, ZIP64, ambiguous framing, hidden/overlapping local records, unsupported extras and size/count violations. It cross-checks original central/local headers, descriptors, the ZIPFoundation inventory and actual extracted CRC. Limits are 65,536 archive bytes, 512 members and 8 MiB total expanded bytes. Every `.fileObject` export must have its referenced file bytes, and the actual report count must match the decoded native-object inventory. Unsupported legacy raw-file layouts remain unproven.

The pinned SwiftProtobuf map decoder drops unknown map-entry fields. The pre-decode guard therefore refuses unsupported map-entry fields, wrong wire types and repeated values. It also prevents distinct native UTF-8 map keys from collapsing through Swift Unicode-equivalent dictionary keys. Other supported message unknown fields remain in their original `UnknownStorage` and participate in equality. This is a fail-closed supported codec boundary, not silent normalization of unknown data.

## Defensive policy change

The old `TorahAnnotationCreateRecovery.assessApplied` API was explicitly advisory, had no active production callsites, and was never an opaque native receipt. It nevertheless returned a positive enum case for matching applied metadata plus a caller-constructible digest. The candidate retains source compatibility but returns `bodyApplicationUnproven` for that path. This removes an advisory shortcut; it is not a claim that production previously acknowledged a fabricated body.

The historical 52-control result at commit `53392efc0010ac0c75b9c104b51bc144b545eb5e` is preserved. Its assertion “matching explicit applied marker retains separate snapshot commitment” describes the earlier policy and is intentionally superseded. The unchanged identity, uncertainty, scope and ordering cases were not replayed. The new closed historical comparison is separately scoped and still cannot supply an atomic COMMIT/ACK proof.

## Verification and remaining gates

Forty new boundary/policy controls compiled and passed using actual Swift 6.3.3 in strict Swift 6 mode. Four full-file syntax parses passed. The exact result is `evidence/boundary-controls-v1/RESULT.json`, SHA256 `38d7278d1acdcb8fb92eb9b8b50eae6c8400182fab7e52923cf52dbab57ab0c2`.

Independent peer review found the map-entry decoder loss before integration. The guard was narrowed, and only 13 new affected map-entry controls were executed. All 13 passed in strict Swift 6 mode; the prior 40 were not rerun. The exact new result is `evidence/map-entry-controls-v1/RESULT.json`, SHA256 `5bd1bae8bd0567a4d20267d3d1c0bc67bae5d5bbcdcb260ce80899cbe4044803`. The former result remains bound to its original source hashes. The four syntax parses precede only the later wrapper-comment clarification; they do not substitute for full module typechecking.

Two independent source reviews accepted the held-read/ownership boundary and, after the map-entry correction, the bounded ZIP/map/wrapper/comparator source. These reviews are not execution evidence.

Thirty new semantic integration cases are prepared for a separate Linux Swift job. They compile the four actual pure comparator files, all 197 exact original generated model files plus their original additive `export_report.pb.swift` dependency, and the existing exact SwiftProtobuf/ZIPFoundation revisions. They exercise mixed Hebrew/English blocks, complete attachment bytes, graph/container ordering, every creation/applied metadata field, exact exclusions, native references/collections/types/file info, supported unknown fields, the actual lossy map decoder boundary and extraction CRC. They use synthetic original-format fixtures; no original engine is linked or native acceptance claimed. Neutral candidate publication does not dispatch the workflow.

The original 40-control closure remains reconstructible from the unchanged candidate files and the three exact historical inputs under `evidence/boundary-controls-v1/retained-inputs`. The test-only identity DTO copy has normalized LF line endings; its exact compiled bytes are recorded, while the production identity source is unchanged. Individual new semantic outcomes are written to retained stderr as they finish so a later failure preserves earlier results.

The first actual Linux run, `45035204985` attempt 1 at `f784bbb71963a57ba142e33b68c68df753e71afb`, failed during compilation after validating Swift 6.4.2, the 197 model blobs and both exact dependency revisions. `Anytype_Model_Notification.Export` references `Anytype_Model_ExportReport`, which is generated in the original `Protocol/export_report.pb.swift` file outside the Models directory. No semantic case executed. All 24 intake/evidence files remain under `evidence/linux-semantic-run-45035204985`; the runner RESULT SHA256 is `9e46da28180a62d0266a5a5241044ab18eba90cfbde2b5a4a13c062e324438d1`. The narrow correction stages that one unchanged original generated file, pinned by its Git blob. Production comparator files, dependency revisions and prior passing controls are unchanged. A new run requires root review of the corrective immutable head; there is no automatic replay.

Full semantic integration execution, actual Apple composition/typecheck of the held-read bridge, one real native observation, stable whole-graph native authority, genuine import-map authority, closed source/commit consumption, durable mapping and ACK remain open. Same-ID or metadata mismatches remain unproven; they never authorize replacement objects or extra exclusions.

## Primary source pins

- Swift source base: `b5162d777e3ebc5c4c0d044e02b52347c0c3dd6e`.
- Original Heart: [`d98420b1113536afd08cde6de9a5816f6d27ffff`](https://github.com/anyproto/anytype-heart/tree/d98420b1113536afd08cde6de9a5816f6d27ffff), especially `core/converter/pbc/pbc.go`, `core/block/export/export.go`, `core/block/export/writer.go`, `pb/protos/snapshot.proto`, `pb/protos/changes.proto`, and `pkg/lib/pb/model/protos/models.proto`.
- Original r14 overlay: repository `docs/pinkha/torah-integration/evidence/native-derived/8494cfb347/approval/revision-14/native-heart-integration.patch`, SHA256 `fb96818eb57bd9e0be8da90a11831bcccc7ca8e72cc0a4e9a065500feb7cc077`.
- SwiftProtobuf: [`c6fe6442e6a64250495669325044052e113e990c`](https://github.com/apple/swift-protobuf/tree/c6fe6442e6a64250495669325044052e113e990c); peer inspected `BinaryDecoder.swift` blob `3407f73abcb9454e2192600bec09e4a765e1f311` for map-entry loss.
- ZIPFoundation: [`22787ffb59de99e5dc1fbfe80b19c97a904ad48d`](https://github.com/weichsel/ZIPFoundation/tree/22787ffb59de99e5dc1fbfe80b19c97a904ad48d), the existing 0.9.20 pin.
- Ubuntu 24.04 runner documentation blob `7fa7e1aeaa474591fccf5973dd2f85c2cf6f5529` advertises Swift 6.4.2. The prepared job records the actual version and refuses drift rather than silently changing the reviewed compiler.
