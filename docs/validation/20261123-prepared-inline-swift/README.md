# Bounded prepared inline-file Swift client

The new additive client targets only the dedicated native inline-file capability and routes. It keeps the existing object/block client and its eighteen original methods unchanged. General file capability stays zero; this source does not activate a runtime or app feature.

## Verified execution

Oracle Swift 6.4.3 on Linux ARM64 compiled the complete current PinkhaAnyHost package, its test target, PinkhaAnyEngine, PinkhaAnyIntegration, PinkhaKit and the exact resolved dependencies. The original Package.resolved bytes remained unchanged.

Twelve distinct new client methods are qualified: ten unchanged passing methods retained from the first execution, plus two actual passing methods from the narrow Unicode fixture repair. The first execution remains FAIL (eleven passing methods, one failed method with two assertions). Its original source and raw log are preserved.

The first source transfer passed raw Unicode through PowerShell's native stdin encoding, replacing the Hebrew and emoji fixture characters with question marks. The product implementation was unaffected. An ASCII-only JSON transport with Unicode escapes now reconstructs exact UTF-8 source. Only the failed byte-bound method and the affected exact-Unicode-input method changed and were run again. Every other method body and all shared helpers remain byte-identical; no prior object/block methods were selected.

AUDIT.json binds all three current files, original logs, exact dependency revisions and the source review. The four compressed source inventories recover their complete original bytes. The 184 existing source/manifest inputs match the frozen base commit exactly; the only current additions are the client and two test files.

## Behavior

- Inline payloads are bounded to 0 through 4095 bytes; metadata is preserved as exact UTF-8, including empty name and MIME fields.
- Intent identity is stable across changed input; content/specification and plan digests expose collisions instead of silently allocating a replacement.
- Dedicated capability parsing binds account, Space, persistent store, version and the explicit inline bound.
- Every receipt binds owner, payload root, file ID, signed row change, content digest, size and specification.
- Two durable commit stages retain all reserved identities. Each stage rechecks authority and current store.
- Lost acknowledgements are surfaced. A subsequent call reconciles the same intent before attempting any remaining stage.
- Deleted, modified and obsolete outcomes never recreate or promote a current success; nonprogressing stages stop without a retry loop.

The transport controls use an explicit modeled transport. They do not claim native or HTTP execution.

## Pending live gate

NativePreparedInlineFileHTTPTests/testRealNativeInlineFilesRoundTripThroughThePublicSwiftClient is compiled but was not selected in the portable runs. It requires a fresh owned native loopback server handshake; an absent server fails instead of skipping. It will exercise zero and 4095-byte files through the real public Swift client, then supply exact nonce-bound observations for independent native Get/Open and durable-status checks. Both the original XCTest terminal and the native harness terminal are required.

Apple, physical device, network file synchronization, large/chunked files and full Space migration are not proved by this evidence.

## Explicit live-test registration follow-up

The separate registration-guard receipt now proves the live HTTP method is absent in default discovery and present only under PINKHA_PREPARED_INLINE_HTTP_ACCEPTANCE. The entire original test body and twelve qualified portable controls are unchanged. Both audit-plumbing failures remain original evidence; successful compiler/discovery results were retained without rerunning any product tests.
