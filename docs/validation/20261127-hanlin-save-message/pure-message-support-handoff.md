# Pure completed-message Save eligibility

## Scope and actual status

This four-file source checkpoint is based on `78ddc75fc23e39b96f75b0ed894c0b66152e5173`. It adds presentation eligibility using the original completed Markdown parser and the same strict content builder used by the real Save conversion. It does not install the Save binding, issue an SDK invocation, mint a write identity or manifest, authorize a native effect, or perform native I/O.

The new caller API is `await PinkhaHanlinOriginalMarkdownSavePlanner.supportsCompletedMessage(title:markdown:citationCoder:) -> Bool`. The optional citation coder defaults to the original `.default`. SDK owner reviewed all four draft files independently and found no concrete source blocker. After awaiting it, the caller must recheck the installed original session, completed SDK run/message origin and exact message bytes. Actual SDK admission, native consent, account/Space/type/runtime fences, engine-specific preflight and complete native body readback remain mandatory.

## Source changes

- `PinkhaHanlinSaveMessagePlan.validateContent(title:markdown:)` extracts the existing exact UTF-8 content guards: nonempty trimmed title, at most 512 title bytes, nonempty Markdown, and at most 65,536 Markdown bytes. The real initializer retains all original SDK envelope and namespace guards before binding its identity.
- `PinkhaHanlinMarkdownSaveConversion` shares one private `completedContent` builder between the authentic-plan initializer and pure content validation. Its original `Inline`/`Builder` implementation, native block representation, exact source-text checks, citation checks, semantic document validation and bounded sorted-key serialization are retained. Only the real initializer constructs the manifest with the original plan.
- `PinkhaHanlinOriginalMarkdownSavePlanner.supportsCompletedMessage` invokes the original `MarkdownParserImpl` with `speculativeRewrite: false`, checks cancellation before/after parsing, invokes that shared content validator and returns false on any refusal or cancellation. Its existing `convert` implementation is byte-identical.
- Four additive hosted source tests cover parser/conversion agreement and immutable manifest, unsupported structures, exact Hebrew UTF-8 boundaries without an invocation, and cancellation. All 15 prior methods and helper bytes remain unchanged.

## Exact dependency identity

Original parser revision: `hanlin-streaming-markdown@5cbb4b6c950051f98f02a0b0ae56756f5174a9b8`. Original Markdown AST revision: `swift-markdown@25cb61d3482054b09ae76ca4f281b1bfe7fe5a43`. This checkpoint changes no dependency pin, package manifest, lockfile, native engine, Xcode project, SDK router, shared UI or host activation.

## Evidence and remaining acceptance

`pure-message-support-source-intake.json` records exact before/after hashes and literal inverse line operations for all four Swift files. Every inverse was applied to the new bytes and reconstructed its exact immutable parent Git blob. The original builder tail has SHA-256 `1588bd0bb69430e53a81fb6f88e2245daf208c325df86a9235dda69c6d2c8e60`; unchanged planner convert tail has SHA-256 `ee9a7ca3d5def1049294b883c6ff0938770a8e0ed7d771659a83a5432e454546`.

`pure-message-support-selected-source-methods.json` is a successor source-only inventory of 101 methods; it preserves the original 97-method inventory SHA-256 `51d8963702f569a730ba317e828665466aa4be9262c548ea751aaec919296c24` and changes only this conversion suite from 15 to 19. It is not compiled test enumeration or execution evidence. The published commit is resolved by this file's Git provenance, not a self-referential embedded SHA.

Swift compiler invocations: **0**. Swift/Apple tests executed: **0**. Native effects: **0**. New four tests: **NOT_RUN**. Production Save remains unadvertised. The next shared source build must bind the actual new Swift compiler inputs and execute the selected original methods before any compile/runtime pass is credited.
