# Expected network identity contract

The host receives public let AnyEmbeddedSession.expectedNetworkID: String only after a successful native bound start. The value is associated with that session generation and comes from the exact native configuration used for that boot. It is not current native account authority.

## Admission

A navigation or imported-content owner passes this independent expectation, the current expected account ID and the actual data client to the account/run binding API. The returned tuple must match the expected account and network exactly and carry the current native run identity. Existing lease, READ membership, cancellation, generation and revocation checks continue to apply.

Network identities are nonempty valid UTF-8, at most 4096 bytes, with no ASCII control/whitespace byte <= 32 or DEL. They are not trimmed, case-folded or Unicode-normalized. Native equality uses exact string bytes. Consumers performing identity comparison must preserve the existing byte-exact checks.

A successful boot never returns an optional identity. A failed boot cannot expose another already-running engine's identity. A later start does not alter a previously returned session value. The original native singleton/concurrent-start contract is unchanged; the Swift owner serializes its own lifecycle.

## Transport and lifecycle

The additive C result contains an exact NUL-terminated 4097-byte network_id buffer. The common core rejects an unrepresentable identity before startup, so the identity is never truncated. Existing C result layout remains unchanged.

The unified Swift path calls the new gomobile bridge; the standalone path calls the new C export. Both require matching compiled native symbols. The existing source/profile identifier must be replaced by W3 only when it produces the actual successor unified manifest and framework. A source-only commit cannot claim a binary identity.

The native bound-start path resolves with config.LoadNodeconf and config.NodeconfNetworkId. It applies the original official/custom push/P2P defaults before replacing the config's nodeconf field with the resolved bytes. server.RunWith receives those same bytes. No network connection to the official network is needed to resolve its identity; account-free runtime tests use isolated custom configurations.

## Failure propagation in real application owners

The already-published d1 navigation contract has no dedicated missing-capability or unsupported-binding error code. Binding acquisition failures propagate through the normal connection/owner error path. This includes HTTP404/501, malformed identity, account/network/run mismatch and cancellation.

The real app must not catch such an error and construct unbound navigation, switch to another run, silently omit navigation or derive an expected network from the refused response. Explicit dependency-injection callers that already choose no navigation remain a distinct construction API; they are not a fallback for an application tuple that requires navigation.

## Ownership and qualification

W1 supplies native startup and host runtime source plus focused tests. W2 owns its app/controller wiring. W3 owns final source composition, the unified native artifact, exact version/profile updates, Apple verification and integration. The new binding backend and bound startup artifact must both qualify before application acceptance.

The current delivery is SOURCE_ONLY_NOT_COMPILED_OR_EXECUTED. Six new Go parents, one affected legacy Go method and one changed Apple method are pending. No current/native authorization, complete application behavior or release acceptance is granted by decoding a stored locator or reading this contract.
