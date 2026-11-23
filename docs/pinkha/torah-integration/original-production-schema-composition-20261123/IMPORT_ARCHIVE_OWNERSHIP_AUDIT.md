# Original archive ownership and reopen audit

## Scope

Read-only audit of the original Anytype editor sources at `de63125b97cd5b91a1fa4f4b71d03738076e735f`, compared with the frozen production preparation at `89926d7839c09a629c195ec6dd9812fe56aad069`. The archive/reopen sources are unchanged. This is a source contract record; no native import, test replay or device operation was run.

## Existing checks and their exact boundary

| Original source | Actual guarantee | Limit |
| --- | --- | --- |
| AnytypeOriginalEditorSnapshot.swift | Bounded canonical supported envelope; exact provenance shape; ZIP magic/count/SHA; successful export-report fields; untouched archive bytes. SHA-256 `ed135a4369313d14493b9b05f9d1efef414da21144f6119b970bc6e88a8389a2`. | Public decoding neither inspects ZIP members/protobuf file source fields nor authenticates historical provenance/current owner. It is not import admission. |
| OriginalAnnotationNativeArchiveLayout.swift | At most 65,536 compressed bytes, 512 entries, 8 MiB expanded; one reconciled central directory, local headers/descriptors and contiguous indexed records; supported compression/flags; exact UTF8 safe paths; no hidden/overlapping/SFX/ZIP64/encrypted/alternate-layout acceptance. SHA-256 `982470bc1bd237eb053edcb8081a53c96baf53a9eba75c408baaced0cc7f7560`. | Framing/inventory only. It does not decompress, decode native objects, confer ownership or prove the native importer uses an owned directory. |
| OriginalAnnotationNativeArchiveComparison.swift | In-memory extraction with CRC and actual expanded count; regular members; complete indexed inventories; native protobuf decode; unique objects/blocks and valid child IDs; exact source Space/root; every fileObject details[source] is safe files/<single-name> with fileInfo/fileID; referenced files exactly equal archived binary inventory. SHA-256 `7cd565292ca7b77fe4eab865cbfe947d9d97e5f83868a96660a84c3b7dff840a`. | Pure comparison data. This internal check is not called by the public snapshot initializer or existing qualification importer. It cannot establish native import ownership, persistence, currentness or acknowledgment. |
| OriginalAnnotationNativeMapKeyGuard.swift | Rejects duplicate or Unicode-canonically ambiguous reachable known map keys, duplicate singular message fragments and unsupported map-entry fields before SwiftProtobuf decoding. SHA-256 `2d8f22ac43e67b1f30cdc6ed2e82a4bd3ce5c3da6666d103da19e61baa060125`. | Uses exact pinned field paths; unknown native message fields are preserved rather than interpreted as authority. Native admission still needs its real generated model/codec. |
| OriginalAnnotationNativeSnapshotWire.swift | Pinned wrapper views preserve original snapshot/file-key protobuf content and unknown fields for comparison. SHA-256 `b2708f212ea9f49e4d661a13a83465c29a37368a9f35e647273a575e8e8581cd`. | This is not a second importer, alternate body format or import implementation. |
| OriginalEditorArchiveFiles in AnytypeOriginalEditorSnapshot.swift | Creates its unique 0700 temporary directory; direct-child standardized file paths; directory/file open with no-follow; regular bounded file read; before/after descriptor metadata and content stability. | Protects the specific export/read path it owns. It does not qualify arbitrary caller-supplied paths or a native converter's global temporary directory. |

The body envelope's total bound also includes its header; the layout's 65,536-byte archive bound is not permission to exceed the body envelope's own caller-selected bound.

## Existing import and reopen identity

`AnytypeOriginalEditorRestoreQualification.importCandidate` is DEBUG+Simulator qualification only. It receives an unconstructible externally owned qualification Space in a new local acceptance account/target. It writes the exact archive to its owned directory, verifies those bytes, and invokes actual ObjectImport with type.pb, mode.allOrNothing, updateExistingObjects=false, isMigration=false, isNewSpace=false and real progress enabled.

The qualification route checks both root oldAnytypeID and uniqueKey before import. It observes the actual native progress/import completion, resolves a unique root with oldAnytypeID + sourceFilePath, validates the actual target collection/Space, obtains ObjectShow and retains genuine response bytes. It does not interpret the immediately returning ObjectImport response as completion. Its fresh owned target is an additional assumption; these root checks alone do not make import into an existing regular selected Space safe.

`AnytypeOriginalEditorQualification.prepareReopen` reads a current local source after the saved row CAS, validates its host profile/annotation/revision/source callback and historical snapshot correspondence, imports once, then returns a new Binding using the actual mapped target account/Space/object. The local source is checked before and after each material suspension. `prepareProcessResume` seals that actual imported target and the same current saved source/body, then a later process reopens the mapped target rather than reimporting or resetting it.

No current original path requires updateExistingObjects=true. Do not expose an update flag merely to fit a future API.

## Same-ID comparison is not remapping proof

`AnytypeOriginalEditorHost.withHistoricalAnnotationBodyComparison` explicitly requires intended archive provenance account/Space/object to match its current Binding. It validates the native metadata/applied commitment around the actual held export, then `requireEqual` compares exact root/Space, object ID graph, file inventory, canonical object bytes and file bytes. Only the exact pinned r14 local projection detail keys are excluded.

This is a genuine historical same-identity comparison; it cannot compare an old-ID archive to a newly remapped import. A production new graph needs the actual original importer mapping and a bounded mapping-aware original readback composition. Rewriting the original bytes/provenance, assuming a new ID from input data or treating nil native error as applied body would not satisfy it.

## Native-owner findings retained as dependency

The native owner independently traced Heart `d98420b1113536afd08cde6de9a5816f6d27ffff`:

- `core/block/import/common/filenameprovider.go` accepts URL/local/absolute paths and extracts through the app-wide TempDirProvider. The proposed byte-owned native front door must validate the actual generated protobuf file source fields against owned ZIP files and supply an operation-owned temporary directory through the original converter's existing interface.
- `existingobject.go:GetIDAndPayload` performs oldAnytypeID/uniqueKey lookup before its getExisting flag; `derivedobject.go` uses that path with true.
- `processor.go` forwards UpdateExistingObjects while reused IDs may have empty payloads; `objectcreator.go` can reset an existing page/type and its resetState path logs some ResetToVersion errors rather than returning them.

These are the native owner's direct source findings, not an executed native outcome from this audit. All graph members matter because the original export includes nested objects. updateExistingObjects=false, a root-only collision check, a terminal nil error or a mapping result cannot prove the absence of overwrite or full body persistence.

The eventual original Start/Observe/Cancel/Release contract remains unimplemented. It must register before original Start, own bounded archive bytes/digest/tempdir and real native application/account/regular-Space permission, preserve historical operation access after source retirement and derive drain from actual Done/Result. The Swift closed session supplies current original selection and saved-source context; wire IDs/hashes are comparison data.

## Outcome

The existing source provides useful bounded archive validation and real original import/reopen primitives, but there is no currently qualified production import route into an existing selected Space. Preserve the exact original engine and controls; close the actual admission, whole-graph collision and mapping-aware readback gaps before activating a production import facade. This audit changes no product source, active SDK pin or acceptance status.
