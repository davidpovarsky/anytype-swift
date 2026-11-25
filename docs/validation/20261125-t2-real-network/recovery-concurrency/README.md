# Original native recovery and concurrent-user acceptance

Eight additional unchanged native E2E methods passed on 25 November 2026, 04:57–04:59 UTC: InviteRefusals, CancelJoin, OverviewConcurrentEdits, P2P, P2PColdRestore, JoinerMarkdownWrite, JoinerDeletePropagation and RealtimeSync. There were zero failures and zero skips. Together with the six original methods recorded in the parent directory, fourteen distinct native methods have now passed.

The source is exact Any 548f5cd0430a723bd26ea724daeb99991f68b9c9 with SDK e195f6c07a053c6588e39ffe72ee4fc44cf3d953; the source manifest is verified before and after the run. The original tests use separate native processes and generated accounts against the retained private, live AnySync network. ANY_E2E_P2P=1 explicitly enables the original P2P cases. No original test assertions or fixtures were changed.

P2PColdRestore exercises a fresh process with the same test account and a distinct device peer ID, unreachable coordinator/sync-node configuration, actual peer discovery and P2P replication. The original assertions require local peers while network peers remain zero. This proof does not by itself establish every offline, mixed-engine, permissions-UI, or whole-space migration scenario.

The original JSON event log SHA-256 is 401aac83acc6dc54d416fc51dbe6c2ce75630475ca2d93db80a2f9ddc7f744c0. Result, exact command and controller are retained here. Original logs, commands and result receipts remain on the Mac under /Users/m1/builds/pinkha-t2-network-20261125/original-recovery-concurrency-attempt1. The original Go fixtures used t.TempDir and removed generated account/peer data during normal teardown; ANY_E2E_KEEP does not override that cleanup. No retained generated-account snapshot is claimed. The controller completed in 158.853 seconds with unchanged source and no resource stop. The public network configuration and exact image/source provenance are retained in the parent proof directory.

T2 remains open: mixed engine versions, the shared permissions interface in the Apple app, and actual fileV2 transfer still require acceptance. This is real native network evidence, not Apple UI acceptance or complete T2 signoff.
