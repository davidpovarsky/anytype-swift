# Torah Inspector embedded search acceptance matrix

Date: 2026-10-25

This matrix is the CI-bound record for the embedded Inspector search implementation. `EXECUTED_PASS` requires an actually executed automated check. Criteria needing an authenticated physical iPad remain `DEVICE_PENDING` even when CI is green.

| ID | Automated status before consolidated CI | Evidence / remaining gate |
|---|---|---|
| K1 | EXECUTED_PASS | Kit package and UI tests retain the legacy X when host search is nil. |
| K2 | EXECUTED_PASS / DEVICE_PENDING | Kit UI tests verify one Search action replaces X with a 44pt target; physical VoiceOver/RTL inspection remains. |
| K3 | EXECUTED_PASS | Route tests cover reader A → search → full source B and pop restoration without dismissal. |
| K4 | EXECUTED_PASS | Relationship root and segment routes share the same search path without duplicate toolbar actions. |
| K5 | EXECUTED_PASS / DEVICE_PENDING | Deterministic detent state tests cover Peek promotion/restoration without sleeps; keyboard interaction remains physical-device acceptance. |
| K6 | EXECUTED_PASS / DEVICE_PENDING | Existing side-sheet UI tests and three RTL simulator detent captures preserve 155pt/medium/large, drag indicator, background interaction and trailing edge. |
| K7 | EXECUTED_PASS / DEVICE_PENDING | Full-reader and nested segment route tests pass; real reader viewport/commentary expansion remains physical-device acceptance. |
| A1 | CI_PENDING | Production shared `TorahSourcesSearchContentView` is used by both compositions; focused test counts exactly one `UITextField`. |
| A2 | CI_PENDING | Screenshot test renders all three scopes, both presentations, Hebrew RTL, using the production component and real SVG assets. |
| A3 | CI_PENDING / DEVICE_PENDING | 0/1/2/12 association cases, 48pt strip, horizontal reachability and persistence states are selected; physical Dynamic Type remains. |
| A4 | CI_PENDING | Presenter test verifies one current-stack navigation callback, unchanged outer selection and no standalone sheet. |
| A5 | CI_PENDING | Native repository test verifies embedded document target despite prior block context, readback/relaunch and unchanged standalone block behavior. |
| A6 | CI_PENDING | Rapid query/scope cancellation plus stale/dismissed/inactive source and write guards are selected. |
| A7 | EXECUTED_PASS / DEVICE_PENDING | Presenter and Kit route state retain query/list anchor and root route state; real viewport, keyboard and commentary expansion remain. |
| A8 | CI_PENDING / DEVICE_PENDING | Topic/word typed document links and existing repository error/idempotency suite are selected; Insert Segment device behavior remains. |
| A9 | CI_PENDING / DEVICE_PENDING | Accessibility labels/44pt targets and RTL/narrow render tests are selected; authenticated VoiceOver, dark mode, compact iPhone and largest Dynamic Type remain. |
| A10 | CI_PENDING / DEVICE_PENDING | Production component screenshot attachments plus Kit detent captures are selected; the full authenticated physical-iPad sequence remains. |

## Preserved boundaries

- No Heart, protobuf, generated code, signing identity, entitlement, bundle identity, native Anytype search primitive or Maktabah change.
- Embedded search writes only to an explicit current document context. Standalone block search remains block-scoped.
- The only new upstream-owned hunk is the owner-authorized project pin recorded in `docs/architecture/UPSTREAM_EXCEPTION_REGISTER.md`.
- CI output is an unsigned same-sandbox IPA. Installation/signing/release remain owner actions.
