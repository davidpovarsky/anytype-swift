# Native restriction defaults in complete schema-state comparison

Status: source reviewed; actual semantic/native execution remains pending. This packet changes one registrar comparison and adds four focused original-model controls. The existing failed native child, all its setup writes, all acceptance assertions and all six raw diagnostic observations remain exactly at diagnostic source `b93b7b351cfeb625607b5b7d86aef7c29fe78b0b`. The twelve previously passing registration children are not selected.

## Observed failure and original cause

Actual native run [45042110729](https://github.com/davidpovarsky/anytype-swift/actions/runs/45042110729), attempt 1, compiled successfully and failed only `MissingAttachmentUsesOneNativeApply`. Its six complete raw pairs show identical heads and native-equal details. In each pair, the top-level `Restrictions` message of block ID `dataview` is present and empty in loaded state and absent in strict persisted state. The complete block differs by exactly the two extra bytes `1a00`; all remaining block bytes match. The prior failed source and all six original raw pairs are preserved at evidence commit `8885a230159570a58ab2b8de4d09df632dcfc8f1`.

Original Heart `d98420b1113536afd08cde6de9a5816f6d27ffff`, `core/block/simple/base/base.go`, blob `c4a0a0dd7cb2985df66a02a27a3e8c7c9c173d55`, makes this allocation in `Base.Diff`. It replaces nil top-level `Restrictions` on both compared models with an empty `model.BlockRestrictions`, then emits an event only if the dereferenced values differ. Original `Dataview.Diff` calls this method first. Thus original runtime processing can introduce message presence in memory without persisting a restrictions event. The two exact original source files and their hashes are included and verified against the real native checkout before compilation.

## Product change

`sameSchemaBlocksWithNativeDefaults` retains complete block membership/identity checks. For each matched pair, it deep-clones both complete original protobuf models, fills only a nil top-level `Restrictions` pointer with an empty original message, and calls full `proto.Equal` on those copies. Every nonnil restriction, nonzero restriction value, nested block field, view, relation link and other represented field remains compared. Neither original input is modified.

This is semantic equality under the original native default, **not raw protobuf byte equality**. The actual raw observations remain unequal when message presence differs. The comparison claims only state represented by the original generated model; it cannot recover unknown wire fields that an original decoder discards.

The exact generated-model audit is complete in `GENERATED_MODEL_SOURCE_EXTRACT.json`: `models.pb.go`, Git blob `5a07a9a96731786a6fb849ab56002c735b10aba2`, matches the 1,180,139-byte input and SHA256 from the real diagnostic compile closure. `BlockRestrictions` contains only the five exported booleans Read, Edit, Remove, Drag and DropOn. Both it and `Block` lack unknown-wire storage; their original Unmarshal default branches skip unknown fields. The five-boolean control therefore covers the exact represented restriction shape. This final audit completes the earlier in-progress note retained in `SOURCE_PRESERVATION.json`; it adds no generated model change.

The strict persisted observer, raw copyout, original current-account/Space/ACL admission, tree-head comparison, complete detail comparison, hidden-property changes, ordinary native Apply and returned phase facts are unchanged. No broad restriction exclusion, reload, repair retry or new mutation path is introduced.

## Exactly five selected controls

| Package | Child | Purpose |
| --- | --- | --- |
| `core/pinkha/annotationschema` | `OriginalDataviewDiffExplainsEmptyMessage` | Runs the actual original Dataview/Base.Diff on copies of captured native blocks and verifies empty allocation without any change event. |
| `core/pinkha/annotationschema` | `CapturedNativePairUsesSemanticCopies` | Accepts only the captured nil/empty difference semantically, verifies both original inputs remain intact, checks deep-copy isolation, and retains unequal wire bytes. |
| `core/pinkha/annotationschema` | `NonzeroNativeRestrictionsRemainDifferent` | Checks each represented original restriction boolean remains significant in either direction and remains equal when actually identical. |
| `core/pinkha/annotationschema` | `OtherNativeFieldsRemainDifferent` | Rejects changed children, background, custom application field, view name, column width/visibility, relation link, target object and invalid block membership. |
| `core/block/object/objectcreator` | `MissingAttachmentUsesOneNativeApply` | Runs the unchanged original native fixture and all acceptance assertions, requiring exactly one normal repair Apply, no recreated schema definition, and preservation of unrelated complete persisted state. |

The four new controls are original-model/Diff tests using authentic historical native bytes. They are not represented as new persisted native state. The fifth case is the actual original disposable native runtime and remains the acceptance gate for the repair.

## Frozen execution and preservation

The runner first reconstructs and verifies the exact nineteen inputs from the original registration run, then the exact twenty inputs from the read-only diagnostic. It replaces only `register_type_layout.go` from its exact reviewed preimage and adds one test file. The final declared compilation closure must include all twenty-one inputs. Nineteen prior diagnostic inputs and thirteen original baseline inputs remain byte-identical; all twelve passing child bodies and the existing failed child assertions remain unchanged.

The finite workflow retains the original Go 1.26.5, Xcode 27, macOS ARM64, original module/Tantivy inputs, absolute deadline, child process groups, drain/cleanup, source equality and post-execution rechecks. Each selected parent/child must start exactly once and return a concrete terminal result; unexpected tests or skips fail acceptance. All six raw paired captures remain required. Product or semantic-test failures remain failures regardless of diagnostic completeness.

`GOFMT.json` records actual Go 1.25.6/Windows explicit-file formatting preflight: both candidate files were already byte-identical to formatter output. The genuine pinned macOS formatter and native compilation remain separate gates. No generated protobuf/Swift source, new RPC, SDK/iOS build, body/import-map authority, COMMIT or ACK is established here.
