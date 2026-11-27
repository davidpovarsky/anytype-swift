# Original Hanlin run cancellation — Wave 3

## Source and behavior

Consumer branch starts at Anytype `a089ff29a5c0a7e415aac800844505f099a5561d`.
Original SDK source is `davidpovarsky/hanlin-ai` commit `0a24e2c13b9b54f8dd8db63e6a2221b352d6ed23`, branch `codex/hanlin-pinkha-run-cancellation-20261127`, based on `a86f52f890bfd1f327b6e27cb49c53358a4ae740` (the original 9565 SDK plus the explicit-handler fix).

The original SDK owns run identity, provider stop, dispatcher fencing, preparation/producer join, native worker drain and persisted cancellation transcript. The original Composer exposes Stop and a disabled Stopping state. Heart and Any implement the same optional SDK drain contract through the shared original-worker runner. Drain returns only original invocation metadata, remains usable after account revocation, and never obtains a replacement-account service. A stored receipt does not release an unfinished native lease. Uncertain effects retain the SDK and UI reconciliation barrier.

The consumer keeps Stop pending until both SDK cancellation and its original stream consumer have joined. It preserves a newer run identity and local partial transcript. Hebrew and English labels are supplied to the original Composer.

## Verified original SDK evidence

Mac root: `/Users/m1/builds/hanlin-wave3-cancellation-0a24e2c13b9b`.
`canonical-cancellation-reviewed.json` SHA-256: `ec1e22f2521ced461fbf3cb3098251e4af0c014ff21f2d6400be02dc3391a9a1`.
The adjacent retained review records all proof hashes and six actual dependency checkout HEADs.

- Actual `HanlinAgentSDK` Swift Testing run: **4 methods, 5 cases PASS**, including both account-change parameter cases. These exercise original SDK engine/session/dispatcher with controlled provider/native-effect fixtures.
- Actual original `HanlinScriptUI` target: **BUILD PASS** on the same source.
- All 513 staged AgentSDK/Platform source blobs matched canonical Git before and after compilation.
- Swift 6.4 (`swiftlang-6.4.0.34.1 clang-2100.3.34.1`); Apple Silicon macOS host.
- The initial clone timeout and cache continuation failure are retained as failures. Neither started a credited test run.
- Swift Testing did not emit requested xUnit XML. Named raw test/parameter results are retained; no synthetic XML was produced.

This does not assert whole-app, real native engine storage, iOS UI, Release, or TestFlight acceptance.

## Consumer tests awaiting the shared iOS build

`AnyTypeTests/Pinkha/HanlinHostCancellationTests.swift` adds two methods, each parameterized by `anytype` and `anytype-any` (four cases):

1. Cancel a native worker, revoke the account, then receive original metadata after the actual worker drains.
2. Receive a confirmed receipt while the native callback still holds its lease; drain must remain pending until that callback exits.

Selector: `AnytypeTests/HanlinHostCancellationTests`. These are shared runner/protected journal tests with controlled callbacks, **not real engine writes or UI tests**. The journal remains protected and iOS-only; it was not weakened for a macOS substitute. Consumer compile and these tests are **NOT_RUN** at this source handoff.

## Dependency identity

| Consumer identity | Exact source | Scope |
| --- | --- | --- |
| Original Hanlin | `0a24e2c13b9b54f8dd8db63e6a2221b352d6ed23` | Qualified focused SDK source; consumer app pending |
| swift-ai-sdk | `abf0921c6e89e6521cc2b510ff11016b45a0ef08` | SDK actual checkout and existing Xcode pin; stale standalone module pin aligned manually |
| swift-collections | `7b847a3b7008b2dc2f47ca3110d8c782fb2e5c7e` / 1.3.0 | Existing Xcode pin unchanged |
| TorahInspectorKit | `9058b489e9acc271b4f8ef69e2ed24648f93b4ed` | Base consumer pin, Wave 2 owns replacement/qualification |

The module lock alignment is not a new whole-module resolution receipt. Root App pin already matched the tested swift-ai-sdk. The old SDK06 acceptance and proposed merge-plan Collections/Kit pins do not qualify a changed final dependency graph.

## Original explicit-handler proof reuse

Actual prior iPad/iOS 27 test `HanlinUnifiedHostServicesE2ETests/nativeScriptActionDeclarationsPreserveRegisteredJavaScriptState()` passed at original Hanlin `c34dd6ae752b3ab3ebc001743fc62c72fc48a203`. Its test and native bridge blobs are identical in a86 and 0a24. The test preserves registered JavaScript state across three declaration paths (40 → 41 → 42) and rejects three declarations without handlers. Reuse is limited to these exact bridge/test behaviors; the entire c34 runtime graph differs and is not substituted for the complete consumer packages.

Original proof: `/Users/m1/builds/hanlin-native-action-handler-fix-20261126/validation/paired52-r4-v8/original/paired-product/handler-registration-review.json`, SHA-256 `abb657d1773db427b9fc73fb0d1bd4223198aac5f49478b225eec3276d80b284`. Original `.xcresult`, summary and test log remain at that root.
