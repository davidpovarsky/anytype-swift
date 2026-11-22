# Prepared original inline files: native-only additive slice

This slice is additive to the frozen prepared object/block v1 bundle, not a
replacement for it. The destination is the pinned Any native engine plus its
retained v10 Any and v9 SDK overlays. No any-sync or any-store source changes
are required. There is no HTTP route in this slice. `MigrationCapabilities`
continues to report `file: 0` and `networkVerified: false`.

## Native API and exact bounds

`Files()` optionally implements `space.PreparedInlineFileService`:

| Method | Input | Result |
| --- | --- | --- |
| `PrepareMigrationInlineFile` | Existing `MigrationInput` scope plus typed `MigrationInlineFileSpec` | Immutable native IDs, fingerprint, source-spec SHA and current stage/outcome |
| `MigrationInlineFileStatus` | Existing native intent ID | Native history/current-row reconciliation; no append |
| `CommitMigrationInlineFile` | Existing `MigrationCommit` scope/fingerprint | At most one native durable stage |

The spec is `{ownerObjectId, name, mime, content, contentSHA256}`. Content is
ordinary caller file bytes, never caller-supplied encrypted or signed native
bytes. The owner must already be a live signed ordinary `object` with a
materialized object row in this native Space. Derived owners, variants and
full-tier files are outside this interface.

The pinned SDK declares `payloads.InlineMaxSize = 4096` and requires size
**strictly less than** that value. This slice admits 0–4095 bytes. Both 4096
and 4097 are rejected before ledger open, root registration or row append.
The SHA is the exact lowercase SHA-256 of content. Names are valid UTF-8 with
at most 1024 UTF-8 bytes, MIME hints at most 255 bytes; neither may contain NUL.

The normalized spec and exact original source-spec bytes are both bound to
the native fingerprint. The full immutable logical-plan digest and physical
native account/Space/store generation use the original ledger contract.
The new kind is `inlineFile`; its private stage key is `inline-file`.
Same intent IDs cannot cross kinds, in either reservation order. Typed
entity identity remains kind-inclusive: an object and its file can share a
logical source key under separate intents. Existing root/bootstrap/block
stage keys and their validation are unchanged.

## Native prepare and publication boundaries

Preparation locks the native owner and any existing payload carrier in stable
ID order. It reads actual current owner/carrier heads and current writer/key
authority. It then builds these values without mutating the native DAG:

1. The native deterministic derived payload root: Space ID, ordinary owner
   parent ID, native class `payloads`, seed `builtin:payloads`.
2. An ordinary native payloads row, with cleartext size/owner and sealed `enc`.
   `payloads.SealEnc` supplies the native AES-GCM member-only encoding and
   native domain-derived key. The name, MIME, hash and inline content are
   inside `enc`. There is no `rootCid`, `networkSign`, full-tier byte object,
   upload queue or broker receipt.
3. The exact native signed row change, including current ACL head, previous
   carrier heads, immutable payload-root snapshot base, timestamp and CID.
   The file record ID is resolved by the original native CRDT ID derivation.

The exact root bytes, signed row bytes, row CID, file ID, sealed row bytes,
normalized spec, exact source spec and preparation fences are inserted in a
single transaction in the same private native migration ledger. The native
full-checkpoint barrier must succeed before preparation is admitted. No root
registration, row append, watcher or publication callback occurs in prepare.
Concurrent contenders select the first complete reservation; retries never
reseal or re-sign it.

| Stage returned by status | Native fact | Next explicit commit |
| --- | --- | --- |
| `file-prepared` | Exact root and signed row reserved; payload root absent | Register only the known deterministic root under final current ACL/key fence |
| `file-root-committed` | Root is present and matches exactly; known row absent | Append exactly the reserved signed row under final current owner/carrier/ACL/key fences |
| `complete` | Exact known row CID is in native history | Read current row and return committed/deleted/modified outcome; no new append |

If a payload root already existed during preparation, the first receipt is
`file-root-committed`, so only one row commit is needed. Fingerprint, root ID,
signed row CID and file ID remain unchanged across stages. A lost reply is
reconciled from actual root/history, not from a mutable host receipt.

## Native append and read fences

The only modified existing production source is `internal/commitguard/guard.go`.
The private inline mode requires the exact native derived payload root and a
signed, nonsnapshot, unencrypted outer change with outer dataset `payloads`.
Its strict parser accepts exactly one native payload create: no extra wire or
cleartext row fields, no alternate dataset, no full-tier fields. It decrypts
the native `enc`, verifies content size and SHA, and rejects a wrapped full-tier
key or variant. The normalized operation is separately compared to those
actual native decrypted bytes before the reservation can be committed.

Current writer permission, exact signed ACL head and exact current sealing
key ID remain fenced while the native storage transaction commits. The
native deferred-updater requirement is retained, so projection/publication
callbacks cannot report an uncommitted append. Ordinary encrypted tokens
still require a nonempty outer read-key ID. Incoming replay keeps its original
historical path; no remote peer can supply the private inline token.

After the stable native owner/carrier locks are acquired, the route also
re-reads the owner's actual head-storage entry. An absent, queued-deleted,
completed-deleted or derived owner refuses before the operation. This covers
the state observed after preload/lock waiting; it is not a claim of a new
atomic fence against every later settings-tree mutation. The real native
deletion/cascade-during-wait control passed both before and after this extra
read. It proves refusal in that exercised cascade, not an old failing
regression or a separately reproduced owner-only queued state.

Pending intents stop if owner/carrier heads, ACL or key have advanced, if an
owner/carrier is deleted, if the exact root is wrong, or if reserved signed
bytes differ. They are not regenerated or rebased. Recovery of a known committed
CID still requires current writer authority and the live current owner.
The file's native historical sealing key may be used for readback after a
later key rotation, but it does not authorize a pending stale-key append.

Current native row contents and original native row version/add sequence
distinguish `committed`, `committed_deleted` and `committed_modified`. Native
tree disappearance or deleted owner may produce `obsolete` when exact
committed row history is no longer available; absence never permits a new
root or file identity. The controlled tests and their limits are recorded
separately in the qualification report.

## Evidence boundaries

Restart means actual SDK and native/projection database close/reopen. It is
not an abrupt OS-process kill or physical-media/power-loss certification.
The ledger checkpoint is a mandatory process-level durability barrier; no
additional physical fsync claim is made. Files.Get/Open read the ordinary
native typed metadata and native plaintext reader, independently of the
private reservation. Hashes are computed from that returned byte stream.

This slice does not qualify network delivery for files, large-file blob upload,
variants, derived owners, Apple runtime linkage or a whole-Space snapshot.
It does not add the ordinary `Attach` route's explicit local file-status
subscription notification to this new optional service. Ordinary Attach and
its notifications remain unchanged; native typed Get/Open are the qualified
readback surface for the new route. Consumer/status integration is a further
gate before any public file capability can be enabled.
It supplies no source census/snapshot fence and does not broaden MIG-01
completion. The original archive planner must continue to refuse unsupported
or incomplete full-Space plans before target writes.

## Pinned source references

- Any upstream: `anyproto/any@88fae2e5ae7d0f46d6707567a3123081faa8de9a`.
- SDK upstream: `anyproto/any-sync-sdk@854df54cdadd76006ae823cbd1b1d923138356d0`.
- Native inline cutoff/class: `internal/payloads/payloads.go`, Git blob
  `bdaef5baebccdee1d674e0dd844fa460320b777d`.
- Native seal/key contract: `internal/payloads/seal.go`, Git blob
  `aa86bd8844155d4a30eb9fd4aea646bc624c5796`.
- Native row/read contract: `internal/payloads/row.go`, Git blob
  `554bc1ba6c486a95a9245b803b7bea11986ff745`.
- Native payloads validator: `internal/payloads/handler.go`, Git blob
  `c896b348eab6727ce6716fe899ed6a726bdac1a1`.
- Frozen object/block bundle SHA-256:
  `95777bc294903b1bd5dede421a80af6e949a85e2d1e2de41d1e2f77a4d054ff0`.
