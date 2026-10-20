# Torah associations production UX acceptance matrix

Date: 2026-10-20

`IMPLEMENTED` is code evidence, not physical-device proof. Any behavior that
requires the owner's authenticated iPad is explicitly `DEVICE PENDING`.

| ID | Status | Evidence / exact boundary |
|---|---|---|
| DOC-01 | IMPLEMENTED / CI PENDING | Fresh repository test stores and reloads document REF/TOPIC/WORD with `blockId == nil`. |
| DOC-02 | IMPLEMENTED / CI PENDING | Document update/removal test retains two unrelated block records. |
| DOC-03 | IMPLEMENTED / CI PENDING | Same source remains three target records at document, block A and block B. |
| DOC-04 | IMPLEMENTED / CI PENDING | Exact-target removal tests preserve other scopes. |
| DOC-05 | IMPLEMENTED / CI PENDING | Typed context plus request UUID prevents stale block refresh from replacing document scope; reverse selection is synchronous and exact. |
| DOC-06 | PARTIAL / DEVICE PENDING | Space/object are immutable per session and records are filtered exactly; authenticated navigation A→B→A and multiple windows require owner hardware. |
| DOC-07 | IMPLEMENTED / CI PENDING | Existing v2/v1, unknown-field and future/corrupt fail-closed coverage retained; no migration or read-time rewrite added. |
| DOC-08 | DEVICE PENDING | Force-close/reopen checklist below; not inferred from same-process tests. |
| GATE-01 | IMPLEMENTED / CI PENDING | Gate state, UI, errors and authorization policy removed; workflow source scan fails if forbidden symbols return. |
| GATE-02 | IMPLEMENTED / CI PENDING | Normal link/unlink/quote/Notes paths have no opt-in; native repository permission/stale/Space tests remain. |
| GATE-03 | IMPLEMENTED / CI PENDING | External Torah drop is copy only for writable valid placement; internal drag is move; readonly is forbidden. |
| OPEN-01 | IMPLEMENTED / CI PENDING | `UICellAccessory.CustomViewConfiguration` badge invokes session source opening and the existing `.torahInspectorSheet`. |
| OPEN-02 | IMPLEMENTED / CI PENDING | Stored section provenance creates exact segment selection and `.relationships` entry. |
| OPEN-03 | IMPLEMENTED / CI PENDING | One REF opens directly; multiple REF or WORD/TOPIC opens localized scoped chooser; document chips open REF sources. |
| OPEN-04 | IMPLEMENTED / DEVICE PENDING | Accessory is outside editable content; no collection/text-view double-tap recognizer was added. Caret/selection/VoiceOver require iPad verification. |
| LOC-01 | IMPLEMENTED / CI PENDING | Central formatter selects stable `labelHe`/`labelEn` by effective locale without changing IDs or canonical refs. |
| LOC-02 | PASS (portable) | PinkhaKit test suite verifies section-derived א׳/ט״ו/ט״ז and refuses fabricated daf/range labels. |
| LOC-03 | IMPLEMENTED / CI PENDING | Anytype and Kit pass environment locale through chips, work titles, controls, Notes and errors; Kit UI tests run on macOS CI. |
| LOC-04 | IMPLEMENTED / CI PENDING | Existing bodies are never migrated; new quote body is provider text only and localized source remains association-backed accessory metadata. |
| DATA-01 | IMPLEMENTED / CI PENDING | Single process queue/readback tests retain records and unrelated document/block data. |
| DATA-02 | IMPLEMENTED / CI PENDING | Wrong type, corrupt/future payload, wrong Space, stale block and readonly cases fail without write. |
| REG-01 | PARTIAL | Local `PinkhaKit`: 131 tests / 16 suites passed. Kit UI and Anytype native tests await Xcode CI. |
| REG-02 | IMPLEMENTED / CI PENDING | Quote insertion retains `setFocus: false`; generic block creation overload is unchanged. |
| REG-03 | DEVICE PENDING | Real iPadOS 27 physical-right system Sheet/detents retain prior Kit evidence; updated authenticated host needs owner verification. |
| REG-04 | CI PENDING | Workflow keeps bundle ID, strips extensions/signature, applies no production entitlements and packages unsigned device IPA. |
| LIMIT-T2 | UNPROVEN / UNCHANGED | Independent multi-device scalar merge is still not claimed. Serialized single-active-writer/readback safeguards remain. |
| LIMIT-LOGIN | FAIL / UNCHANGED | Historical simulator AccountSelect run `39306273085` remains separate and does not represent the owner's physical iPad session. |

Authenticated Anytype screenshots are not manufactured in CI. Kit demo
screenshots, if produced, must remain labeled as Kit evidence only.
