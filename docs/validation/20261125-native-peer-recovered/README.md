# Original native migration source/peer evidence recovered — 25 November 2026

The GitHub run [45501479246](https://github.com/davidpovarsky/anytype-swift/actions/runs/45501479246) remains **FAIL**. This audit qualifies native scopes from its original archive, without another native build or test.

## Actual observed scopes

- Custom schema: TestLoadedAccountCustomSchemaSource PASS, 156 snapshots, 20 types / 126 property definitions in the captured source, one added custom type, 7 added properties, 4 options, 2 typed documents and explicit empty/default/current value checks.
- Separate owner and Reader member processes: both original native methods PASS with actual native tree transfer. The receiving account started without the local file, fetched the complete 2 MiB encrypted file through the native network and checked all plaintext and metadata bytes.
- Fresh process, offline: original native method PASS in 0.83 seconds; same member identity, no network interface, 2 MiB exact payload, native owner reference, matching 145-tree census, account stopped successfully.
- Audit verifies all 1,717 regular archive members by size and SHA256, 68 original command streams, 99 selected readback files, original native manifests and all five capture-attempt receipts. It reuses the unchanged original pure schema/census/capture validators.
- Product builds/test reruns during audit: 0 / 0. Full Space destination migration and history semantics remain open.

## Controller failures and correction

The offline reopen completed before Docker inspect. The controller demanded State.Running even though the original container had already exited with status 0. Its original stdout and final native receipt both show success.

A second latent predicate also fails on these original bytes: the offline container's network namespace inode reused the already-stopped owner's inode. Inode and PID numbers are not stable process identities across lifetimes. Actual distinct Docker container IDs plus timestamps show the reopen started after both previous containers had exited; Docker configured network=none, and the native receipt confirmed no IPv4 address.

The correction adds a start barrier before the native binary runs. The host records the actual running container identity, PID and start time, then releases that specific launch. Fresh process acceptance requires three distinct original Docker IDs and a reopen start time after both recorded exits. Native same-account, file, metadata, census, cold/offline, shutdown and method-PASS assertions remain intact. Concurrent owner/member namespace inequality is preserved.

Three focused controller tests PASS (including four negative lifetime cases); the barrier test starts an actual shell child and verifies it cannot finish before host release. One earlier controller test attempt failed because the edit transport had not applied the new helpers; that infrastructure failure does not represent product behavior. The archive auditor was corrected for selected-file extraction (all files are verified in the archive), the original Variants array, and byte-exact LF source transfer; preliminary errors did not run native tests or modify the original evidence.

## Provenance

Controller source: c0482eefb372ecd2cf6ccc91b6a2d5083b75a1c7.
Native source: ea796999d648e27dcb7ad23a0bbd849d35fadc5a.
Artifact: 14972345626, 100141950 bytes, SHA256 3dece544572620b0feb8761d0120258c3344f78b470021d763f329162e54a10c.
Original result SHA256: e959cbb0aa00e9b2d33e73ba920e5fcd24996b5896dc773d0b6bc7904ebc4133.
Original controller SHA256: 4db3dbf17c147ad92d5d7d9d85588acdc3c86c9abcc21fc4a836b5342580902b.
Auditor SHA256: 78e0c11cfd81a3baf5155c804fba37904bb67f7f91138ef4f0b8681008374212.

Private originals remain under C:/Users/DAVID/AppData/Local/SentinelX/anytapy-immutable-evidence/native-file-peer-45501479246-1. No account keys, wallet data or file payloads are committed here. The original failed producer result is preserved byte-for-byte alongside the separate recipient audit. The audit does not convert the GitHub run's status or claim the unexecuted destination migration gates passed.
