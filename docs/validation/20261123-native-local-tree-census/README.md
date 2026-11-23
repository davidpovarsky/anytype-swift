# Captured local tree storage census qualification

## Actual result and scope

Five new native methods executed once and passed on the original compiled binary. An independent audit then verified all six original private witness/census pairs. This qualifies structural accounting for captured local storage rows and references. It does not issue a production source capability, establish a whole-Space semantic census, validate signatures/replay or authorize migration writes.

Native source 35c169e7a39e3dafc0a1281f56a1fe37fce57533 directly follows the qualified witness hardening source 102f6243edb17068048869b85bc151f177897a68. Exactly four Go files were added. All six existing package files remain byte-identical. The implementation consumes an already captured Witness and never opens a live database, invokes ReadDoc, obtains a production issuer or writes destination data.

## Original execution remains faithfully recorded

Original controller source: 5d6ec4b42db00ec01737ea150b4e288be9ab3743.

The single build produced binary SHA256 4721b54afc0052d28de4e20043287d0da245dbd92818f611ce82fac59d0bba2c. The original native command returned 0, with its owned process group absent. Exact named START/PASS events identify:

- TestLocalTreeCensusNativeStorageRelationships
- TestLocalTreeCensusUsesCapturedCheckpointWithoutLiveReads
- TestLocalTreeCensusRetainsUnknownRowsAndExactTypedIdentities
- TestLocalTreeCensusReportsMissingCrossTreeAndACLReferences
- TestLocalTreeCensusQualificationLimitsAndPrivateReceipt

There were no native failed or skipped methods. The existing six witness methods, two hardening methods and eighteen dry-run methods were not reexecuted. Native build and execution preserved all 42 source inputs and 4,045 dependency input bytes.

The original wrapper nevertheless returned FAILED with private_pair_directory_mode. Its original execute.json, command receipt, named safe events and safe native receipts are preserved unchanged. This failure is not rewritten or relabelled.

## Exact audit-only correction

The native private fixtures and their private ancestors were mode 02700: owner rwx plus inherited setgid, with zero group or other permission bits. Every paired regular file was 0600. The Go fixture checked ordinary permission bits, while the Python auditor compared a mode including special bits.

Audit-only source 6195e74381a68c2cd8da54f262bb296e1f074c5a changes one predicate from exactly 0700 to exactly either 0700 or 02700. Its literal inverse reproduces the original auditor bytes and SHA256. It does not admit arbitrary special bits and does not change any file or directory permissions. Original run.py and all native source/test files remain unchanged.

The separate audit_existing.py reads the fixed existing original attempt only. It binds original artifacts, the exact five native events, the old source and dependency snapshots, the retained binary and all private file identities before independently reading the six pairs. It then rechecks source/dependency bytes and private contents, inodes, modes and ownership.

The audit-only command returned 0 in 3.173 seconds. Receipt SHA256: 890ccd8a7a36c0fe83c3c13b3435b02f331a5f81f7e2d698bef9148075c4e489. It performed zero builds, zero native test executions and zero chmod operations.

## Independently audited captured evidence

| Fixture | Captured rows | References | Resolved identities | Unknown collections |
|---|---:|---:|---:|---:|
| native | 12 | 21 | 21 | 1 |
| captured-old | 10 | 16 | 16 | 1 |
| captured-new | 11 | 19 | 19 | 2 |
| unknowns | 14 | 9 | 9 | 4 |
| references | 15 | 27 | 18 | 1 |
| boundary | 7 | 9 | 9 | 2 |

These are per-fixture captured counts, not a unique global census. All captured rows and recognized references are accounted for, including unresolved rows, empty collections and opaque or unknown collections. Each census contains its exact original witness. Resolved means structural identity only, not valid content/signature or authorized migration.

Public evidence contains fixed classifications, counts, hashes and source metadata. Raw native output, SQLite stores and private witness/census bytes remain only in the owned private external evidence directory.

## Evidence layout

- qualification.json joins the original five native results and independent six-pair audit, with explicit false authority/write/semantic-completeness gates.
- original/ contains unchanged safe originals, source/dependency maps and exact command receipts.
- original-artifact-bindings.json pins all nineteen original artifact identities, including external private logs. Four byte-identical dependency snapshots are represented by one exact copied map; the other originals remain externally retained and hash-bound.
- audit-only/ contains the unchanged new receipt, before/after source and private metadata, safe pair accounting, and original audit-launch stdout/stderr/receipt.
- artifact-index.json hashes the complete committed evidence set except the index itself.

External originals: /mnt/development/projects/evidence/local-tree-census-20261123/attempt1.
External audit-only originals: /mnt/development/projects/evidence/local-tree-census-20261123/audit-only-attempt1.

All native source admission, destination-write permission and semantic census completeness flags remain false. The original native snapshot and identity census requirements remain true.
