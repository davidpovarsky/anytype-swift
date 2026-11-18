# Inspector iPad evidence ? 44268689146

The original XCTest results are **5 UI PASS, 0 FAIL, 0 SKIP**, plus **1 preparation PASS**. This is evidence for the five named methods at source `70a505d68ca839b44c5215e809b1f059d64f4068`, Kit `4e59e909dd22685bb46f9396bc57e5f8c627d773`, and the verified r14 runtime from run `44203168617`.

Run: https://github.com/davidpovarsky/anytype-swift/actions/runs/44268689146

## Observed behavior

- Home was observed in 1.145338 seconds for the live app PID 14836. Ordinary method entry/final boundaries and the post-UI observation retain that process identity and source/runtime bindings.
- Add Property, document source search presentation, source chip opening/closing, empty search followed by clear, and the indexed related document all passed their existing XCTest assertions.
- Original screenshots were visually reviewed for the empty and cleared search, indexed document row, Add Property button, Hebrew property search, and opened Inspector.
- The Add Property label and Hebrew property row are readable in this English/light/portrait iPad Simulator configuration.

## Visual review follow-up

The no-match screenshot shows only ?Results come from the configured Torah provider.? It does not communicate that the search found no matches. The original test checked the empty-state container, so its PASS does not establish this user-facing message.

The follow-up changes the nonword empty-state title to the existing localized `Loc.noMatchesFound` string, retaining the lexical-entry-specific message for word searches. The existing UI test now requires the visible no-match text inside the empty state. This source change has not yet earned Apple acceptance from the original run; a new run is required.

The opened Inspector screenshot has a loading spinner. This five-method lane proves opening and closing, not completed provider commentaries or search results. The separate Inspector search lane remains required.

## Scope and preservation

Original selected artifacts are byte-preserved under `original/`; `original-manifest.json` lists each SHA-256. The complete remote artifact and the retained host ZIP have SHA-256 `07bc088a3e2def7366d2ae9d2aec16fa6a80053fc7a03b86a8ab853e906db86c` (7,972,274 bytes). Its inner evidence ZIP is `80bf0c51a88dd9211b847d20c5bb896facfa6ddf27e055c4a26122046200d90f` (8,007,920 bytes). Derived observations are separate from those originals.

This result does not establish physical-device acceptance, iPhone, dark mode, landscape, accessibility sizes, VoiceOver operation, every relaunch, the full Properties matrix, r15 block/quote freshness, or a release. The broader parent tasks remain open.
