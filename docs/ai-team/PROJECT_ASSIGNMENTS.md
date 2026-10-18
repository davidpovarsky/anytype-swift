# Pinkha / Anytype — Team Assignments & Work Routing

**Asana Project:** [Pinkha (1219604672449660)](https://app.asana.com/0/1219604672449660/list)  
**Base Branch:** `pinkha/torah-functional-ui-single-device-2026-10-18`  
**Setup PR:** https://github.com/davidpovarsky/anytype-swift/pull/1  
**Setup Task:** `1219611621133496`

---

## 1. Project Scope & Technical Boundaries
- **T2-L SINGLE DEVICE SCOPE:** Active implementation is strictly limited to the T2-L single active writer architecture on `pinkha/torah-functional-ui-single-device-2026-10-18`.
- **ORIGINAL T2 CROSS-DEVICE SYNC REMAINS BLOCKED:** Multi-device sync is blocked pending separate Heart/protobuf minimal RFC approval. Do not silently edit production Heart/protobuf or claim sync safety.
- Native iPadOS 27 trailing side sheet, semantic word selection anchors, Quote blocks, and Notes integration.

---

## 2. Active Open Tasks & Role Assignments

| Task / Area | Logical Lead | Reviewer / QA | Scope & Constraints |
|---|---|---|---|
| **[P0][IN PROGRESS] T2-L Single-Writer Storage** | נועם (noam) | איתן (eitan) + דנה (dana) + רוני (roni) | Native property store, serial transaction queue, ObjectShow/ObjectSetDetails readback, disposable middleware probe. |
| **[P0][BLOCKED] T2 Multi-Device Sync Architecture** | איתן (eitan) | דנה (dana) | Keep BLOCKED until minimal immutable-operation Heart RFC is independently approved. |
| **[P0][PLANNED] Semantic Word Selection Anchor** | איתן (eitan) | נועם (noam) + רוני (roni) | Stable text anchor for word selection in Anytype blocks without brittle character offsets. |
| **[P0][PLANNED] TorahInspectorKit Native Side Sheet** | מיה (maya) | נועם (noam) + רוני (roni) | Integrate pinned Kit trailing sheet (155pt, medium, large) with background interaction. |
| **[P1][PLANNED] Native Quote Block & Excerpt** | מיה (maya) | נועם (noam) + רוני (roni) | Native Anytype Quote, no autofocus, read-only yet selectable, undo/retry lifecycle. |
| **[P1][PLANNED] Native Notes & Reverse Knowledge** | נועם (noam) | רוני (roni) | Notes fetcher, reverse lookup, Space isolation, bounded incremental indexing. |
| **Upstream Sync & Regressions (U10/U12/U13)** | תומר (tomer) | רוני (roni) | Track U10 focused native regressions, investigate U12 manual editor and U13 migration gaps. |

---

## 3. Mandatory Subagent Delegation & Approval Gates
- **חובת האצלה:** הסוכן הראשי פועל כמתאם בלבד ומחויב להפעיל סוכני משנה (`invoke_subagent`). כל קוד מועבר לרוני לאימות.
- **Heart / Protobuf Integrity:** No modifications to Heart, protobuf schemas, or CRDT engine without explicit owner approval.
- **Personal Space Mutation:** Testing must use disposable isolated Spaces only. Never mutate personal Spaces.
- **Release & Merges:** PR merges to `develop` or production releases require owner approval.
- **Physical Device:** Narrow iPad window and RTL tests require physical hardware verification.
- **Asana Policy:** Autonomous updates and verified completion are authorized per `docs/ai-team/ASANA_POLICY.md`.
