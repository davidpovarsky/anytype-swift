# Torah associations production UX acceptance matrix

Date: 2026-10-20

`IMPLEMENTED` is code evidence, not physical-device proof. Any behavior that
requires the owner's authenticated iPad is explicitly `DEVICE PENDING`.

| ID | Status | Evidence / exact boundary |
|---|---|---|
| DOC-01 | PASS (CI) | Fresh repository test stores and reloads document REF/TOPIC/WORD with `blockId == nil`. |
| DOC-02 | PASS (CI) | Document update/removal test retains two unrelated block records. |
| DOC-03 | PASS (CI) | Same source remains three target records at document, block A and block B. |
| DOC-04 | PASS (CI) | Exact-target removal tests preserve other scopes. |
| DOC-05 | PASS (CI) | Typed context plus request UUID prevents stale block refresh from replacing document scope; reverse selection is synchronous and exact. |
| DOC-06 | PARTIAL / DEVICE PENDING | Space/object are immutable per session and records are filtered exactly; authenticated navigation A→B→A and multiple windows require owner hardware. |
| DOC-07 | PASS (CI) | Existing v2/v1, unknown-field and future/corrupt fail-closed coverage retained; no migration or read-time rewrite added. |
| DOC-08 | DEVICE PENDING | Force-close/reopen checklist below; not inferred from same-process tests. |
| GATE-01 | PASS (CI) | Gate state, UI, errors and authorization policy removed; the workflow source scan passed. |
| GATE-02 | PASS (CI) | Normal link/unlink/quote/Notes paths have no opt-in; native repository permission/stale/Space tests remain. |
| GATE-03 | PASS (CI) | External Torah drop is copy only for writable valid placement; internal drag is move; readonly is forbidden. |
| OPEN-01 | PASS (CI) | `UICellAccessory.CustomViewConfiguration` badge invokes session source opening and the existing `.torahInspectorSheet`. |
| OPEN-02 | PASS (CI) | Stored section provenance creates exact segment selection and `.relationships` entry. |
| OPEN-03 | PASS (CI) | One REF opens directly; multiple REF or WORD/TOPIC opens localized scoped chooser; document chips open REF sources. |
| OPEN-04 | IMPLEMENTED / DEVICE PENDING | Accessory is outside editable content; no collection/text-view double-tap recognizer was added. Caret/selection/VoiceOver require iPad verification. |
| LOC-01 | PASS (CI) | Central formatter selects stable `labelHe`/`labelEn` by effective locale without changing IDs or canonical refs. |
| LOC-02 | PASS (CI) | PinkhaKit verifies section-derived א׳/ט״ו/ט״ז and refuses fabricated daf/range labels. |
| LOC-03 | PASS (CI) | Anytype and Kit pass environment locale through chips, work titles, controls, Notes and errors; Kit tests ran on Xcode 27 CI. |
| LOC-04 | PASS (CI) | Existing bodies are never migrated; new quote body is provider text only and localized source remains association-backed accessory metadata. |
| DATA-01 | PASS (CI) | Single-process queue/readback tests retain records and unrelated document/block data. |
| DATA-02 | PASS (CI) | Wrong type, corrupt/future payload, wrong Space, stale block and readonly cases fail without write. |
| REG-01 | PASS (CI) | TorahInspectorKit: 25 tests; PinkhaKit: 131 tests / 16 suites; focused native suite: 15 tests / 1 suite; all passed. |
| REG-02 | PASS (CI) | Quote insertion retains `setFocus: false`; generic block creation overload is unchanged and the device target compiled. |
| REG-03 | DEVICE PENDING | Real iPadOS 27 physical-right system Sheet/detents retain prior Kit evidence; updated authenticated host needs owner verification. |
| REG-04 | PASS (CI) | Xcode 27 device build produced the audited unsigned IPA with the original bundle ID, no extensions, no signature, no provisioning profile and an empty entitlements override. |
| LIMIT-T2 | UNPROVEN / UNCHANGED | Independent multi-device scalar merge is still not claimed. Serialized single-active-writer/readback safeguards remain. |
| LIMIT-LOGIN | FAIL / UNCHANGED | Historical simulator AccountSelect run `39306273085` remains separate and does not represent the owner's physical iPad session. |

Authenticated Anytype screenshots are not manufactured in CI. Kit demo
screenshots, if produced, must remain labeled as Kit evidence only.

## CI and package evidence

- GitHub Actions run `39469048720` passed at Anytype commit
  `e58516b113f00d067472772493dee033bb2f97bf` with TorahInspectorKit pinned to
  `1ebbbd2d43e1ba078e50408ce518d739fe6ca94f`.
- Unsigned IPA artifact: `Anytype-Torah-iPadOS27-Unsigned-IPA`, artifact ID
  `12290847132`, 149,095,450 compressed artifact bytes. The contained IPA is
  149,688,876 bytes with SHA-256
  `0fb5c898f5e17fa46639868043508ca910d2e55c7ce2b300d262202ebf803762`.
- Package audit: `com.gloiiire.anytype.torahtrial`, display name
  `Anytype Torah`, minimum iOS 17.0, device family `[1, 2]`; unsigned, with no
  embedded PlugIns, appex, provisioning profile or `_CodeSignature` directory.
- Toolchain: Xcode 27.0 (`27A266a`), Apple Swift 6.4.
