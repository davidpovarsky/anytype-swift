# Anytype Torah seven-fix acceptance matrix

Date: 2026-10-21

This matrix records evidence for the seven owner-reported physical-iPad defects
on top of the earlier eight-fix stage. `EXECUTED_PASS` means a deterministic
portable check actually ran. `CI_PENDING` and `DEVICE_PENDING` are not passes;
the workflow appends the exact Anytype and TorahInspectorKit identities to the
uploaded copy.

| ID | Pre-CI status | Evidence / remaining gate |
|---|---|---|
| F1-A | EXECUTED_PASS / DEVICE_PENDING | Sanitized Genesis 1:5 fixture decodes two `thinsp` plus `nbsp` at the provider display boundary. Real Anytype reader comparison remains an owner-device gate. |
| F1-B | EXECUTED_PASS | Portable PinkhaKit tests pass named, decimal, lower/upper hex, bounded double encoding, malformed/unknown entities, niqqud, raw payload identity and text longer than 4,096 characters. |
| F2-A | CI_PENDING / DEVICE_PENDING | The bespoke detail title row was removed; the native navigation title is the single header and the selector region disappears as a unit. Xcode compilation and host scroll capture remain. |
| F2-B | CI_PENDING / DEVICE_PENDING | Existing hysteresis, upward reveal, manual tools action, short-content guard and iOS 17 preference fallback remain. Runtime anchor/jitter requires host/device evidence. |
| F3-A | CI_PENDING / DEVICE_PENDING | Root relationship mode derives the Book action from empty navigation path and places it in the native leading toolbar slot with a 44pt target. Hebrew physical-right placement remains visual acceptance. |
| F3-B | CI_PENDING / DEVICE_PENDING | Any non-empty route path removes Book and leaves native Back; full-source pushes on the same stack. Three-deep Back/viewport behavior remains runtime acceptance. |
| F4-A | CI_PENDING / DEVICE_PENDING | Host picker is now a native sheet composed from Anytype DragIndicator, TitleView, SearchBar, PlainList, ListSectionHeaderView, AnytypeText, assets and semantic tokens; GroupBox and prominent blue row CTAs were removed. |
| F4-B | CI_PENDING / DEVICE_PENDING | Session queues inspector/search transitions through actual sheet dismissal so only one modal owns presentation. Existing document/block scope, link/open/unlink and error paths remain under focused host tests. |
| F5-A | CI_PENDING / DEVICE_PENDING | Panel demand maps Commentaries→links, Links→links+topics, Notes→notes and In Documents→related documents; repository cache reuse has a deterministic fetch-count test. |
| F5-B | EXECUTED_PASS / CI_PENDING / DEVICE_PENDING | Typed request tokens reject stale completion and cancellation restores idle/cached state. Portable GET retry/backoff/cancellation tests pass for 429/503, timeout recovery and non-transient status; UI state tests await Xcode. |
| F5-C | CI_PENDING / DEVICE_PENDING | Every links response recomputes grouping, topic error/loading renders independently of usable links, and source changes reset every typed state. Repeated live A↔B opens remain device acceptance. |
| F6-A | CI_PENDING / DEVICE_PENDING | Accessory uses Anytype book asset, semantic control/shape colors, caption font, 44pt target and truthful 1/2/10+ count helper. Visual comparison to IMG_0105 remains. |
| F6-B | CI_PENDING / DEVICE_PENDING | EditorViewListCell owns/removes only its Torah accessory, preserving unrelated accessories during reuse. Live edit/scroll/move/undo remains device acceptance. |
| F7-A | CI_PENDING / DEVICE_PENDING | Peek and initial reader resolve stored Hebrew presentation metadata before network content; unresolved Hebrew routes show neutral localized “Source”, never canonical English. |
| F7-B | CI_PENDING | Presentation metadata is additive and explicitly excluded from selection equality/hash/id; host association/search/resolved-reference routes carry Hebrew/English labels. |

## Preserved boundaries

- No Heart/protobuf/CRDT, association schema, native writer, permission,
  signing, entitlement or bundle-identity changes.
- Earlier reader restoration, Peek detents, related-documents limitation,
  no-autofocus quote insertion and legacy Otzaria tool/default APIs remain.
- Space-wide reverse-index item T04 remains out of scope and unresolved.
- No physical-device claim is made by CI or by the standalone Kit demo.
