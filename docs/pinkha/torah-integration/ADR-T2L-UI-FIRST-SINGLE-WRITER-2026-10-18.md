# ADR T2-L — UI-first single-active-writer association storage

Date: 2026-10-18

Status: **BLOCKED — native middleware cold-relaunch gate failed; dependent UI stopped**

Decision scope: the owner-approved limited acceptance track `T2-L → T5-L` on
one actively writing device. This ADR does not replace or relax the original
multi-client T2 gate in `ADR-T2-STORAGE-CONCURRENCY.md`.

> **Risk banner:** this mode is not safe for two independent clients that add,
> update, or remove Torah associations from stale/offline copies of the same
> document property. Ordinary Anytype sync remains enabled, but only one active
> writing device may mutate Torah associations. Full T2 remains
> `PARTIAL / BLOCKED` until its separate operation-record and two-client gate
> passes.

## Decision

For the deliberately limited single-active-writer track, the existing hidden,
Space-scoped `pinkha.torahAssociations` long-text property may hold one
versioned canonical document payload. That payload covers both document and
block targets using explicit `(spaceId, objectId, blockId?)` identities.

This representation is authorized only when all of the following are true:

1. Every local mutation for one `(spaceId, objectId)` is admitted through one
   process-wide service and a true per-document serial operation chain. No
   actor method may leave a read/write transaction reentrant across suspension.
2. Each operation is an individual add/upsert/update/remove request with a
   stable association ID. Deprecated public whole-snapshot setters remain
   throwing APIs.
3. Every mutation performs authoritative native read-latest, pure collection
   policy, native `ObjectSetDetails`, then `ObjectShow` readback. A successful
   optimistic Swift state change is not a successful save.
4. Unknown, corrupt, or future-version bytes fail closed and remain untouched.
   Legacy v1 values are decoded without dropping stable IDs or unknown fields;
   any migration is verified before replacement.
5. The explicit Space and object identity are validated on every read and
   mutation. Block targets must exist in that object. Deleted, archived,
   read-only, restricted, or wrong-Space targets are rejected without falling
   back to the currently active Space.
6. Uncertain acknowledgement is reconciled by reopening native state and
   looking up the same stable item ID before any retry. Blind replay with a new
   ID is forbidden.
7. Block fields are not used as canonical Torah storage. This avoids
   `BlockListSetFields` whole-struct replacement and preserves unrelated native
   block metadata.

## Serialization and lifecycle

- The canonical payload is deterministic and explicitly versioned.
- Every stored record retains target, kind, role, provider ID, external and
  canonical identity, Hebrew/English labels, timestamps, raw provider data,
  unknown fields, and quote provenance when present.
- `source_quote` remains readable; canonical writes use `sourceQuote`.
- Context retries deduplicate only within the same exact target. Source quotes
  remain separate unless the same stable association ID is retried.
- Waiting, saving, saved, uncertain/conflict, and error are distinct observable
  states for later UI composition.

## Mandatory enablement gate

No dependent T3-L/T4-L/T5-L UI may be enabled until a disposable, real
middleware-powered simulator/app probe passes SD01-SD05, including overlapping
mutations, close/reopen and force-relaunch readback, offline local persistence,
Space switching, uncertain acknowledgement recovery, simultaneous scenes or
fail-closed behavior, permission/target failures, and preservation of unrelated
block fields. Portable fakes and compilation are supporting evidence only.

The independent two-client stale JSON add/add probe remains an expected
negative result and is recorded as SD06/T2 blocked evidence, not as a T2-L
failure.

If the native probe cannot establish these guarantees without Heart/protobuf
changes or unsafe user-data behavior, dependent UI implementation stops. The
repository retains useful codecs/tests/documentation, reports T2-L blocked,
and requests an owner decision rather than installing an unsafe fallback.

## Native gate result — 2026-10-19

The bounded implementation and its pre-relaunch native proof completed useful
work, but the mandatory cold-relaunch acceptance did not pass:

- `AnytypeTorahAssociationRepository`, the canonical v2 codec, the process-wide
  document mutation queue, fail-closed decoding, stable-ID reconciliation and
  disposable native probe remain on the feature branch as proof-ready work.
- Each final run passed the five focused repository tests and the one native
  Phase 1 test. Phase 1 exercised document and block targets, all three kinds,
  overlapping add/remove/update work, same-source target isolation, quote
  identity, lost acknowledgement, document close/reopen, background/foreground,
  Space switching, future-version refusal, stale-block refusal and byte-for-byte
  preservation of unrelated blocks.
- Run `39246935214` first proved that a fresh process must recover the wallet;
  its Phase 2 failed immediately with `wallet not initialized`.
- Runs `39286528380`, `39295768767` and `39306273085` recovered the wallet, but
  Phase 2 then timed out inside native `AccountSelect`. The final run also
  completed `AccountPreloadRemainingSpaces` before a real forced host
  termination. Its stage markers reached `state-loaded` and
  `wallet-recovered`, but never `account-selected`.
- The middleware log repeatedly reported `space storage missing` for internal
  Space IDs and left `client.space` in `components start in progress` until the
  bounded 20-minute timeout. The exact validator therefore failed, as designed.

Final evidence is run
[`39306273085`](https://github.com/davidpovarsky/anytype-swift/actions/runs/39306273085),
tested SHA `1a1bb3606721edb1586f77074950d1305d434b40`, artifact
`pinkha-t2l-native-evidence-39306273085` (`12218585026`). Earlier diagnostic
artifacts are `12185619069`, `12206249637` and `12213956450`.

The application DI registration for the unaccepted repository was removed.
No editor, Kit, quote, Notes or knowledge UI was started. This is an intentional
gate stop, not a claim that the portable/native work is production-ready.

### Owner decision alternatives

1. **Preferred:** fix or upgrade the pinned middleware so a disposable
   local-only account can complete `walletRecovery → AccountSelect` after a
   forced process restart, then rerun the unchanged `5/5 + 1/1 + 1/1` gate.
2. Approve a narrowly scoped middleware/Heart API change that makes all native
   Space stores durably recoverable before reopening the canonical property;
   this requires a separate RFC and is outside this branch's authority.
3. Explicitly weaken the product requirement to graceful account shutdown.
   That would be a new acceptance decision and still must not be reported as
   the force-terminate/relaunch PASS required by this ADR.

Standalone SQLite, `UserDefaults`, a hidden-page journal, optimistic cache-only
state, or silently skipping relaunch are not acceptable alternatives.

## Explicit exclusions

- No claim of multi-device or offline multi-client convergence.
- No Heart, protobuf, CRDT, or sync-engine change.
- No standalone SQLite, `UserDefaults`, cache, or temporary-file authority.
- No hidden association pages, schema-option abuse, or rejected BlockCreate
  journal.
- No disabling normal Anytype sync and no personal/production Space probes.
- No promotion, signing, distribution, Otzaria, autolinking, or automation.

## Consequences

T2-L can provide a bounded, recoverable single-device writing experience if
its real middleware gate passes. It deliberately accepts that a second
independent writer can overwrite a stale scalar value. Therefore T2 remains
`PARTIAL / BLOCKED`, and future multi-client work continues under the separate
immutable operation-record RFC and its Tier C/D proof plan.
