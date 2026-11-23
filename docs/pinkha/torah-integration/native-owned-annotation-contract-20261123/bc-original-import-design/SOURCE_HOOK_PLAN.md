# Exact B/C hook plan

## B1: closed annotation preparation and graph disposition

The current package-private `newOwnedImportProcessor` clones the original protobuf request and constructs fresh original dependencies. It validates type/mode/sync/no-progress, but it does not own the archive path, selected Space, whole graph, or schema-reuse policy. Its existing qualification path must remain byte-identical where possible.

The proposed new annotation preparation path accepts immutable bytes into the existing Slice A archive owner, stages only its own archive, and builds the fixed original PB request internally. It accepts no caller filesystem path, update-existing flag, converter, executor, completion closure, or success boolean. Application admission remains the real retained app, wallet identity, usable account lease, regular Space, and signed ACL.

| Exact hunk site | Proposed narrow behavior | Why this location is required |
| --- | --- | --- |
| New `core/block/import/owned_annotation_graph.go` | Own the inspected raw archive, source inventory, staged path, source-to-converter correspondence, per-member disposition, target schema observations and concrete original dependency references. All fields are private. | A parsed public snapshot is data, not native import authority. |
| `owned_import_dependencies.go`, new closed constructor beside the unchanged generic constructor | Supply the owned staging object as the original PB converter's `TempDirProvider`; construct the same original provider and creator with the closed annotation preparation. | The current dependency closure uses the component-wide temp directory. The original filename provider can otherwise resolve an external local path before ZIP extraction. |
| `processor.go:handleBuiltinConverterImport`, after `initConversionFields` and before `createObjects` | Admit the entire actual original converter response against the frozen generated Snapshot inventory. Refuse skipped, added, duplicated, generated, ambiguous or unrecognized sources; require exact root and all member dispositions. Reject `KeptIDs`, unsupported file/network effects, and unsupported transformation before the first assignment. | File upload happens during `assignIdsToAllObjects`; a creator-only check is too late. Converter normalization is real behavior and must be checked, not silently replaced. |
| `processor.go:processSnapshot`, surrounding the existing `GetIDAndPayload` result before maps/payloads are populated | Check that the actual original provider returned the exact planned disposition. A fresh member must yield a concrete root payload whose ID equals the assigned ID. A reused member must return the exact natively observed schema ID and no create payload. Preserve errors; never substitute a requested ID. | Both oldAnytypeID and uniqueKey can select existing objects with update-existing false. Derived providers call the existing-object path with true regardless of the flag. |
| New `common/objectcreator/owned_annotation.go`, plus minimal opt-in hook at the first line of original `ObjectCreator.Create` | Resolve the already-bound actual member. Exact reused schema returns after native read-only revalidation, before setRootBlock, workspace/widget branches, file-relation sync, bundled installation, reset, favorite/archive, or later block sync. Fresh members proceed only with the actual retained create payload. | `canUpdateObject=false` prevents only one reset branch; it does not suppress other writes. |
| `objectcreator.go:Create`, existing remap/install error sites, scoped only to the new closed annotation mode | Return actual remap errors. Refuse implicit bundled installation unless an exact separately qualified schema effect is required. Initially require schema already installed and revalidated. Leave the generic importer behavior unchanged. | The generic route logs some errors and can continue; a body-equality result cannot treat those as success. |
| `objectcreator.go:createNewObject`, actual `ErrTreeExists` branch | In the closed fresh-member mode return the original collision error. Do not call `spc.Do` to read the colliding object as successful creation. | A collision can occur after preflight or payload generation. The actual storage outcome is authoritative. |

A separate `task.go` change is unnecessary if the fresh per-operation creator holds the closed immutable disposition map and resolves the actual `sn` and `DataObject` it receives. If implementation proves that additional transport is necessary, that path must be added explicitly; no mutable public caller policy flag will be used.

The whole-graph gate needs two correspondences: raw exported identity to the converter's real source observation, and converter UUID to the original provider's actual assigned native ID. The original mapping builder already retains actual source and assignment history. The new policy must not overwrite that history to manufacture a bijection.

## Per-member decisions awaiting authentic specimens

| Candidate role | Required native evidence | Permitted effect |
| --- | --- | --- |
| Fresh annotation root or nested page | Exact source member, complete typed references, no unsupported fields, zero ambiguous target oldAnytypeID/uniqueKey matches, actual nonempty root payload, later strict native create outcome | Original fresh creation only; no reset/reimport |
| Already registered fixed annotation type/property | Exact original manifest identity, complete compatible source definition, genuine persisted/native readback and unique positive index row in the same target account/Space; original provider must select that exact ID | Read-only reuse; no creator mutation path |
| Additional bundled schema member from genuine export | No assumption yet. Require its actual original exported definition and native target identity, plus a complete explicit field policy | Refused until the real specimen and source rule are reviewed |
| File object/binary, legacy file, unresolved network bookmark | Slice A only binds bytes and inventory; existing owned upload drain alone does not prove reused-versus-created identity or full body/file readback | Refused in B1 import |
| Workspace/widget/profile/participant/chat, tombstone/kept ID, arbitrary relation option/type, unknown or partial member | No general-import interpretation or name-based reuse is available | Entire graph refused before assignment |

Preflight is not a transaction. Concurrent native changes can still make a later actual assignment, schema recheck, create, or readback fail. Every actual effect remains historical evidence; ALL_OR_NOTHING does not promise rollback. Existing or uncertain outcomes must be recovered by their actual mapped objects, never by blind repeated import.

## B2: actual write permission boundary

The source trace in `CURRENT_PERMISSION_TRACE.md` is an independent blocker. The current original root path stores a root before historical ACL validation; a later current-permission check on body Apply cannot establish that no root was stored after revocation. Holding an outer ACL read lock across the full existing PutTree/GetObject path is not an accepted fix because it reenters ACL locking and original callbacks.

Do not activate B1 as production until a concrete original-owner hook has its own exact hunk review and genuine revoke-at-boundary test. Candidate placement is inside the original native root-storage owner, where current writer identity, the exact prepared payload and one storage insertion can share a well-defined admission boundary. No any-sync edit is included in the current allowlist. The dependency trace also shows that content admission and storage are separate phases; the eventual contract must name its exact linearization point instead of claiming an atomic commit from a preliminary check.

## C: retain the original operation through actual readback

Current `OwnedImportOperation.run` executes the real processor, copies the response/mapping/files, cancels its derived context, and closes Done. The original registry removes only operations whose Done channel is actually closed. `beginOwnedImportRetirement` requests cancellation and returns pending without waiting under its registry or application lock; it is safe for actual synchronous reentry.

The annotation extension belongs in that same run method, after the actual Execute/finalizer returns and before cancel/Done. It must not start an independent import engine or release the application's lifetime then reacquire it for readback.

1. Copy the actual import outcome, mapping and owned file results. A failed/cancelled import retains that history and grants no positive body result.
2. For a successful closed annotation import, require a complete actual unique mapping against the frozen graph and the exact target account/Space. The empty NoOp progress ID remains valid and non-authoritative.
3. Call the concrete original export service with the same operation context and an output location owned by the operation. Use the fixed reviewed PB format/options and the actual mapped root. No caller-provided verifier or callback is accepted.
4. Wait for the original export to return. Inspect both `ctx.Err()` and the actual `ExportReport`; the original API deliberately clears context.Canceled from the returned error, while preserving diagnostics. Its `waitExportTasks` joins started workers before writer/report cleanup.
5. Inspect the real returned archive through the same bounded archive owner. Require exact expected member/reference/file coverage. Compare typed generated models using the actual source→converter→target mapping. Remap only documented native identity slots; do not rewrite text, arbitrary bytes, source provenance or unknown fields to fit.
6. Record a closed historical verification result. The body result stays absent on incomplete export, issue/error report, unknown member/field, non-bijective mapping, unsupported transformation, content/style/order/nesting mismatch, canceled context, currentness mismatch, or cleanup failure. A native historical match is not a Host save ACK.
7. Close only this operation's staging and readback files, then take the final cancellation observation, cancel the derived context, publish the immutable outcome, and close Done. Cleanup error is a drained failure, not permission to remove arbitrary paths. No worker is represented as drained before its real completion.

The current `sealAndDrain` seals file admissions but does not itself cancel a successful context; therefore a concrete readback can use the same live context before `run` releases it. The annotation extension must not reopen file upload admissions.

## Exact C source scope proposed

- New `core/block/import/owned_annotation_readback.go`: concrete original export, owned output and complete report/context admission.
- New `core/block/import/owned_annotation_comparison.go`: closed mapping-aware generated Snapshot comparison, explicit field policy, no caller-supplied predicate.
- `core/block/import/owned_import_operation.go`: private annotation state and closed verification observation; original run retained through readback; final cancellation snapshot occurs after readback, not only immediately after Execute.
- No RPC/proto/generated or Swift activation in B/C. A later native handle service must expose real Start/Observe/Cancel/Release and preserve historical access after source retirement. The original registry remains the owner.

The supported comparator field table and exact minimal implementation hunks will be bound to the authenticated Slice A specimens. The current same-native-identity Swift comparator is not reused as proof for a fresh remapped graph. Cold reopen and process recovery are separate native/Host gates.
