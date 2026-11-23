# Read-only handoff to the existing SDK23/32 and ACK7 owner

The canonical native run 45219628237 passed on Anytype source 988f451959af1a40d1bc49bd6ed3798a730f5e37 with Hanlin SDK pin 32da9e314e22bbf22391fcf8902302acfbb281e2. No additional native/UI test is requested by this handoff. The shared-editor worktree and its test ownership remain untouched.

## Available original products

GitHub's actual cache readback identifies cache **10983997745**, created 2026-11-23 at 17:25:24 UTC, 3,209,544,441 bytes, with exact key:

    pinkha-ui27-compiled-v2-arm64-xcode27.0-Debug-Anytype-75b252f662811f1fe136b7c1df99145dd2e1b7416d226523046ca22d898cc0e6-988f451959af1a40d1bc49bd6ed3798a730f5e37

Its ref is refs/heads/codex/chatgpt-wave15-canonical-hanlin-20261123. The original workflow retains both native/UI Build directories, SourcePackages and the named compiler caches. The original evidence artifact contains the product inventory and source-input inventory; the binary products themselves are in this cache, not in the 16.5 MB evidence ZIP. No cache was downloaded for this handoff.

The authenticated product inventory observed the original Anytype_AnytypeTests_iphonesimulator27.0-arm64.xctestrun (15,617 bytes; SHA256 44479fe745a1f396de2dc04c1d4b3e9c2434fa33c69baffb4530e8bd0800abbe), AnytypeTests binary (27,692,240 bytes; SHA256 f48d67536c55743bcc5407e8f4059c6ac2977ad5016b9e34d66a780e389428ca), App shim and debug dylib. Their exact entries are in reuse-handoff.json.

## Source compatibility actually checked

Four suite files were read from immutable Git at original App75bd, canonical988f and current owner shared283c. The old App75bd and current shared283c suite files are byte-identical. Canonical988f differs only in the pending23 tag annotations: eleven table methods, ten focus methods, two related-read methods. Removing exactly those annotations reproduces canonical bytes. All test bodies, assertions, argument cases and all seven ACK methods match. The four canonical SHA256 values also equal the original native run's actual source-input inventory.

The synchronized AnytypeTests source membership includes these files and does not exclude them in the project exceptions. This proves source membership, not registration in a loaded test binary. The native build succeeded, but selected only the fixture preparation and reused unchanged incremental test inputs; the four individual suite filenames were not emitted as fresh compilation records. No exact23 enumeration was performed by this lane.

## Reuse is not yet admitted

The original inventory deliberately says OBSERVED_PRODUCTS_INVENTORY_NOT_BUILD_PROVENANCE, every_entry_build_origin_verified=false and build_reuse_enabled=false. Those limits are preserved. The current cache is a possible source for a separately reviewed focused test-without-building route, not a ready acceptance substitute.

The existing external-owner route is pinned to different App75bd products. Canonical988f also changes the SDK package graph and includes eleven listed source-tree path differences; only the four suite bodies were proven equivalent here. Complete dependency/module compatibility, exact descriptor selection and actual registered methods must be qualified before borrowing this cache. The exact23/0 gate and existing seven-method exclusions must remain intact; do not replay already qualified cases or weaken registration checks.

Fresh GitHub readback showed external-owner run 45223678862/1 on shared283c completed FAILURE at 17:21:38 UTC. Its failed step is the exact23/continuation lane and the outer failed log reports “Original lane has not passed.” This lane did not acquire the external owner's artifact, interpret uninspected internal counts, repair their code or dispatch a retry. The owner retains diagnosis and next-execution responsibility.

This handoff performed only Git/JSON/log/cache-metadata reads. It ran no compiler, product test, simulator, binary enumeration or duplicate watcher, and changed no shared/editor branch or worktree.

## Firebase support-closure pointer for the existing owner

The owner's later authenticated result (Asana comment 1220832184215336) identifies missing FirebaseCore and FirebaseMessaging during dependency scanning; all SDK23/32 and ACK7 product methods remain NOT_RUN. Their source-only support-closure work remains authoritative.

The already acquired successful canonical build log records **19** explicit Clang module maps in its Anytype app driver, including CAtomic. The owner's original App75bd AnytypeTests driver has **18**. These are distinct commands and are not interchangeable. compile-support-handoff.json preserves the exact original canonical commands, line numbers, 19 map paths, Firebase header paths and source hashes.

FirebaseCore.modulemap and FirebaseMessaging.modulemap are referenced under build/ui27-derived/Build/Intermediates.noindex/GeneratedModuleMaps-iphonesimulator/. Public headers are referenced under build/ui27-derived/SourcePackages/checkouts/firebase-ios-sdk/FirebaseCore/Sources/Public and FirebaseMessaging/Sources/Public (with related Installations and CoreOnly paths recorded). The original workflow retains Build and SourcePackages in exact-source cache 10983997745. There are **zero** Firebase map/header entries in the captured Build/Products manifest. The individual cached header/map bytes have not been acquired or independently hashed.

Both original App75bd and canonical988f Git locks, plus the actual canonical resolved-pin receipt, pin firebase-ios-sdk **11.8.1** at **6318278e8e64d21f0fdcc69004395e4d34048aaf**. The complete lock files have different hashes; only this exact dependency lineage is asserted. The existing owner can use these pointers while retaining their original App/native binaries and exact23 gate. No support-closure implementation or additional execution was performed here.
