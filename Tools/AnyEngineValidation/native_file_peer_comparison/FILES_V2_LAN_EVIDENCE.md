# FilesV2: retained independent accounts, LAN, crash and offline bytes

## Accepted boundary

The actual native run at `2026-11-27T02:15:42Z` completed in 13.951 seconds with `PASS_COPIED_PRODUCTION_ACCOUNTS_LAN_PARTIAL_CRASH_COLD_FILE_BYTES`. This is a file-transfer qualification on exact custody copies of two independently created, genuinely granted production-test accounts. It is separate from the unresolved original private-network invitation and from cloud durability.

Receipt: `/var/lib/pinkha-c-filesv2-20261126/production-lan-files2/result.json`, SHA-256 `c23b78e312fa9efbe1a5fe7abd9e0061e131a0514fdb4fc07cf12ebe42376692`. An exact copy is included in `receipts/production-lan-files2.json`.

The original production account stores were never opened by the LAN controller. The custody-copy receipt is `/var/lib/pinkha-c-filesv2-20261126/production-lan-custody1/result.json`, SHA-256 `2de21c6aefc8b6b2e79cf831bb8c5ee53c2eafb1454651402584f6cb09a32468`. It records 9,496,599 copied bytes, equal contents and modes, distinct inodes, and unchanged original stores during the copy. Later owner activity on those original stores is outside this controller's custody assertion.

No account initialization, invitation, join, grant or attachment was performed in the LAN continuation. It reused the real Reader grant and all four preexisting file identities. Every recipient file was uncached at the start of this accepted transfer.

| Existing payload | Plaintext bytes | Native metadata | Plaintext SHA-256 |
|---|---:|---|---|
| `cloud-binary.bin` | 8,192 | Generic MIME omitted; HTTP octet-stream fallback | `5b3ad191f3c210b61bd5d1ef5ffc838b7fbabe38e8b42207fa04bf2388831313` |
| `cloud-original.png` | 49,363 | Explicit `image/png`, 128 × 128 | `9dda40b15a6a23e5788514b731aff65dcf0e62d01c137507d6c05f43d40ca54e` |
| `cloud-large.bin` | 8,388,608 | Generic MIME omitted; HTTP octet-stream fallback | `2014e7bacfcf9085084a41e5d6a1976965aa0b958d9e99f3f95a905547416eeb` |
| `cloud-thumb.png` | 12,420 | Explicit `image/png`, 64 × 64, original variant relationship | `710df0c12429ecca0af68e5217edf5a1d82176869b0c4a30ee52082c858e21c1` |

The controller checks account, space, object, file and root-CID identities; names, sizes, stored MIME, inline flags, variant relationships and the existing durable flags. The binary and thumbnail remained `durable=true`; the image and large file remained `durable=false`. A successful LAN read did not promote their cloud custody.

## Actual network and process evidence

The native processes ran inside a fresh OS network namespace containing only loopback and an internal veth pair. There was no default route; an external connection failed with `ENETUNREACH`, all six private-node ports refused connections, and both native clients observed one mutual LAN peer with zero network/global peers.

The 8 MiB file first returned HTTP 206 for bytes `0–32767`, with the exact content range and hash. Bob still reported the file incomplete. Its encrypted CAR had 8,389,979 logical bytes and only 4,202,496 allocated bytes. The controller then sent SIGKILL to that owned Bob process, observed exit `-9`, and proved its process group absent.

A fresh Bob process inherited the established OS seccomp outbound-denial policy. It returned the persisted partial range without changing the sparse CAR. Another fresh LAN process completed the same partial cache, and all four full payloads and nonzero byte ranges matched the owner. The native thumbnail URL resolved to the retained thumbnail bytes and identity.

After normal shutdown, a fresh Bob process under OS outbound denial returned all four complete payloads plus the thumbnail. Native sync reported offline with zero peers. A write attempt with Bob's Reader authority returned HTTP 403 `space.read_only`. The denial helper's positive controls first showed reachable local TCP/UDP, followed by actual denied connect/send syscalls and inherited seccomp/no-new-privileges flags.

There were six native processes and one denial probe. Every normal process exited zero, only the deliberately crashed process exited `-9`, and all seven owned process groups were positively absent. Forced cleanup is a failure, not an accepted crash result.

## Preserved first failure and metadata contract

`production-lan-files1/result.json`, SHA-256 `eaca0b1c09dccf5930b03e2dd6c580658d4c5ce8ca8f7a7e98bb2a81542763be`, remains a failure. It established mutual LAN discovery in 6.218 seconds but the controller incorrectly required a stored `application/octet-stream` MIME field before reading any file content.

The exact native source declares MIME with `omitempty`, omits an unknown binary's MIME, and supplies `application/octet-stream` for the HTTP response. The continuation compares owner/recipient stored MIME exactly, including omission, and checks effective HTTP content type separately. PNG must still contain literal `image/png`. All identity, byte, range, variant and initial-cache assertions were retained. It used the same copies and their hash-pinned final custody from the failed attempt, without clearing caches or repeating grant/attachment stages.

## Cryptographic and integrity qualification

The separate original-method run completed at `2026-11-27T02:25:54Z`: nine passes, zero failures/skips, 10.520 seconds for the actual Go command, exit zero and positive process-group absence.

Receipt: `/var/lib/pinkha-c-filesv2-20261126/files-crypto-integrity1/result.json`, SHA-256 `99ccdd67f5514a1eda4304decde8e5766453a339dfc667980b9a9398ba74d0ac`. Exact copy: `receipts/files-crypto-integrity1.json`. Original JSON test log SHA-256: `3e3446229ad0ac1214d7f804d0e6485d0c5cd944db5b4d3df61f7f6e6d50aea0`.

The unchanged original methods were `TestEncryptFormat`, `TestReaderSeek`, `TestReadBlockDetectsCorruption`, `TestSparseWriteRejects`, `TestLyingPeerFallsBackToHTTPAndBans`, `TestCorruptBlockHeals`, `TestWriteBlockVerifiesWhenNotPersistable`, `TestUnseal_WrongKeyFails`, and `TestDeriveEncKey_DomainSeparated`. The original seek method includes its random seek coverage; no weaker replacement test was introduced. The six previously accepted signed-ACL regression tests were not rerun.

The original file construction is Heart-compatible AES-256-CFB with a fresh per-file key and ciphertext integrity checked through Merkle CIDs. Metadata uses AES-GCM with domain-separated object/read-key context. Ciphertext-sample absence in the retained CAR is an additional observation; it is not alone an authenticated-encryption proof, and this is not an AEAD-file-cipher claim.

The test controller used the qualified original cache with all Go test intermediates on an owned development-volume directory. Root stored bounded evidence only. The original 2 GiB root and 512 MiB development emergency floors held throughout; no source/account deletion, cache overlay or additional resource reclamation was required.

## Qualified source and remaining boundary

Original inputs: Any `8fbd1e819fb132ac0e0a848d2ddf5c5714189b81`, SDK `c1fd59bd8f0ed62471234ec1a65a402d22eab6a9`, retained source manifest `12ad65cd178aa31b6aa5761d42507d8618f1d3d4865a627548af2036c0a40a6c` across 1,594 files.

The LAN run uses only the signed-ACL refresh overlay from commit `baa37153538b9b3f3bf22fa049acc902d445844c`. Its qualified native binary is SHA-256 `79248a63132a0146deff4e9fe1c4104a381a34d5c2ffcad536247a8429f98857`, from a 1,597-file source manifest with SHA-256 `44abb44523e01b4631c8eff5f3ff183aca17f58b472fbb041e7a1e501028ca68`. Its build receipt is `/var/lib/pinkha-c-filesv2-20261126/acl-refresh-native1/result.json`, SHA-256 `bfafdf6d7304786726235fd1d2f3065dbf5782091123f03fbd6bb54b09328380`; actual build time was 86.205 seconds. Exactly four SDK files differ from the original closure. Original and qualified source admissions remained identical before/after the accepted runs.

The original private-network owner's pending request was genuinely recovered by this binary and one ordinary Reader acceptance returned 204. The recipient still remained pending; that complete continuation is retained as a failure. Its local signed grant is not yet represented in the observed node snapshot. See `acl_refresh/EVIDENCE.md`. The unrelated production accounts used here had already completed a real Reader grant; no account reset or replacement is claimed to fix the private failure.

The existing 12 network cases, two ACL-enforcement cases and two Linux P2P cold-restore cases remain unchanged evidence for their own recorded inputs. This document does not relabel them as rerun tests of the new binary. Cloud quota recovery, whole-space migration, Apple device qualification and final release acceptance remain distinct gates owned/coordinated by their lanes.

## Controllers and custody

`copy_production_pair.py` records the original stopped-pair copy. `resume_production_lan_files.py` is the exact accepted LAN continuation. `qualify_files_crypto.py` runs only the nine original methods. The accepted native-build and retained-private-recovery controllers are included alongside them.

These are custody-bound validation controllers, not reset scripts. They refuse an existing output directory, a different source/custody receipt or an unexpected process/identity/state. Accepted stages should be reused from their exact receipts; later work must continue from the latest custody inventory and preserve previous failures.
