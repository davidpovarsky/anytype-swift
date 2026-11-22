# Native missing-attachment diagnostic

This candidate runs **only `TestOtzariaAnnotationSchemaRegistration/MissingAttachmentUsesOneNativeApply`**. It adds six read-only captures inside that child and one helper file. All product bytes, all existing assertions, the three original setup mutations, and the twelve passing registration children are preserved. No native diagnostic run has occurred yet.

## Preserved result

The original source is `60b8300c3506e53638c8ca883f82484de073fae8`. [Native run 45038140322](https://github.com/davidpovarsky/anytype-swift/actions/runs/45038140322) compiled successfully and actually executed thirteen children once: **12 PASS, 1 FAIL, 0 SKIP**. The sole failure refused repair before invoking type Apply because the loaded complete type state differed from strict persisted readback. Its final unrelated-state preservation assertion was not reached.

The original artifact and independently verified result remain at [evidence commit e725050d9463b6786b8b54421b4a279daa116878](https://github.com/davidpovarsky/anytype-swift/tree/e725050d9463b6786b8b54421b4a279daa116878/docs/pinkha/torah-integration/native-annotation-schema-registration-20261122/first-native-run-45038140322). This diagnostic is an additive child of that evidence commit. It does not supersede the first failure or replay its twelve passing siblings.

## Exact capture boundary

The existing original `Space.DoCtx` locks the already loaded type. Under that lock the helper copies `NewState().Details().ToProto()` and `BlocksToSave()`, then calls the unchanged persisted-only native observer. It records the actual original native scope, tree heads, complete details protobuf bytes, every complete block protobuf, SHA256 of each byte payload, JSON rendering for inspection, and original Go `proto.Equal` results. It excludes and normalizes no fields. Protobuf byte hashes are integrity records; original protobuf equality remains the semantic comparison.

| Stage | Existing operation immediately preceding capture |
| --- | --- |
| `00-registered` | Initial native registration and readiness |
| `01-unrelated-property-added` | Original `ObjectTypePropertyAdd` |
| `02-second-view-applied` | Original `Apply` of description, second view and custom width |
| `03-metadata-property-removed` | Original `ObjectTypePropertyRemove` |
| `04-before-registration-attempt` | Existing direct strict native read |
| `05-after-registration-attempt` | Existing registration attempt; deferred capture also survives `t.Fatal` |

The final capture runs before fixture teardown. Capture errors are retained and fail the diagnostic; no successful capture substitutes for test acceptance. The selected child still fails if its original guard or final assertions fail. No additional Apply, cache reload, create, retry, permission, body authority or ACK is introduced.

## Composition and selection

`EXECUTION_INPUTS.json` seals the two test sources, diagnostic runner and preservation/format receipts. The runner first reconstructs and checks all nineteen exact source inputs from the original native run. It then verifies the old test preimage, adds only the six capture lines within the failed child, and adds the helper. Removing those six lines must recover the original file byte for byte. Eighteen of the nineteen original inputs remain byte-identical, including all twelve product files; twenty inputs must appear in the original Go dependency closure.

The test selector admits the parent plus exactly one child. The collector requires exactly the six named paired-state files, verifies payload hashes and scope framing, retains the unmodified test stream, and reports the actual case outcome. Commands, deadlines, owned process cleanup, source rechecks and upload-on-failure remain the established runner route.

## Verification limits

Local Python syntax, sealed input hashes, exact child boundaries and the byte-for-byte preservation transform have passed. A revised bounded Sentinel formatter invocation used explicit files in a fresh owned temporary directory, closed stdin, and emitted stage receipts. Actual Go1.25.6 formatting returned the two candidate files byte for byte unchanged; the temporary directory was removed. `FORMAT_STATUS.json` records this result and links the earlier timed-out invocation, whose failure remains preserved. Native compilation and execution remain pending. The pinned macOS Go1.26.5 formatter must independently confirm equality before compilation; it never rewrites reviewed source.

Read-only review of the immutable original dataview implementation found that new views are emitted as complete `BlockDataviewViewSet` messages and existing relation rows use `proto.Equal`; no definite omission of the fixture's explicit ID, name or width was established. The paired native captures are required to identify the actual difference. The complete-state product guard is unchanged.
