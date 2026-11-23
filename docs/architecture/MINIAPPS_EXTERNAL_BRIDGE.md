# Anytype external MiniApps bridge

The integration adds a square-grid MiniApps entry beside the original editor controls, in the object menu, in selected-block controls, and in the existing UITextView selection menu. Shared HanlinMiniAppsPicker owns Favorites, visibility, ordering and the new-window preference. Only the lightweight bridge and picker products enter Anytype.

## Context and transport

A nonempty native selection requests replaceSelection. A caret or toolbar invocation requests insert. Input text at a caret is deliberately empty; full document text remains in source.documentText. A MiniApp can explicitly return display, insert, replaceSelection, replaceDocument or custom output.

The real shared container is group.com.itorah.shared. Requests use hanlinminiapps://x-callback-url/run?request=<UUID>; returns use the actual resolved Anytype bundle scheme with host miniapps and path /return. Source metadata binds the original account, Space, object, scene, stable block IDs, UTF16 selection and original text/marks. Selected native files finish copying into the group before launch.

Cold callbacks use the original queued object deep link. Warm callbacks use the actual registered mounted editor. Pending results remain durable until their original document is ready. No private temporary container substitutes for a missing App Group.

## Native writes and replay

The existing BlockActionService performs text changes, insertion and file upload. Text changes retain native IDs, children, styles and unaffected marks. Multi-block/document-body replacement writes returned text to the first affected block and empties subsequent affected text blocks, preserving titles, non-text blocks and the native hierarchy.

A local write-ahead journal holds the original snapshot and exact plan before native writes. Current native content is compared before each write, and openForPreview verifies the saved result. If the original changed, returned output is inserted separately. Native BlockReplace cannot safely replace a block with itself because the original middleware unlinks the target after adding its replacement.

Inserted blocks contain a deterministic request/item ID and a request marker in the same native BlockCreate. Per-block verified progress survives relaunch. Duplicate callbacks resume the saved plan or acknowledge a completed receipt. The bridge is acknowledged only after native readback and a durable completed receipt. Display/error results remain pending until their actual result sheet is dismissed.

The existing text API has no atomic compare-and-swap or combined text/receipt transaction. Fresh preflight/readback and the journal do not claim to eliminate the race with an external concurrent edit between a read and a write.

## Signing identities

| Configuration | Existing identity | Existing group | Added group |
|---|---|---|---|
| Debug / Debug-Anytype | io.anytype.app.dev | group.io.anytype.app.dev | group.com.itorah.shared |
| Release-Anytype | io.anytype.app | group.io.anytype.app | group.com.itorah.shared |

Source DEVELOPMENT_TEAM remains J3NXTX3T5S. The companion apps use owner team NA6HPWARQ2. Physical sharing requires the owner's verified registered fork identity and matching group profiles. No such identity was found in the inspected tracked Anytype workflows/scripts/fastlane/docs; existing IPA lanes are unsigned. Simulator execution is separate from physical signing.

## Validation

Thirteen new PinkhaMiniAppsEditPlannerTests passed on Oracle Swift6.4.3 against the actual bridge package, covering Hebrew/emoji UTF16 replacement, caret insertion, invalid ranges, mark preservation, native block IDs, conflict/replay, attachment identity and durable-plan round trip. A first test-helper compilation error was corrected before 13/13 execution. The initial twelve new/changed Swift source files passed frontend parsing; plists and diff checks also passed.

Run only the new portable suite with:

```sh
python3 scripts/validation/run_miniapps_consumer_tests.py --bridge-package /path/to/Hanlin/Packages/HanlinMiniAppsBridge
```

Logs: docs/validation/20261123-miniapps-consumer. These portable checks do not claim Apple SDK typechecking or an actual two-application native editor round trip; those remain a separate focused gate. Accepted SDK06/component/UI journeys were not replayed.
