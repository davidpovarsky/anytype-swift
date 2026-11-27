# Original pending invitation: actual recovery

The original retained recipient completed its existing signed Reader grant on 2026-11-27. This continuation used the same original accounts, space, invitation and pending request. It did not initialize an account, mint an invitation, submit another join request, grant again, or attach files.

The earlier 90-second failed continuation remains a failure. It established that the owner refresh recovered the exact original pending request and that one ordinary Reader acceptance returned HTTP 204. The later successful run continues that same grant; it does not rewrite the prior result or establish an immediate-grant latency.

## Exact-node publication observation

`/var/lib/pinkha-c-filesv2-20261126/retained-node-grant-comparison1/result.json`

SHA-256: `b4ea294a8090cd867bae1246a635d0afba8a48e12ee073a9362f2598591321c6`.

The helper copied the stopped owner's retained wallet and consistent database to an independent diagnostic directory. It used the original SDK's authenticated `Pool.Get(exactPeerID)` and `SpaceSync.AclGetRecords` to query each of the three original private tree peers. Every returned chain was rebuilt with the original network-key verifier. All three had the same four-record chain and grant head as the owner's retained signed ACL:

`bafyreig7uw2qjb4alanirk3cqg64gujdwyuuwcgaehtwcqa6xv2ed2gx5u`.

Each root and head matched, and each pending-request list was empty. There were no mutating ACL RPCs, node-configuration changes or native processes on the original account stores. Original stores and all 1,594 original source members remained unchanged. The helper used 713 original SDK files plus one diagnostic main; its source manifest is `92e8799325e308a2c94db4a17482b3aecf726e145a2f8de82d297bc342215d87` and binary is `46efa5ce752e279d6a8362f0dfa1622224cfbf3c608368ef557f210bcd35f096`.

Actual compile time was 55.107 seconds; the actual diagnostic process took 3.870 seconds. Both exited zero and their owned process groups were positively absent. This observation proves current publication across those three peers. It does not measure when the previously stale node became current.

## Original recipient and cold authority

`/var/lib/pinkha-c-filesv2-20261126/retained-recipient-continuation1/result.json`

SHA-256: `7ba37273e7c31492e5bc01c4c9e7e72de2f00fd123c64b3aec85050f66a5625d`.

The controller pinned the exact-node observation and the prior original-account custody, then started only the original Bob store. It observed HTTP 409 `space.not_accepted`, followed by the same account becoming active Reader at 26.110 seconds from controller start. The ordinary native resume path materialized the space. Native sync then showed two of two trees synchronized and three network peers.

An ordinary file-write attempt returned HTTP 403 `space.read_only`. After a clean shutdown, a different native PID reopened the same Bob store with the qualified OS outbound-denial helper. The process inherited seccomp mode 2 and no-new-privileges; it reported active Reader and zero local/network/global peers. A second file-write attempt again returned HTTP 403 `space.read_only`.

The existing exact helper's positive TCP/UDP denial controls were reused from the hash-pinned LAN2 receipt rather than rerun. The two actual native processes each exited zero without forced termination, and both process groups were positively absent. Total controller time was 44.120 seconds.

The owner store was never opened and stayed byte-identical. Original and qualified native source admissions stayed unchanged. The new stopped original-pair custody inventory is SHA-256 `c9d6d7c245c239bd2a56b47f7b89e4a104630db5a15675a3f703cd9d434499b4`.

## Source closure and subsequent work

The recovered native is SHA-256 `79248a63132a0146deff4e9fe1c4104a381a34d5c2ffcad536247a8429f98857`. Its exact 1,597-file manifest is `44abb44523e01b4631c8eff5f3ff183aca17f58b472fbb041e7a1e501028ca68`. It is Any `8fbd1e819fb132ac0e0a848d2ddf5c5714189b81` plus SDK `c1fd59bd8f0ed62471234ec1a65a402d22eab6a9` and the four-file signed-ACL refresh overlay from `baa37153538b9b3f3bf22fa049acc902d445844c`.

The independent-pair four-file LAN/partial/crash/resume/cold-byte proof and nine original cryptographic/integrity methods remain separately accepted for this exact source closure. The original private pair's subsequent file attempt created two ledgered attachments but failed the second file's complete metadata convergence deadline; no original-pair full-byte or role/revocation acceptance is claimed here. That failure remains at `original-files-after-join1/result.json`, SHA-256 `39d0d0a6887a7766d9a73012178f38f1f2d4af8cc2bade924bcf81daaf1131d2`. Its latest custody is `073920bd511d35a844de548bc7d689c9636e074dea66bcc21c5ef9dd4120165a` and must be used for future original-pair work instead of the earlier join-only custody.

Any later permission promotion, removal or restoration is a distinct explicit regression action after this original-join proof. It must not be counted as part of, or a substitute for, the original single-grant recovery. Whole-space migration, all-four cloud durability, Apple device acceptance and final integration remain separate gates.
