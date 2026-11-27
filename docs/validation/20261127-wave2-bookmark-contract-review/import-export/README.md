# Original import/export: bounded source map

**Pinned integration source:** `af63f6209c38bddf6ed851f0b894e2f627a671af`, tree `c3c3f46ec9241b6d446000bbdb3f5f89826b6a0c`.

**Outcome:** the current source contains original Heart protocol entrypoints and reusable Files UI. This bounded inspection did not locate a dedicated general document/Space import/export route in the inspected iOS Object, Space or application Settings menus. The Native provider/format contract remains unmapped. No source, account, controller or runtime was changed, and no operation or test was executed.

`source-manifest.json` binds 28 exact primary file reads (499,698 bytes). Every retained source was checked against its Git blob identity. The tree inventory is a bounded filename catalogue; it is not a repository-wide content-absence proof.

## Original contracts and entrypoints

| Source boundary | Exact current declaration or route | Readiness implication |
| --- | --- | --- |
| Export formats | `Anytype_Model_Export.Format` declares Markdown, protobuf, JSON, DOT, SVG, graphJSON and additive AnyBlockV2. AnyBlockV2 is documented as an index/properties plus per-document bundle. | These are protobuf declarations. Each format's effective provider support and result must be qualified; the enum alone enables no Native feature. |
| One object result | `ClientCommands.objectExport` takes Space/object/format and returns a result string, error, event and report. | It calls `Lib.ServiceObjectExport` through the original `Invocation`. It is a Heart provider boundary, not an AnyHTTP route. |
| File or selected/whole-Space export | `ClientCommands.objectListExport` declares destination path, Space and object IDs, format, ZIP, nested/files/archived/backlinks/Space options, and Markdown properties/schema. The request comment treats an empty ID list as all available documents. Response includes path, succeeded count, event and error. | Reusing this option vocabulary does not prove complete export semantics, permission behavior, file custody or Native support. |
| Legacy workspace export | `ClientCommands.workspaceExport` takes destination path and workspace ID; response includes path/event/error. | No format selector is declared here. Keep this original protocol separate from a newly qualified Native full-Space format. |
| Import formats and parameters | `Anytype_Model_Import.TypeEnum` declares Notion, Markdown, external, PB, HTML, TXT, CSV and Obsidian. `Object.Import.Request` binds Space, typed parameters, optional external snapshots, update-existing, migration/new-Space and declared all-or-nothing/ignore-errors mode. | The declared mode is not evidence of Native transaction atomicity. The optional current AI parameter does not belong in a required baseline import route. |
| Import discovery and completion | `Object.ImportList` returns a provider list whose response enum declares Notion/Markdown/HTML/TXT. `Object.ImportRunStatus` takes `importID` and returns statistic, manifest-state and live state. The older `Object.Import.Response` marks its error/collection/count fields deprecated. | Do not populate a UI from every type enum or treat a request acknowledgement as completed import. The owner must supply the exact supported-format and completion contract. |
| Original provider dispatch | The generated `objectExport`, `objectListExport`, `workspaceExport`, `objectImport` functions serialize requests and call their respective `Lib.Service…` functions. `Invocation` handles actual response errors/events and cancellation around the original call. | A Native implementation requires its own qualified typed provider. Calling the Heart wrapper while Any is active would not establish cross-engine support. |

Primary anchors: [export format][export-format], [list export][list-export], [import request][import-request], [import discovery][import-list], [import status][import-status], [generated dispatch][dispatch], [invocation][invocation].

## Existing UI and reusable provider boundary

| Inspected surface | Observed source | Reuse / exact limit |
| --- | --- | --- |
| Original Object actions/settings | `ObjectAction`, `ObjectMenuBuilder`, `ObjectSettingsViewModel` and coordinator. Actions include copy links, duplicate, archive, history/settings and publishing; no generic file import/export action appears in this inspected route. | Copy-link and publishing remain separate operations. No existing export-format sheet was found here to rewire. |
| Original Space/application Settings | Complete inspected `SpaceSettingsView`/view model and `SettingsView`/view model contain no general import/export action. | This is a scoped source finding, not proof about every repository surface or another platform. |
| Imported-type localization | `ObjectImportType+Loc` maps original import metadata values to localized names. | It is not a format picker or provider capability list. |
| Original generic file picker | `AnytypePicker` embeds `UIDocumentPickerViewController(forOpeningContentTypes:asCopy:true)`, one selection, and forwards chosen URLs to its view model. | This provides original UI mechanics, not archive parsing or import authority. |
| Shared public transfer picker | `PinkhaDocumentTransferPicker` supports export-as-copy or one open-in-place URL, real initial directory, one-shot completion, actual delegate URL and explicit cancellation. `PinkhaDocumentExportSource` owns only a fresh protected staging file/directory. | This already shared engine-neutral Files layer can be reused after a concrete producer/parser exists. The caller still owns bounded security-scoped reads, qualified output bytes and current permission/lifetime checks. |
| Native association transfer | Existing `AnyNativeArchiveTransfer` exports canonical source associations/provenance and explicitly excludes document text/attachments. | D5 remains this narrow roundtrip. Its body assertions preserve independently existing source/destination text; they do not serialize that text. Existing failure and picker diagnostic retain their original status. |
| Heart migration inspection | `AnyHeartSpaceArchive` is bounded byte-preserving inspection of a Heart AnyBlock 2.0 export, with explicit issues for missing snapshot/census/schema/file proof. Its header expressly limits it to inspection. | This W1 migration boundary is useful input material; it is not a generic document/Space importer or write authority. |

Primary anchors: [Object actions][object-actions], [Space settings][space-settings], [generic picker][generic-picker], [shared picker][shared-picker], [migration inspection][migration]. Source-capture controller, original ObjectActions service/protocol and current AnyHTTPClient were also read and retained. The inspected AnyHTTPClient has generic JSON and file/migration-file methods; it does not itself supply a typed full import/export contract.

## Concrete next owner handoff

Root already requested the full document/Space Native owner and format mapping in C comment `1220959803935163` and D comment `1220959686822138`. This map adds source coordinates; it does not issue another request or prescribe a new Native schema.

The unresolved contract must identify the actually supported formats and scopes; document/block/type/property/link/file identity preservation; current account/Space/role authority; output completeness and actual file custody; import run identity, validation, unknown-ACK/retry/cancellation behavior and final readback. These are adapter requirements inferred from the real original request/result shapes and the user's full import/export requirement. Their implementation and acceptance belong to the qualified provider, not to the system picker.

Once that contract exists, Wave2 can wire one original-style format/options surface around the existing shared Files picker and the corresponding typed engine provider. Actual cancel, export Save, bounded import/read, result/error, identity and cold-reopen UI acceptance will then use a matching shared build. No general import/export selector or capability was fabricated during this map.

[export-format]: https://github.com/davidpovarsky/anytype-swift/blob/af63f6209c38bddf6ed851f0b894e2f627a671af/Modules/ProtobufMessages/Sources/Protocol/Models/Anytype_Model_Export.Format.swift
[list-export]: https://github.com/davidpovarsky/anytype-swift/blob/af63f6209c38bddf6ed851f0b894e2f627a671af/Modules/ProtobufMessages/Sources/Protocol/Commands/Anytype_Rpc.Object.ListExport.swift
[import-request]: https://github.com/davidpovarsky/anytype-swift/blob/af63f6209c38bddf6ed851f0b894e2f627a671af/Modules/ProtobufMessages/Sources/Protocol/Commands/Anytype_Rpc.Object.Import.swift
[import-list]: https://github.com/davidpovarsky/anytype-swift/blob/af63f6209c38bddf6ed851f0b894e2f627a671af/Modules/ProtobufMessages/Sources/Protocol/Commands/Anytype_Rpc.Object.ImportList.swift
[import-status]: https://github.com/davidpovarsky/anytype-swift/blob/af63f6209c38bddf6ed851f0b894e2f627a671af/Modules/ProtobufMessages/Sources/Protocol/Commands/Anytype_Rpc.Object.ImportRunStatus.swift
[dispatch]: https://github.com/davidpovarsky/anytype-swift/blob/af63f6209c38bddf6ed851f0b894e2f627a671af/Modules/ProtobufMessages/Sources/Generated/service%2Binvocation.swift
[invocation]: https://github.com/davidpovarsky/anytype-swift/blob/af63f6209c38bddf6ed851f0b894e2f627a671af/Modules/ProtobufMessages/Sources/Invocation.swift
[object-actions]: https://github.com/davidpovarsky/anytype-swift/blob/af63f6209c38bddf6ed851f0b894e2f627a671af/Anytype/Sources/PresentationLayer/TextEditor/EditorPage/Views/Settings/ObjectActions/ObjectAction.swift
[space-settings]: https://github.com/davidpovarsky/anytype-swift/blob/af63f6209c38bddf6ed851f0b894e2f627a671af/Anytype/Sources/PresentationLayer/SpaceSettings/SpaceSettings/SpaceSettingsView.swift
[generic-picker]: https://github.com/davidpovarsky/anytype-swift/blob/af63f6209c38bddf6ed851f0b894e2f627a671af/Anytype/Sources/PresentationLayer/Common/UIKit/Pickers/FilePicker/CommonViews%2BPickers%2BFile%2BUIKit.swift
[shared-picker]: https://github.com/davidpovarsky/anytype-swift/blob/af63f6209c38bddf6ed851f0b894e2f627a671af/Modules/PinkhaKit/Sources/PinkhaKit/PinkhaDocumentTransferPicker.swift
[migration]: https://github.com/davidpovarsky/anytype-swift/blob/af63f6209c38bddf6ed851f0b894e2f627a671af/Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegration/AnyHeartSpaceArchive.swift
