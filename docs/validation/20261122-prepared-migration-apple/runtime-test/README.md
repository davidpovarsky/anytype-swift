# Prepared migration: one new Apple runtime acceptance method

This is an unexecuted Apple acceptance test candidate. Swift 6.3.3 parsed the final source with `PINKHA_PREPARED_MIGRATION_ACCEPTANCE` enabled. No Apple typecheck, C-runtime execution or XCTest method has run for this file. The original portable client controls and native migration controls retain their separate scope.

## Selected method

`AnyPreparedMigrationRuntimeTests/testManagedPreparedObjectAndBlockSurviveOrderlyReopenAndRejectRevokedOwner`

The new file is compiled only under `PINKHA_PREPARED_MIGRATION_ACCEPTANCE`. It requires `.linked == .pinkhaPreparedMigrationCandidateV1` and the actual native version prefix `any v0.5.0-pinkha.prepared.1 `. Root owns the build enum, Package flag, source composition and Apple workflow plumbing. No existing lifecycle test or workflow is modified by this bundle.

## Native path and assertions

The method creates one disposable account, Space and store through the actual C runtime and its managed HTTP transport. An `AnyApplicationSession` supplies a revocable owner lease to the production `AnyNativePreparedMigration` client. No internal transport injection or fake persistence is used.

The object is prepared with a stable plan and source identity. The test checks that preparation alone has not published the ordinary object. It then closes the native SDK/store and restores the same disposable account into the same directory. Two explicit one-stage native `/commit` requests expose `root-committed` and `bootstrap-prepared`, with another orderly reopen after each stage. The original object identity, fingerprint and signed change identity are checked at the corresponding boundaries. Final orchestration uses the actual typed client.

A heading with Hebrew, combining characters, an emoji sequence and a trailing newline is prepared next. Before commit the ordinary editor body must still be empty. Another native reopen retains the exact block reservation; the client commits it. The final reopen reconciles both completed intents without allocating replacement identities or a second block. There are five orderly reopens and six runtime generations in one XCTest OS process.

Current property/body reads and historical records at the original signed change IDs must retain exact UTF-8 text, type, style and hierarchy fields. Root history uses the native `objects` dataset; block history uses `editor_blocks`. A bounded, uncoalesced history list must include each exact original change once, with the native account author and touched record. The list must be exhausted; timestamps are never used as an order or authority fence.

The retained old application owner and lease must reject work after reopening. This checks application ownership, not a native ACL role change. Cleanup drains the owner, deletes the disposable Space, signs out and stops the runtime before removing its local directory.

## Evidence and boundaries

The bounded attachment `pinkha-prepared-migration-runtime-proof.json` contains native IDs, fingerprints, specification hashes, returned history entries, observed text hashes and runtime generations. It contains no authentication response, recovery phrase, managed token or raw private stdout. Its status is `OBSERVATIONS_ONLY_ORIGINAL_XCTEST_RESULT_REQUIRED`: attachment generation alone never means PASS. The original named XCTest terminal and result bundle remain necessary.

The file does not test an OS process crash, injected lost HTTP acknowledgement, network synchronization, a native ACL mutation, inline-file HTTP, or a complete Space import. The frozen service exposes no inline-file route. Native prepared-byte tests and client transport controls remain separately identified; none were rerun here.

The migration implementation owner independently reviewed the staged wire calls and confirmed they match the qualified native fixture. `SOURCE_REVIEW.json` retains the exact source references. `FINAL_GRAMMAR.json` and its empty raw log refer to the final file; the earlier grammar receipt is retained as superseded evidence for its earlier source hash only.
