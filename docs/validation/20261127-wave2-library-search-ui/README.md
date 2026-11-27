# Native Library search: one additional UI journey

This is a test-only source preparation for the frozen shared App commit
`6aab20344fcf1c645d7c96e0b9ec034ef07003a9` (tree
`69ca9d5d7e602b6f11d309faa9882f829ebc27c1`). No application source or
instrumentation changes are included. No Apple compiler, XCTest, simulator, or
physical-device action has been performed for this new method.

## Why this journey is required

The `03dae6742dec6279b8329991d435a7562918a278` Library presentation fix retires
previous-query results before the replacement read. Its two focused model tests
address failed replacement and obsolete completion. The original NativeLaunch
search interactions exercise the source Inspector; none type, replace, clear,
open, and cold-reopen the native Library's document search. Existing hierarchy
and drag results remain retained for their original scope.

## Actual UI route

The new selector is
`PinkhaAnyNativeUITests/NativeLaunchTests/testLibrarySearchReplacementAndColdReopenUseCurrentQuery`.
It uses the unchanged native account, observed creation-transition, keyboard,
save, navigation, and owned-workspace cold-reopen helpers. Its allowance is
900 seconds.

Two documents are created in a fresh owned Space with separate titles and unique
body search tokens. The journey searches for the first document, replaces the
query with the second token, observes a true empty result for a third token,
clears to both original hierarchy identifiers, opens the exact first result,
and cold-reopens the same account and Space before searching for and opening the
second result. Opened documents must retain their original native block
identifier, body SHA256, block count, title, and saved state. Search rows are
identified within the mounted Library by their unique actual title and must
replace the hierarchy rows. Error alerts cannot count as empty results.

Seven phases retain typed JSON, bounded private accessibility observations, and
actual app screenshots using `.keepAlways`:

- `alpha-result`
- `replacement-beta-result`
- `no-match`
- `cleared-hierarchy`
- `opened-alpha`
- `cold-beta-result`
- `cold-opened-beta`

The JSON records the actual hierarchy object IDs and editor block identifiers,
body hashes, current query, owned scope, and cold-reopen count. Observation makes
no extra native API call and has no test-storage override. The existing
post-onboarding guard prevents a recovery or sign-in screen from serving as an
accepted application observation. Failed-phase evidence is retained separately.

## Source custody and independent review

The whole NativeLaunch file changes from
`e32f68676df1330c0255aa7ffa93b71c16f158570250013c607084f440c54375` to
`31c64474cebf4890050f9077d3c44fac63264d878a77bd6f55811cc407e02422`.
One inserted method has SHA256
`7aa590a857aded09116f058ccdd080be43185600b8e407597ea995ef17ddadc1`.
Removing that exact insertion restores every original byte and all 18 original
methods in their existing order. The final file declares 19 methods.
The original RTL and sharing-title inverse proofs remain unchanged.

The Torah agent independently reviewed the source and reused helper contracts.
Its one setup concern was addressed by using the existing
`createNamedItemWithObservedTransition` helper and propagating its errors. The
final exact source and insertion inverse were reviewed again, with no remaining
concrete source-level blocker. This review is not compilation or UI acceptance.

## Later execution boundary

Wave3 owns the shared Mac and dispatch. This branch is derived exactly from the
frozen App commit. A separate reviewed NativeUI-only profile must bind this
fixed test source commit, retain the exact two real compiler inputs
`NativeLaunchTests.swift` and `NativeHistoryTests.swift`, and preserve the App's
qualified source, native manifest, SDK, products, and code carriers. The new
method shares that one runner with the original sharing, Archive, and finite
RTL journeys. The passed drag journey is not selected.

The source preparation does not authorize a generic source overlay, a different
App, or replacement of source pins. Successful actual compiler receipts,
method enumeration, one-case XCTest results, the seven typed evidence groups,
and visual review are required before acceptance. Build, runtime, visual, and
physical-device results are all **NOT RUN** for this new method.
