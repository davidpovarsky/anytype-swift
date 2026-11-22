# First actual original Heart observer execution — 45008694456

Run [45008694456](https://github.com/davidpovarsky/anytype-swift/actions/runs/45008694456), attempt 1, executed the exact reviewed control commit `382e5ac62575d4df533d5ad38286ca5a09049b45`. The original Heart base is `d98420b1113536afd08cde6de9a5816f6d27ffff`, composed with unchanged r14 and frozen observer V5. This is the actual first execution, including its failures.

## Observed results

Both selected original packages compiled successfully with actual Go 1.26.5 on macOS ARM64/Xcode 27 and the original pinned Tantivy library. The original strict decoder controls passed 12/12. The native observer suite recorded 17 raw PASS, 16 FAIL and zero skips; the package and GitHub run failed. No timeout or unexpected/duplicate case was reported.

Four raw native passes are semantically unproven because a generic unavailable assertion accepted the earlier archive decryption failure before reaching the intended counter/order/common-snapshot/derived-header checks. The exact counts are preserved; they do not establish successful coverage of those four boundaries. `diagnosis/PASS_FIRST_FAILURE_MAP.json` maps all17 and states which attributions are constrained by exact source evaluation order rather than logged runtime cause text.

Fourteen native failures reached the same real defect: the observer used the original ACL key directly rather than the original per-tree derived key to decrypt persisted content. Two ACL cases failed during fixture setup because the original network `AclClient.AddRecord` path could not connect in the disposable LocalOnly runtime. No repair or second execution is represented by this evidence packet.

## Evidence and ownership

There was one normal trigger push, one finite watcher, one artifact metadata read/download and one artifact intake. The observer finished without timeout and all its owned child processes were reaped. No additional watcher or download was created.

The exact once-downloaded archive is `artifact-intake-01/original-native-schema-evidence.zip`, 2,865,799 bytes, SHA-256 `8964fc69cef15f2d70cd7064edf9248c3a26fccb07d3d63f4e9fe2a174bebdcb`, matching the GitHub artifact digest. Artifact ID14749096407 contains the full38 indexed payloads /27,149,303 bytes plus its index, with all CRCs verified. The ZIP includes complete raw native/strict test2json streams, commands, source closure and runtime receipts. Selected small extracted files are copied separately for review; the 7.5MB raw native stream and 16MB dependency listing remain available inside the unchanged ZIP without another download.

The runner observed 11,334 declared compilation input files, all9 required product/test files, unchanged original module/checksum inputs, unchanged native-library file set/bytes and source postchecks. Both executable hashes matched before/after execution. Native binary bytes were excluded from the artifact, so independent root binary rehash is not claimed. Complete CGO-generated and Apple SDK header closure is not claimed. The disposable runtime directories were removed and no wallet/account directory was uploaded.

`root-final-git-review/` preserves root's final source admission, including its original Windows argv-length read-only failure and corrected continuation; neither was a native test. `asana/COMMENTS.json` preserves the actual authorized launch and result milestone comments. No task was completed or acceptance gate promoted.

## Reuse boundary and next action

The unchanged strict12 and the13 source-independent early-rejection cases can be retained within their exact dependency closure. The proposed correction selects only the14 failed observer cases,4 masked negatives and2 failed ACL setups. That separate candidate is under review; no second native execution or pass is inferred here.

This packet does not establish native schema provisioning/repair, annotation object creation, selected-Space authority, an opaque native receipt, mapping/body ACK, original editor StageB acceptance, or release qualification.
