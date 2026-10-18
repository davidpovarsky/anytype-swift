# ADR T2-L — UI-first single-active-writer association storage

Date: 2026-10-18

Status: **PROPOSED / IMPLEMENTATION IN PROGRESS — native middleware gate not yet passed**

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
