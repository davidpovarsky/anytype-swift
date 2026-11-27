# Original Hanlin message UI integration — candidate source

This milestone adds the original shared message interaction and activity components to the two-engine Pinkha consumer. It is a source candidate. Its changed iOS code and eight consumer projection cases have not yet compiled or run on an Apple host. The first shared application milestone remains the independently frozen SDK385 build until the integration owner admits this candidate.

## Canonical source

- Repository: https://github.com/davidpovarsky/hanlin-ai
- Branch: `codex/hanlin-pinkha-original-ui-20261127`
- Candidate: `f3afac65296e843ced1f7ddd7a55c2452e90b270`
- Tree: `8522f99dab4208bfda087ba0a933dfa50136ce86`
- Actual clean merge parents: cancellation `38528941720d9b4f2da8dce7afbc788c2e554a0c` and original full source `6a6638c314fe04c481eb0a2e29fbeaaafcbb0908`.
- Normal publication: Oracle job `job_f59e2fac64c8`, exit 0, 2026-11-27 01:22:48 UTC.
- Full four-package source inventory: `original-ui-source-provenance.json`, 1,006 regular Git blobs, 249,861 bytes, SHA-256 `2814ea9ee1b90228d03ab6d1d791f243a986db8b628a88ad874c4319c0dcb20c`.
- The entire AgentSDK is unchanged from385. The three Platform cancellation/Composer sources and all cancellation tests are unchanged. PresentationSDK and MiniAppsBridge are exactly original6a.
- The original UI extraction/fix chain includes7d752ba3,7923425b,a6aefeed,f3b55fdd,07f65268,730bbb6d and the original244dc02 launcher lineage. This is a real merge of published sources; no rendered component was recreated in the consumer.

The candidate retains the original explicit-handler source outside the four SDK packages: `Packages/HanlinNativeScriptRuntime/Sources/HanlinNativeScriptCoreSupport/HanlinNativeServicesBridge.m` blob `7bbc804da241fe31d6e860eaedd064a192b97e49` and `AI_HLYTests/NativeScriptRuntimeWireTests.swift` blob `ab113355ec8b87b34bc07216806b08f005dc1c36`. A read-only full-tree query on the published candidate verified these exact blobs. Those files do not become a compiled NativeScript companion merely by changing the four-package pin.

## Consumer changes

`PinkhaHanlinMessageView` composes original HanlinUserMessageBubble/HanlinAssistantMessageBubble, HanlinMessageActions, HanlinMessageActionBar, HanlinMessageActionMenu, HanlinMessageMarkdownView, HanlinMessageSelectionView, HanlinMessagePreviewPresenter, HanlinAgentActivityView, HanlinSourcesButton and HanlinSourcesList.

The consumer supplies only its real host callbacks: current-message copy and selection, native system translation, presentation-owned AVSpeechSynthesizer, local transcript deletion, explicit retry/continue through the original AgentSession, and current-source URL opening. Callback dispatch revalidates the actual mounted presentation and current account/source ownership. Speech completion is correlated to the original utterance so an old completion cannot clear a newer operation.

Retry/continue cannot start during preparation, streaming, Stop, native drain or an unresolved-write barrier. They preserve the unsent draft. Deleting a row does not erase effect receipts or imply native rollback. The existing original SDK Composer and its Stop/Stopping controls remain in place.

The transient activity adapter accepts only one exact session/run and strictly increasing sequence. It projects parsed calls as requests, creates execution-result entries only from actual SDK results, and leaves the run active through provider EOF until the owner observes the original stream/worker join. Citation offsets are admitted only for identical original text; another ordered text part is never assigned a guessed offset. URLs are bounded HTTP(S) values from the actual stream. No provider credentials, raw arguments or business content enter durable receipt logs.

A local output/projection error can terminate iteration before producer EOF. The consumer now joins the original SDK cancellation/native-worker boundary before releasing its run identity in that path. Existing close and account revocation still join both an ongoing Stop and the original consumer.

## Exact dependencies

The original four-package pin is the candidate above. Both original AgentSDK and Platform retain Swift AI SDK `abf0921c6e89e6521cc2b510ff11016b45a0ef08`. The consumer directly declares the original Markdown public API product at `5cbb4b6c950051f98f02a0b0ae56756f5174a9b8`, the same revision already in the original PresentationSDK and the application lock.

TorahInspectorKit remains `9058b489e9acc271b4f8ef69e2ed24648f93b4ed`, owned by Wave2. SDK Collections remains application revision `7b847a3b7008b2dc2f47ca3110d8c782fb2e5c7e` (1.3.0). The native8ac identity and MiniApps producer86 pin are unchanged by this milestone.

The standalone module lock predates the complete PresentationSDK dependency closure and does not yet list its Markdown dependency. It must be regenerated/validated on the admitted Apple source using the existing exact original revisions; this source review does not label that lock as a successful resolution. The primary application lock already contains the required exact Markdown revision. No floating latest dependency is introduced.

## Prior evidence and its boundaries

The original385 cancellation job `job_4526bd29587c` passed five methods/seven cases on the actual Mac. Raw receipt SHA-256 `3f8a291cde1e1f18ae93f0d0703401f11d51633ace90d604f0bba63c1ab25f90`; reviewed proof `c5fd9839ee7e2d2675d1de644230a23703a718af35c30797d5f5b83e923e747b`. Its original source, dependency fingerprints and raw output remain in `/Users/m1/builds/hanlin-wave3-cancellation-0a24e2c13b9b/eof-drain-385289`. The unchanged cancellation blobs support source retention; they are not a new test run of this consumer or the full union.

Original shared message-action/preview metrics source730 ran on the actual iPad simulator host. Receipt `/Users/m1/builds/hanlin-shared-chat-a84ecd6d-20261126/native-receipt-r6.json`, SHA-256 `ad4899d797cbbacc5eaffbc0c6aa0c55438bdb1c07414be5376398e897172632`; result summary `7d78d7ce19d5e87bf0af2809d64b547bddacde76fafb4aed1ec30aba37f27431`; log `99619cd0d2ff3c41b1b540c2c53bd875a241806ece031470a63179930da43410`. The canonical interaction files remain those original implementations. The complete PresentationSDK differs from730 in AnimatedDisclosure and the localization catalog, so the five original methods remain scoped to their original source/dependencies. New integration compile and UI acceptance are required.

The earlier c34 native explicit-handler runtime exercised preserved JavaScript state40→41→42 and three unhandled routeNotFound responses with the exact bridge/test blobs retained above. c34's complete graph is not a suitable consumer baseline. No c34 binary has been relabeled as this complete union.

## New acceptance work

`AnyTypeTests/Pinkha/HanlinOriginalMessageProjectionTests.swift` contains four methods, each with Heart/Any namespace arguments (eight cases):

1. Session/account/run/sequence rejection and the separation of provider cancellation from native drain completion.
2. Parsed tool calls cannot become execution receipts; actual failed results remain failed.
3. Hebrew/emoji citation indexing preserves original text and source identity; unsupported URL schemes and rebinding are rejected.
4. Oversized transient output is bounded.

These are controlled SDK-event projection tests, not real provider/native-write/audio/translation/UI evidence. Status at source publication: **NOT_RUN**. Run them on the same accepted application host as the existing four original-worker cancellation cases where possible. Actual iPhone/iPad interaction, Hebrew/English, appearance, preview/selection/translation/speech, Stop/retry, and account change remain necessary.

## Work still in progress

- Attach the original Sheet/Inspector/Zoom launcher to the actual Wave2 editor/home source view through an additive source-owner adapter. The existing UIKit modal and its ownership fences remain functional; no empty fake workspace or weaker fence was introduced.
- Connect the remaining original rich content/file/Composer capability surfaces through their actual host services.
- A real save-message aggregate planner/binding is being implemented by the MiniApps lane. The current title-only create-page tool is insufficient. Both original save callbacks are absent until body semantics, original-scope root/body/readback journal, partial outcomes, consent and drain are qualified.
- The original full-feature companion owner is repairing native build759e. R5 failed on an actual UNNotificationContentExtension main-actor conformance error, not a runtime assertion. Receipt SHA-256 `b37c8d4f5a69c92cf9c2c5d36068677d9d8f8ffc8046129b5bdd1f8a42e7565b`; log `815c31f3a9849d86342dc85557c73557a1f0132d5260697fd5612d13d28f31c7`. The owner was notified on task1220916800603484. Producer86 remains separately admitted and unchanged.
- No Release archive, signature, physical-device, TestFlight or full SDK06 acceptance is claimed here.
