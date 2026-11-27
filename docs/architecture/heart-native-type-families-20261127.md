# Heart native type families and destination engine contracts

## Scope and admission state

This is the engine contract map for the retained `original156` capture. It is based on the captured Type definitions and the exact qualified Any/SDK source below. It does not admit the complete source for migration. `HasNativeSourceAdmission`, `HistorySemanticsValidated`, whole-space functional acceptance and permission to write the complete source remain false until their respective checks pass.

The capture contains 20 Type definitions, 126 property definitions, four option definitions, two Basic documents and four system objects. There are 64 captured read-only property definitions. The table covers the 17 Types outside the Page, owned custom Basic type, and the explicit Bookmark lifecycle contract. Qualification of a lifecycle component does not automatically qualify an entire captured definition: the original Bookmark also carries `headerRelationsLayout = 1`, which the current definition catalog still reports as an unknown field.

Accepted evidence is retained rather than repeated:

- Original source preservation: 182 operations, 159 heads, 156 snapshots, 332 archive records, and a new process with OS-level TCP/UDP denial. Receipt `/var/lib/pinkha-c-native-preservation-20261126/linux-resume-attempt1/result.json`, SHA-256 `f7f4a5b34465907c3285229a266a488229a92eb1c3a7c04c5b4cdd162ed1b32b`.
- Retained capture coherence and member audit: all 313 manifest-referenced files match their declared bytes and hashes. Receipt `/var/lib/pinkha-w1-engine-contracts-20261127/original156-coherence-audit/result.json`, SHA-256 `68319ff3adca0da6191ce0a4df8ff9654bac6d5be745306922662da5d5454244`. These 313 member checks are distinct from the 332 archive records.
- Bookmark URL lifecycle: commit `cffb819015bbb86aea23e94ee7ff11e1a90a1ec7`, receipt SHA-256 `48a64384f9702df073c27d4e9a8f4d889a9a91af3521fee280d6098f17b5bc22`. This qualifies eight explicit prepared operations, edit/undo and cold offline identity retention; it is not original-source admission.

## Exact native source

The native implementation inspected for this map is Any `8fbd1e819fb132ac0e0a848d2ddf5c5714189b81` with SDK `c1fd59bd8f0ed62471234ec1a65a402d22eab6a9`. The retained Linux binary SHA-256 is `1dc1803c656da2215760477dadd26bf0e829b6ee592e337db6fa0295a6ed9636`.

Source root: `/var/lib/pinkha-root-t2-linux-20261126/build1/current/source`. SDK source is the `.runtime-artifacts/sdk-source` subdirectory. Source manifest SHA-256: `12ad65cd178aa31b6aa5761d42507d8618f1d3d4865a627548af2036c0a40a6c` (1,594 members). This map describes code contracts, not additional test results.

## Family map

| Original Type keys and layouts | Existing native primitive | Required engine adaptation and remaining acceptance |
| --- | --- | --- |
| `ot-file`, `ot-audio`, `ot-video` (6), `ot-image` (8) | `Space.Files()` binds every file to an existing object. `FileInfo` carries `fileId`, object, root CID, plaintext size, MIME, name, variant and variant-of. Content endpoints support byte ranges. | Preserve the source file-object identity separately from its encrypted file ID and native destination object. Map original/thumbnail relationships, file-property target restrictions and MIME-specific roles explicitly. Source metadata must remain separate from current native cache and custody status. Wave1 root owns the additive native durability status/retry contract; FilesV2 transport evidence does not automatically admit the Heart file-object layout. |
| `ot-collection` (14), `ot-set` (3), `ot-dashboard` (7) | Native collections supply actual membership. Registered `dataview` objects have a `host` and own `dataviews` and `views` datasets. A native editor part supplies document content where needed. | Translate collection membership, Set filters, source property IDs, ordering, query semantics, layout settings and hierarchy. Keep the host object, saved-view object and their identities distinct. Native view query/settings payloads are intentionally opaque; successful storage alone does not prove the Heart query has the same meaning. |
| `ot-objectType` (4), `ot-relation` (5), `ot-relationOption` (13) | SDK Type definitions use the `__type__` marker and the `type` namespace. Property definitions are records on the declaring owner's `properties` dataset. Choice options live under their exact option ID in `x-format.options`. | Resolve an original source schema ID to the correct native Type object, property record, or embedded option address. Preserve ordered recommendations, hidden state, provenance, defaults and target restrictions. An option is not a standalone native object. Existing canonical-property and embedded-option evidence joins remain mandatory. New live schema reads must retain current account, space and process authority. |
| `ot-participant` (19), `ot-space` (10), `ot-spaceView` (18) | Authoritative members and ACL surfaces return native identities, role and membership status. Space metadata and the derived `spaceIndex` are separate from account-private `/settings`. | Bind source participant/space identities to their actual native counterparts. Keep original membership/history evidence separate from current authorization. A copied value must never grant permissions or stand in for an active native member. Preserve the account-private boundary of settings and distinguish per-space shared metadata from account-private presentation. |
| `ot-chatDerived` (22), `ot-discussion` (27) | The canonical `chat_messages` module supplies native messages, replies, attachments, derived mentions and identity-scoped reactions. Native creation stamps creator and timestamps. The module declares `NoCopy = true`; its dataset declares `SkipHistory = true`. | Ordinary message replay is not an acceptable historical importer: it would attribute originals to the importer and change their clocks. A qualified import requires exact original authors, ordering, reply/reaction identities and signed source history, with an explicit distinction from new native signatures. The current source must remain blocked for such replay. |
| `ot-template` (0; smartblock 288) | The SDK's hidden `template` collection marks an ordinary object of its underlying type. `CreateObjectOpts.From` copies it, omits the template marker from the new object, and records `any.template` identity/version provenance. | Map the source template's underlying Type, body, property values, template label/version and internal references. Validate a real template-derived creation and its provenance. Layout 0 by itself is insufficient to classify a Template as a Basic document. |
| `ot-date` (17; smartblock 516) | Native `datetime` values are supported. | A scalar date is not yet a qualified first-class Heart Date object. Canonical date identity, uniqueness, source date interpretation, references and offline reopen need an explicit adapter and proof. No generic-page fallback is admitted. |

## Native source anchors

- Files: `internal/api/files.go` and `internal/server/handlers_files.go`.
- Collections and saved views: SDK `internal/types/collection/collection.go`, Any `internal/dataview/dataview.go`, `internal/server/handlers_collections.go` and `internal/server/handlers_dataview_test.go`.
- Definition objects: SDK `internal/types/type/type.go`, `internal/types/any/any.go`; current Swift `AnyDestinationDefinitionCoverage.swift` and `AnyHeartNativeDefinitionPlan.swift`.
- Membership and space boundaries: `internal/api/members.go`, `internal/api/spaces.go`, `internal/server/handlers_members.go` and `internal/server/handlers_settings.go`.
- Chat: `internal/chat/chat.go`. The source explicitly refuses client writes to derived creator/time/mention fields; `NoCopy` and `SkipHistory` are material import constraints.
- Templates: SDK `internal/types/template/template.go` and Any `internal/server/handlers_templates_test.go`.
- Built-in registration: `internal/server/sdk.go` and `internal/server/handlers_builtin_types_test.go`. `page` and `dataview` are registered Types. `template`, `miniapp` and `bin` are collections, with distinct native surfaces.

## Computed properties and original metadata

The native link index is a dedicated read surface. The original `links` and `backlinks` definitions select that surface through an exact source-evidence binding. They must not create mutable SDK property shadows. Account/space/process leases govern each live read, while original definition bytes remain provenance. A truncated result is refused by default, and an empty device-local result is not proof of object existence or global replication completeness.

Likewise, source creator/time facts cannot overwrite the destination's native signer or creation clock. Existing canonical bindings and immutable source facts retain these two meanings separately. A new contract is needed for each remaining computed/system relation; merely storing its old value in JSON is not functional equivalence.

## Next implementation boundary

After the new computed-links adapter passes its focused native qualification, the next selected boundary is source schema identity resolution and live Type/Property/Option reads. The original accepted destination already contains real type/property records and the four embedded options. The adapter can reuse those exact records and the saved plan/progress mappings, exposing an explicit navigation target without repeating the 182-operation migration or fabricating standalone option objects.

This contract map leaves full C acceptance open. Every new family requires a closed source-to-native correspondence and actual evidence for the affected behavior before its existing refusal is removed.
