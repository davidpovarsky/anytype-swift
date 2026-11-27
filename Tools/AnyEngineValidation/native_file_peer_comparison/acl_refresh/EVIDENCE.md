# Evidence and acceptance boundaries

## Observed original failure

The retained original failure and continuation remain under `/var/lib/pinkha-c-filesv2-20261126/attempt1` and `retained-invite-continuation1`. No replacement identity, invitation or grant was introduced during diagnosis.

`retained-sync-diagnostic5/result.json` has SHA-256 `412af4d6ee05bbf1051726ff8fc488fb4df33b5017b3206fff911577be638774`. Its nine observations show the owner with three network peers and an empty pending-request list while the original recipient remains `409 space.not_accepted`. Both native processes exited with code zero and their owned process groups were absent at finalization. The exact latest account inventory is retained privately with SHA-256 `bfcc893ae6f7516441804365b2fac28be445c5468b1ee5d15c706746251b1621`.

## Verified chain comparison

`acl-verified-comparison8/compare.log` has SHA-256 `4f5175f2e5c4000244da9672b3f34b6a593fa5a6afcd2ce6711cd43d8c185f20`.

The original SDK loaded an exact copy of the owner's existing credentials and an independent, stable copy of the space database. It used the original `BuildAclListWithIdentity` and `AclSnapshot` paths to validate the two chains. Both have the same ACL root. The local chain contains two records; the network chain contains three and identifies the existing recipient's pending request. The comparer exited with code zero; its owned process group was absent. The original account inventories and all 1,594 retained source files remained unchanged.

The original wrapper incorrectly parsed the final shutdown-log line as JSON. That failure is retained. `acl-refresh-overlay1/diagnosis.json` qualifies the unique diagnostic JSON record from the hash-pinned original log without rerunning the native comparer. Its SHA-256 is `a0d862afa0ba3c8f9b5c187bc1c32641027608322fe9c7f35c049062bb6ccaee`; its status explicitly says `PASS_DIAGNOSIS_ONLY_NOT_FILE_ACCEPTANCE`.

## Source preparation

`acl-refresh-overlay1/result.json` records `PREPARED_NOT_TESTED`. The isolated SDK source is 6,604,519 original bytes across 713 input files. The patch adds three files and modifies one, yielding 716 files. The complete overlay source manifest has SHA-256 `81fb6bf29c672010f7fe98554ae562b7e75b6154f10e933ac5682fe3916c4a4a`.

The initial patch encoding had SHA-256 `589505c1ec942b8068ac231871ec60093f19c309fedb8d7522a17d2d715f8d11`. The source admission still verifies Any `8fbd1e819fb132ac0e0a848d2ddf5c5714189b81`, SDK `c1fd59bd8f0ed62471234ec1a65a402d22eab6a9`, original native binary SHA-256 `1dc1803c656da2215760477dadd26bf0e829b6ee592e337db6fa0295a6ed9636`, and 1,594 unchanged retained source files.

## Replay packaging qualification

The first applier check exposed missing `new file mode 100644` headers for the three added files. Its failed result remains at `acl-refresh-replay1/result.json`, SHA-256 `afc8c6e2a28ff1394c16d53a3cf85bb3d98feb20cc23d45e1a01156d5ac7c7a0`. The patch packaging was corrected by adding those three headers only. No Go source bytes changed.

The final replayable patch SHA-256 is `1d4213438a5d9e8024f5506309bd759ef6a72ef9d880ce9269392fc185f43f6c`. `acl-refresh-replay2/result.json`, SHA-256 `316aa607523802417380357481bca061d6dfe33d5f1557f0d25eeb23695f5b14`, records successful `--check-only` and actual application to a fresh independent SDK copy. All 716 resulting source files exactly equal the same overlay manifest used by the passing regression tests. The original SDK export remained unchanged. This source-only packaging correction does not require repeating tests of identical Go source.

## Focused SDK qualification

`acl-refresh-unit1/result.json` has SHA-256 `7827178191ca7ea6dda4bb26a1272bd6bcc1523e288b1df13f5d6e99275d767a`. The actual `go test -json -count=1 -p=2 -run '^TestRefreshACL' ./internal/anysyncx` process exited zero in 102.795 seconds including compilation. All six named tests passed; no test failed or skipped. The original JSON test log has SHA-256 `3be76c4f85bcbf751e2712e92ec9b2ac6e9078c28894f7c239fd16813667be8c`.

The combined controller correctly retained an overall failure when the separate production-hook compilation could not meet its 2 GiB plus 384 MiB free-space reserve. The six actual passes were preserved, not rerun. After reclaiming only attributable, unused compiler intermediates, `acl-refresh-hook1/result.json` continued the still-missing compilation. It pins both previous hashes, verifies unchanged original and overlay source, and records `go build -p=2 ./internal/spaceimpl` exit zero in 23.028 seconds. Its SHA-256 is `bd35ba50a31ba7cc82c73a20a19fa7eeb96f4e5027d957976d46eba744425d5d` and status is `PASS_FOCUSED_SDK_TESTS_NOT_NATIVE_ACCEPTANCE`.

Both owned compiler groups were positively absent at finalization. The original 1,594 source files and the 716-file SDK overlay remained byte-identical. These tests did not start the retained native accounts or make network grants.

## Actual native build and retained-owner recovery

`acl-refresh-native1/result.json`, SHA-256 `bfafdf6d7304786726235fd1d2f3065dbf5782091123f03fbd6bb54b09328380`, records the actual 86.205-second build with exit zero and positive process-group absence. Binary SHA-256 is `79248a63132a0146deff4e9fe1c4104a381a34d5c2ffcad536247a8429f98857`. The exact 1,597-file source manifest has SHA-256 `44abb44523e01b4631c8eff5f3ff183aca17f58b472fbb041e7a1e501028ca68`; only the four SDK overlay files differ. The original 1,594-file source stayed unchanged.

`retained-acl-recovery1/result.json`, SHA-256 `8793e1eb84315d793022b8f1ed6ea98247a94b5acfc67e37cbbe845696eb2e8d`, remains `FAIL_RETAINED_ACL_RECOVERY`. The fixed native binary returned the exact original Bob pending request on the first owner request-list read. Exactly one ordinary Reader grant returned HTTP 204. No initialization, replacement invitation or rejoin was performed. Bob still returned `space.not_accepted` for the bounded 90-second observation, so complete membership acceptance was not claimed. Both native processes exited zero with positive process-group absence. The latest private original-account custody inventory has SHA-256 `9e0719b6bf2837c9717de89e61e5d49cf9b7478458e34a2117a61fbf4e95025c`.

`retained-grant-comparison1` reused the earlier qualified signed-chain reader. Its log SHA-256 is `c41f800b5fabbd280b725ec3adc260c42898558f10fe5563c73b5fffcf7491bf`. The stable copy of the owner's database contains a valid four-record chain whose last record is the grant, while the selected node snapshot contains the earlier three-record pending chain. Both roots and signatures validate. This node read is not a consensus-authority proof: the original NodeClient selects one available tree node. Per-node publication diagnosis is still open; no second grant or data-store injection has been attempted.

## Separate native file and integrity qualification

Exact custody copies of a genuinely granted independent production pair passed the four-file LAN transfer, large partial read, intentional SIGKILL, persisted partial offline read, resume, thumbnail and fresh OS-offline full-byte pipeline. Receipt SHA-256 is `c23b78e312fa9efbe1a5fe7abd9e0061e131a0514fdb4fc07cf12ebe42376692`. This proves those operations with the new native binary but does not repair or bypass the separately retained private invitation failure.

Nine original unchanged crypto/CID-integrity methods also passed with no failures/skips, receipt SHA-256 `99ccdd67f5514a1eda4304decde8e5766453a339dfc667980b9a9398ba74d0ac`. Details, byte hashes, MIME-contract correction, source identity, crash/process gates and preserved failure are in `../FILES_V2_LAN_EVIDENCE.md`.

The original 12 network scenarios, two permission-enforcement cases and two P2P cold-restore cases have not been rerun. They remain evidence for their recorded, unchanged original inputs. This package is not a claim of whole-space migration, all-four cloud custody, original private membership recovery, Apple or physical-device qualification, or release readiness. Wave 3 owns final integration.
