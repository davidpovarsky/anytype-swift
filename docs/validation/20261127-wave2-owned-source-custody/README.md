# Wave2 — completed custody of three cold source worktrees

This packet retains the exact controllers, independent source reviews and actual Oracle receipts for three archived, published Wave2 source materializations. The existing branches and Git history remain available. The private source archives remain at their original Oracle evidence paths.

## Terminal outcomes

| Lane | Preserved source commit | Actual terminal outcome | Receipt SHA256 |
|---|---|---|---|
| Editor | `ac606cc0add9a861ed02edb38af956924e7b017c` | Normal Git removal passed at 2026-11-27 06:56:01 UTC | `17260638416c55fb2b5abfce8feb3e9f7db2e479bef45b9b2584be04c7be28ff` |
| Torah | `3406906e27c0f2c2d71abba52f30d20b7b612bc6` | Exact archived remainder recovery passed at 07:13:33 UTC; original permission failure retained | `3fbc2a293ca74c8da3de103b94e746cd22ed26d12894e8d81b37b74510dcf091` |
| Interfaces | `2f18fe876b0d87f76403ed849dcad880c8369f28` | Exact archived source and missing registration removal passed at 07:51:30 UTC | `4d1b80949c16ea0cea25eb96fb19dff20262bca18b2c5f107ed02fa1e9c8a131` |

The [completed inventory](originals/completed-custody-inventory1.json), SHA `52b75987096e005dbeb407a2e2ee5d9aa70522d29d7c8e2c8c6cb8e75ef18666`, independently observed all three old paths and registrations absent, the three branch refs unchanged, all retained restore artifacts matching their pinned hashes, and no persistent custody hold. Its current-process operation was limited to ordinary read-only Git; historical process-group IDs were not probed again.

## Preserved failures and corrective boundaries

The original Torah `git worktree remove` exited 255 after unregistering its worktree but failing to remove a directory that the Git user could not write. Its [failure receipt](originals/torah-1/retire-receipt.json), SHA `3ebe7ec7f41da2e03ed047fc82dc56a89abd8212b53c1b6b340e6e442a561e14`, remains unchanged. The separately reviewed `21043e4e…` recovery accepted only the exact remaining entries already in the completed archive; its successful receipt is separate.

For Interfaces, an initial read-only check as `ubuntu:chatgpt-agent` found exactly one unwritable directory among 3,329 traversed directories: `docs/validation/20261127-wave2-native-rtl`, owner0/group1002/mode02755. Every original mode and owner was preserved. The unchanged approved archive controller `fdcac872…` first completed and validated all 13,685 source entries plus the linked Git metadata.

A tiny disposable Oracle repository then proved that the same Git2.43.0 can normally remove an already-missing linked worktree. That [actual probe receipt](originals/missing-worktree-probe1.json), SHA `3313463a0caa452ededa7b9606617845e1c400a382a79bf969b06cf9ea5fa7f3`, records exit0, removed registration and unchanged clean probe main commit. Production repository changes were zero.

The separately reviewed Interfaces controller `1edb3b86…` validates the full live source and Git metadata against their original archives before mutation. One stable global lock and durable claim span fixed-parent descriptor-safe root removal, normal unprivileged Git removal of only that missing registration, exact original `99dcacda…` owned-process cleanup, and final branch/archive/source-absence checks. It changes no existing permission or ownership. The original Git command and its fresh child have separate retained process receipts; only a terminal process with the original ESRCH absence evidence can qualify. Any unresolved failure keeps the custody claim. The successful final receipt was durable before the claim was cleared.

The [independent Interfaces review](reviews/editor-archived-interfaces-review-1edb.json), SHA `0190cc7dc37f62bb6411333bc630d89aac9efdf5a850ab29357ef42415dd5378`, is source-only. The actual retirement receipt supplies the execution evidence. Prior source-review findings and versions are retained in this packet.

## Archive custody and capacity

All archives and full source manifests remain under:

`/mnt/development/projects/evidence/wave2-owned-source-retirement-20261127`

The original archive receipts bind exact member paths, regular bytes, symlink targets, modes, owner/group and nanosecond modification times. They do not claim preservation of access/change time, inode identity or unrecorded extended attributes. This Git packet contains only text controllers, reviews and small receipts. It contains no tar archive, private screenshot or raw Git index.

At the 07:55:41 UTC inventory:

| Retained set | Exact bytes |
|---|---:|
| Three source archives | 186,346,025 |
| Three Git metadata archives | 2,723,542 |
| All six archives | 189,069,567 |
| Twelve restore artifacts plus three original archive receipts | 201,146,749 |

The latest Interfaces source alone had 195,732,694 regular bytes and 235,651,072 allocated bytes before retirement. Its whole-host development free-space observations were 174,604,288 bytes before and 413,499,392 bytes after. The subsequent whole-host observation at 07:55 was 144,322,560 bytes; this packet does not attribute concurrent capacity changes to a particular job. Root free space at that inventory was 1,218,289,664 bytes; available memory was 5,011,517,440 bytes. These are timestamped whole-host observations, not an asserted net reclaim of all three source trees.

The proposed next archival custody operation has not run. Against the separately supplied 07:29 Windows C observation of 2,976,956,416 free bytes, the 201,146,749-byte restore set would leave 2,775,809,667 bytes, exceeding 2 GiB by 628,326,019 bytes. A fresh destination-capacity/ongoing-growth check and the separately reviewed transfer route remain required. This lane made no Windows write or archive movement.

Publication is bounded to at most 1 MiB of text evidence, plus 16 MiB Git allowance and 64 MiB source-operation margin, measured immediately before the isolated sparse worktree is created. Native/compiler admission floors remain unchanged.

## Scope

These operations archived and retired only the three explicitly handed-off cold source materializations. Current worktrees, branches, history, caches, account state and application products remain outside the mutation scope. No compiler, Swift, Native engine, Mac or simulator test was started. The source-only publication provides custody evidence and does not grant application acceptance.
