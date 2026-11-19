# T2 application, settings and target leases

This candidate is based on `cab855d95c74f4f45eeacd07a6b1b6334151c138`, including the separately reviewed remote-tree commit-guard correction. The application capability stays OFF. This record documents source composition and controller execution; pinned native execution is required before accepting the behavior.

## Durable boundary

The application service now lends its current application under its existing lifetime read lock. The handler releases that lock on every return. It acquires this lock before loading the Space or objects; subsequent scope checks read only the request context and active lease flag. They never recursively call `GetApp`, which could deadlock behind a pending Stop writer.

Target loading completes before cross-object locks are acquired. A native Space adapter then supplies the existing reserved settings object from the actual object manager. The code does not rebuild a second settings object with an independent mutex. It locks settings, reconstructs verified settings history from genesis, locks the target SmartBlock, and checks both the current native State and exact live cache object identity. Same-ID stale or closing objects cannot authorize a new write.

The lock order is application lifetime → settings → target → private operation tree → ACL. The native storage guard retains the target/settings lease across the actual `Storage.AddAll` transaction. On success it releases the ACL lock and then the target/settings lease before head-update construction, broadcast and projection recovery. The existing durable-commit witness and exact retry semantics remain intact if a later step fails. Failure, cancellation, idempotent retry and collision paths release each borrowed lease once.

Verified historical `ObjectDelete` and `SpaceDelete` deny a new local target operation even when a later snapshot omits an earlier deletion and asynchronous target cleanup has not run. Native permanent object deletion is distinct from current target State: a restored block or reinstalled template is judged by its live State. Local retries still require a currently available target; historical remote replay remains governed by the unchanged historical signature/ACL verifier.

## First private root

Only a canonical Add may initialize an absent local private history. A first Remove or Replace with valid syntax but unavailable predecessors returns history-unavailable and leaves the root absent. Reads, rejected request shapes and canceled requests also cannot create it.

The private object-cache creation branch requires a request-scoped root-creation guard bound to the native Space and canonical root. That guard checks the active application/target lease and current writer ACL around the real `CreateTreeStorage` transaction. The subsequent private registry open happens after the ACL read lock is released. This avoids wrapping generic PutTree and recursively taking its ACL lock. No generic import or direct root-creation bypass is enabled.

## Evidence scope

- The original pinned Heart tracked files were extracted with `git show` and checked against every existing before hash. The updated registration patch was actually applied. All 65 composed files matched the updated source inventory; the only changed tracked patch output is `core/block/object/objectcache/tree.go`.
- The registration → RPC → account fixture hash cascade was refreshed. The actual account fixture patch was applied and its resulting Go files checked. `native.apply_sources`, `rpc.source_inputs`, `account.fixture_inputs`, `account.verify_fixture_copy` and `clients.source_inputs` passed.
- Remote Go 1.25.6 `gofmt` parsed/formatted the 28 changed Go source files. This is a formatting check, not execution with the pinned Go 1.26.5 musl runtime.
- The Linux controller suites passed 108 tests, plus all 6 RPC controller tests, with zero failures/errors/skips. Required native lifecycle events have negative controls for individually missing, failed and skipped outcomes.
- Component regressions exercise real native signed storage with controlled settings/target mutexes, cancellation after preparation, and lease release before a deliberately failing head update. Registry regressions exercise actual settings storage/history, reserved-object identity, cache close/replacement, target changes after preload, one borrow/release, application locking, and a real absent private root after missing-guard rejection.
- The generated account fixture now includes syntactically valid first Remove/Replace rejection and root-absence assertions. These assertions require the native account lane to execute; controller success does not stand in for that execution.
- The seven native-client scenario fixtures and original lost-reply acceptance remain unchanged. Full T2, iOS, causal display order and parity with the separate new engine remain outside this source-only result.

The accompanying JSON records source identities and exact controller log hashes. Independent source review is recorded separately. Native run receipts must retain their original test events and source hashes; this document does not mark pending native work as passed.
