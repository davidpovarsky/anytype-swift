# Pinkha Any engine adapter

This package targets the actual Any v0.5.0 HTTP API (source commit
`88fae2e5ae7d0f46d6707567a3123081faa8de9a`). It is a new storage adapter,
not a replacement for the app's Heart services or a claim of completed migration.

## Preserved behavior

- The canonical binary T2 operation identity matches the pinned native Go golden
  vector at app source `90fcb6033ca4f8aecf8e04d4959cf06fb104adf9`.
- Payload is opaque bytes. Provider metadata, unknown canonical JSON fields,
  Hebrew, licenses, provenance and quote-instance identities are not normalized.
- A hidden derived bundle holds immutable, undeletable records, with the native
  creator stamp. Slash-containing legacy physical IDs have a reversible 128-hex
  record-key encoding. Schema is verified after install/adoption.
- Distinct payloads under one logical operation ID remain separate claims.
  Every variant is quarantined from the live fold, even if it names another
  target. Observed remove retains unobserved adds; concurrent replacements retain
  both successors. Referencing a tombstone never resurrects previous content.
- Same-repository writes are serialized, exact retry returns the existing claim,
  and an ordered mismatching operation ID is refused.
- HTTP 200 is inspected for top-level and per-page rejections. A write is read
  back before acknowledged to the host. Lost replies reconcile by the same ID.
- Literal-loopback HTTP only; redirects are refused. Account checks before and
  after each request detect an account switch. Hanlin/host consent is still
  supplied explicitly by the caller before dispatch.

## Deliberate limits and remaining engine work

These are acceptance boundaries, not implicit successful fallbacks:

1. This package uses a complete bounded native snapshot (maximum 10,000 claims
   per space and 256 variants per operation). It fails on overflow instead of
   returning an incomplete projection. Large-space indexed target queries need
   a native atomic snapshot across the target and full logical-operation groups.
2. Serialization is per repository instance. Generic HTTP does not provide a
   cross-client transaction spanning collision lookup, target liveness, block
   reachability and claim append. The HTTP layer does not validate canonical
   content hashes or observed-reference causality for unrelated callers.
3. Native creator stamps and change IDs are not the previous custom host's
   independently verified signed ACL-head receipts. Actual SDK authorization
   applies, but equivalent receipt/target-lock guarantees remain separate work.
4. Account pre/post checks detect changes; they cannot atomically bind a server
   request to an account while an independent process switches the engine.
   Production use requires the app to own the embedded/managed engine lifetime
   and hold its account/consent fence through writes.
5. A derived bundle is permanent for the space lifetime. This package is
   exercised only in disposable spaces. Schema changes require a versioned
   migration and fresh parity proof.
6. Native computed Torah properties, the existing block editor, durable text
   anchors, file migration, two-device ACL/revocation behavior, all iPad UI and
   the complete Hanlin host are not implemented or certified by this package.
7. Readers discover an existing bundle with GET and revalidate its schema; they
   never create or heal it. Call install() explicitly from an authorized setup
   flow before appending into a fresh space.

The original Swift and native packages remain intact on the isolated port branch.
No automatic migration of existing user spaces occurs.

## Validation

`swift test --jobs 2` exercises identity, native-author mismatch, malformed records,
conflicts, observed remove, concurrent replace, bounds, schema adoption and HTTP
partial failures. These are portable component tests.

The `PinkhaAnyEngineProbe` executable calls the real release engine. It requires
an already-created disposable account and space:

```text
swift run --jobs 2 PinkhaAnyEngineProbe --endpoint http://127.0.0.1:42166 --account-id <disposable-account> --space-id <disposable-space> --allow-disposable-writes
```

Its JSON receipt labels the scope as a single-process HTTP component proof.
`--mode verify --expected-claims <comma-separated-physical-claim-ids>` reads and
compares an existing fixture for process-restart or second-peer evidence.
A repository re-open in the exercise is not an engine restart; actual restart and
network convergence are the external harness's responsibility.

Public source references:
- Any `internal/api/typedatasets.go`, `bundle.go`, `upsert.go`, `query.go`.
- Any `docs/03-api.md` runtime datasets, shared datasets, bundles, idempotency.
- Existing `Tools/TorahNativeOperations/overlay/core/block/editor/torahops/`.
