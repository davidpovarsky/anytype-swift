# Bound node discovery so LAN file updates can progress

This layer follows the signed ACL refresh on the retained Any source `8fbd1e819fb132ac0e0a848d2ddf5c5714189b81` and SDK `c1fd59bd8f0ed62471234ec1a65a402d22eab6a9`. It changes peer scheduling only. The original ACL, signatures, identity checks, encryption, payload storage and file fetch code remain unchanged.

## Observed native failure

The original private Alice/Bob accounts completed the existing invitation and sole Reader grant. The first subsequent LAN transfer attempt attached the preserved source archive and an 8 KiB binary. The archive's exact metadata arrived after about 49 seconds; the next row remained absent (`404 file.not_found`) for the unchanged 90-second limit. No content was fetched. A separately closed copy of Bob, started with OS outbound denial, confirmed that the binary row was absent from both FileInfo and the object's file list. Original accounts were not opened by that diagnostic.

The bounded continuation reused both exact IDs. It recovered the existing binary row after 49.617 seconds and attached the planned 8 MiB binary, whose row arrived after 0.407 seconds. The following PNG row remained absent for 90 seconds. This second failure preserves four confirmed attachments; none may be reattached in a continuation.

During the PNG stall, native goroutine captures showed all four shared `streampool.ExecPool` workers in each process blocked in `KeepAlive → GetNodePeers → pool.Get`. The fast subscription cadence queued repeated unbounded node lookups. Its documented ten-second budget was discarded when `KeepAlive` substituted the space lifetime context. Headsync also looked up unavailable nodes before the already connected LAN peer. Both native processes otherwise reported a mutual, authenticated LAN peer, zero network/global peers, and no external route. The original source archive was confined to that fresh network namespace.

| Receipt | Exact SHA-256 | Scope |
| --- | --- | --- |
| `original-files-after-join1/result.json` | `39d0d0a6887a7766d9a73012178f38f1f2d4af8cc2bade924bcf81daaf1131d2` | Preserved original first file-transfer failure |
| `original-files-after-join2/result.json` | `85867ee6b4f2e586c11b9962dbccaf902e700b5757dc8d81023cc334a62178bb` | Native same-ID continuation, metadata samples and pinned goroutine evidence; FAIL after 152.040 s |
| `lan-progress-unit1/result.json` | `77e1d1ebc5f8c19c0427fdad78f88aa912659f56882f05323522ce17ce58b984` | Five intended baseline failures plus a typed-nil test-fixture panic; preserved, not accepted |
| `lan-progress-unit2/result.json` | `5e9df7a7e9a3039938996d68108fab934f6b4fe1888ba3d34097843c0277a64c` | Actual baseline five failures/two passes, then corrected 17 passes, zero skips |

All paths above are under `/var/lib/pinkha-c-filesv2-20261126` on Oracle. Every listed native/test process ended with a positively absent process group. No permission or source acceptance assertion was relaxed.

## Implementation boundary

`KeepAlive` permits one queued or resolving node subscription per space. A completed lookup or rejected queue entry releases that admission. The queue getter starts an actual ten-second discovery deadline when it runs, and at most three node lookups proceed concurrently, preserving configured result order. Cancellation still derives from the owning space's lifetime. If shutdown drops a queued getter, the coalescing flag belongs to the discarded manager; this change does not claim to reuse a closed manager.

Node lookup before a known LAN/global device gets a separate one-second budget. The subsequent device lookup retains the original caller context, so a node timeout cannot count as a cancelled local-peer dial or erase a peer through the existing strike policy. Node-only responsible-peer lookups retain their existing caller budget and errors. The public `GetNodePeers` operation remains unchanged and nodes-only. All secure transport, space membership, signed tree and signed ACL validation remain in their original paths.

## Actual focused qualification

Seven new methods exercise bounded responsible-peer lookup, bounded broadcast lookup, queued-subscription coalescing, queue rejection recovery, concurrent node discovery with a live deadline despite caller cancellation, actual four-worker queue starvation, and preservation of node-only error handling. Ten existing affected local-peer, global-state and parked-broadcast methods also passed after the fix.

The first new-test run exposed a fixture error: a typed nil `*fakeLocalPeers` was stored in an interface. The corrected fixture uses an explicit empty peer source; every assertion remains unchanged. The second run used identical test bytes for its baseline and corrected production code.

| Stage | Outcome | Process duration | Raw log SHA-256 |
| --- | --- | --- | --- |
| Corrected-fixture baseline | 5 targeted failures, 2 passes | 24.040 s | `b88915b959c068d26933ebf441066459c101ea641f9851391560f251228bbb7a` |
| Production correction | 17 passes, 0 failures, 0 skips | 12.029 s | `9b4fb84586ebfb93dc5443e4b622ad0a2246462dbfdd7635b0ba3a36d3188a06` |

The qualification ran with two Go jobs, no module downloads, a 2 GiB root reserve floor and a 512 MiB development reserve floor. Compiler temporary work and the qualified cache remained on development. Original 1,594-file source and the prior 716-file ACL overlay remained byte-identical. The final 718-file SDK manifest is `324f2136ecc953906549a2fe2963337bef4fcef03446e6604c8066299b1faf5c`.

## Application and remaining acceptance

Apply `acl_refresh` first, then run this directory's `apply.py --sdk-source /absolute/isolated/sdk-source`. The script checks prerequisite ACL source hashes, exact pre/post hashes for these three files, and the entire actual delta. It refuses the retained exports and qualified SDK source. `--check-only` performs source applicability checks only.

The focused proof is qualified SDK scheduling evidence. Native rebuild and same-account, same-four-ID file-transfer acceptance with the unchanged 90-second limit remain separate gates. Earlier large-file range/crash/offline, crypto-integrity, original-join and mixed-network receipts retain their original binary/source scopes; this document does not silently rebind them to a new native binary. Cloud quota/custody remains owned by Wave 1's root agent.
