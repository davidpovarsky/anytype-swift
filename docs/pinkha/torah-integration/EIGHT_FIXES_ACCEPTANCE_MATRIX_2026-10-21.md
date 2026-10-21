# Torah Inspector eight-fix acceptance matrix

Date: 2026-10-21

This record distinguishes portable evidence, Xcode CI, and physical-device
acceptance. The workflow appends its exact Anytype and TorahInspectorKit commit
identities to the uploaded copy. `CI_PENDING` in the checked-in source is not a
pass; the matching workflow result is authoritative.

| ID | Pre-push status | Evidence / boundary |
|---|---|---|
| S01 | EXECUTED_PASS | PinkhaKit tests cover lexical 404/no-results and valid emptiness as zero suggestions; the host renders `.empty` inline and does not assign the alert message. |
| S02 | EXECUTED_PASS | PinkhaKit tests preserve malformed payload and HTTP 503 as errors; host state exposes a localized retry action. |
| S03 | CI_PENDING | Focused Anytype test exercises out-of-order query, Words→Topics scope change, cancel, clear, empty and genuine error transitions. |
| H01 | EXECUTED_PASS | Full-segment fixtures cover named/decimal/hex entities, tags, breaks and exact raw payload retention. |
| H02 | EXECUTED_PASS | Fixtures preserve niqqud, segment ordinals and a body longer than 4,096 characters without truncation or merging. |
| R01 | CI_PENDING / DEVICE_PENDING | Kit session stores canonical segment plus relative viewport and cached section window; Xcode compile/tests and visual Back comparison remain required. |
| R02 | CI_PENDING / DEVICE_PENDING | Prepend restoration and seven-section window use the stored canonical anchor; runtime pagination/jitter remains device acceptance. |
| R03 | CI_PENDING | Initial reader honors `preferredSegmentRef` only when the exact segment exists; no first-verse substitution. |
| P01 | CI_PENDING | Peek contains reference, 44pt expand/close controls and the native segmented picker; preview and insert CTA were removed. |
| P02 | CI_PENDING | Selecting any segment, including the already-selected one, expands the native sheet to medium with one shared binding. |
| P03 | CI_PENDING / DEVICE_PENDING | Existing native right-hand sheet/detents remain; RTL physical placement and drag behavior require the Xcode demo plus real iPad. |
| T01 | CI_PENDING | Anytype opts into Commentaries / Links / In Documents and omits a standalone Notes tab. |
| T02 | CI_PENDING | Legacy configuration remains Commentaries / Links / Notes and retains the old bindings and initializers. |
| T03 | CI_PENDING / DEVICE_PENDING | In Documents maps real current-document note associations and supports open/create/unlink without deleting the note object. |
| T04 | BLOCKED | No verified host reverse index exists for Space-wide backlinks. UI explicitly reports current-document-only coverage and never presents a fake Space-wide zero. |
| U01 | CI_PENDING / DEVICE_PENDING | Selector state-machine tests cover hysteresis and manual reveal; live scroll direction/jitter requires runtime acceptance. |
| U02 | CI_PENDING / DEVICE_PENDING | Short-content and loading inputs keep the selector stable; Dynamic Type clipping remains visual acceptance. |
| N01 | CI_PENDING / DEVICE_PENDING | Relationships root book action pushes `.fullSource` in the same NavigationStack and carries the exact preferred segment; Back chain needs runtime capture. |
| N02 | CI_PENDING | New-tab controls are emitted only when the optional host callback exists; inline full source is separately opt-in. |
| D01 | DEVICE_PENDING | Anytype adapters use `AnytypeText`, `AnytypeFont`, `Color.Text`, `Color.Control`, `Color.Background` and `Color.Shape`; authenticated before/after screenshots are not manufactured. |
| D02 | CI_PENDING / DEVICE_PENDING | Kit captures Hebrew RTL Peek/medium/large; Anytype light/dark, narrow Stage Manager and landscape remain physical acceptance. |
| D03 | CI_PENDING / DEVICE_PENDING | Package minimums remain iOS 17/macOS 14 and new APIs are availability-gated; iPhone and older-iOS visual fallback remains device coverage. |
| A01 | CI_PENDING / DEVICE_PENDING | Torah quote insertion keeps no-autofocus behavior and generic insertion code is untouched; keyboard/caret verification remains physical. |
| A02 | CI_PENDING | Existing native document/block association tests remain in the consolidated workflow; storage schema and writer are unchanged. |
| A03 | CI_PENDING | Kit tests compile legacy tools/initializers and the default legacy full-reader opt-in remains disabled for Otzaria. |
| CI01 | CI_PENDING | Kit Xcode 27 package/UI workflow must pass at the exact immutable Kit SHA and publish logs, xcresult and screenshots. |
| CI02 | CI_PENDING | Consolidated Anytype Xcode 27 workflow must pass Kit, PinkhaKit, focused host tests and unsigned device build at matching SHAs. |
| DEV01 | DEVICE_PENDING | Only the owner's physical iPad can close the right-sheet, keyboard, Stage Manager and authenticated-space acceptance gap. |

## Change-to-proof impact map

| Change | Module | Focused proof | Runtime scene |
|---|---|---|---|
| Typed search state + request epoch | Anytype host / PinkhaKit lexical provider | S01-S03 | Hebrew word search |
| Faithful source normalization | PinkhaKit text provider | H01-H02 | reader, copy, drag and new quote |
| Viewport/session cache | TorahInspectorCore/UI | R01-R03 | reader → detail → Back and paging |
| Compact Peek + selector state machine | TorahInspectorUI/Demo | P01-P03, U01-U02 | native 155pt/medium/large sheet |
| Typed related documents | Core repository + Anytype note adapter | T01-T04 | In Documents |
| Host semantic theme | TorahInspectorUI + Anytype DesignKit adapter | D01-D03 | search and inspector surfaces |
| Full-source route | TorahInspectorUI | N01-N02 | relationships root → reader → Back |

No Heart/protobuf/CRDT, signing, entitlement, bundle-identity or association
schema change is part of this patch.
