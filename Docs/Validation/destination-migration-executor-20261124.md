# Resumable destination migration executor — component proof, 24 November 2026

This is Host orchestration and real-filesystem evidence. The native transport in these focused tests is an explicitly injected fixture. These results do not establish a full Space migration, actual native application migration, atomic final Space validation, or physical-device acceptance.

## Implemented boundary

The validated typed plan binds the exact UTF-8 source account, Space, native witness, capture manifest, semantic plan, destination account/Space/store and logical plan. Explicit coverage must account for every declared source object. Unknown semantics remain blockers. File payload locators remain outside the immutable plan while their size and SHA256 are bound.

A private durable journal is persisted before preparation. The same original native intent, source specification, IDs, signed changes and property revision are used after lost replies and process replacement. It never refreshes a property sequence to force a retry and never substitutes a matching object. Native terminal outcomes remain terminal. An OS lock spans suspension points; directory ownership, non-writable parent namespace, inode identity, regular-file mode, link count and descriptor-relative access are checked.

Initial scalar creation fields and deferred mapped-reference fields are disjoint so later link writes do not invalidate the original creation receipt. The final receipt reports individual current reconciliations; it is not an atomic destination Space snapshot.

## Evidence

- Production source 82065bd1bb0a97fc59715076e5602b5012e21ccb built successfully, job6501b9914ed8, 72.61 seconds, source stable, zero selected tests. Log SHA256 b110db0218dfff8216701d096360b9c77744a97107d59157f651d7d106b8e9fa.
- Original test source ec6844cf03141a3be24c565e10e32bdefca74fcf, job_b6b1742d8cee: six methods executed, one passed and five failed. The injected fixture provided a signed root change CID different from the root object ID. The production receipt validator refused it. Log SHA256 881f5240e6bb82b651d78dfe1481b00f42060eff239de0f7f742e39e390fc442.
- Only the fixture's root identity was corrected at d3324001e29139c0b0a31b34a093bb96fe8c95b2. All four production files stayed identical. The five affected methods passed, zero failures/skips, job_ca60ffc8bb45, completed 19:42:33 UTC, 8.388 seconds total / 1.099 seconds tests. Log SHA256 da0a702d5bda28c7436b9e5b5ee4cb220dfc02bc587e3a96ca51727901e8e183.
- The unchanged coverage/exact-UTF8/owned-target control's original pass is retained. Six distinct methods are qualified; there is no claim that the first attempt passed.
- Original receipts and logs: /mnt/development/projects/evidence/destination-executor-20261124/attempt1-build.*, attempt1-tests.*, attempt2-tests.*.

Qualified control areas: coverage/decode/exact UTF-8 identity and owned targets; lost preparation reply and cyclic references; original property-revision checkpoint before dispatch; inline and 2MiB file resumption without original paths; native terminal and changed-plan refusal; namespace ownership, live lock, root replacement, source withdrawal and checkpoint corruption.

## Subsequent closed-owner correction

The accompanying source change separates part owners from property owners: parts require a type created by this plan; properties can target a created type or collection. The focused positive-type/negative-collection control also confirms collection-owned properties remain admitted. It passed as the sole selected method at source dbf69774ab5055e45b03df0395c9cf3050b9eff1, job_4c663e190036, completed 19:53:28 UTC. Build 95.95 seconds / test 0.022 seconds, zero failures/skips, source stable. Original log SHA256 f69d6ec8b32889d208d6fe49f992fd1e885da136851cbe2dcd0c707083564e22; receipt /mnt/development/projects/evidence/destination-executor-20261124/attempt3-part-owner.json. Seven distinct focused methods now have qualified passes across the retained exact source stages; prior failures remain explicit.

## Actual Apple result, retained separately

The original combined native artifact built successfully at source 44cb86a86d5eddb481fc09f1eadf07b838c5c794. The actual XCTest consumer 0bba1974a464af739e439a51039924f99256b96b, local run 76fb2036-1f76-4c3a-92a2-6a3bf2a67926, built and executed one method, which failed with HTTP400 type.not_a_type. Type, collection, atomic six-record part and type-owned property phases completed; the collection-owned property preflight failed. Full-file and reopen phases were not reached.

Exact source diagnosis: the generic prepared-definition route calls requireOwner, whose default is the type-only route. SDK typesAPI.Properties already supports both type and collection owners, and collection properties delegate to it; no SDK change is justified by this failure.

After the actual suite failure, the exact owned simctl diagnose process was interrupted following a documented idle grace period, allowing xcodebuild to finalize. Original xcresult, summary, attachments, logs and operator action are retained at /Users/m1/builds/anytapy-prepared-components-0bba1974/consumer-evidence. Terminal receipt SHA256 cc27d5de28fe0606ceebfbb8b43f6ef83e8d4d5a7e234161085218d2cbbbf92e. Owned simulator cleanup succeeded, owned processes absent, source and compiled products unchanged.

Asana C milestone 1220878609413023 records both results and leaves phase C open.
