# Actual Heart source review: UI candidate

This checkpoint adds one separate original-app UI method:
PinkhaStage1AcceptanceUITests/HeartSourceCaptureAcceptanceUITests/testActualHeartSourceReviewCloseAndRecapture.
It is referenced by the original UI project's build phase, file reference and Tests group.

Scope: open the real engine menu in the existing Heart app, request production source capture, compare actual account/space identity and native census, observe concrete semantic blockers, close through the throwing native lifecycle, then capture again with a new request ID and close. It calls no native capture/session API itself, changes no user data, and does not qualify destination writes, full-space migration, history or permissions. The source view moves identity and summary counts before long detail lists and exposes stable accessibility values; no admission rule changes.

## Actual qualification so far

- Both changed Swift files passed swiftc -frontend -parse.
- git diff --check passed.
- PBX source, build-file and group references were checked.
- Original E methods and their fixtures are unchanged.
- **Apple typecheck and actual UI execution are pending D's next already-required original-app/UI increment. No UI pass is claimed.**

## Sequential original-account handoff

Use only E's actual fresh disposable account, after E reaches a terminal checkpoint and seals its original receipts and private account backup. Do not run concurrently with E, extend the original fixture deadline, silently recreate an account, or use a production recovery key. The independent controller must verify original native profile, app/UI product identities, exact owned device, source/run/attempt/nonce binding, original freshness deadline and private witnesses before invoking the method.

In addition to the original exact PINKHA_SEMANTIC_MOUNTED_{TESTING,FIXTURE_JSON,SOURCE_SHA,RUN_ID,RUN_ATTEMPT,NONCE} and PINKHA_SIMULATOR_UI_DISPOSABLE=1, provide:

- PINKHA_HEART_SOURCE_CAPTURE_TESTING=1
- PINKHA_HEART_SOURCE_CAPTURE_FIXTURE_SHA256: SHA-256 of the exact fixture JSON bytes passed to the test
- PINKHA_HEART_SOURCE_CAPTURE_HANDOFF_SHA256: SHA-256 of the independently validated sealed handoff receipt
- PINKHA_HEART_SOURCE_CAPTURE_DEADLINE_EPOCH: the original fixture's deadline, never a newly extended deadline

The test launches the ordinary English Heart app with the mounted observer disabled and no phase/deep link. It does not dismiss a new middleware warning: E must have accepted the original exact warning already. It requires a real full native source census and nonzero mapping requirements, because current semantics are still incomplete.

The independent collector must retain the original xcresult, UI JSON/screenshots, actual app-private Application Support/Pinkha/NativeSourceCaptures directories, full source manifests/files and owned account before any simulator cleanup. It must join the two UI capture IDs/fingerprints and account/space/counts to those real retained bundles, and preserve failures. Private source data and account secrets remain outside Git.
