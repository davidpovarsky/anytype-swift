# FilesV2 current-authority repair and qualified native product

The SDK now revalidates current signed read authority and the captured application/Space lifetime before releasing file bytes. The actual qualification combines 35 signed-ACL/lifetime events, two fresh synthetic `Files.Open` integration methods, one complete Any/Anytwo native build, and 14 ordinary HTTP denials on the original removed member. The original insecure HTTP-200 receipt and the first fixture compilation failure are retained.

## Why the repair is required

The original role continuation successfully removed the member and observed `removed/none`, but an existing file content route returned HTTP 200 with the 8,192-byte canary. That failure is published in parent commit `92a2904112738619f2f689b137ba663b08378730`, raw receipt SHA-256 `ecd4e58378cbb82731926536e82fca655da64ee156057ba411a242c95942c2ab`. A successful membership mutation alone therefore did not qualify subsequent file access.

The repair captures the real signed ACL identity, root/head and application/Space lifetime for each reader. A read or seek must pass current authority checks; a fetch writes into a private buffer of at most 64 KiB, then rechecks authority before copying bytes to the caller. The final copy is protected by the existing ACL read lock followed by the short lifetime token lock. Network waits and close-attempt waits hold neither lock. Current removal, signed head changes, application retirement and same-ID Space reload invalidate an earlier reader. A declined `TryClose` preserves its still-live wrapper; committed close retires it without resurrecting an old token.

`Reader.Close` cancels pending operations and close-attempt waits. It does not drain a bounded copy that was already admitted immediately before `Close`; that exact boundary was reviewed and remains explicit. Previously released plaintext cannot be recalled.

## Actual evidence

| Stage | Actual result | Exact raw receipt SHA-256 |
|---|---|---|
| Signed ACL/lifetime qualification | 21 parent methods plus 14 subtests: 35 starts, 35 passes, zero skips; two normal absent groups | `68964e6db8802065ba69edad5614ec52cde3603b14f9628d65d808aa76563766` |
| Fresh SDK fixture attempt 1 | Preserved compile-only failure, zero test starts, no SDK/account open | `411fc3533f77073019e348e48c8cb73643c12a765e6d0cfd7a579bd550f71a7b` |
| Fresh SDK fixture attempt 2 | Two actual `Files.Open` methods passed under OS outbound denial using new synthetic identities/data | `4eb696473d3cc199f935f826944a03681e0decd16047039579aba9718fc2ff35` |
| Absolute HTTP deadlines | Two actual slow-header/slow-body controls passed, including timer/handler/mask restoration and process closure | `0a2da3fdb8c1d962a0e6d74e750292dc934ff5c826c0b025bb38702717394db6` |
| Corrected native producer | One actual `cmd/any` build and two toolchain/module metadata commands; all three groups normal and absent | `e26587d911cec570f9215db8bc424f9faa7fe2d09c4354f71cdb772e6fafd394` |
| Original removed member HTTP continuation | Fourteen strict `403 / acl.forbidden` decisions, seven online and seven in a fresh OS-offline process; all three groups normal and absent | `7efa899783f5cabb54b2693dca0a22a9571d499ef4b9838749dfb8e677784099` |

The individual stage reports describe the boundary established at that stage. This table and [HTTP14.md](HTTP14.md) include the later completed product and HTTP acceptance. Original network, crypto, migration and cloud receipts retain their original product/source scopes; no prior successful test was rerun by this tranche.

The first fresh fixture used the wrong native ACL API type: `Records()` returns decoded `AclRecord` objects. The corrected fixture captures original `RecordsAfter(ctx, "")` raw records under the same read lock as root/head/count, checks their exact first/last/count, then uses the unchanged complete native verifier. The production patch did not change between that compiler failure and the successful fixture.

## Exact standalone product for Wave 3 and other consumers

| Binding | Value |
|---|---|
| Any commit | `8fbd1e819fb132ac0e0a848d2ddf5c5714189b81` |
| SDK base commit | `c1fd59bd8f0ed62471234ec1a65a402d22eab6a9` |
| Standalone Sync dependency | `github.com/anyproto/any-sync@v0.13.8` |
| Build workspace | `GOWORK=off`, Any uses its local `.runtime-artifacts/sdk-source` replacement |
| Base Any source | 1,599 files, manifest `e785ed2faf1d0bf0d18e7be7f0090cdee4061bd714f3be1509927895b9df336a` |
| Readguard overlay | 10 paths: seven production and three tests; manifest `ac2f849e1ca2d7bda725c9c10b46af58d2ac39876a4abf26fa3ce37479d0d896` |
| Readguard patch | `874220977c12a789d77acbd7a86fa4889693a5196c32ef52effac20207dcc32f` |
| Fresh integration fixture | `b7d91dd885239f0b5c7cad99d22985affd3d20cc554b9f097487ce2be6dfc76b` |
| Guard SDK source | 725 files, manifest `d2fbd4f75d80e14c518f9ed84fac80ceda5f83e59bfb59108b308b745a845661` |
| SDK including fresh fixture | 726 files, manifest `8f572975bb767e6eb573d30061015382a2c4133c0065f84a635e44e276ca8d34` |
| Complete native source | 1,607 files, manifest `aa43f853a28c2cd0e125b70cdcc01b05a4748f0c25541f5ed86cea511e6b8dd1` |
| Native executable | 78,093,866 bytes, SHA-256 `1b25764f9af1af854a928b3c445044a6906cb3477b64b4da6689b9e29997e639` |
| Retained executable | `/var/lib/pinkha-c-filesv2-20261126/readguard-native1/any` |

The complete source and executable remain beside the retained producer receipt. The executable is not placed in Git. A consumer must verify the complete producer/source tuple rather than infer acceptance from a commit label or filename. Root's fresh ordinary uploader will consume this same binary; this handoff does not require another native build.

To prepare the standalone SDK on an independent copy, retain the existing source order:

1. Original c1fd SDK and original 1,594-file Any closure.
2. Published ACL refresh `1d4213438a5d9e8024f5506309bd759ef6a72ef9d880ce9269392fc185f43f6c` and LAN progress `d6afca4fe2267c4b1da15b246619851fbbd31e19e91d6b42846e96096fc31c65`, already described in the parent two-product ledger. These produce the exact 1,599-file baseline.
3. This handoff's `Tools/AnyEngineValidation/native_file_read_authority/sdk_overlay/sdk-files-readguard.patch`, checking every before/after entry in its manifest. This produces 1,606 source files and the 725-file SDK.
4. Add the exact fresh integration fixture only when reproducing the qualified 1,607/726 source closure. Do not mislabel a different production-only source map as the accepted complete map.

The seven production SDK paths are `internal/anysyncx/app.go`, `internal/anysyncx/file_read_lifetime.go`, `internal/anysyncx/spacecache.go`, `internal/files/readguard/readguard.go`, `internal/readlifetime/lifetime.go`, `internal/spaceimpl/files.go`, and `internal/spaceimpl/files_read_authority.go`. Original Any HTTP source was unchanged by this patch. It uses the existing typed ACL error mapping, now observed as `403 / acl.forbidden` on the content routes.

## Integration boundaries

This executable contains the standalone Any/Anytwo product. It does not embed Heart, qualify a new combined Go workspace, or establish Apple bindings. Heart core/RPC/FullSpace and account-run activation remain separately owned and qualified by E and Wave 3. The earlier two-product source ledger still distinguishes standalone Sync v0.13.8 from the Heart workspace's local Sync source.

The original removed member remains removed. The HTTP continuation did not restore a role, repeat a join, reattach a file, export signed private records, inspect account-file contents, or claim a new account byte inventory. Its five metadata rows remained cached while content was denied. No cloud durability, quota recovery, deletion of previously received plaintext, UI or Apple runtime acceptance follows from these checks.

The earlier original same-four LAN proof, 8 MiB partial/crash/resume/offline proof, nine original crypto/integrity methods, 12 network scenarios, two ACL enforcement checks and two P2P checks remain preserved. Their receipts should be joined by explicit source-delta reasoning, not relabeled as executions of this new binary. A separate T2 gap assessment follows this publication; no broad replay is authorized merely by this source handoff.

## Newly observed metadata boundary remains open

The successful HTTP14 receipt also records removed-member `Files.Get` responses containing cached file metadata. This is an observed remaining boundary, not evidence that metadata is protected. The exact SDK `docs/files.md` in the accepted1,607-source map is SHA-256 `a603d071211aac5dd879a7c703b7282c412458934d905ec8af8360da1e7a4f8b`; it describes `Space.Files()` for members, with sealed `Name`, `Mime`, `Variant` and `VariantOf`, and a separate `Space.Payloads()` route for keyless/broker readers. It states no removed-member local-history exception.

The unchanged `Files.Get/List` implementation maps retained decrypted row metadata without the new current signed-authority/lifetime fence. A separate minimal SDK metadata guard and fresh synthetic qualification are therefore still required. Status, Stats, Query and subscription neighbors must retain their separately assessed scope. This publication closes the demonstrated content-release and held-reader gaps; it does not declare all file metadata authorization complete. The original14 calls are not rerun or relabeled for that next tranche.
