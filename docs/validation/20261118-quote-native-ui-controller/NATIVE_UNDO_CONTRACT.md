# Native quote history contract correction

The initial source-only UI test assumed that one Undo removes both the quote block and its canonical source association. Independent inspection of the actual pinned Heart contract disproved that assumption before any run of this new UI method.

The current product intentionally uses the existing BlockCreate request followed by ObjectSetDetails for canonical document metadata. On Heart d98420b1113536afd08cde6de9a5816f6d27ffff these are two normal history actions. Neither request provides an editor group ID. The approved r14 patch fb96818eb57bd9e0be8da90a11831bcccc7ca8e72cc0a4e9a065500feb7cc077 does not change that history behavior.

Relevant native source boundaries inspected by the SDK agent:

- core/block/editor/basic/details.go: UpdateDetails applies the changed state with NoRestrictions and KeepInternalFlags, without NoHistory.
- core/block/editor/state/state.go: actual Details before/after values are recorded in the history action.
- core/block/editor/smartblock/smartblock.go: the action receives State.GroupId and is added to native undo history.
- core/block/undo/undo.go: only a nonempty explicit group is merged; Previous returns one history action.
- pb/commands.pb.go and pb/commands.proto: BlockCreate, ObjectSetDetails and BlockPaste expose no suitable shared editor group field. BlockPaste has no document Details payload.
- The separate HTTP v2 object mutator has one-State Apply, but inserted block IDs are assigned by Native and cannot be interpolated into the accompanying canonical JSON property by an existing request contract. It is not a drop-in atomic quote API.

The T4 Asana acceptance task 1219604770637161 requests verification of Undo/Redo for this existing add-plus-metadata path. It does not define a new atomic insertion API. The corrected test exercises that existing native history precisely:

| Action | Quote block | Block-local source accessory |
| --- | --- | --- |
| Initial completed insertion | Present with original ID | Present, one canonical source |
| Undo metadata | Present with original ID | Absent |
| Undo creation | Absent | Absent |
| Redo creation | Present with the same original ID | Absent |
| Redo metadata | Present with the same original ID | Present, one canonical source |

The unrelated typed anchor must survive every stage. Each intermediate stage has a screenshot and accessibility attachment. Product code, native history and metadata retention were not modified to obtain this result.

This is a source-backed contract correction. The actual Apple UI result remains NOT_RUN. Single-step atomic quote Undo is not implemented or claimed. It would require a defined native operation that creates the block and its canonical association under one object state/lock and performs one Apply, plus generated bridge bindings and native authorization/history tests.
