# Native T2 transport milestone, 18 November 2026

These are verbatim source-bound execution artifacts, with separate evidence
scopes. Source code is in the same repository under Tools/TorahNativeOperations.

## Signed host and genuine two-process protocol

Source: 12bef033a3fd217b67c0e9f2af77e242b487fad6.
Heart: d98420b1113536afd08cde6de9a5816f6d27ffff, Go 1.26.5 windows/amd64.
Job job_9f7050cb35b1 ended successfully at 2026-11-18T01:07:30Z.
The initial dependency compilation plus tests took 703.358 seconds according to
the runner; the actual two-process transport test took 2.98 seconds.

18 top-level tests and 36 subtests passed (54 pass events), with no failures.
Two helper test entries are skipped in the parent test process; the corresponding
subprocess tests execute them with their required disposable fixture environment.

The transport log records independent OS processes 2692 and 32664, distinct
peer identities, separate native and projection SQLite databases, and generated
ObjectSyncRequestStream/TreeSync DRPC traffic over loopback TCP. Both final native
trees contain 13 changes. The recorded second-client counters include 8 requests,
8 responses, 11,941 payload bytes and 8 received signed changes. It proves the
listed AB01-05 native protocol subsets, post-commit process exit/retry, real CID
rejection and fresh projection reconstruction from signed history.

This is not Heart middleware, production peer authentication or coordinator
acceptance. Both devices belong to one disposable account. It does not prove
cross-user ACL transport, block-target races, hidden/search/export/undo lifecycle,
application RPC, Swift binding, migration or iOS. Full T2 remains NOT_RUN.

Review after this pass found that OpenNativeHost/ReadTarget did not yet enforce
the supplied host key's current read membership. The 12bef pass is preserved
without overstating its security scope; a subsequent source change adds the
current-read guard and actual signed-ACL regression cases. This evidence is not
a pass for those later cases.

The shared Windows host became slow during its first dependency compilation.
An ownership-checked stop was prepared, but the job had already completed
successfully when checked. No process was stopped. This is not an interrupted
or failed test run. No further local build was started.

## Separate original component CI

Linux run: https://github.com/davidpovarsky/anytype-swift/actions/runs/44209921762
Source: c39be59df0513359ca8571397fd964fbd6a61a8c.
The downloaded artifact and its receipt prove PASS_COMPONENT_ONLY:
16 top-level tests and 26 subtests, no failures, and overlay hash identical to
the earlier Windows component proof. This older CI does not contain the signed
host or two-process transport source from 12bef.

The artifact identity and ZIP digest are preserved in manifest.json. The raw
downloaded log and receipt hashes were checked against the receipt and again
against these copied files. Heart dependency file byte hashes differ between
the Windows CRLF checkout and Linux LF checkout; their Git source pin agrees.

## Byte preservation

Raw receipts and Go logs are copied without newline conversion or sanitization;
the receipts contain no fixture private keys. The Windows receipt uses its
original CRLF bytes, so a whitespace-only CR notice is expected if diff-checking
that raw JSON as source text. The directory's attributes preserve artifact bytes.
README and manifest use LF. No fixture config, account key, database, build
product or cache is committed.
