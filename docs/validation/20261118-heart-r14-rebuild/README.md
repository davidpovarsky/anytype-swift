# Actual Heart r14 rebuild evidence

Run: https://github.com/davidpovarsky/anytype-swift/actions/runs/44203168617
App control source: b5dc53b799a70269b8082734106d8cd30a99fc44.
Heart source: d98420b1113536afd08cde6de9a5816f6d27ffff.
Reviewed r14 patch: fb96818eb57bd9e0be8da90a11831bcccc7ca8e72cc0a4e9a065500feb7cc077.

The run completed successfully on 2026-11-18 at 00:11:15 UTC. The downloaded
evidence artifact 14382918182 was checked against its GitHub SHA-256
452a6c136c6fcd27919069e7cddb9f227760936a4f0f47c617601103cbef0ec2.
Both original archive layers and the extracted raw build record/logs are retained;
download.json records their byte hashes. Git text conversion is disabled for raw
records so that their hashes stay reproducible.

The actual builder receipt is PASS and records three verified framework slices:
iOS device arm64 and iOS Simulator arm64/x86_64. It explicitly records
native_tests=NOT_RUN_BUILD_ONLY. This receipt proves framework construction and
recorded binary identity, not native tests, app startup, UI, T2 synchronization,
or release acceptance.

The framework itself remains in GitHub artifact 14383247626,
Pinkha-Universal-Verified-Heart-r14, archive digest
7ac88836edc2ee9ff0c7d8cb8943b8e968f0c73b2b94752ba27cebc241c69996.
It was not copied into this evidence directory. Downstream installers separately
verify the downloaded framework and its correspondence to their app source.
