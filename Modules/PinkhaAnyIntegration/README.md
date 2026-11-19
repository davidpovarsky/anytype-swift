# PinkhaAnyIntegration

Additive bridge between the real PinkhaKit domain and PinkhaAnyEngine. It does
not change the application's active Heart-backed document/session composition.

## Implemented boundaries

- Explicit account/Space ownership; mismatched stores and target validators fail.
- Existing TorahAssociationRepository CRUD, canonical codec, context identity,
  quote instance identity, and unknown metadata preservation.
- Immutable operation storage with replace/remove predecessor observations;
  concurrent live variants are surfaced as conflicts, not silently overwritten.
- Native Any membership and exact object/block checks, including orphan/cycle
  exclusion for block targets. Allowed document Type IDs are explicit.
- Non-destructive, deterministic migration plans for canonical association
  snapshots, with complete Space/object/block mapping, original bytes and
  resumable partial-progress receipts.

The HTTP target checks are sequential reads, not an atomic cross-object ACL
transaction with the claim carrier. This remains a whole-app activation gate.
A migration plan covers associations only: editor content, files, hierarchy,
native derived properties, notes, Hanlin and existing account data require
their own adapters and acceptance.

Run `swift test --jobs 2` from this package. Unit tests use actual PinkhaKit
models and codecs with an explicit in-memory operation store; that is not
proof of native Any sync, iOS UI parity or physical-device acceptance.
