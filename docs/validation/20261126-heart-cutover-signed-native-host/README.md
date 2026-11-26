# Heart explicit legacy cutover: actual signed native host

This checkpoint qualifies the inactive native host against actual encrypted SyncTrees, signatures, ACLs and SQLite. It does not register the new private object, expose an RPC, change the production Heart repository, or claim App or independent peer acceptance.

The original native invocation ran eleven methods: the four new host cases and seven affected original v1 authority/commit-lease cases. Ten passed. The two-author partial-phase case failed because its test constructed a noncanonical seal with Imported entries but no corresponding metadata-backed ImportRecords. The host correctly rejected that request before the intended incomplete-history predicate.

The separately preserved test-only correction includes only metadata-backed imports in both paired seal lists, and explicitly proves CanonicalBytes succeeds before calling Append. The actual pending v1 claim remains present. The original ErrIncomplete expectation and byte-identical before/after refusal checks remain. Only that failed method was rerun: one passed, zero failed, zero skipped; production source is unchanged from the original eleven-method run. The original failure is retained verbatim.

Qualified new paths include real two-author claim bindings without coalescing physical provenance, begin/import/seal phases, partial import refusal and resume, exact legacy-byte divergence, native unlink with no legacy resurrection, same-OS reopening, current ACL and retired component-lease refusals, and a durable lost-ACK retry. The property lease is a component fixture. The actual application account/property lifetime, registry, generated RPC, remote peers, offline convergence and production repository are still required.

The test payload originates in the actual shared Swift canonical codec and cutover planner. Its first successful compiler invocation was initially classified as FAIL because the collector searched the wrong SwiftPM binary path. The separately pinned qualification identifies the original binary and exact 71-source closure without rebuilding or rewriting the failed receipt.

The production adjustment in this checkpoint holds the actual ACL read lock while constructing and replaying the metadata history candidate, checks current permission at that locked boundary, and retains all original v1 append behavior. Raw private account keys, source documents and fixture payloads stay in private evidence directories; tracked evidence contains source, commands, hashes and original test outcomes.
