# Retained FilesV2 revocation: actual read-authorization failure

The original retained pair reached a real signed removal, but the current native file-content endpoint still delivered the complete previously uncached synthetic canary. **Revocation read enforcement is not accepted.** The controller stopped on the first failed denial and preserved the removed state without restoring permission or repeating any completed mutation.

This handoff contains existing receipts only. It adds no product patch, build, test rerun, private account/key access or export. The held-reader/lifetime source candidate is separately reviewed and remains uncompiled and unqualified.

## Actual sequence and preserved effects

Earlier retained receipts already established the sole Writer promotion, a genuine successful 8,192-byte Writer attachment, and the sole Reader demotion. The current continuation reused those effects and the same account/file identities. None was dispatched again.

The independent-device comparison helper compiled in 18.669 seconds. Its diagnostic transport identity is separate from the simultaneously running owner, while its account signing identity is checked unchanged. The build changed only its own one-file Go overlay, made zero account opens or RPCs, and retained all 713 SDK source files. The new comparator is 47,399,229 bytes, SHA-256 `cfca1f994c7d369f3107b0b1aa29be263179083c314825231114fa1232d7b945`.

The actual Reader continuation ran as `job_5148c7b4f407`, from 09:57:38 to 09:57:55 UTC on 27 November 2026. Its internal duration was 16.897 seconds. It first verified the complete original six-record chain on each of the three pinned private nodes, in 0.647 seconds, with the original sixth head:

`bafyreifb5hglieuymrkn6sgrre3uebeiss452shvigwvd6vev3pssrdgvy`

It then issued exactly one owner Remove request, which returned HTTP 204. The owner and recipient each observed the recipient with status `removed` and permission `none`. The recipient's file metadata had been captured as `cached: false` immediately before removal.

The required next assertion was `403 acl.forbidden` for the canary content request. Instead the native endpoint returned:

| Field | Actual result |
|---|---|
| File | `E9ZfwB8Biag` |
| HTTP status | `200` |
| Content type | `application/octet-stream` |
| Delivered bytes | `8192` |
| Exact synthetic plaintext SHA-256 | `e5692a06f162eaee5563ae82736eece85a31bc83e4bd30cd8e36362469aa68e1` |
| Expected typed authority refusal | Not observed |
| Explicit restoration after failure | `0` |

That response is retained as an unqualified denial observation, never relabeled as a pass. The run did not reach its removed-state three-node checkpoint, fresh-offline denial, explicit restoration, or final restored-reader checks. No seventh-record raw export is included or claimed.

All five owned native/helper groups exited zero and were positively absent. No forced cleanup or unresolved process remained. The original 1,594-source/base-native and current 1,599-source/native admissions were unchanged. All previously retained original CAR hashes were preserved. The failed canary request itself may have populated recipient cache, so later work must not describe the current original recipient as still uncached or clear its cache to reproduce the prior condition.

## Exact receipt custody

| Artifact | SHA-256 |
|---|---|
| `independent_helper_build.json` | `b49b5d7c27e2adedbf7c8a748a04e593a55daa4b58e31ad3f644ce652e80207e` |
| `actual_revocation_failure.json` | `ecd4e58378cbb82731926536e82fca655da64ee156057ba411a242c95942c2ab` |
| Final original-account custody manifest, retained privately on Oracle | `792268b4d7448d9c9b6665ee6388f26c18e5de0635aa05f1b390db7f20a5567d` |
| Pre-mutation closed Reader6 snapshot manifest, retained privately on Oracle | `c714c54d36bc67bfd53e79f7b61d1dcd6035a2ea6eefbced2fcc7aa283514232` |

The first receipt's original path is `/mnt/development/projects/evidence/pinkha-w1-role-helper-20261127/result.json`. The second is `/var/lib/pinkha-c-filesv2-20261126/original-native-authority-reader-continuation1/result.json`. Its sibling `private-current-accounts.json` preserves the final closed-state inventory. Private account contents, keys, stores and snapshot manifests are not part of this Git handoff.

The pre-mutation snapshot was captured before any process or Remove in the continuation, from the already closed six-record Reader state: 36 entries, 10,628,089 content bytes, 10,739,712 allocated bytes. The run verified that this unopened snapshot remained unchanged at finalization. This is a custody observation, not direct held-reader acceptance.

The unchanged earlier failed receipts remain part of the causal chain: `70f6dd9f6ae6eb24e6d6eaced2387bdea8511a396981d66888dd7338a02a59bf` for the first Writer/publication attempt, and `24d00c2cad87b9943050f453288c132406cf56267b145c83cbabeb2be7bc5c94` for the sole Reader demotion followed by helper failure. The current run did not rewrite them.

## Source and acceptance boundary

Current native remains `0796b939145f98fd3436b40c3ae3c7c9daec239b54f8c1fa237fb20a349d0b07`, with 1,599-file manifest `e785ed2faf1d0bf0d18e7be7f0090cdee4061bd714f3be1509927895b9df336a`. Helper controller `ca856b106263b25937fce0da76733b4bc2476304a32947294d4b1538cc02699e` and Reader continuation `21933a4d9b7bc05460e5f1f0de5617284fb0a597ed09427e0e5c1936c353c78a` are identified by the original receipts; publication does not invoke them.

The separately reviewed source candidate `874220977c12a789d77acbd7a86fa4889693a5196c32ef52effac20207dcc32f` proposes current signed ACL/generation and concrete account/loaded-Space lifetime fences around `Files.Open`, held Read and Seek. Its 21 synthetic signed-ACL/lifetime methods have not run. `Reader.Close` is intended to wake pending fetch/lifetime work; it does not promise to drain a bounded memory copy already admitted just before Close. Actual retained-account read correction, fresh-offline refusal, held-reader behavior and explicit restoration remain open.

The current narrowed follow-up is only synthetic unit-qualification preparation and preservation/publication of the already produced failure. No retained private account/key access, copy, open or export is authorized by this publication. Compiler/native starts require a separately reviewed controller and root-coordinated resource window. Prior nine crypto/integrity methods and twelve network, two ACL and two Linux P2P results remain retained under their original source/platform scopes, without rerun. This handoff creates no Apple, cloud-durability, full T2, or release acceptance.
