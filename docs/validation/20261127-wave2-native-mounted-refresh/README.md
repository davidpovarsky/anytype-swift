# Mounted native editor Unicode refresh regression — source preparation

The product correction is the single cache predicate in commit
`6eecb62f3bb101306b6036fbc04cc08257c3425f`, a direct child of Native26
`d528e5413c72320c423ce9ccdbd4fbe423ca4a4a`. This separate candidate appends
two XCTest methods to the already bridged `AnyNativeTextRendererTests.swift`.
The complete original 3-method, 3,269-byte file remains the prefix.

The existing renderer, focus, empty-paragraph and marked-text tests do not
construct `AnyDocumentPresentation` or exercise the controller's same-cell
cache. The complete current UI-test directory was read at immutable
`2752229aacf72f468f32a4bfe5fe0a91142f5dbe`; the existing HTTP fixtures are
Python subprocesses guarded for macOS/Linux, not iOS fixtures.

## Finite fixture and assertions

The candidate uses a new private, in-process `Network.NWListener` bound to
`127.0.0.1` and an OS-chosen port. It serves controlled component responses
through the original `AnyHTTPClient`, public `AnyApplicationSession.connect`,
`AnyUIFoundationCapabilities.verify`, `AnyNativeNoteMarker.verify`, and
`AnyDocumentPresentation.load()`. Neither the model's read operation nor its
state is replaced. A real `AnyNativeEditorController` is mounted in a real
hosted UIKit window; `render()` updates the original visible table cell.

The two cases are Latin composed/decomposed text and Hebrew combining-mark
order. Each changes only the server's source text and corresponding document
version, keeping block ID, object ID, native style, block type and UI category
stable. Assertions compare exact UTF-16 arrays for source, plain text and
attributed text; preserve a valid ASCII-prefix selection and the identities of
the mounted table cell and text view; and require a clean, writable, unchanged
document owner with no journal mutation.

The fixture serves only these existing routes for one account/Space/object:

| Method | Existing route | Purpose |
| --- | --- | --- |
| GET | `/v1/auth` | Actual client account fences |
| GET | `/v1/health` | Actual session run fences |
| GET | `/v1/pinkha/capabilities` | Original capability decoders |
| GET | `/v1/spaces/{space}/members/me` | Original membership decoder |
| GET | `/v1/spaces/{space}/collections/{notes}` | Original private Note-marker verification |
| GET | `/v1/spaces/{space}/pinkha/document-targets/{object}` | Original canonical editor policy |
| GET | `/v1/spaces/{space}/objects/{object}` | Native-shaped object read brackets |
| GET | `/v1/spaces/{space}/objects/{object}/editor/editor_blocks/markdown` | Text/version read brackets |
| POST | `/v1/spaces/{space}/query` | Complete one-block read, original query body |
| GET | `/v1/spaces/{space}/bundles/{bundle}` | Original claims root lookup |
| GET | `/v1/spaces/{space}/pinkha/objects/{object}/claims?limit=10000` | Complete empty association snapshot |
| GET | `/v1/spaces/{space}/pinkha/targets/{object}?limit=10000` | Complete empty derived properties |
| POST / GET | Original editor/claims `subscribe` routes | Explicitly held SSE streams, cancelled and drained in cleanup |

No other route is accepted. The two subscribe routes deliberately send only a
valid SSE comment and hold their connections: they do not claim a delivered
live snapshot. The ordinary HTTP snapshot and properties reads must complete
without errors before either rendering assertion. Requests, connections,
headers, bodies, responses, fixture lifetime and cleanup have finite bounds.
All fixture records are controlled data, not an accepted Native account or
signed Native proof. This is a hosted UIKit/Host component regression, not
Native, end-to-end app, or real-device acceptance.

## API decision and remaining gates

Apple documents the global URLProtocol list for the shared session and the
`protocolClasses` list for configured sessions. The documentation did not
establish interception of the production client's independently created
ephemeral session through registration alone. The candidate therefore uses
normal loopback HTTP, without swizzling or a production transport setter.

Primary API references:

- https://developer.apple.com/documentation/foundation/urlsession/shared
- https://developer.apple.com/documentation/foundation/urlsessionconfiguration/protocolclasses
- https://developer.apple.com/documentation/foundation/urlsessionconfiguration/ephemeral
- https://developer.apple.com/documentation/network/nwlistener
- https://developer.apple.com/documentation/network/nwparameters/requiredlocalendpoint
- https://developer.apple.com/documentation/network/nwlistener/port

Actual Apple compilation and runtime status are **NOT_RUN** until the next
matching product compiles and enumerates both appended methods. The prior three methods
and Native25/26 do not supply that evidence. No PBX, package, controller, Native
API, product instrumentation, original test method, or current build changes
are part of this test candidate.

## Hosted selection handoff

The complete renderer class changes from **3 methods / 3 cases** to **5 methods
/ 5 cases**. The two new method names and the existing direct-source PBX bridge
are recorded in `hosted-selection-delta.json`, with primary readback from the
exact parent commit. The file is already compiled by `AnytypeTests`; no new
source path, PBX entry, module dependency or source-count increase is proposed.

The retained Core22/26 renderer profile validates the old whole-file hash and
three original declarations, then selects the whole renderer class. It must
continue rejecting this successor until a separately reviewed selection binds
the new source. W3 must choose either the two explicit new selectors with a
reviewed explicit filter for the original three, or a reviewed 24-method /
28-case aggregate if every other original input and case remains unchanged.
This report does not implement either runtime route. Heart focus 22/34 and
NativeLaunch26 are unchanged, and accepted hierarchy drag is not selected.

## Retained listener review finding

`review-v1` retains the first reviewed source 81ade and suffix 30a. Root identified
that `NWListener.newConnectionLimit` is a cumulative remaining connection
allowance, not a simultaneous-connection cap. The successor sets that allowance
to the existing finite 512-request budget while retaining the independent 16
tracked simultaneous-connection limit. Connections rejected by the scoped
fixture still consume the listener allowance and are tracked through actual
cancellation. `listener-limit-correction.json` records the exact inverse to the
predecessor; no runtime attempt was made or characterized as a test failure.

Primary API: https://developer.apple.com/documentation/network/nwlistener/newconnectionlimit

The next source review identified two ownership corrections. The connection's
state handler now cancels through the existing queue-owned connection dictionary,
so it does not retain its own connection. The previous key window is captured
from the same foreground scene used by the test window. `review-v2` retains the
preceding e0d8/60f source and root review; `ownership-correction-inverse.json`
restores that entire predecessor. These are source findings and corrections,
with no compiler or test execution attached to them.
