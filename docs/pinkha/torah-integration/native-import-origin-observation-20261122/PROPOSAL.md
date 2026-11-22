# Original protobuf import mapping: audited boundary and next implementation

## Status and decision

This is a read-only source audit of original Heart `d98420b1113536afd08cde6de9a5816f6d27ffff`. No original importer, active SDK, body-comparator candidate, or native data was changed. It identifies a small first implementation: copy execution-origin mapping facts from the real protobuf converter and real ID assignment into an immutable native observation. That observation must remain separate from application success, current account ownership, complete file effects, body equality, and ACK authority.

The original importer does not currently supply a complete, durable, attempt-bound graph map to the Swift production boundary. A copy of `oldIDToNew`, the import notification, or a successful RPC response cannot fill that gap alone.

## Actual route and identity stages

`core/object.go: Middleware.ObjectImport` dispatches protobuf imports to the original `importer.Importer` with `IsSync=false`. It immediately returns an empty RPC response. Importv2 has durable run status and a ledger, but its `Handles` switch covers Markdown, Obsidian and Notion only. It does not handle protobuf archives.

| Stage | Actual original source | Meaning and limit |
|---|---|---|
| Archive identity | `pb.Pb.makeSnapshot` reads `SnapshotWithType` and the original `details.id` | This is the source object's archived ID. It must be captured before normalization; a later indexed `oldAnytypeID` query is not equivalent execution evidence. |
| Converter identity | `makeSnapshot` allocates a UUID, then `normalizeSnapshot` may change it | `pb.Pb.updateLinksToObjects` builds original exported ID → converter ID and rewrites supported reference slots. This first map is not returned in `common.Response`. |
| Native identity | `importProcessor.processSnapshot` calls the actual `IdAndKeyProvider.GetIDAndPayload` | `oldIDToNew[snapshot.Id]` maps converter ID → actual native ID. Existing-object matching may reuse a destination even when `updateExistingObjects=false`. |
| Internal-key aliases | `extractInternalKey` adds old type/relation unique keys to the same string map | These are different from object identities. A truthful observation must keep typed records and detect duplicate/overwritten map keys instead of treating this mixed dictionary as a bijective object map. |
| File objects | File IDs are assigned last; object-format context references are remapped before upload | `fileObject.GetIDAndPayload` may upload the file during assignment and substitute the upload's actual file-object ID. Assignment already has native side effects. |
| Application | Schema batches drain before ordinary object batches | `ObjectCreator.Create` can create a new tree, reset an existing tree, skip some existing objects, or return no details. An assigned ID does not establish which state was applied. |
| Additional effects | File relations, text icons, legacy files and bookmarks have later sync paths | Some can create further file objects or rewrite references without adding those identities to the processor map. They remain outside the first observation's completeness claim. |

The converter also migrates legacy snapshots, changes source paths to extracted local paths, supplies import dates, removes its own local/derived detail list, and may add a root collection. The latter is a synthetic import collection, not the archived annotation root. These original operations must not become extra exclusions in the strict body comparator. Original ID assignment facts support a future explicit remapping contract; they do not authorize silent changes to text, metadata, unknown fields, collections or attachment bytes.

## Completion, cancellation and account lifetime

The async importer runs `importObjects(i.componentCtx, request)` in a goroutine. `Import.Close` cancels that context but does not join the goroutine. The request caller's context is not the running async import context. The Swift Owner can hold its own operation reservation, but it cannot turn the immediate RPC response into a completed native import.

On success, `readResults` receives until the worker result channel closes; `WorkerPool.Start` closes that channel after its worker wait group drains. A successful batch has therefore drained its worker calls. On cancellation or an ALL_OR_NOTHING error, `readResults` calls `pool.Stop()` and returns immediately. `Stop` only closes the quit channel. It does not join workers or roll back earlier writes. The worker's select send expression also evaluates `task.Execute(data)` before selecting a ready send/quit case, so a quit signal is not proof that no task entered. A future failure path that releases an original native operation lease must drain those workers explicitly.

Object and file operations use per-object native locks and original storage methods; there is no one transaction or whole-graph revision covering this import. Several paths log errors without propagating them through the final result: file-object upload fallback, existing-object `ResetToVersion`, bundled schema installation, favourite/archive updates and some relation/icon sync failures. `Err == nil` and a completion count therefore cannot replace actual semantic readback.

The existing component's converter and ID provider instances also retain mutable per-import fields. A new API must not assume that two overlapping calls get independent converter state merely because their processors differ. The scope of concurrent admission must be settled before using these observations as production mapping authority.

The schema agent's proposed `WithActiveApp` lease is intentionally synchronous. It must not be held around this generic async importer or around work whose cancellation requires AccountStop/Select. No import use of that lease is proposed here.

## Evidence currently retained

The original `ImportResponse` carries root collection ID/layout, process ID, object count and error. It carries neither source archive identity nor either map stage. The async import notification includes Space/process/type/error; `ImportFinish` includes collection/count/type but lacks the same complete attempt identity. The processor maps are ordinary in-memory fields and are not persisted by this protobuf path.

The existing Swift restore qualification uses a fresh privately owned test Space, retains original events and searches for a unique root with `oldAnytypeID` plus `sourceFilePath`. Its scope is explicitly root-only qualification. It must remain separate from a production full-graph map, and resume must continue to reopen the existing object without another import.

## Proposed first bounded implementation

Implement an observation-only addition, isolated from current candidates:

1. Add internal immutable source-origin records to `common.Response`, populated only by the real protobuf converter while it still has the parsed source ID, member identity and converter ID. Keep generated collection records and kept/deleted-reference IDs separate.
2. In the actual processor, record each successful `GetIDAndPayload` return as a typed converter-ID/native-ID assignment. Record internal-key aliases separately. Refuse to publish a complete map observation if source IDs, converter IDs, or alias domains collide or any source record lacks exactly one assigned destination. Do not guess from indexed metadata or regenerate IDs.
3. Expose a copied observation through an original `ImportResponse` accessor with an unexported backing value and no public constructor or deserializer. For a drained successful execution it describes the map chosen by that original attempt. It must explicitly say that assignment/application/file-side-effect completeness and current ownership are separate. Failure may retain partial diagnostic facts but cannot return the complete observation.
4. Retain the exact source archive hash/member inventory and original operation identity in a later closed adapter; that adapter must obtain the observation from its actual original invocation. Serializing the observation for evidence must not make serialized bytes an admission path. No map writes, ACK, second import, or production callsite is enabled by this first addition.

This is deliberately an origin observation, not a claim that every original mutation succeeded. The full production composition still needs: a cancellation-safe original operation lifetime; worker drain on failure; independent concurrent-converter state or original admission serialization; authentic capture of file/sync remaps; exact source archive binding; post-import native readback; and a closed consumer that validates these facts together. The strict same-ID body comparator remains unchanged until that genuine mapping contract exists.

## Focused validation proposed after technical review

Use actual modified original functions with small controlled ID-provider/worker fixtures to test two-stage map composition, separated internal keys, duplicate/collision refusal, returned-copy independence, missing assignment, generated collection/kept-ID separation, no observation on failure, and no observation before worker drain. Do not call these native integration acceptance. Preserve existing suites and run only the new affected closure. Actual original Go module compilation and a real owned native attempt remain separate gates.

## Immutable source references

All paths below are in the original Heart commit above:

- `core/object.go` — `2d251ea8c12e35e14f82a12ac45b9fa01969b2a6`.
- `core/block/importv2/adapter/adapter.go` — `7480afb650a6eb0f6e26adcc1da89ad4b9c4b5fe`.
- `core/block/import/importer.go` — `de04c5fe040472950a20f3ecca3ff47c00b4a997`.
- `core/block/import/processor.go` — `d69696c42d09870ded4bc58cf30254c98d05be83`.
- `core/block/import/types.go` — `adb740cbbe31839e298454b211c1dd917704b48f`.
- `core/block/import/common/objectid/provider.go` — `af18b5c65a0ce59697ed102f7fd1659d86276461`.
- `core/block/import/common/objectid/existingobject.go` — `29698d0b90b2479c4b0a6c4fa29b94af4f8d004e`.
- `core/block/import/common/objectid/fileobject.go` — `4e2a66e17f9651a120feff0df8d03ac0c18452c7`.
- `core/block/import/common/objectcreator/objectcreator.go` — `4bfad158aaeb14488b33751b897f223d4b5ec0ae`.
- `core/block/import/common/workerpool/workerpool.go` — `3238acc630348ed5f8b2a59e8b01164936c15f90`.
- `core/block/import/common/syncer/relationsyncer.go` — `d6c78366f946be7a3089ec4ad8c6238bda0b9d98`.
- `core/block/import/common/syncer/icon.go` — `59fb34f9cf77ef41a868378d876a8d1dc7c3b404`.

The protobuf converter/common source and original Swift qualification adapter are also retained in the separate body audit input set. The source manifest records exact blobs for every reference used; source review is not execution evidence.
