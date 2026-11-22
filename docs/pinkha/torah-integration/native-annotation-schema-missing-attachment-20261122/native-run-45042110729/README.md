# Missing-attachment diagnostic: one native FAIL, six complete state pairs

The unchanged `MissingAttachmentUsesOneNativeApply` acceptance child still failed. Original native compilation passed, all six read-only diagnostic captures completed, and no other child ran. The twelve passing registration controls remain preserved at their original source and run.

| Identity | Actual value |
| --- | --- |
| Frozen diagnostic source | `b93b7b351cfeb625607b5b7d86aef7c29fe78b0b` |
| Original registration product | `60b8300c3506e53638c8ca883f82484de073fae8` |
| Original Heart | `d98420b1113536afd08cde6de9a5816f6d27ffff` |
| Actual run | [45042110729, attempt 1](https://github.com/davidpovarsky/anytype-swift/actions/runs/45042110729) |
| Job | `137268621948`, `failed-native-child` |
| Artifact | `14762199006`, `Otzaria-Schema-Missing-Attachment-45042110729-1` |
| Original ZIP | 2,634,204 bytes; SHA256 `270b824b9c0210cd1cd584db0315215678bfa04c29c4251692527c57e403fd6e` |
| Diagnostic manifest | SHA256 `0653a672d696f200e1333b163a6e6362262e46629e0d70346069607d68652744` |

The run was created at 16:08:07 UTC and GitHub recorded terminal failure at 16:23:42 UTC on 22 November 2026. Actual Go 1.26.5/macOS ARM64 compilation took 131.344 seconds. The native command took 3.369 seconds, reported process 24081, and selected exactly the parent and the one unresolved child. It retained the original failure: `loaded type differs from complete persisted native state`. The failing registration phase recorded zero creates, `apply=false`, and `returned=false`.

## Exact paired-state discriminator

All six pairs have identical loaded/persisted tree heads and native `proto.Equal` details. The only differing block is ID `dataview`. Its top-level `model.Block.restrictions` is an allocated empty message in loaded state and absent in persisted state. This is not a field inside `BlockContentDataview`.

The difference is present from `00-registered`, before the fixture's three subsequent setup mutations, and remains at all stages through the deferred after-attempt capture. For every pair, the loaded block has exactly two additional bytes, `1a00`, at offset 10: field 3, length zero. All remaining bytes of that complete block match the persisted block. Every other complete block matches directly. Thus the actual loaded and persisted protobuf bytes are **unequal**, with the difference precisely localized; this receipt does not alter or normalize them and does not change the failed native outcome.

`DIAGNOSTIC_PAIRED_FIELD_DIFF.json` presents the field location. The six `missing-attachment-*.json` files retain original complete protobuf bytes, their hashes, native JSON, account/Space/object/ACL/archive identity, tree heads and the original equality decisions. `RESULT.json`, `COMMANDS.json` and the complete ZIP remain the original runner outputs.

## Original source explanation

At exact Heart `d98420b1113536afd08cde6de9a5816f6d27ffff`, `core/block/simple/base/base.go`, Git blob `c4a0a0dd7cb2985df66a02a27a3e8c7c9c173d55`, `Base.Diff` replaces a nil `Restrictions` pointer in both compared blocks with a new empty `model.BlockRestrictions`. It then emits a restrictions event only when the dereferenced values differ. The original `Dataview.Diff` calls that base method before its view/link comparisons. Consequently, a live nil-to-empty allocation may occur without a corresponding persisted event. This exact original behavior explains the observed two-byte difference while heads, details, views and other block content match.

The retained original source is provenance for a separately reviewable future fix. No product change, comparator projection, extra native mutation or rerun is part of this evidence. A later fix must preserve every meaningful restriction value, all remaining block fields and the actual persisted-head guard. The strict persisted observer and its raw output remain unchanged.

## Verification and limits

The read-only verifier checked ZIP CRC, exact membership and all 48 payload hashes; all 18 command streams; the exact one-child start/terminal sequence; six complete scoped pairs; every embedded protobuf hash; all 20 compiled product/test input hashes; 18 unchanged previous inputs; and all 13 earlier composed baseline inputs. It also checked pinned formatter equality, post-execution source/native dependency checks, and owned disposable cleanup. The binary hash is a runner observation; the executable was excluded from the artifact and was not independently rehashed.

From a checkout of this evidence commit, run `python3 verify_missing_attachment_artifact.py` in this directory. The verifier reads the adjacent frozen diagnostic packet and the existing registration packet, and writes its receipt locally. It never compiles or executes native code.

The sole finite Sentinel observer `job_6fdc32065bdf` succeeded at 16:24:10 UTC with exit code 0 and `TERMINAL_ARTIFACT_RETAINED`; it retained the native failure without converting it into success. No observer, CI dispatch or acceptance replay was started by this publication.

The exact successful explicit-file formatter script and prior local collector proof are retained separately. The earlier formatter timeout remains in the source packet; its exact initial script text was not retained, so no claim is made that its cause was specifically stdin/EOF or Go startup.

Swift/RPC generation, native bridge behavior, selected-destination production wiring, ordinary annotation creation/recovery, body/import-map authority, COMMIT and ACK remain separate open dependencies.
