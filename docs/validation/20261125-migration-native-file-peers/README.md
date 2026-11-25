# Real native file peers and cold offline reopen — 25 November 2026

## Accepted scope

The unchanged Any CLI built from Any `548f5cd0430a723bd26ea724daeb99991f68b9c9` and SDK `e195f6c07a053c6588e39ffe72ee4fc44cf3d953` passed a real two-account, two-process file comparison. The source file manifest verified all 874 Any and 709 SDK files before and after execution.

Controller source: `68a937c6979aebd1517ab2dfcc1547b53d6ea5b0`; controller SHA256 `c2754d3a62abafd43e576c67c7e30b463dd202f2b6aecbf77356fee68d2a902d`.

Native binary: `bc73441d05a502e3e77df479f54279540489869b00ca1aecf4e1e9f681fa0f49`, 80,914,834 bytes. Incremental build took 13.005 seconds; the original native runtime comparison took 13.369 seconds. These are observed run times, not release performance acceptance.

| Check | Observed result |
|---|---|
| Fresh independent native accounts | Different account IDs, native peer IDs, process IDs and private data directories |
| Membership | Original invite, join request and owner Reader grant; recipient's actual identity/role checked |
| Discovery | Actual native mDNS; both connected peers identify the other with source `lan` |
| Payloads | 8,192; 1,048,576; 10,485,760 plaintext bytes, all non-inline |
| Before recipient read | Real payload rows synchronized; complete local bytes absent |
| Full reads | Source and recipient SHA256 equal for all three files |
| Partial reads | Actual HTTP206 and byte-equal Range responses |
| Original process shutdown | Both exited0; no forced kill |
| Offline enforcement | macOS `sandbox-exec` denied outbound TCP connect and UDP send with EPERM; the same listener was reachable outside the sandbox |
| Cold process | New recipient PID, same retained native account/data, all three peer counters0 and state `offline` |
| Cold file comparison | All three root/object identities and complete plaintext hashes retained |
| Final shutdown | Cold native process exited0; no forced kill |

### File hashes

| Plaintext bytes | Source = target = cold offline SHA256 |
|---:|---|
| 8,192 | `5eb8cafc97b2b4b6c1e5b47940b6f0f89d06eb198dbbbc6c39948a3715a470f3` |
| 1,048,576 | `f5c858b64acc27d1a9a71b6844cc11687272695d4f0ae44d5ae68b0828d505b9` |
| 10,485,760 | `720b2d564a4bfa8c040b87db378a18a2a654916f1db7b7f1102efcc0287339e3` |

This proves the original SDK's actual peer byte transport and retained offline data. It does not prove cloud custody or complete Heart-to-Any migration. The private AnySync configuration advertises no fileV2 nodes; every non-inline file honestly remained `durable=false` and `inflight`. No receipt, signature or durability acknowledgment was synthesized.

## Preserved production failure

The unchanged original `TestE2E_MultipeerFileLatency` on the shipped production configuration failed at its warm-up durability gate. Its log SHA256 is `b7307d3cf6f88db03d0cc792733e7ab001530f0c26ce98395401b47c6d8b59bb`. The log contains the actual native queue outcome `limited=true`, `filestatus: storage limit exceeded`.

The SDK maps only `upload.ErrLimited` to that queue error. The uploader returns this error only for broker per-item `ErrLimitExceeded`. This establishes a broker storage-limit refusal, not an absent fileV2 node or proven object-store outage. The run did not record the numeric account/space allowance, so the exact exhausted quota scope is not asserted. The original signed access-code endpoint can obtain a legitimate grant; configuring its URL alone does not grant storage. No code was invented or redeemed, and no existing user's keys were used.

The full original latency test was not rerun and was not converted to PASS. Public OCI metadata checks for `anyproto/any-sync-filenode2` found DockerHub404 and unauthorized anonymous GHCR/Docker-registry metadata. No container layers were pulled; lack of anonymous access is not proof that no private producer exists.

## Retention and resource evidence

- Mac durable proof/fixture root: `/Users/m1/builds/pinkha-c-native-file-peer-20261125`.
- Exact original run JSON: `attempt1/result.json`, SHA256 `30bfbb2ef782451fdc6574cb22c3dd53174f6e69356e08b4aafc26fa2b3b37c4`.
- Native binary remains at `any548`.
- `attempt1/alice`, `attempt1/bob` and original native logs remain private, outside Go's automatic TempDir cleanup. They contain generated fixture credentials and must stay out of Git.
- Safe source/command/result/policy receipts are committed here. The transport receipt records original Mac file hashes.
- Oracle evidence root: `/mnt/development/projects/evidence/migration-final-20261125/file-v2-quota-diagnosis`.

An initial build controller stopped before compilation at a fixed4GiB reserve. That infrastructure result is retained. Per project AGENTS, the continuation used the already established 612,368,384-byte warmed-phase estimate plus the2GiB emergency floor for active shared work. Actual minimum free disk during build was5,705,015,296 bytes, and during the runtime comparison8,836,435,968 bytes. No product/test gate changed. Runtime-only estimated new disk was256MiB; model downloads were disabled using the original documented `index.embedder: none` setting.

## Remaining C acceptance

The complete source plan still blocks unsupported layouts, derived/read-only fields, unknown resolver values and full settings/history/account/permission semantics. The new original-app capture adapter and read-only review preserve those blockers. The producer-qualified runtime identity is checked before minting any source session (follow-up `9bbfd33c6a6b8e34d27be3754fb33bfca61104f6`); actual full app source capture remains a separate Apple acceptance gate.

Full real-space destination execution and a complete semantic comparison after a fresh offline process are not accepted by this file-only proof. Earlier source/anchor evidence is in `docs/validation/20261125-migration-source-and-anchors` and owned-session evidence in `docs/validation/20261125-migration-account-session`.
