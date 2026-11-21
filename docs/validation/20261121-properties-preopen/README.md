# Properties postflight: native store proof before account open

## Why this changes

The earlier simulator postflight selected `UseDestinationArtifacts`, a device-only mode. It therefore failed before the original native Type-preservation method ran. The simulator now retains the original XCTest host and bundle paths and uses normal `test-without-building` installation.

A path change alone cannot establish data loss or data preservation. XCTest may relocate the app data container. The postflight now proves that it opened the same stopped native store before making the existing exact canonical, Tag, link, backlink and Type comparisons.

## Proof sequence

1. Preserve the original source/run/nonce-bound baseline and fixture bytes outside mutable app data before UI. The two existing UI methods must both pass, including owned-app termination.
2. Keep the controlled same-build install: executable/test bundle identity, four stopped-process observations, and byte-for-byte inventory equality across that install remain mandatory.
3. Bind the installed container and middleware directory device/inode identities and exact birth nanoseconds, plus a portable digest of the complete native store inventory.
4. During the normal XCTest host startup, the downstream auth decorator captures a read-only proof before `AccountSelect`. It requires the same account, source/run/nonce, directory identity, birth times, original baseline/fixture hashes and complete inventory. A second capture cannot overwrite or reuse the first proof.
5. The native test requires that proof from its own PID, checks directory continuity through native reads, and compares the complete final canonical bytes, IDs, timestamps, Tag and link sets, link blocks and Types with the original baseline. The controller independently validates the receipt and actual final container identity.

The hook is compiled only with `PINKHA_NATIVE_DERIVED` on Simulator and activates only under the existing Properties postflight flag with all preparation flags disabled. It does not create, restore or repair native data. The native inventory has one 120-second deadline, a 20,000-entry limit, stable file metadata checks and no symlinks. Account readiness retains its existing 45-second bound. No retry or timeout extension was added.

## Portable inventory framing

SHA-256 starts with the UTF-8 bytes `pinkha-native-store-inventory-v1` followed by one zero byte. Every subsequent field is prefixed by its UTF-8 byte length as an unsigned 64-bit big-endian integer. Directory names sort by UTF-8 bytes and contribute `D`, relative name. Files sort by UTF-8 bytes and contribute `F`, relative name, decimal byte count, lowercase SHA-256. Finally the original baseline and fixture names sort by UTF-8 bytes and contribute `I`, filename, lowercase SHA-256. Only the aggregate digest and counts are published; database contents and the private filename inventory stay in memory.

## Validation at this commit

Controller controls passed on Linux using exact Git-matched dependency sources. All nine changed code files were byte-for-byte verified against the isolated Windows worktree after transfer.

```sh
python -m unittest -v test_type_preservation
# 32 passed
python -m unittest -v test_destination_artifacts
# 5 passed
python -m unittest -v test_wave15_batch.BatchControls.test_batch_pass_requires_six_original_preparations_and_fifteen_original_ui_cases
# 1 passed
```

The controls include pure relocation, rejection of a copied/recreated store even with identical bytes, changed inventory and birth time rejection, account/PID/source binding, disabled preparation, exact canonical/native sets, normal simulator configuration and saved parent qualification. They are controller evidence only. Native compilation and the real stateful Properties preparation/UI/postflight journey still require the shared simulator acceptance run; no native PASS is claimed here.
