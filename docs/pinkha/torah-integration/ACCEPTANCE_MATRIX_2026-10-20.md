# Torah Inspector iPad trial acceptance matrix

Date: 2026-10-20

Any unobserved iPad behavior is `USER TEST PENDING`. `IMPLEMENTED` means the
source path exists; it is not a device PASS.

| ID | Status | Evidence / exact boundary |
|---|---|---|
| KIT-1 | IMPLEMENTED / CI PENDING | App target links `TorahInspectorUI` directly and PinkhaKit links Core only, both at `f67582097f9f083f9b4ea55c7ac2828853093f87`; Kit retains its own NavigationStack. |
| KIT-2 | IMPLEMENTED / SCREENSHOT PENDING | Actual `.sheet` and iOS 27 `.presentationPlacement`; RTL physical-edge unit test. Current Kit run `39338038543`; prior UI identifier-observation failure `39333954262` is retained. |
| KIT-3 | IMPLEMENTED / SCREENSHOT PENDING | 155/medium/large detents and Kit UI test. |
| KIT-4 | IMPLEMENTED / CI PENDING | Production `AnytypeTorahWorkspace` fetchers feed actual Kit reader/commentaries/links; no fixture provider in Anytype UI. |
| KIT-5 | IMPLEMENTED / USER TEST PENDING | Native Note create/open/unlink callbacks and cache invalidation. |
| UX-1 | IMPLEMENTED / APP SCREENSHOT NOT VERIFIED | `תורה / מקורות` editor entry has accessibility ID `torah-sources-entry`. An authenticated app screenshot cannot be captured without a fresh normal login. |
| UX-2 | IMPLEMENTED / CI PENDING | Provider suggestion/resolve calls for refs/topics/words with 300 ms cancellation task. |
| UX-3 | IMPLEMENTED / USER TEST PENDING | Document and single-block add/list/unlink; exact session Space/object/block and disposable gate. |
| UX-4 | IMPLEMENTED / CI PENDING | Resolved refs alone create Kit selections; word/topic do not masquerade as verses. In-Kit routes remain active; unsupported new-tab callback is hidden. |
| UX-5 | UNSUPPORTED, DISCLOSED | No verified edit-stable native character anchor; no UTF-16-only durable control exposed. |
| QUOTE-1 | IMPLEMENTED / USER TEST PENDING | Native quote block, shared handler, `setFocus: false`; ordinary overload remains default-focus. |
| QUOTE-2 | PARTIAL / USER TEST PENDING | Block association stores canonical/provider/snapshot/version/license metadata and duplicate drop claim. Strict read-only, Undo/Redo and two-window checks are pending. |
| DRAG-1 | IMPLEMENTED / REGRESSION CI PENDING | Internal `BlockDragConfiguration` path remains `.move`; focused policy test added. |
| DRAG-2 | IMPLEMENTED / USER TEST PENDING | External UTType path returns `.copy` and revalidates session opt-in; physical system-sheet drag unobserved. Explicit Insert is independent. |
| DATA-1 | IMPLEMENTED / FOCUSED TEST PENDING | Present non-string property now fails closed; future/corrupt/target tests retained. |
| DATA-2 | FAIL (UNCHANGED) | T2-L run `39306273085` remains failed at cold AccountSelect. |
| DATA-3 | USER TEST PENDING | Physical iPad force-close/relaunch and offline persistence not observed. |
| REG-1 | CI PENDING | Anytype run `39335838450`; no regression PASS claimed before completion. |
| PLATFORM-1 | PARTIAL / USER TEST PENDING | Kit fallback source path and RTL resolver exist. Orientation/window/iPhone screenshots are unobserved. |
| BUILD-1 | CI PENDING | Xcode 27 device lane `39335838450`; no IPA claim until artifact exists. |
