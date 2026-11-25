# Original native store context: exact lifecycle row and empty default KV

## Qualified result

Product source `055cbe29647277cc0a14a81adc1a501a49df8aec`.
SentinelX `job_984c6ce773b1`: 20 distinct Swift methods passed, 0 failures, 0 skips. The unchanged source was compiled against the existing warmed Oracle cache. Full command and source hashes are retained. Original log SHA256 `b84d1882eff3d2f52d5d8e60b9bed4c80f0379115dbb853c8c5e7bb94f3e414e`.

This includes six new context controls, ten existing native-bundle integrity/identity/member/refusal controls and four existing complete-Page composition controls. It reads the original real156 capture and the separately qualified fresh native5e8 capture143; it does not rerun a native engine or turn archived evidence into a current account lease.

## Concrete source finding

The real156 private witness has six native collections, 477 rows and 405,933 encoded-value bytes. The SHA256 of the complete original framed witness is `31e69a8801070274f01ff0dd2f2899c81fae3e0fb70933a2984017ecae8846ec`.

Its retained nonempty `_client` collection contains exactly one 21-byte native anyenc row, with original ID `space` and `created:false`. The original writer `space/spacecore/storage/anystorage/clientstorage.go` uses this row solely for local Space creation lifecycle. It is not an Anytype user Collection or mutable object property. Original row SHA256 `646cfb00a89f7ea887ed855eda75e6c943ffe34647032d3eb4fba2a545727d38`.

The second retained collection is empty. Its identity exactly equals the original native `StorageHeader{spaceId:1,storageName:2="default"}` protobuf followed by SHA2-256, CIDv1 DAG-CBOR and canonical base32. The original inventory independently reports one key-value store and zero rows. A foreign empty collection is not admitted as that native store.

## Implementation and boundaries

`AnyHeartNativeStoreContext` validates the complete original framed witness, native owner nonce hash, Space identity, generation, SHA256, ordered unique collection and row identities, per-collection census, total row/byte counts, retained collection membership, and exact end of input. Parsing uses bounded slices and does not decode or rewrite arbitrary private row payloads.

The only closed classifications are:
- exact original `_client/space` lifecycle row with a Boolean `created`;
- the exact natively derived default key-value collection with no rows.

The original row and archive remain authoritative and unchanged. No lifecycle flag is copied over the destination engine's own state. Unknown fields, extra lifecycle rows, non-Boolean flags, nonempty key-value data and foreign empty collections remain unmapped. Bad framing, stale owner/Space binding, inconsistent counts, omitted retained collections and trailing bytes are refused. Nonzero Data slice indices are also covered.

The bundle exposes the verified context, and Page composition no longer reports these two internal store contexts as user collections needing a mapper. All other source/schema blockers remain. Both original156 and fresh143 still reject complete schema admission. The historical156 bundle still lacks its original compiled descriptors; the newly captured native5e8 descriptors are not substituted into it.

## Provenance and evidence reuse

The original Heart source remains `5e8f9ce4ec789c1cd775b148a6cc49d4a28f56b5`; no Go source, native ABI or Apple producer changed. The decoder is based on the actual original Heart writer and any-store v1.0.3 encoding. Hashes of primary source files are included.

The real156 manifest remains `cbfb3aa1fd89707138adeccbce7389c40dc0a993f2285f6e517120e4e4239ed4`. The fresh143 manifest remains `04b9309e1b96918c47d1b00eed6b1a76b2e13432636a0aba77706f2f69082994`. Only read-only comparisons were performed; original producer statuses, private accounts and all source bytes remain unchanged.

The first compilation failed because a component fixture's chained Data expression exceeded Swift's type-check budget. That original failure/log is retained. Splitting the same fixture expression into typed subexpressions changed no tested condition or product behavior; the subsequent run passed all 20 methods.

## Remaining C scope

This closes the concrete internal-store classification blocker. It does not establish full-space migration, translate derived fields/layouts/history/settings, replace source session/checkpoint authorization, or authorize destination writes. Existing actual native file/default/content proofs remain scoped to their exact unchanged component paths. Task C remains open.
