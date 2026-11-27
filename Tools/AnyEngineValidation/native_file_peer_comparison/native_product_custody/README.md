# Superseded native792 custody and restoration

## Current location

On 2026-11-27, the closed, superseded ACL-refresh executable was moved as an exact ordinary raw file from the Oracle root filesystem to the development filesystem. The operation preserved every binary byte, size, file mode, uid, gid and mtime, verified both copies and fsynced the destination and restore mapping before retiring the duplicate original. No account, retained source, current executable or base executable was changed.

| Item | Value |
| --- | --- |
| Former path | `/var/lib/pinkha-c-filesv2-20261126/acl-refresh-native1/any` |
| Retained raw path | `/mnt/development/projects/evidence/pinkha-w1-network-native792-raw-20261127/any-79248a63132a0146` |
| Binary SHA-256 | `79248a63132a0146deff4e9fe1c4104a381a34d5c2ffcad536247a8429f98857` |
| Binary length | 78,074,642 bytes |
| Allocated root space recovered | 78,082,048 bytes |
| Original mode / uid / gid | 0700 / 0 / 0 |
| Original mtime_ns | 1795743968115720063 |
| Raw custody receipt SHA-256 | `378c4fe23d43c697ad475526b9687491d8f8c3fa29e74e93774e96574c140f2e` |
| Restore script SHA-256 | `f4b368bdf8280caa52967585fd55be03a99b9c8ecf4aa9c50421bfd814f6b481` |

The former path is absent. Earlier accepted receipts remain unchanged and continue to identify the same binary content. Any historical replay that requires that former path must first perform the guarded restoration below. New tests use current native0796; restoration is unnecessary for those tests.

The retained 1,597-file source, source manifest and original native792 build receipt remain at `/var/lib/pinkha-c-filesv2-20261126/acl-refresh-native1`. The build receipt remains SHA-256 `bfafdf6d7304786726235fd1d2f3065dbf5782091123f03fbd6bb54b09328380`.

## Guarded restoration

Run only when a specific historical replay requires the old path:

```sh
/usr/bin/python3 -B /mnt/development/projects/evidence/pinkha-w1-network-native792-raw-20261127/restore.py
```

The script reads the original `receipt.json` beside it. It refuses to overwrite an existing destination, verifies the retained raw file's exact hash and size, requires 2 GiB plus the binary allocation and 4 MiB free on root, preserves the 512 MiB development floor, copies with a fresh exclusive temporary file, verifies the complete stream, restores original metadata, fsyncs and atomically installs the old path. The retained raw copy remains available. This command has been preserved and reviewed; restoration has not been run because no current test needs the superseded executable.

This directory carries byte-exact copies of the receipt and restore script for review. The operative persistent copy is the absolute Oracle evidence directory named above.

## Failed compression remains evidence

The initial single-thread, idle-I/O xz attempt stopped when unrelated root growth crossed its unchanged 2 GiB emergency floor. Its owned process terminated with exit -15, without forced SIGKILL, and its entire process group was positively absent. That attempt retired no original file.

- Failed receipt: `/mnt/development/projects/evidence/pinkha-w1-network-native792-archive-20261127/result.json`, SHA-256 `473afc8999467fe8450264e2ece0bd135e16f9aed015d99180f0272f0a0e1d47`.
- Retained incomplete xz output: `/mnt/development/projects/evidence/pinkha-w1-network-native792-archive-20261127/any-79248a63.xz`, 31,481,856 bytes, SHA-256 `0aea3a6faf76ec40f7d86d114838e493eff3f84766f02db5d44abc7853df6b5d`.

The incomplete xz is not a qualified archive or restoration source. Its receipt and bytes were reverified unchanged during the successful raw relocation. The raw relocation was a separate, explicitly scoped recovery operation: zero bulk root writes, a bounded 4 MiB control allowance, the original development floor and exact custody checks. It did not lower any native test or build admission floor.

## Unchanged executable boundaries

Both before and after relocation, the original base binary remained SHA-256 `1dc1803c656da2215760477dadd26bf0e829b6ee592e337db6fa0295a6ed9636` and current LAN-progress binary remained SHA-256 `0796b939145f98fd3436b40c3ae3c7c9daec239b54f8c1fa237fb20a349d0b07`. No compiler, native account process or compression was started by the raw relocation. No unique binary bytes were deleted.

The custody operation succeeded in 3.516 seconds. Root free space rose from 2,121,699,328 to 2,199,781,376 bytes; development free space changed from 1,224,847,360 to 1,146,757,120 bytes. These are operation-time observations, not a current resource admission for future work.
