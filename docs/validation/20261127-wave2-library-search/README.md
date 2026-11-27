# Native library search: replacement query publication

## Problem and change

The native library kept `searchResults` when a nonempty query was replaced.
If the replacement search failed, its error handler reported the failure but
left the previous query's rows visible below the new query. This follows from
the original presentation method and its view; it is not a claimed simulator
reproduction.

The presentation now clears those rows before starting the replacement read.
The original 300 ms debounce, cancellation, request and workspace generation
checks, error reporting and final loading-state ownership remain intact.

The production native read was moved without changing its behavior to the
private `searchDocuments` method. Its exact normalized body is bound in
`source-review.json`: the FTS request, limits, excluded collections, metadata
authorization, duplicate handling and final lease validation are preserved.
The public constructor and `searchChanged()` API are unchanged. An internal
typed-read overload returns the same owned task so tests can drive the actual
publication method without dispatching HTTP or native work.

## Source custody

The reviewed shared baseline is
`a82fa890a0114990e474b48830e4a2de3e32c79d`. Its library presentation bytes match
the isolated branch's `a089ff29a5c0a7e415aac800844505f099a5561d` source exactly:
Git blob `52aa0232a27ac571340bbc1e088b3669b525f56f`, SHA-256
`790b63de535dd44aa02925a5df93a42a2b52928a1a4e5390e33eee6bd4f09bbe`.
All source outside the search methods is byte-identical. This downstream file
is absent from original source baseline `586c98`; no existing source-preservation
map entries, editor, native contracts or archive controls were changed.

The source ownership notice is Asana HQ51 story `1220940977020217`.

## Focused regression and outstanding acceptance

`AnyLibrarySearchPublicationTests` contains two methods:

1. Load a real presentation's initial query result, replace the query, fail its
   read, and require the old rows to disappear both while pending and after the
   failure, with the real failure feedback retained.
2. Hold an older read, fail the replacement query, then release the older read
   successfully despite its task having been cancelled. Require the newer
   failure and empty results to remain unchanged.

These are typed presentation-boundary tests. They use the real library model
and lifecycle and do not claim native search/index/ACL or mounted UI authority.
Both are **NOT_RUN**, pending the coordinated Apple build. No application,
UI build, XCTest or native operation was executed for this change. Source
preservation checks are not a substitute for these tests.

The shared product still requires visual search checks in the native library.
The original Archive733b failure and diagnostic8e473 remain unchanged and are
not explained or accepted by this independent search fix. No historical drag,
T5 36+9 calls, or passed library scenarios were rerun. Physical-device acceptance
remains open.

Rollback is the source commit's ordinary inverse on this isolated branch;
there is no data or schema change to reverse.
