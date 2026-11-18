# Inspector UI: actual evidence and accessibility correction

## Original execution

[Run 44253627931](https://github.com/davidpovarsky/anytype-swift/actions/runs/44253627931), attempt 1, executed the actual application at App SHA f0e0165d3396f933a14cd755312b836b60643623 with TorahInspectorKit 3beb271230ba104f0cad741984403568f1ee9980. The native r14 marker was fb96818eb57bd9e0be8da90a11831bcccc7ca8e72cc0a4e9a065500feb7cc077.

The original GitHub archive, artifact 14408577667, is 50,950,098 bytes and has SHA-256 0c35747271f1e7571511c54ea7ae125541337cbfa24013440b605cf4728c0db7. It was verified in memory before selective extraction. The complete archive and xcresult remain on GitHub. This directory retains 16 original files with exact byte hashes in verified-summary.json; the local attributes file disables text conversion for that evidence.

Native preparation passed 1/1. The original UI summary and named test nodes report **3 passed, 2 failed, 0 skipped**:

| Named method | Original result |
| --- | --- |
| testObjectAddPropertyButtonAndPickerSearch | PASS |
| testDocumentSourceSearchPresentation | PASS |
| testSourceChipOpensAndClosesInspector | PASS |
| testDocumentSourceSearchEmptyAndClear | FAIL |
| testInspectorShowsIndexedRelatedDocument | FAIL |

The actual device was an arm64 iPad Pro 13-inch (M5) Simulator on iOS 27.0 build 24A434. The original readiness attachment reports Home in 1.160277 seconds, bound to application PID 37741. The test methods subsequently opened documents by their complete disposable Space/object identity. This is current startup/document evidence for this run, not acceptance of every UI lane.

## Diagnosis from original failure attachments

The failing empty-search test had already rendered the empty-state text, “Results come from the configured Torah provider.” The actual failure hierarchy shows the outer sheet identifier on that text, the search field, its clear button, the segmented picker and the association strip. The expected child identifier was absent. The production container's accessibility identifier had propagated into its children.

The related-document failure hierarchy contains the exact canonical document row: the full UTF-8-length-prefixed Space/object identity, a visible 552 × 69 point frame, and the native label “UI27 source document, November 18, 2026”. The old test asked for a button whose entire label was only the title. The original row and metadata were present; this failure does not establish a missing native document index.

The failure-point attachments are DC266F0D-282E-40B2-9A2C-8FB1ABD8A5EE.txt and 28580675-22B1-448B-8B8C-2249313AD4CA.txt. They are original XCTest exports, not reconstructed trees.

## Narrow source correction

TorahSourcesSearchView now gives its sheet and content explicit accessibility containers, preserving descendant controls and state identities. Empty/error states retain accessible children; the idle prompt and loading state have distinct IDs. Search, providers, association storage and the native query remain unchanged.

The existing UI methods require the search field's own ID. The no-match method verifies the complete typed query, the actual empty state, and then the idle prompt after clearing; an error cannot satisfy that transition. Those outcome failures throw so the existing Swift evidence defers execute.

The related-row query uses an exact NSPredicate over the complete canonical row identifier, preserving identities longer than 128 characters. It requires one row, the original title within the combined label, and a hittable button. The date remains accessible.

## Original visual review

The three original Properties screenshots were inspected: the existing Add property label is readable at its regular body size, without clipping or crowding; the native picker opens and shows ordinary formats; Hebrew input and the מקור/ות property label remain readable and unclipped. XCTest independently passed the actual button interaction and Hebrew lookup.

This visual result covers the English application, light appearance and portrait iPad Simulator shown in those original screenshots. The historical universal Properties, type change, persistence, retry, other document kinds, physical-device and VoiceOver criteria remain open. The original search sheet and Inspector screenshots are retained for context.

## Validation limits

The two changed Swift files passed Windows swiftc frontend syntax parsing and git diff --check. That is not Apple type checking or a rerun. The original 3/2 result remains a failed run. Acceptance of this correction requires a fresh actual UI execution; full Inspector and Properties acceptance are not asserted here.
