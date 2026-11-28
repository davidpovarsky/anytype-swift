# Root disk and ext4 geometry: no unallocated growth capacity

Status: **actual read-only metadata evidence; no capacity admitted and no resize performed**.

Two separately authorized observations on the existing Oracle host establish that the root filesystem already occupies every complete 4,096-byte block available in its partition. The containing device has only 33 sectors after that partition. Neither observation changed storage, reserved blocks, acceptance guards, accounts, caches, or runtime state.

## Exact observations

| Measurement | Device/partition observation | Ext4 header observation |
|---|---:|---:|
| UTC completion | 2026-11-28 09:31:32.990275 | 2026-11-28 09:38:43.018990 |
| Commands | `findmnt` and `lsblk`, plus kernel block size/start metadata | Existing `/usr/sbin/tune2fs -l /dev/sda1` |
| Command results | Both exit 0 | Exit 0 |
| Script elapsed time | 0.012029 seconds | 0.012859 seconds |
| Root device and filesystem | `/dev/sda1`, ext4 | `/dev/sda1` |

Each observation had a 10-second outer limit and a 16-KiB output ceiling. The attached raw JSON strings are the exact returned observation bodies; they have not been reformatted or given an added trailing newline.

## Geometry reconciliation

| Quantity | Exact value |
|---|---:|
| Whole device `/dev/sda` | 53,687,091,200 bytes (50 GiB) |
| Whole-device length | 104,857,600 sectors of 512 bytes |
| Root partition start | Sector 2,099,200 |
| Root partition length | 102,758,367 sectors = 52,612,283,904 bytes |
| Root partition end, exclusive | Sector 104,857,567 |
| Tail after the root partition | **33 sectors = 16,896 bytes** |
| Ext4 block count | 12,844,795 |
| Ext4 block size | 4,096 bytes |
| Ext4 size | **52,612,280,320 bytes** |
| Partition bytes beyond ext4 | **3,584 bytes: less than one filesystem block** |
| Header overhead | 421,917 clusters of 4,096 bytes = **1,728,172,032 bytes** |
| Header reserved block count | **0** |

The complete earlier partition-to-statvfs difference reconciles as:

```text
52,612,283,904 partition bytes
- 1,728,172,032 filesystem overhead bytes
-         3,584 trailing partition bytes
= 50,884,108,288 statvfs filesystem bytes
```

The other two partitions are `sda15` (103,809,536 bytes) and `sda16` (967,836,160 bytes). All raw geometric gaps total 3,161,600 bytes, including partition-table and alignment space. This total is not a claim of safely allocatable bytes. The root-adjacent tail and the sub-block remainder cannot relieve the observed capacity deficit.

## Free space and unchanged admission

At the first observation, statvfs reported **1,691,357,184 available bytes**, which was **590,344,192 bytes below** the unchanged 2,281,701,376-byte native admission. At the later header read, the on-disk header reported 419,827 free blocks, or 1,719,611,392 bytes. **Header free blocks are not statvfs available space**, and the later number is not a new admission measurement. No capacity credit is taken from it.

The 1,728,175,616-byte partition/statvfs difference is fully explained by metadata overhead plus the 3,584-byte remainder. There is no whole filesystem block to add inside the existing partition. Reserved blocks are already zero. No filesystem growth, reserve change, device expansion, or provider operation was performed or authorized by these observations.

This evidence-only commit leaves all source carriers and qualification controllers unchanged. N24, the boot/lifecycle33 extension, broker7, their combined64 selection, E97/Swift23, and the retained-account quota query receive no new runtime acceptance or launch permission.

## Evidence

- [Device and partition observation](root-device-geometry.json): 5,258 bytes; SHA256 `1366be885d875787de8246de380a1dd8721fb8fba2ceecf340b693c2a0ca537f`.
- [Ext4 header observation](root-ext4-header.json): 3,608 bytes; SHA256 `e08e293d6a8a9e7b95a75053c64078833bd5c9ba6e052d97fb04cfd36a16e739`.
- [File and provenance manifest](FILES.json).
