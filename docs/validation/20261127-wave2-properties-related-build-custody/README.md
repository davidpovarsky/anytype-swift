# Two terminal Properties build directories — relocation preparation

**Source preparation only. No remote execution, storage slot request, compiler, test or process-group probe has occurred.** Root is holding this operation while the already queued consumers proceed; use it only if a fresh reserve assessment establishes a remaining need.

The single fixed-path script is `relocate_terminal_properties_builds.py`. Its only selectable input is the actual coordination-story identifier. It cannot accept arbitrary sources, destinations or historical process IDs.

## Exact scope

| Original build path | Destination beneath the new namespace | Original files / directories / links | Surveyed allocation |
| --- | --- | ---: | ---: |
| `/var/lib/pinkha-wave2-properties-related-lifetime-20261127/build` | `retained/original-failed-build` | 578 / 409 / 1 | 35,352,576 B |
| `/var/lib/pinkha-wave2-properties-related-lifetime-source2-20261127/build` | `retained/source2-passed-build` | 631 / 417 / 1 | 58,060,800 B |

The namespace is `/mnt/development/projects/evidence/wave2-properties-related-build-custody-20261127`. Directory counts include each build root. Both trees admit only their observed internal `debug → out/Products/Debug-linux-aarch64` symlink. The original survey remains verbatim in `readonly-inventory.original.json`.

The original failed receipt `8fbaf3c6…` and successful receipt `05971770…` are immutable admission inputs. Their positive historical absence evidence is read as retained evidence only. Neither historical process/group is probed, signalled or used as a fresh owner. A separate current path/inode census refuses an active reader or writer without retaining full command lines. Existing actual component results retain their original scope; relocation grants no new acceptance or future warm-build claim.

## Preconditions and resource bound

- Root execution on the existing `torah-social` host, an actual coordinated storage slot, and the existing exclusive custody lock. The destination namespace and both fixed temporary duplicate names must be absent. A previous partial operation is never replayed automatically.
- Both source parents must remain physical directories, mode `0700`, owned by `ubuntu:chatgpt-agent`, with the originally staged ordinary POSIX access policy. Destination ancestors must be traversable by that actual owner. The new namespace and its `retained` directory use the same owner-only traversal; every copied tree entry retains its actual mode, UID and GID.
- The destination must be a different filesystem. Source trees must retain the exact surveyed entry counts, logical byte totals and allocated totals. No nested mount or special file is accepted.
- Root free space must initially cover **2 GiB + 1 MiB** metadata allowance, and the existing **2 GiB** live floor remains enforced. This script does not lower a compiler, Native or runtime admission floor.
- Destination admission uses **512 MiB live reserve + the measured rounded logical copy size + 16 MiB evidence margin**. The measured copy bound must be at most **128 MiB**. Hardlinks may reduce actual copying; admission deliberately counts each logical regular-file path, so it remains conservative. Both original surveyed allocations total **93,413,376 B**, but actual unique source allocation is separately computed across both trees, including any cross-tree hardlinks; a free-space delta is not assumed equal to the survey sum.
- File contents stream in 1 MiB chunks. Tree manifests are bounded to 2,500 entries per tree, extended attributes to 1 MiB per entry and individual evidence documents to 8 MiB. A 300-second operation deadline and separate 60-second final-read deadline apply between filesystem operations. These are storage bounds, not test timeouts.

## Copy, verification and original paths

1. Bind both terminal receipts and all eight receipt-listed artifacts per run; verify their original component/input source copies and controller hashes. No parent, source, log, receipt or shared-cache tree is relocated.
2. Capture complete hashes, modes, UID/GID, timestamps, extended attributes, child topology and inode identities. Ordinary reads use `O_NOFOLLOW` and `O_NOATIME`. Preserve every internal regular-file hardlink equivalence class across both trees; reject any hardlink escaping the two selected trees. Fresh copied symlink access-time read effects are restored only on the copy and do not change original metadata.
3. Copy to the exclusive destination, restore metadata, fsync files/directories, and independently hash both copies. Re-read original trees to reject drift and verify hardlink classes, not just equal file contents.
4. Record the fixed restoration map in immutable phase evidence. Beside each original `build`, create only `build.verified-wave2-custody-original-20261127` as a symlink to its verified destination. Use Linux `renameat2(RENAME_EXCHANGE)` to exchange that link with the exact original directory. The public `build` path is never deliberately absent; the old physical tree now occupies the temporary duplicate path.
5. Only after **both** original paths are stable aliases to durable verified copies, recheck copies and current users, then retire the two exact duplicate trees. Each file is identity/metadata/hash checked before unlink; remaining hardlink counts are tracked across both originals. No chmod of original trees or recursive deletion of an unverified path is used.
6. Recheck retained copies, original alias targets, original source/evidence hashes and owner traversal, then write the terminal custody receipt. The only source-parent changes are the specifically authorized directory-entry exchanges and removal of those verified duplicates; parent ownership and access policy stay unchanged.

## Failure and recovery behavior

There is **no automatic rollback or recovery replay**. Before an exchange, failure leaves the original tree at its original path and retains any partial copy. After an exchange, the original path remains an alias to the already verified destination, and the full or partially retired original duplicate remains available. Both aliases and both durable copies exist before any deletion starts. A failure, interruption, new live user or capacity violation stops further retirement.

Immutable phase receipts and the full before/copy/duplicate manifests preserve the last completed boundary. The first failure remains the first error in the result; later final-integrity, state-read or receipt-write errors are recorded separately and cannot produce PASS. An abrupt process death can leave no final receipt; the exclusive namespace then requires a separately reviewed recovery based on the existing phase records. Neither the retained destination nor an old result is deleted to make a retry possible.

If a physical original path is later needed, perform a separately admitted exact copy from the retained tree to a new sibling under the original parent, verify/fsync it, and exchange only with the still-exact alias. Do not remove the sole retained copy. Any future compiler run needs its own source/resource admission.

## Validation status

Only Python AST syntax parsing and source inspection have been performed locally. No filesystem relocation or synthetic relocation control has run. Root must review the exact frozen source before deciding whether a coordinated execution is useful.
