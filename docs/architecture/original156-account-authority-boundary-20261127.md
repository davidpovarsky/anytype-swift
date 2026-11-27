# Original 156: retained account-authority boundary

The new read-only inventory passed. It did **not** recover an account credential,
reconstruct plaintext history, or promote Heart source admission. C remains open.

## What actually ran

On 27 November 2026, one controller streamed the entire original compressed
archive from its unchanged, pinned Windows location. It read 106,036,361 bytes
through EOF and matched SHA-256
`f85036744b0cb76ffecb4e29f752dd293a74a1f76c2d13c273df57691a4a8c64`.
The stream completed in 19.046 seconds. Its owned SSH process exited zero and
the entire process group was positively absent; no forced cleanup occurred.

The controller selected 42 exact archive members. All 28 files belonging to the
original source account, totalling 3,225,222 bytes, were hashed in memory and
classified as follows:

| Files | Classification | Inspection performed |
| --- | --- | --- |
| 7 | SQLite databases | Full-file hash and SQLite header; no SQL connection or row decoding |
| 16 | Tantivy index and bookkeeping files | Full-file hashes; bounded JSON metadata classification where present |
| 3 | Flatfs bookkeeping files | Full-file hashes and expected member category |
| 1 | Native configuration | Full-file hash, original configuration schema keys, candidate-field classification |
| 1 | `device.key` | Full-file hash and the 116-byte envelope size; no authentication or decryption |

Account files were not extracted. No account, database connection, native
process, compiler, test account, or peer wallet was opened. No private credential
or account-file payload was emitted. The accepted 182-operation migration was
not replayed. All old controls, selected source bytes and the archive remained
unchanged.

The exact private receipt is retained at:

```
/mnt/development/projects/evidence/pinkha-c-original156-private-authority-20261127/attempt1/result.json
SHA256 74b4c03367bc4b1bd428fb6b0914303353cb3fc4b0fef909618db8afeac67bf2
```

The public qualification is a documented projection of that receipt. It keeps
all 28 full-file hashes, sizes and classifications while hashing their relative
paths. It omits raw private commands, file payloads and credential values. The
raw receipt remains the authority for the exact private member names.

## Original source and producer identity

Twelve selected account, session, wallet, configuration and encryption source
files joined the original source manifest and its unchanged derivation chain.
Their current retained copies were read at the explicitly admitted physical
location from custody receipt `331b93a174d36a639d3748dfa01692fc0add62624d31c7a3cd957f5a5eb5d772`.
This inventory does not infer source equality through an arbitrary symlink.

The exact original custom-schema fixture was also retrieved from producer
checkout `bfd73d7d2d05a3dc115f6fddf2fb938844b17280` and joined byte-for-byte to
the archived original delta. It is 15,728 bytes, SHA-256
`699fe5e97942360e53b0ac364105dbf11350e81b33f042337b49995e32edac79`, Git blob
`1d9b5a5062fb4014fb1d2378acbf0fee438470cd`. The descriptor is SHA-256
`315b63e0496cf260691c6fae367a555f143209cf3e35f45da9302836ce5ba8cb` and derives
Heart `65caee9bfc386c2f9182564d6ad1eb2f02cfadd1`. No reverse patch or later
`ordinaryPageKey` correction was substituted for this original source.

GitHub run `45492064232`, job `138792712711`, used the GitHub-hosted
`ubuntu-24.04-arm` runner. The original source container's argv, environment,
bind mount, inspection result and cleanup record bind the wallet root to:

```
/home/runner/work/_temp/pinkha-native-file-peer/private/fixtures/TestLoadedAccountCustomSchemaSource
```

The original archiver included the entire `fixtures` subtree. Its sibling
`work` and `go-build` directories were excluded. The source container had
already stopped with the retained fixture exit code 1 before its exact cleanup
returned zero. All five reported container cleanups returned zero. The archived
failure remains a failure; this new inventory does not change its status.

The old GitHub runner's unarchived host directories have not been independently
inspected. A live original account session or a separate authorized credential
retention location would be distinct evidence; this inventory does not assert
that no such material can exist anywhere.

## Why the original account API route is still blocked

The original fixture calls `WalletCreate`, discards the returned account master
node, and retains the mnemonic in its in-memory fixture. `WalletCreate` assigns
the derived account authority and a session-signing key in memory. It does not
write a mnemonic or account-master-node file. The original select and recover
paths require the original mnemonic or account master node; they do not provide
a directory-only recovery fallback.

The original device-key writer serializes a device Ed25519 private key, then
encrypts it to the account public key. Its expected 68-byte protobuf plus a
32-byte ephemeral public prefix and 16-byte authenticated-box overhead is
consistent with the observed 116-byte `device.key`. The original loader requires
the account private authority to decrypt that envelope. It is a different key
from the missing account master authority.

This is a source-and-size classification only. The receipt deliberately says
`deviceEnvelopeAuthenticated=false`. It neither authenticates the ciphertext
nor proves the plaintext within it. The original load-or-create helper was not
called: that helper can replace a missing or unreadable device key and is not a
read-only inspection operation.

No credential candidate was found in the bounded JSON/metadata inspection. The
SQLite payloads were not queried, and the result is not a universal search for
every possible credential encoding. The original API call chain and retained
material do not currently provide usable authority for opening this original
account. Borrowing either peer wallet would change account identity and is not
an acceptable substitute.

## Scope and next gates

The earlier `19c454ee9feed8bc98697eb6db316ca4e0b19bdeeb0b759a6f37ddfb83ce2d9d`
receipt remains unchanged with its original, narrower metadata scope. This
tranche adds actual hashing and classification of all 28 original account
files, the exact original custom fixture, and concrete producer path/cleanup
joins.

Public CID/signature/historical-authority validation is a separate proposed
proof. It can authenticate encrypted history without asserting plaintext
reconstruction. Plaintext history recovery, functional admission of every
remaining family, and complete C acceptance remain separate unfinished gates.

The controller has an independently reviewed read-only budget: all retained
output on development, an 8 MiB initial allowance above a 512 MiB development
floor, a 256 KiB output cap and a 120-second deadline. It makes no root bulk
writes. Its 64 MiB root read-only floor is not a native or build floor. The
existing 2 GiB native/build emergency floor was not reused, reinterpreted or
relaxed. The reviewed stream helper supplies only immutable reads, fixed
non-multiplexed SSH and owned process-group cleanup; its original `main` and
resource guard are not invoked.

Prepared3, all previously accepted native products and source closures remained
untouched. This is an evidence and forensic-controller tranche only.
