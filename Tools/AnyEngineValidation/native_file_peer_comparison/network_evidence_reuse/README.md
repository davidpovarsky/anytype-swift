# Retained T2 network evidence and current source delta

## Qualification performed here

This is a read-only verification and reuse ledger. The audit checked the exact retained archive hashes, selected original member sizes/hashes, raw Go terminal records, original lifecycle receipts, source manifests and current executable hash. It started no compiler, native peer, account or test and issued no network request from the controller.

Audit: `retained-evidence-audit.json`, SHA-256 `f02e889371683127cd9dc9e821d38a1bc51cd28ac46ce7dc548aca42d1134cfa`.
Controller: `qualify_retained_network_evidence.py`, SHA-256 `fdaebfee76dd9aa67d6924b1a60f918e64cf2602b0c0f2e40d6646e1b7e0ab8e`.
The read-only audit completed in 4.938 seconds. Its PASS describes evidence verification, not a new product execution.

The retained results contain **12 distinct network methods, two fixed remote-authority methods and two Linux P2P methods**. All remain scoped to their original versions and platforms. Raw logs and disposable account stores remain private in the original archives; this directory publishes only method outcomes, provenance and source boundaries.

## Twelve original network methods

Each row ran in both original owner/member version orientations. These executions used the original Mac native CLIs: Any548f5cd / SDK e195f6 against Any41c07bd / SDK c1fd59. The exact executables were SHA-256 `8d92bbfa55eaad625c814f27bd918d7b6f63d4bfb48c6e6fdf9d0b469a07f129` and `6ff900f1354f11044d8619e3ce1c0a20673d0608fd4bd3b50ff0bd4bb850f9ba`.

| Original method suffix | Old owner / new member | New owner / old member |
| --- | ---: | ---: |
| InviteAccept | PASS 16.55 s | PASS 29.66 s |
| CRDTConvergence | PASS 17.10 s | PASS 10.67 s |
| PermissionChange | PASS 15.91 s | PASS 11.86 s |
| StopSharing | PASS 13.20 s | PASS 13.88 s |
| OverviewConcurrentEdits | PASS 19.64 s | PASS 29.40 s |
| InviteRefusals | PASS 37.99 s | PASS 73.73 s |

These are method-level results. The original records preserve two important distinctions:

- The InviteAccept run has an original **FAIL collector receipt**, SHA-256 `138e97950b965088d55fb02ebf8e8819696d6c7766c37606a45d3efe53b99fd8`, despite two native methods and the Go package passing with exit zero. Its separate process-observation qualification `e9969aa6cb019f7d47d6adb8bf78df48cf6cdc39f55936fada30036601bd4a8b` checked the original evidence and exact process-group absence without invoking new tests. The audit retains both records.
- The two InviteRefusals passes occur inside `mixed-remote-authority-attempt1`, whose original result remains **FAIL, two pass / two fail**, SHA-256 `4592e388798000aaf62cf4833f67b15935661978a268aa3530ff18c8c0ea31da`. The failed role methods are recorded separately. Their failures are not reclassified by counting the two successful refusal methods.

The eight-method run remains `PASS_EIGHT_REAL_NATIVE_MIXED_VERSION_NETWORK_SCENARIOS`, receipt SHA-256 `94cee86068682bbee962024f61b889130fe3eb8441803198ac749fd44f16414b`, raw log `615e1be438541e5251560038e125710c39031f234b11da3046384293c730f1e9`. Its package completed in 132.042 seconds. The earlier 12/12 failure against the lost temporary infrastructure and both original Mac P2P failures remain retained failures.

The first ten methods are preserved in:

`/mnt/development/projects/evidence/pinkha-t2-mixed-originals-retained-20261126/original-t2-mixed-build-and-executions.tar.gz`

Archive SHA-256: `8999a6a781ae416050c828e48b0d0d72e7b85e7f62511459f66a49d0d8ca0d7d`; 54,616,872 bytes. Its 45-member inventory is `9d1c291f873a2d1719e660a2d7e30e5eb0d1971df5abf2072b21054c4ba095a0`. This archive alone contains ten qualified network methods, not all twelve. The two additional refusal methods are in the second archive below.

## Two fixed remote-authority methods

The actual corrected mixed-version role executions both passed: old-owner/new-member 15.53 seconds; new-owner/old-member 13.64 seconds; package 29.490 seconds. They used Any `8fbd1e819fb132ac0e0a848d2ddf5c5714189b81` / SDK `c1fd59bd8f0ed62471234ec1a65a402d22eab6a9` and the minimal legacy backport Any `9a190eb8236f18da75e5d85c3d1db31cd558d098` / SDK `e195f6c07a053c6588e39ffe72ee4fc44cf3d953`.

The Mac executable hashes were `8df7897ee6f45cdcef28c42fe025ad6f69062f15db779a660660cdc4016b00f7` and `ab8b03dee941645eb1608f49f1611b56e0e62f5fafb0b0d82a996dab13eaa647`. The older uncorrected548/41c executables do not acquire this PASS.

Receipt: `b8694dbd2ac3facce43771bdb7f206461d1b95924a5ccb1248114185a394ce1d`.
Raw log: `36aee08b83cdefc5a097f40defd23ba85664f966df37c485f8d752f19723892e`.
The original receipt requires zero forced stops, unchanged sources and an absent owned group.

These scenarios cover actual signed canonical-content reads, a successful member Writer write and owner convergence, Reader read with write refusal, restored Writer, and observed ACL removal with defined 403 read/write denial and no private payload. Their object/content authority boundary does not by itself prove the FilesV2 plaintext-reader boundary.

The complete fixed-role originals and the earlier failed role runs, including the two successful InviteRefusals, remain in:

`/mnt/development/projects/evidence/pinkha-t2-fixed-originals-retained-20261126/t2-fixed-originals-private.tar.gz`

Archive SHA-256: `eb56b9e55ef24aa87e6d732f36d112f9e7cbb1adca29309dc66d80b1cc2eb546`; 213,543,961 bytes. Inventory SHA-256: `52ab4da287fcd19a6abd3aa2481e6523bbf056343d1c9acb10f410102f42517a`; 6,964 entries. This private archive was read in streaming mode; no account member was extracted or opened as a native store by this audit.

## Two original Linux P2P cold restores

The original methods passed on Linux/arm64 with real independent native CLI peers and zero network peers: old-owner/new-member 6.98 seconds; new-owner/old-member 65.25 seconds; package 72.253 seconds. Their original 120/30-second deadlines and assertions were preserved. The original Mac failures remain failures.

Retained directory:

`/var/lib/pinkha-root-t2-linux-20261126/p2p-cold-originals1`

- RESULT SHA-256: `13931e7aba8941b0d71113626ec9349e3495cd99ba1cc1bc79723b81e3cd410f`.
- Raw log SHA-256: `55eb7f90b4c7214b645c5583c45218ac55ab9074853a86a0c1056575b0c607dd`.
- Source qualification SHA-256: `6ed8f71ba7a44a44e9a7fc48a1d4f714b913063a23abfed34368585bf49afb57`.

The current Linux executable is `1dc1803c656da2215760477dadd26bf0e829b6ee592e337db6fa0295a6ed9636`; legacy is `29fb9c39bd5b18d1dfc52a116f5b1635ac636400a850ce2cfadb5db20afc2481`. Their versions are the same fixed8fbd/9a190 source pair above. Only binary hash pins and diagnostic commit labels changed in the original wrapper; its inverse restores every original byte. There was no assertion or deadline change. The original SOURCE_QUALIFIED_NOT_EXECUTED qualification is an admission record; the separate RESULT and raw terminal records are the execution proof.

## Exact boundary of the current seven-file overlay

The qualified original current source contains 1,594 files, manifest SHA-256 `12ad65cd178aa31b6aa5761d42507d8618f1d3d4865a627548af2036c0a40a6c`. The current LAN-progress executable is `0796b939145f98fd3436b40c3ae3c7c9daec239b54f8c1fa237fb20a349d0b07`, built from 1,599 files with manifest `e785ed2faf1d0bf0d18e7be7f0090cdee4061bd714f3be1509927895b9df336a`.

The exact source-manifest delta has seven SDK paths:

| SDK path | Change |
| --- | --- |
| internal/anysyncx/aclrefresh.go | Added bounded original signed-ACL fetch/application |
| internal/anysyncx/aclrefresh_test.go | Added signed-chain negative/positive controls |
| internal/spaceimpl/members.go | Added membership refresh hook |
| internal/spaceimpl/members_refresh.go | Added bounded/coalesced membership refresh integration |
| internal/anysyncx/peermanager.go | Changed queued keepalive bookkeeping and bounded node discovery |
| internal/anysyncx/peerprogress.go | Added ordered bounded node concurrency and independent local/global progress |
| internal/anysyncx/peerprogress_test.go | Added starvation/cancellation/coalescing controls |

The audit records every before/after SHA and size. Every other original manifest entry is unchanged, including the CRDT implementation, ACL signature validation, native HTTP permission mapper, file encryption/integrity code, SDK module declaration and lockfile. This is an explicit source-delta argument, not a claim that the old network executions ran the new executable.

The changed boundaries have separate actual qualification: six signed-chain tests using the original validators; the 17 focused peer tests; original retained request/sole-grant recovery; and the native0796 same-four-file continuation with a fifth thumbnail, exact ranges, real SIGKILL, cold OS-offline partial bytes, resume and final cold reads. See `../acl_refresh/RETAINED_JOIN_RECOVERY.md` and `../lan_progress/NATIVE_ACCEPTANCE.md`. The latter receipt is `0c0d4622bff1075d7da331b3f2d393aa536ce688e05a92013defde153210c5da`.

At this ledger's publication, the original-pair current FilesV2 Writer/Reader/removal/restoration controller is prepared and independently reviewed but has not run because its native runtime slot is held for resource recovery. No current file-revocation PASS is inferred from the retained object-role tests. Apple UI, cross-engine Heart/Any compatibility, full-Space cutover and release qualification remain their separate gates.

## Rechecking this ledger

The controller is optional for a future custody audit; passing product stages should not be rerun merely to regenerate this document. It refuses an existing output file, opens only the named retained archives/receipts/source inputs, validates the exact original terminal records and source deltas, and writes a filtered report. It never mutates the archives, accounts or native source.
