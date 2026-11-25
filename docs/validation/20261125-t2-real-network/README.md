# Original native multi-account acceptance — 2026-11-25

## Executed result

Six unchanged original Any e2e methods passed, with zero failures and zero skips,
in 124.686 seconds on the Scaleway Mac. Each method used independent original
`any` processes and fresh native account/data directories. The original real
coordinator, three sync nodes, consensus and storage services ran in the isolated
Oracle Docker Compose project `pinkha-t2-20261125`. Its published ports bind only
to loopback. Six SSH TCP forwards transport the unchanged native protocols.
No mocked peers, fabricated ACL response, forced convergence or modified test
expectation is introduced by this execution.

- TestE2E_MultipeerInviteAccept — EXECUTED_PASS
- TestE2E_MultipeerCRDTConvergence — EXECUTED_PASS
- TestE2E_MultipeerSpaceMetadataSync — EXECUTED_PASS
- TestE2E_MultipeerDecline — EXECUTED_PASS
- TestE2E_MultipeerStopSharing — EXECUTED_PASS
- TestE2E_MultipeerPermissionChange — EXECUTED_PASS

## Source and evidence

Any source548f5cd0430a723bd26ea724daeb99991f68b9c9 and SDK
e195f6c07a053c6588e39ffe72ee4fc44cf3d953 were exported from exact Git commits.
Every canonical input file and the public node configuration were hashed before
and after execution. The original Go JSON event log, command, result and runner
fingerprint are retained here. Complete source archives and the file manifest
remain at /Users/m1/builds/pinkha-t2-network-20261125. The original network source
is anyproto/any-sync-dockercompose at960805aab318d45854f4cbd735fb28059d835573;
actual image IDs/digests and successful infrastructure health are recorded.
Private node/account keys and deployment credentials are excluded from Git.

## Remaining acceptance

This proves only the six named original methods. It does not close T2, certify
the new shared permissions UI, or prove mixed Heart/Any versions. Original offline,
cold-process, concurrent-edit and additional invitation scenarios are running
separately. The network currently has the original file-v1 service; native fileV2
transfer requires its real broker and object store, and is NOT_RUN here.
Heart/Any application adapters and real Apple UI still need source-bound acceptance.
