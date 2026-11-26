# Two original mixed-version native LAN cold restores — actual Linux PASS

Both original methods executed with unchanged assertions and deadlines:

| Method | Result | Seconds |
| --- | --- | --- |
| TestPinkhaMixedOldOwnerNewMember_P2PColdRestore | PASS | 6.98 |
| TestPinkhaMixedNewOwnerOldMember_P2PColdRestore | PASS | 65.25 |

The Go package reported 72.253 seconds, exit 0, two passed, zero failed or skipped, and zero forced native stops. The exact owned process group was absent with ESRCH. Source manifests and both independently built executables matched before and after execution.

These are independent native device processes, a fresh cold restored peer, actual local discovery and peer transport, and zero network peers. This cold-restore scenario restores the same account onto another device. The separately retained signed-ACL tests are the evidence for different accounts and roles.

Current: Any8fbd1e819fb132ac0e0a848d2ddf5c5714189b81 / SDKc1fd59bd8f0ed62471234ec1a65a402d22eab6a9. Legacy: Any9a190eb8236f18da75e5d85c3d1db31cd558d098 / SDKe195f6c07a053c6588e39ffe72ee4fc44cf3d953. Both include the qualified minimal ACL error mapping correction. Only two binary hashes and diagnostic labels changed in the original wrapper; the inverse restores every original byte.

## Scope

This is Linux/arm64 native acceptance. It does not prove Apple UI, Heart-to-Any compatibility, FilesV2 byte/variant/resume/offline behavior, physical-device behavior, or full T2 completion. The original two Mac cold-restore failures remain failures. No passed network scenario was replayed.

## Original custody

The private complete archive contains 5,193 members, including 4,801 files and 217,491,258 original source/product/log bytes. Every member's bytes, mode, kind and symlink target matched unchanged originals. Only the reproducible Go cache was excluded. The archive is 95,040,743 bytes, SHA256 1caf9d7bbd76af5d8985a5515cd0156d89d8739e37bd75f5adddd3f7932f4bb1.

Originals: /var/lib/pinkha-root-t2-linux-20261126/.

Oracle archive: /home/ubuntu/pinkha-t2-linux-retained-20261126/.

Independent Windows private copy: C:\Users\DAVID\AppData\Local\PinkhaEvidence\T2-Linux-P2P-20261126.

Windows independently verified archive and inventory byte identity. Its original receipt was copied back and rehashed without conversion. Raw native logs contain ephemeral test account secrets and stay private, outside Git. Original temporary-account cleanup was not modified.

All public receipts are exact original bytes; receipt-files.json binds them. No Release Archive, app signature, upload, TestFlight or physical-device success is inferred.
