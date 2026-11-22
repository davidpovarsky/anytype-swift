# Original native annotation schema readback

Status: source candidate; no native build or test result is claimed by this packet.

This is the next bounded dependency after the original fixed-schema observer. It composes the real active `application.Service`, original account identity, selected existing native Space, original fixed-schema observer, and the Space's raw index. It does not create an account or schema during production observation. The actual tests own disposable LocalOnly accounts and Spaces.

## Native change and downstream behavior

`observer-readback.patch` changes exactly two previously reviewed observer files. It retains private details and blocks from the original strict replay and publishes them only after both complete native snapshots, ACL/account/Space checks and final cancellation checks succeed. `CopyPersistedSchemaState` deep-copies original protobuf data on every call. An externally constructed result cannot supply its private payload. All previous native disposition predicates and their order remain unchanged.

The new `core/pinkha/annotationschema` package defines the exact dedicated `ot-pinkhatorahannotationv1` type and 17 longtext property keys from `OriginalAnnotationNativeMetadata`. Explicit longtext zero is required. It reads the actual persisted type and relation IDs, flags, recommended property lists, dataview links and every view's column visibility. Unrelated original properties remain present. A metadata column that is visible is a conflict. Missing attachments are incomplete. Present malformed or true `isUninstalled`, `isDeleted` or `isArchived` flags are conflicts, including the durable retirement marker before derived deletion information is available.

Index readiness uses existing `SpaceIndex.QueryRaw(FilterEq, 2, 0)`. Ordinary `Query` injects filters that could conceal a conflicting retired row. Zero raw rows remain unresolved; two rows conflict; one row must match the observed original ID, exact key, Space and required state. This is positive local readiness, not proof of absence or global uniqueness.

Each native observation is historical. The 18-definition batch is not an atomic schema transaction or a lease for a later operation. Results confer no create/recovery authority, registration receipt, annotation identity/body authority, materialization, mapping, COMMIT or ACK. A root-only uncertain creation remains untouched. UI hiding beyond the observed type lists and views is not claimed. Production Swift/RPC composition and recovery of missing or root-only definitions remain downstream work.

## Exact source composition

Repository parent: `dc4929239ebd9cb199a7e0c238f5bf155305f7d8`.

Native base: `anyproto/anytype-heart@d98420b1113536afd08cde6de9a5816f6d27ffff`; existing r14 patch, frozen V5 observer and V6 correction are reused through the unchanged V7R1 input manifest. Existing fixture/control files and prior results remain byte-for-byte in their original packet. Source provenance and complete before/after hashes are in `EXECUTION_INPUTS.json` and `READBACK_PROPOSAL.json`.

Original API references at that Heart SHA: `core/application/application.go`, `space/service.go`, `core/block/object/objectcreator/{creator,relation,object_type}.go`, `core/block/detailservice/relations.go`, `core/block/editor/{objecttype,state/state}.go`, `pkg/lib/localstore/objectstore/spaceindex/{queries,relations}.go`, `pkg/lib/database/database.go`, and `core/block/delete.go`. The retirement fixture uses the same genuine `Space.Do` / `SmartBlock.Apply` persisted step as `deleteDerivedObject`.

## Focused execution selection

Only the new `TestOtzariaAnnotationSchemaReadback` parent and these nine new children are selected:

1. `ActualDefinitionsHiddenAttachmentsAndViews`
2. `CallerMutationCannotChangeCopiedNativeReadback`
3. `ConflictCannotExposePersistedPayload`
4. `ChangedRowsCannotExposePersistedPayload`
5. `FinalCancellationCannotExposePersistedPayload`
6. `MissingAttachmentRemainsIncomplete`
7. `VisibleNativeMetadataColumnIsConflict`
8. `UncertainRootIsPreservedWithoutCreation`
9. `OriginalNativeRetirementIsConflict`

Prior strict 12, original native 13, V6 native 18 and V7's two passes are retained without replay. This packet does not transfer those passes to its new code. `RUNNER_DELTA.patch` records the focused derivative of the existing finite runner. It preserves deadline, process-group cleanup, module/native dependency hashes, actual compilation input closure and post-execution source rechecks. The exact Go 1.26.5 formatter must accept frozen sources without rewriting them. Original native streams, command results and actual details/block protobufs are retained, including failure results. No native wallet directory is uploaded.

## Checks completed before native execution

Actual Sentinel Go 1.25.6 `gofmt` accepted the six source files; `GOFMT.json` records exact bytes. The Python runner parses successfully. Neither check is Go type checking, native compilation, an Apple SDK build or a product acceptance result. The isolated workflow is prepared for one reviewed focused run; publishing a source packet alone does not claim execution.
