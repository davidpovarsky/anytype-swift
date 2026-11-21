# Heart authorized operation read adapter candidate

This opt-in package decodes the additive pinkha-authorized-operation-read-v1 Heart RPC into the same PinkhaKit types used by Any. No existing app dependency or default native runtime is changed.

The generated public protobuf source is the actual output of protoc 3.21.12 and SwiftProtobuf 1.32.0; its input and tool hashes are recorded in docs/validation/20261121-heart-authorized-read-swift/. The package preserves the exact binary operation envelope and verifies its domain, version, field framing, canonical observed set, logical/content identity, byte-exact account/Space/author/target bindings, and all native provenance. Heart remains responsible for signed-history, current ACL, target eligibility, and complete closure authority. Swift does not claim to reverify native signatures.

A session is one adapter-owned native account/Space lifetime. The owner must synchronously invalidate it before closing or replacing that lifetime, including reopening the same public IDs. Cancellation and scope are checked before and after the byte call. UI owners call publishIfCurrent on the main actor immediately before publication; it has no suspension between the final check and publication.

The transport protocol is a byte boundary, not an account authority implementation. The production Lib bridge, concrete account/Space owner, positive generated native account fixture, and iOS runtime journey are separate qualification steps. This package alone does not activate a native capability or full T2.

The 14 new tests cover canonical/transport validation and adapter lifetime behavior. The archived Windows command proves syntax only; it is not test execution, Apple compilation, native account proof, or iOS proof.
