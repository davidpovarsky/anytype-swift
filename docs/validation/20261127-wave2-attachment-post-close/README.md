# Attachment recovery after the original owner closes

This packet contains a reviewed source change in three existing files, based exactly on `9b510b5ea80fba508d01314cefb646682943f7a9`. It retains the original attachment creator before the possible upload so the existing caller can recover its genuine in-memory acknowledgement after a completed owner change. The current owner still uses the original Host read-only resume path, original journal reservation, current authority and native readback. Unknown outcomes remain unresolved and are never turned into another upload.

**Source-only status:** Root and independent Swift/source reviews found no concrete blocker. This packet has not been compiled or executed. The new component cases, actual protected-journal failure/reopen, mounted Apple flow, HTTP/Native recovery and process-death recovery remain **NOT_RUN**. The packet is frozen for root review before any Git write; its eventual publication receipt must provide the commit and complete tree readback.

## Fixed source scope

| Existing path | Exact candidate SHA256 |
|---|---|
| `Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeAttachments.swift` | `bba403bfe183ffed00709c973549043980eed52e478c840bb613bbd1cc8673d8` |
| `Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeAttachmentIntentStore.swift` | `949651cb362238b713a626164f95eb378d0e54de47b7c84d7bca5821e1122480` |
| `Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeAttachmentIntentStoreTests.swift` | `a02e081d56d58b3fa964c601e712fd969901096755daf67bffb22499b5c7aa25` |

The exact parent already includes Host `063d3ef0b16392f67e5044faa81cf8689a75dab2`. That API is unchanged. The caller stores only the original intent durably; creator and opaque acknowledgement stay in process memory. The original claim, pending-record CAS, session/ACL checks, FilesV2 reconciliation and final presentation checks stay authoritative. Cancellation releases a caller claim only after nested work settles. A different actor/generation pair alone is not proof of an owner transition: the unchanged serialized drain, journal close and reopen route supplies that boundary.

## Current journal-close proof

`proof-index.json` identifies the current root-approved `owner-transition-source-proof-v2.json` and `journal-close-source-precision.json`. They correct one documentation phrase: the unchanged protected-journal `close()` poisons that owner and releases its **exclusive flock claim**. File descriptors may remain open until the retained files/actor are deallocated. Successful reopening must still acquire the original lock; no actual close/reopen runtime result is inferred here.

The three Swift files, fifteen declaration bodies/hashes, test counts and runtime limits are unchanged. Original proof `b2ac684c…`, manifest `12db1ccf…`, root review `631a67a7…` and peer review `d253bd1d…` remain verbatim historical evidence. The v2 proof/addendum take precedence only for the descriptor-versus-lock wording. `preparation-history.json` maps every original packet file to an identical retained byte sequence; the original 30-file packet and target also remain untouched locally.

## Test declarations and pending acceptance

| Scope | Methods | Declared cases | Status |
|---|---:|---:|---|
| Original intent-store prefix | 3 | 4 | Retained; not run by this tranche |
| Reviewed carrier precursor | 4 | 4 | NOT_RUN |
| New original-creator suffix | 3 | 4 | NOT_RUN |
| Combined full source file | 10 | 12 | Declarations only; no compiled enumeration |

The new suffix checks original creator retention through drain/reopen, exact actor/generation pairing, authority-error versus missing-ACK classification, and late export after claim/session retirement. Tests use real session/Host/store code with explicitly modeled journal/native callbacks. They cannot establish mounted UI or actual Native acceptance.

`handoff.json` lists exact source-level selectors and separates the three scopes. No target, PBX, package, producer, gate, consumer, runtime deadline or shared App61/Stage1UI10 inventory is changed. W3 owns any later matching build and explicit selection. This packet does not imply a whole-class run or grant compiled-result credit.

## Evidence and restoration

`retained/full-caller-preparation/` preserves the original candidate manifest, complete inverse, both patches, source-transition proof and both final reviews. Its original README/review status wording is retained verbatim as historical preparation evidence. `retained/carrier-preparation/` and `retained/live-ui-preparation/` preserve both reviewed predecessors and their inverse material, including their original bases and unexecuted limitations.

`source-bindings.json` binds twelve exact source bodies to their immutable primary Git URLs, Git blob IDs and retained response hashes. `owner-transition-declarations.json` retains fifteen exact source excerpts with original full-file/declaration hashes for inspection; it is evidence, not an alternate implementation. Broad Asana responses, actual user data, private runtime fixtures and the unfinished mounted-caller draft are excluded.

`packet-manifest.json` accounts for every payload file except itself. `scope-screening.json` records exact three-file restoration to the parent and the finite file allowlist. Local paths in retained review artifacts describe their original review environment; the packet paths and immutable Git source bindings are the persistent locators after publication.

Planned owned branch: `codex/chatgpt-wave15-wave2-attachment-post-close-20261127`. Parent: `9b510b5ea80fba508d01314cefb646682943f7a9`, tree `5e473fcc6c5d744fb27e75c402bd4dca35cf9cd1`. No final branch, unrelated source or prior evidence is to be overwritten. Fresh branch/workflow checks and a complete all-entry Merkle comparison remain required before an authorized API publication.
