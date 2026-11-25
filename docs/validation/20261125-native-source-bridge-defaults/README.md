# Actual native source-capture bridge regression

The real core bridge failed before the change and passed after the four-line constructor correction. This qualifies the native Heart source-capture entry point on macOS; App UI, unified Apple slices and whole-space migration remain separate acceptance requirements.

## Actual results

| Input | Original method result | Observed behavior |
| --- | --- | --- |
| Heart `d59568f999c9f1e6aa1d014a743d16999de84006` | 0 passed, 1 failed, 0 skipped | The exported bridge reaches the original native ownership refusal because its request contains zero source limits. |
| Heart `b7454dca344db7d32f0dc7b7eb5aff575b6a2535` | 1 passed, 0 failed, 0 skipped | Two actual captures using two independently minted Full sessions succeed; current checkpoint revalidation and release/close refusal assertions pass. |

The single original method is `TestPinkhaSourceCaptureBridgeActualBoundedDefaults`. Its fixed XCTest-equivalent Go method duration is 2.95 seconds; the full fixed controller, including incremental native compilation and source verification, took 77.705 seconds. The baseline controller took 388.724 seconds. The original Go exit codes are 1 and 0 respectively. A controller status describing successful reproduction does not turn the baseline test failure into a passed product test.

The fixed actual account produced two separate private bundles, each with 143 native trees and 142 captured objects. The retained source-row digest is identical across the two captures. Each manifest binds its own current capture and private immutable files. These are new generated fixture data, not the previous 156-object source.

## Root cause and narrow correction

The original `core/PinkhaCaptureLoadedAccountSource` constructs a `LoadedAccountSpaceWitnessRequest` without `Source.Limits`. The request normalizer fills other bounded caps but does not fill this nested field. The native store boundary deliberately rejects zero, partial and above-ceiling limits before acquiring an owned lease.

The production change imports `localstorewitness` and supplies `localstorewitness.DefaultLimits()` at that exact request constructor. No lower boundary changes, session substitutions, weakened caps, destination permission or synthetic ACK were introduced. The parent commit adds the same actual regression test used on both inputs.

The fixed run additionally proves:

- Original zero, partial and above-ceiling native limits remain refused, three actual cases.
- A normally closed native session cannot revalidate a capture.
- A released capture binding cannot revalidate, and a second release cannot claim success.
- A new Full session can capture again into a distinct immutable private bundle.
- Both original private recovery bundles remain after release.
- The actual source manifest and native immutable rows match the bridge descriptor.
- Destination writes remain explicitly denied.

The fixture opens a real LocalOnly native account and warms the actual original object cache as test preparation. That preparation is not claimed as an ability of the exported bridge to load an absent Space. The gomobile registry cancellation layer and app controller are not exercised by this host method.

## Source and dependency closure

Each complete Heart input contains 2,580 Git-bound files. Both use the exact 580-file native-witness any-sync source `c005bd6cde8d8f8a6007c35f06894f3d89f9f07c`. Complete source manifests are verified before and after each run. Original module files remain unchanged; a private modfile adds only the exact local any-sync replacement. This host closure is the standalone Heart 5e8 lineage, not the full E154/unified producer overlay.

The pinned Tantivy Darwin v1.0.6 release has SHA256 `f0e4fa9bdca31da3b115db4fbe6689c5d6cab771be8f9468e5309c818b3f8add`. The original static library is retained. The already reviewed embedded-LLVM removal produced the same derived library `30c4bc974615e03575c2d1f796ff594f2d0a0f7dd21e5b97ffbd836c99c31788`. All 800 archive members retain native code, data, symbols and relocation identities. The fresh Mac check confirms all 41,786 native external symbol rows match the original library. No native feature was removed and the Go LTO guard was not disabled.

## Process lifecycle and evidence custody

The baseline used original controller `f6bf130b...`, preserved in Git commit ed5f5f09. Before the fixed phase, a separately reviewed controller successor `80f1e25a...` records a positively absent process group and never probes or signals that historical ID again. Two fault controls verify the absent/recycled and unresolved-PermissionError paths. These controls made no native calls or real signals and do not change test acceptance.

The original baseline and fixed result/command receipts are retained here byte-for-byte. Raw Go logs and account/store data stay private on both hosts. Their exact hashes appear in the result receipts. The closed-account archives were checked against every source path, mode and byte before and after copying; public custody receipts record counts and hashes only.

Private originals:

- Mac: `/Users/m1/builds/pinkha-c-source-bridge-limits-20261125`.
- Oracle: `/mnt/development/projects/evidence/migration-final-20261125/native-bridge-limits-qualification`.

The earlier actual App source-review failure remains 0 passed, 1 failed and 0 captures. The constructor change must be composed into the complete unified native source, built for both Apple slices with a matching runtime profile, and then accepted through the app's ordinary review/close/recapture flow. Full 156-source migration, unsupported layout/derived-field/collection semantics and final destination comparison remain open.
