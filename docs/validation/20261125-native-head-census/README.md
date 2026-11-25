# Complete native source census and system identity coverage

Product: 6a168b811a3a9abeedf5ca5b04eab7590f84cd8a. This closes two source-accounting gaps while leaving Task C open for actual full migration.

The source review previously bound only decoded object snapshots to a future migration plan. Original native settings/tombstone trees, the ACL head and the default native key-value head were not in that binding. The review now uses every exact native head from the already bound original anyenc witness and joins it against the native tree inventory, original ACL collection and native-derived default key-value identity. Any mismatch blocks complete source binding. Explicit component plans keep their existing serialized form; the capture coordinator rejects a snapshot-only or otherwise partial census before native checkpoint revalidation.

Retained system coverage previously accepted a matching witness hash and caller-selected kind/row count. It now requires the original manifest, exact native ACL ID or derived default KV ID, exact original collection row count and empty KV semantics. Ordinary captured snapshots, retained settings trees, foreign IDs, mismatched kinds and altered counts cannot be relabeled as ACL/KV. Retaining original ACL bytes does not translate destination permissions or prove history replay. Settings/tombstone trees and ACL permissions are now visible as unmapped source requirements in the review. The review still cannot authorize destination writes.

## Actual qualification

The final source ran 45 distinct impacted component methods with zero failures or skips, split into disjoint batches of 22 and 23. This includes five new original-census/system-identity controls, all six source-capture coordinator lifecycle/authorization controls, existing bundle/descriptor/page/context controls and the existing nine destination executor controls. The injected bridge controls remain explicitly injected; no native session or destination was created by these tests.

The immutable 143-snapshot capture has 144 native trees and 146 heads. The original 144-snapshot capture has 145 trees and 147 heads. The original 156-snapshot capture has 157 trees and 159 heads. In each, the settings tree, ACL head and default KV head remain accounted. Original source schema/semantic blockers stay enforced. Attempt 1 contains four earlier controls before the final bounded-allocation refinement; those are preserved and not added to the final distinct count.

The SwiftUI review counter/source-requirement wording awaits the next original Apple main-app increment. All host/integration source compiled on the retained Swift 6.4.3 Linux cache; no native or Apple rebuild was performed for this change.

## Original fixture recovery

During this continuation the previous Oracle 144/156 fixture directories were observed absent. No C cleanup removed them. The immutable Windows originals remained available under the existing SentinelX anytapy-immutable-evidence native-file-peer run roots. Their original small fixture archives were copied through the existing pinned Windows-to-Oracle SSH connection, safely extracted into new private C-owned directories, and checked against the original context and manifest hashes plus all 604 declared source members (291+313). No private key was copied or read, no new fixture was manufactured and the custom source producer's original FAIL remained unchanged.

The exact new private paths and archive digests are in private-original-recovery.json. Original GitHub artifact ZIPs were also independently redownloaded and matched their original published SHA256; they remain private, along with all raw source/account contents. Only receipts, commands, source hashes and original test logs are tracked here.

The broader whole-source requirements remain open: definition/layout/derived-field mappings, settings, ACL/account transition, original history semantics, complete destination execution and full source/target comparison after reopen. These controls must not be represented as full-space migration acceptance.
