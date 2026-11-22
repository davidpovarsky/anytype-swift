# Heart V7 native counter acceptance — 22 November 2026

Run [45027606300](https://github.com/davidpovarsky/anytype-swift/actions/runs/45027606300), attempt 1, executed on the exact reviewed source `7431d8fd3b3e9f4a3ef167dbb3b6c995ab972508`. It completed SUCCESS at 13:34:25 UTC. The original Go 1.26.5 darwin/arm64 package compiled on Xcode 27.0 (27A266a), then exactly two previously unresolved child cases passed once. No previously passed test was rerun.

| Case | Native result | Full observations | Counter |
|---|---|---|---|
| ActualLocalZeroCounterAccepted | PASS | First observation changed; second stable match | 0, unchanged throughout |
| NativeComputedRemoteCounterAccepted | PASS | First observation stable match | 3, unchanged throughout |

The first local-counter observation recorded an actual difference in the complete persisted `state` row: fields `nh` and `oh`. The unchanged observer returned the exact Changed error. The reviewed bounded fixture admitted one new complete observation, which returned PersistedMatch with no row differences. This establishes the observed row change; attributing its scheduling to the asynchronous native head updater remains an inference from original source. No fields were omitted from comparison and no failed result counted as acceptance.

## Retained evidence

`Heart_45027606300_artifact.zip` is the complete, unmodified GitHub artifact 14756238741, downloaded once: 2,598,552 bytes; SHA256 `2145510a2b7619daae6d7d7cfd47c12351a39033af400c7ea1f94611be2c018f`. Its digest matches GitHub and ZIP CRC passed. It contains all 39 payloads plus their original index, including full raw test2json, the declared source closure, compiler commands and all three raw snapshot receipts.

Independent intake rehashed all payloads, every encoded snapshot row and complete counter byte string, checked all 15 original command receipts, and required exactly two distinct child starts and two PASS terminals. Every observed transaction committed and reported Done; each snapshot contained 11 recorded rows. Scope and counter bytes stayed identical within each case. The runtime reported native process ID 16152 consistently; this is not an independent process-launch observation. Native executable bytes were not included in the original artifact, so its stable binary hash remains a runner observation.

For reproducible intake, extract the ZIP into a sibling `extracted` directory and run `python verify_heart_artifact.py`. This reads retained results only; it runs no Go compiler, native test or iOS application. `VERIFIED_RESULT.json` is the resulting intake summary.

## Preserved prior results and remaining boundary

The 18 passing V6 cases and the earlier strict 12 are excluded from this run; the original 13 unaffected native cases also remain source-bound to their earlier execution. The full prior evidence and source ancestry remain in their existing packets. No claim is made that all historical cases ran together on this commit.

This acceptance covers the genuine disposable LocalOnly Heart fixed-schema observer controls. Production schema creation/repair, original authentication integration, the Apple SDK consumer, iPad editor process relaunch, native body equality, COMMIT/identity acknowledgement and broader product acceptance remain separate open gates.

The Windows host became unresponsive during artifact-intake preparation. The single download and verification therefore used the GitHub connector and the analysis workspace; the unchanged full archive is persisted in this commit. No second workflow attempt or download was started.
