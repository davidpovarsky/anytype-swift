# Native object links and computed migration fields

Date: 2026-11-27
Owner: Wave 1 engines
Consumer integration: Wave 3; UI/editor ownership: Wave 2

## Available API

PinkhaAnyEngine now exposes the additive, read-only
`AnyNativeObjectLinks(client: AnyHTTPClient)` adapter. It depends on the
HTTP lifetime fix in `6fdcabeff7a39bc206ce250b069cc076a1d29895`.

| Operation | Native endpoint | Result |
| --- | --- | --- |
| `links(spaceID:objectID:selection:kind:limit:requireComplete:authorize:)` | GET /v1/spaces/:spaceId/objects/:objectId/links | AnyNativeLinksSnapshot.links |
| `backlinks(spaceID:objectID:selection:kind:limit:requireComplete:authorize:)` | GET /v1/spaces/:spaceId/objects/:objectId/backlinks | AnyNativeBacklinksSnapshot.object and .parts |

Both snapshots preserve accountID, spaceID, objectID, selection and truncated.
They are read values, not persistent mutation receipts or a grant to read a
target in another space. The adapter introduces no account-wide query.

The authorize closure must be a side-effect-free validation of the original
consumer lease and space. It runs before dispatch, after HTTP, and immediately
before returning the decoded snapshot. Account identity and cancellation are
also rechecked. The caller must retain its existing owner/session publication
fence when showing or storing the result.

## Exact identities and selection

| Selection | Forward read | Backward read |
| --- | --- | --- |
| .object | All indexed edges sourced by the object | Separate object-level and part-level target groups |
| .record(dataset:recordID:) | Only that source record | Only that exact target record, in object; parts empty |
| .property(propID) | The source property, using native dataset prop | Only that target property value, in object; parts empty |
| .dataset(dataset) | One source collection | Rejected before dispatch: a target record is required |

The optional kind argument is one native edge-kind slug. Omit it to read every
kind; the adapter does not reinterpret several kinds as one query value. The
native open slug set is retained, including future valid edge kinds.

Source fields are spaceID, objectID, dataset, recordID, optional typeID and
optional field. A property source retains the declaring type and property ID;
a record-field source retains its exact field. Targets retain the canonical
URI and the native object, property, identity or file fields. Target URI and
parsed identity must agree exactly.

Opaque identities are compared as UTF-8 bytes. Unicode-equivalent spellings
are not interchangeable. Outgoing sources must match the requested space and
object; incoming sources and targets must match the scoped native route.
A forward edge may name another space, but reading that destination still
requires its own authorization.

Native relation PROPERTY VALUES use the legacy `any://<objectId>` form.
The link INDEX canonicalizes that value to
`any://o/<spaceId>/<objectId>`. Do not rewrite stored property values to the
index URI. Property-value targets use `any://p/<spaceId>/<objectId>/<propId>`;
block/record targets retain their dataset and record ID.

## Completeness and admission

Limits are 1 through 500. Native provides a truncated flag and no continuation.
The default requireComplete=true throws readLimit for a truncated result.
A UI that deliberately requests a partial view must pass false and expose the
returned truncated state. Migration acceptance must not treat that partial
result as complete.

Missing/null arrays, malformed truncation flags, conflicting target fields,
wrong source/target scopes and inconsistent canonical URIs fail closed. Unknown
target kinds are an incompatible-schema error, not a silently discarded edge.

The native index is device-local. An empty response does not establish that an
object exists or that every remote change has arrived. Native index.disabled
(409), native authorization failures and other server errors propagate. This
API does not replace the original source census, head/snapshot proof or a
native index-delivery acceptance record.

Migration may bind the exact original read-only links/backlinks definitions
to these providers using a separately versioned computed-field descriptor.
Do not fabricate a writable SDK property, replace native derived descriptors,
or promote broad semantic admission on the strength of this adapter alone.

## Verification

The committed evidence under
docs/validation/20261127-wave1-native-object-links records 13 actual XCTest
methods: eight parser/identity/completeness methods and five loopback HTTP
methods. All passed, with zero skips. The HTTP tests cover route/query identity,
account switch, revoked consumer lifetime, disabled native index and rejection
before dispatch of ambiguous dataset-only backlinks. This is component
acceptance, not an assertion of native ACL or graph synchronization acceptance.

The source compiled successfully in 24.90 seconds. Its first test execution was
rejected because a new Python fixture inherited Swift's blocked SIGTERM and
stalled during teardown. Only the observed owned runner/fixture processes were
terminated, and the original failed result and termination records are retained.

The fixture then adopted the existing finite/unblocked signal lifecycle.
All Swift source and the built runner stayed unchanged. The accepted execution
used --skip-build, took 1.690 seconds for the 13 tests, and positively verified
that no owned fixture or runner remained. Only that fixed runtime fixture
changed between the compiled source inventory and accepted execution. Original
console method names and terminal outcomes are the acceptance evidence;
unrelated zero-case Swift Testing XML is never counted as XCTest coverage.

No Apple, native engine, consumer app or UI rebuild was performed for this
adapter. Wave 3 can integrate the additive source and reuse the exact component
receipt when its source closure matches; C owns the narrow typed Host binding
and its reuse of the already accepted native graph evidence.
