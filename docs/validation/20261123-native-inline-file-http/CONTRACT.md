# Prepared inline-file HTTP contract

This separately selected candidate exposes the existing prepared native inline-file service through the public Any HTTP boundary. It adds local file-status publication after the exact reserved file row commits. The frozen v11 manifest and patches remain separate.

## Capability and routes

All routes use the existing engine gate and space resolution under `/v1/spaces/:spaceId/pinkha/migration`.

| Method | Relative route | Operation |
| --- | --- | --- |
| GET | `/inline-file/capabilities` | Read immutable store, account and space binding plus the bounded capability. |
| PUT | `/intents/:intentId/inline-file/prepare` | Reserve immutable native root and row identities from the exact typed source specification. |
| GET | `/intents/:intentId/inline-file` | Reconcile the actual native state without publishing a file-status event. |
| POST | `/intents/:intentId/inline-file/commit` | Perform one authorized native stage using the reserved signed bytes. |

Capability fields are exactly `contract`, `storeId`, `accountId`, `spaceId`, `inlineFile`, `maximumInlineBytes`, `file`, and `networkVerified`. The contract is `pinkha-native-prepared-migration-v1`; the new values are `inlineFile: 1` and `maximumInlineBytes: 4095`. General `file` stays `0`; `networkVerified` stays `false`.

## Exact input

Prepare uses the existing outer fields `contract`, `storeId`, `planId`, `planSHA256`, `sourceKey`, `specBase64`, and `specSHA256`. The route supplies `intentId`. `specBase64` is the canonical standard base64 encoding of the exact original UTF-8 JSON bytes; `specSHA256` binds those bytes.

The inner JSON has exactly five explicit string fields:

| Field | Requirement |
| --- | --- |
| `ownerObjectId` | Current ordinary owner identity, nonempty, at most 256 UTF-8 bytes. |
| `name` | May be empty; valid UTF-8, at most 1024 bytes, no NUL. |
| `mime` | May be empty; valid UTF-8, at most 255 bytes, no NUL. |
| `content` | Canonical standard base64 of the plaintext bytes; empty string represents zero bytes. |
| `contentSHA256` | Exact lowercase SHA-256 of those plaintext bytes. |

Content length is inclusive 0 through 4095. The HTTP decoder rejects 4096 or more bytes before opening the native migration service or reserving an intent. Missing, null, wrongly typed, duplicate, unknown or case-aliased fields fail. Existing strict UTF-8 and JSON validation remains in force. Full-tier files, variants and caller-signed/encrypted envelopes have no route in this candidate.

Commit uses the existing explicit `contract`, `storeId`, `planId`, `planSHA256`, and `fingerprint`. Existing error envelopes distinguish invalid input, immutable collision, absent intent and native authority failures.

## Native receipts and transitions

The response is the original `MigrationInlineFileReceipt`: the existing prepared receipt plus `ownerObjectId`, `fileId`, `contentSHA256`, and `size`. `kind` is `inlineFile`. Every prepared stage already carries stable nonempty `objectId`, `changeId`, `fileId`, one `recordIds` entry, fingerprint and specification digest. `objectId` identifies the native payload root; the ordinary owner is separate.

Stages are `file-prepared`, `file-root-committed`, and `complete`. An already existing payload root can begin at `file-root-committed`. Each commit performs one native stage. Outcomes retain the native meanings `prepared`, `committed`, `committed_deleted`, `committed_modified`, and `obsolete`. An obsolete reservation is never reported as successful migration.

A preparation or root-only commit does not expose a file row. The final row commit makes the original content available to native `Files.Get` and `Files.Open` and the ordinary HTTP content route. Retries reconcile the same original root, row and file identities. No replacement row, rebase, re-signing or changed authority policy is introduced.

## Local status publication

The native wrapper compares actual state while holding the existing migration lock. A transition from a non-complete stage to `complete` with outcome `committed` schedules one local `FileStateDurable` event with `Cached: true`, the original file ID and ordinary owner ID. It releases the migration lock before invoking subscribers, allowing a callback to reenter native status and read the committed file.

Prepare, root-only commits, refused commits, status reads and already complete retries do not publish a new transition. This is a local live subscription, not a persistent notification outbox. A process failure between durable row commit and callback delivery does not acquire a new delivery guarantee. General file migration and network delivery remain unqualified.

## Qualification boundary

The new native controls select only strict inline input, real HTTP/native lifecycle with reentrant status publication, and pre-reservation oversize refusal. The separately selected Swift bridge requires a fresh nonce-bound handshake, an actual Swift XCTest result, and independent native verification of zero-byte and 4095-byte files, original specifications and exactly two local durable events.

Old object/block controls, earlier inline-native controls and their immutable source bindings are retained as historical evidence. They are not relabeled as a new aggregate run. Linux public HTTP qualification does not establish Apple linkage, device behavior, network delivery, arbitrary file migration or whole-space snapshot consistency.
