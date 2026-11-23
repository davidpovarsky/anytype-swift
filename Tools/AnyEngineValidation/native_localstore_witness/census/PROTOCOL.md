# Captured local tree storage census

Status: source design; not compiled or executed. This additive package consumes only a completed in-memory localstore Witness. The existing six native witness files remain byte-identical to 102f6243edb17068048869b85bc151f177897a68.

## Authority and boundary

The report describes one previously captured, owned fixture checkpoint. It opens no database, reacquires no capability, starts no transaction and reads no live Heart Object. There is no production capability issuer. A serialized receipt, database path or arbitrary decoded row list cannot construct a qualified census.

NativeSnapshotProofRequired and NativeIdentityCensusRequired remain true. HasNativeSourceAdmission, PermitsDestinationWrites and SemanticIdentityCensusComplete remain false in every receipt. AllCapturedRowsAccounted means only that every row in this exact captured witness has a census row. A resolved_identity_only reference proves the exact storage identity and expected local namespace/tree relation, not signatures, ACL authority, object semantics, immutable global membership, payload availability or migration eligibility.

Retirement of the fixture owner after capture cannot create current authority. The census retains the captured owner, generation, Space and witness digests. New scans are distinct witnesses, not updates to the old report.

## Native schema used

The source manifest pins the actual cached source and exact cached module ZIP members of any-sync v0.13.8 and any-store v1.0.3.

| Collection | Read structural fields | Retained unresolved boundary |
| --- | --- | --- |
| state | id, ACL a, settings s, native header e | nh, oh and h stay in the exact source row; no global watermark is inferred. |
| heads | id, heads h, common snapshot s, deletion d, derived r, parent p | q remains original typed numeric metadata; deleted and queued rows are included. |
| changes | id, tree t, raw r, predecessors p, snapshot i | o, sz, sc, a, q remain original metadata/payload. Raw changes are not replayed. |
| Exact captured ACL-ID collection | id, raw r, predecessor p | o and sz remain original metadata; ACL membership/permissions are not interpreted. |
| _client | Original rows only | Opaque client collection, including empty collections. |
| Any other collection | Original rows only | Unknown collection and all its records remain unresolved, including empty collections. |

Normal HeadStorage.IterateEntries filters deletion metadata. This census uses the already captured unfiltered registered collection rows; it never substitutes that active-only iterator for a census.

Every source row carries its collection index, ordinal and exact anyenc encoded ID. String, number and binary IDs remain distinct. Raw UTF-8 byte identity is used for collection names and native string IDs; canonically equivalent Unicode strings are never merged. Duplicate known fields are ambiguous. Unknown fields remain inside the exact original row and have explicit issues when their collection is structurally interpreted.

References retain source row, field and array position, expected namespace/tree, observed candidate and resolved target separately. Missing local targets are not asserted absent from the complete Space. Cross-tree, wrong-namespace, wrong-root, malformed target and missing-target outcomes never gain a resolved target. The schema's local sequence field is not a whole-Space transaction or snapshot version.

## Private and public representations

The private census starts with four unsigned 64-bit big-endian length-framed values: format identifier, authority boundary, source witness SHA256, and the exact original private witness bytes. It then contains counts and all row, reference and issue records. Integer fields are themselves length-framed eight-byte big-endian signed integers; -1 denotes an absent position or target. The original Witness encoding and typed anyenc row values are unchanged.

Rows encode collection, ordinal, fixed kind, original typed ID, optional native string ID/tree, deletion, derived state and unresolved flag. References encode source row, position, fixed kind/domain, source field, exact identifier/tree bytes, fixed outcome, target and observed indexes. Issues encode collection, row, source field, position and fixed code. The framing is deterministic and bounded; short writes or incomplete writes fail.

Only the explicitly private fixture directory receives source or census bytes. Its directories require owner permission bits 0700; exactly mode 0700 or mode 02700 with inherited setgid is admitted. Group and other permissions remain zero. The new paired evidence files are mode 0600, exclusively created. Raw execution output also remains private. Public receipts contain fixed labels, digests, counts and booleans, never native IDs, payloads, collection names, owner nonces, recovery data or private source paths. The public event projection excludes arbitrary test Output fields.

A separate Python reader validates the native anyenc/frame representation without importing the Go census. It verifies the exact embedded witness, complete typed row coverage, recognized reference coverage, source/target bounds, namespace and tree constraints, issue origins, receipt digests/counts and six paired private artifacts. Its public result contains only hashes/counts and fixed outcomes. It does not grant semantic or production authority.

## Five new native methods

1. NativeStorageRelationships creates actual signed native storage roots and a change using ChangeBuilder, SpaceStorage.CreateTreeStorage and Storage.AddAll. Native queued/deleted and derived rows remain captured, ACL and settings namespaces stay distinct, and one future source field remains visible as unresolved metadata. This is native storage behavior, not a Heart Object creation/ACL authorization claim.
2. UsesCapturedCheckpointWithoutLiveReads mutates the live fixture after capture and proves the old census still uses the exact old bytes without more database or authority calls. A second capture has its own new row/inventory. Owner retirement does not upgrade the historical report.
3. RetainsUnknownRowsAndExactTypedIdentities exercises an empty collection, distinct composed/decomposed collection and row names, string/number/binary IDs, repeated spelling across collections, duplicate opaque metadata and a malformed numeric native-head ID.
4. ReportsMissingCrossTreeAndACLReferences supplies explicit negative storage fixtures for a cross-tree head, absent snapshot/predecessor/root, ACL namespace mismatch, ambiguous tree owner, duplicate reference and unsupported metadata.
5. QualificationLimitsAndPrivateReceipt rejects nil/zero/cancelled or over-limit inputs without partial qualification, propagates short writes, and verifies fixed false authority flags and absence of fixture IDs/nonces in public output.

The exact five fully qualified names are pinned in source.json and in the controller. No old six-method witness suite, two-method hardening scope or archive dry-run method is selected. Prior results remain their original source-bound receipts. There is no new concurrency/interleaving proof claim.

## Bounded controller and capacity

The controller uses the existing Oracle Go 1.27.4 linux/arm64 glibc profile, one compile worker and the already qualified module/build caches. All eight new direct nonstandard-library imports occur in the original hardening dependency graph. No Heart service/Tantivy build, toolchain install, network dependency download or production data access is involved.

Original hardening compilation produced a 25,486,041-byte binary in 6.00 seconds and consumed 27,230,208 more free bytes between the observed command endpoints. Peak usage was not measured. The new planning allowance is 50–150 MB for incremental objects/link/temp plus less than 1 MB for source/evidence. This estimate is not permission to cross the reserve.

Build start still requires at least 2,950,000,000 free bytes. The owned process is stopped if free space falls below 2,600,000,000 bytes. The required minimum reserve remains 2,500,000,000 bytes. Parent approval and sufficient capacity are required before any build or execution. No retained artifact or shared cache is deleted by this controller.

Source commits are frozen before execution. Native/current-controller/schema/dependency inputs are hashed before and after; actual original commands, logs, process ownership and binary identity are preserved. Only the five new methods run once against that built binary. A failure remains a failure and receives a distinct new attempt if a reviewed correction is needed.

## Still required for full migration

This slice does not enumerate or reconstruct native semantic Objects, object-scoped blocks, Types, property definitions/uses, links, tombstone semantics, encryption/key availability, all referenced file payloads or remote-only records. It does not establish a production-owned immutable whole-Space snapshot or an authoritative globally complete census. Live ReadDoc/BuildState may perform migrations or depend on mutable services and is not admitted as a frozen reader. Those authority and coverage gaps remain explicit before migration writes can be enabled.
