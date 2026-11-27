# Native FilesV2 durability and retry contract

Date: 2026-11-27

## Purpose and source boundary

`AnyNativeFileDurability` exposes the existing native status and explicit retry routes to engine consumers. It responds to the actual `limited` state observed on the retained synthetic production-cloud account. It does not grant storage quota, remove files, offload the only local copy, recreate an account or repeat an upload.

The production route contract is pinned to Any `8fbd1e819fb132ac0e0a848d2ddf5c5714189b81` with SDK `c1fd59bd8f0ed62471234ec1a65a402d22eab6a9`. The existing qualified native executable is SHA256 `1dc1803c656da2215760477dadd26bf0e829b6ee592e337db6fa0295a6ed9636`.

Source references in that exact native tree:

- `internal/api/files.go`: FileStatus, the three state names and independent cached availability.
- `internal/server/handlers_files.go` SHA256 `a7e299282612adcdb76f2b8f3c64553a92770edcf6ba2bab4ab91e3bb9786658`: GET status, POST retry, native typed errors and the 204 acknowledgment.
- `internal/client/files.go` SHA256 `b64c7160cef4e57246b9dbaf8a40f725f8900164c28d258cb4b9665d41344be1`: original Go client action contract.
- SDK `internal/files/status/queue.go`: KickJob makes existing background work due, clears the limited flag and retains the attempt count. Acknowledgment does not mean that the next network attempt succeeded.
- SDK `internal/files/upload/upload.go`: a real storage-limit response parks background work; the existing slow retry cadence and explicit retry remain native behavior.

## Consumer API

All types are in `PinkhaAnyEngine`; no app-owned source is changed.

| API | Contract |
| --- | --- |
| `AnyNativeFileReference(accountID:spaceID:objectID:fileID:)` | Immutable exact scope. Invalid path-like IDs are rejected at construction. Opaque IDs compare as UTF-8 bytes. |
| `AnyNativeFileDurability(client:)` | Uses the original loopback-only managed `AnyHTTPClient`; the capability remains private to that client. |
| `status(_:authorize:)` | Reads one native file status, verifies the native object/file pair against the scope, and rechecks account and consumer authority before publication. |
| `retry(_:authorizeRead:authorizeRetry:)` | Reads the exact file/object status first, then admits one explicit native retry dispatch with a separate one-shot approval. A valid empty HTTP204 returns an acknowledgment. |
| `AnyNativeFileStatus` | Retains the reference, exact state, cached flag, failed-attempt count and optional private native diagnostic. |
| `AnyNativeFileRetryAcknowledgement` | Identifies the original scope only. It has no durable/cached/completed flag. Read status again to observe progress. |

The read closure must be side-effect-free and fence the current account, space, object, permission and consumer lifetime. The retry closure is independent and may consume a one-shot approval. Neither a successfully fetched row nor a 204 acknowledgment expands the caller's permission.

The adapter calls the shared HTTP client's separate `validateResponse` closure for retry publication. It never consumes the dispatch approval again. A lost account or authority after dispatch yields `writeUncertain`; there is no automatic repeat. An unexpected successful response shape is also uncertain because the action may already have happened. Native typed HTTP errors remain typed native errors.

## State and availability are independent

| Native state | Meaning | What a consumer may infer |
| --- | --- | --- |
| `durable` | Native engine has a verified custody receipt, or the file uses the inline tier. | This status alone does not distinguish inline data from a remote custody receipt. |
| `inflight` | Registration exists; background work is not confirmed. | Do not display completed backup. |
| `limited` | Native cloud storage-limit refusal. | Preserve the local file and present the retry/capacity state explicitly. |

`cached` is a separate Boolean. A limited file can still be fully readable from its retained local copy. A durable file can require a network read when it is not cached. Unknown state names, wrong field types, negative/noninteger attempt counts and different object/file identities are refused; they never become a default success.

The native `lastErr` value is retained for scoped troubleshooting. Both public debug descriptions redact it, together with scope identities. Consumers must not place this diagnostic in analytics or shared logs.

## Cloud quota recovery proof

The retained production test accounts are in the private Oracle evidence root `/var/lib/pinkha-w1-cloud-filesv2-20261127/attempt2`. They are synthetic, independent accounts and do not contain the original user archive. Their credentials are not part of this contract or Git evidence.

The original `attempt4/result.json` records a real native `limited` state and `storage limit exceeded` diagnostic for the original image. That failure remains immutable.

The prepared continuation reopens those same accounts and four already attached files. It first checks cached plaintext and native refusal to offload nondurable originals under OS network denial. It then allows one explicit retry request per still-nondurable file and requires the unchanged native verified-custody, exact remote metadata, range, SIGKILL/reopen, whole-byte, thumbnail, permission and cold Offline gates. No repeated upload, invented quota, changed signature or P2P fallback may qualify as production-cloud custody.

A loopback contract test is not this native quota-recovery proof. Only an actual completed native continuation receipt can accept that boundary.

## Ownership and integration

Wave1 owns this additive engine adapter. Wave2 owns presentation and gestures. Wave3 owns Hanlin, MiniApps, Otzaria, integration and the coherent Apple product.

Consumers should construct the reference from their existing trusted account/session binding and selected object/file identity. Do not accept account or space overrides from tool arguments. Do not use retry acknowledgment as an upload receipt, a durable-state update or permission to clear cached bytes.

The existing bounded native content reader and private download writer remain in `AnyHTTPClient`; this change does not alter their 1MiB range, MIME, byte-count, digest, output-path or cancellation checks. It does not claim native runtime, Apple or app acceptance from component tests alone.
