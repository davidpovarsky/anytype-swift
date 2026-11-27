# Three owned component-cache roots — exact preservation handoff

This is a **source-reviewed preparation candidate**, not an executed relocation, compiler admission, warm-cache qualification or test result. Root owns the actual storage operation and any later component execution. The controller has not been invoked by this agent.

## Fixed scope and original custody

The source root is `/var/lib/pinkha-wave2-native-block-menu-20261127`. Only its `build`, `cache`, and `clang-module-cache` directories may be copied and replaced with stable aliases. The completed Add-block receipt and handoff, `component`, all Properties controller inputs, and all four local source packages remain at their original physical paths.

| Root | Actual entries | Actual allocated bytes |
| --- | ---: | ---: |
| `build` | 6,191 | 339,099,648 |
| `cache` | 100 | 27,303,936 |
| `clang-module-cache` | 24 | 35,536,896 |
| Total | 6,315 | 401,940,480 |

The bounded read-only census found no regular-file hardlinks or special nodes. It found one symlink: `build/debug` → `out/Products/Debug-linux-aarch64`, owned by ubuntu:chatgpt-agent with mode 0777. The controller permits only that exact relative link, verifies its target and all its directory ancestors in the same physical inventory, and never dereferences it when retiring the duplicate. There is no generic symlink allowance.

The complete original Sentinel response is retained in `metadata-inspection.transport-original.txt`. `metadata-inspection.exact.json` was decoded from those raw bytes using Python, preserving integer nanosecond values. The earlier `metadata-inspection.original.json` is a retained JS-rendered summary and **must not be used as a nanosecond metadata authority** because JavaScript rounded large numeric values. Neither census is the future mutation authority: the controller captures and verifies complete fresh noatime content/metadata manifests before any mutation.

Exact raw owner handoff `493a7d62…` and the original Package.swift/Package.resolved were separately read from four fixed paths and retained under `originals/`. The original Properties runner `99dcacda…` was hash-verified without modification. All handoff field names, status, original source-copy paths, bytes and hashes in `input_closure` came from the actual original JSON.

## Source derivative

`preserve_owned_component_cache.py` is a finite derivative of W1's published `0852b8ff…` controller. `source-derivative.json` contains every exact changed segment and a verified inverse that restores the complete original bytes. The original functions `directory_names`, `sha_file`, `portable`, `durable_directory`, `immutable_json`, `live_users`, `protected_files`, and `exchange_paths` remain byte-identical.

The new fixed scope, pins and source checks preserve:

- original 493 handoff, bbf Add-block result, 67c complete local source manifest and all six original compiled source copies;
- original component Package.swift and Package.resolved;
- all six actual Properties inputs plus the unchanged 99dc runner;
- exact complete 370-file local dependency source set and full physical trees;
- original modes, owners, timestamps, xattrs, child topology, bytes and SHA-256 of every source/cache node, with destination filesystem identity differences reported separately.

Linux may update the access time of a newly copied symlink when `readlink` reads it. The only special handling restores the immediately observed access-time change on the new copied `build/debug` link after proving all other metadata unchanged. It never restores or masks drift on the original source. Each correction is retained in the result. New link ctime changes are explicitly nonportable; target, inode, mode, owner, original timestamps and xattrs are still checked.

## Actual operation contract

The destination is the fresh fixed directory:

`/mnt/development/projects/evidence/pinkha-wave2-component-cache-preserved-20261127`

The controller requires its parent to be canonical. A single stable nonblocking global lock is acquired before the output is created. A durable active claim is written before the first exchange and blocks all replays until completion. Existing output or an unresolved claim causes refusal.

Before copying, actual free development space must fit **rounded logical copy size + 512 MiB reserve + 256 MiB further component budget + 16 MiB evidence allowance**. During custody, development retains the 512+256 MiB reserve. The storage-only root emergency floor is 256 MiB; it is not a compiler gate. The original 99dc compiler start and live floors are unchanged.

The controller performs fresh current no-live-user checks against paths, file identities, descriptors, cwd and mappings. It does not signal processes, recheck any historical group ID, or infer current absence from the old handoff. Full destination and unchanged-source verification precede an immutable restoration map. All three original path exchanges occur before any original duplicate retirement. Each retirement revalidates the complete source duplicate and the destination, then deletes only the verified duplicate; the sole retained destination is never deleted.

On failure, verified copies, stable aliases, remaining duplicates and original errors remain available. Final access preparation or claim-release failure is recorded as FAIL and retains or recreates the durable claim. Consumers require both a successful durable receipt and the absence of that claim. Exact de76 pre-review source/inverse and its finalization finding remain retained; `retained-exact-diffs.json` retains the exact original finalization-only diff and complete derivative diff, including their SHA-256 values.

Only newly created destination/evidence directories receive traversal permissions for ubuntu:chatgpt-agent. Existing source/cache/evidence ownership and modes remain unchanged. `component`, `attempt1` and the parent SHARED path remain physically on root.

## Separate original source-location qualification

After a genuinely successful custody receipt, root may invoke the fixed companion as the original compiler user:

```text
runuser -u ubuntu -g chatgpt-agent -- python3 -B <reviewed qualifier path> <exact actual custody receipt SHA-256>
```

`qualify_component_source_location.py` accepts no source-root override. It requires the exact reviewed custody controller, actual successful receipt and restoration map, actual new physical roots, original alias identities, no unresolved claim, original 493 handoff, and exact unchanged 99dc source. It imports that controller with bytecode generation disabled and calls only its existing `pinned_inputs` function. It does not call main, prepare component sources or invoke Swift.

The original check verifies the 370 local inputs, the complete Git blobs and physical file sets of the three actual dependency checkouts (135/211/919 files), original four component source files plus only the previously authorized three Properties additions, Package/lock and error enum/provenance. Current results and alias identities are retained in the new `source-qualification1/receipt.json`.

This is a distinct phase: the original input reader and Git may legitimately advance atime after completed immutable custody. The qualifier does not claim all timestamps remain unchanged after those ordinary reads. It leaves the original handoff, controller, argv, scratch/cache and Clang module-cache path spellings unchanged. Compiler warmness remains **UNPROVEN**.

The unchanged 99dc resource sampler still measures its physical SHARED directory on root; it requires 2 GiB + 256 MiB before a run and a 2 GiB live root floor, one job, original memory floors and a 300-second deadline. It does not independently monitor development live free space. Any later actual compile remains a separate root-owned admission with current capacity. A relocation or source qualification PASS never supplies a test PASS.

## Validation performed here

Only Python AST parsing and exact source-inverse verification were performed on these controllers. No storage/controller invocation, test, Swift, Native, simulator or historical process observation occurred. Independent root source review and all eventual actual custody/qualification receipts must remain distinguishable from these preparation proofs.
