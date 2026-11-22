# Actual Kit results from run 44969141133

The original workflow failed in its result qualifier. Its original receipt and
all nine artifact files remain unchanged under `original/`. Artifact
14732218185 has ZIP SHA-256
`24dfdf81711cba9abd3af48c036790db700f725077d933eb083fa21357851969`.
The producer is application source `f6d565064462d73300e66861c8113dd6e6a085a9`
with Kit `511454e49450cb2581ddf77f644146ff3e30dbef`, actual ARM64 macOS,
Xcode 27.0 (27A266a), and Apple Swift 6.4.

## Observed result and correction

The actual Swift command exited zero and its owned process group was drained.
The original stream and verbose log prove ten named methods and twelve argument
cases: six authority methods and four presentation-state methods. No failure,
known issue, skip or cancellation occurred. These executions are requalified
from the original bytes; they are not repeated.

The qualifier made four incorrect assumptions. Swift 6.4's ABI-v0 case-end
records have an empty `messages` list and identify the case using `_testCase`.
Its simple function-end records also have empty messages, while the original
verbose log contains each named passing terminal. SwiftPM appended two complete
target runs to this invocation's event file. Finally, the five refresh functions
are top-level declarations in a file called `RelatedDocumentsRefreshTests.swift`;
that filename is not a Swift suite and the old suite filter omitted them.

The corrected parser binds case descriptors, exact argument labels/values,
opaque case IDs, actual start/end pairs, named simple-method log terminals, and
independent complete target closures. It rejects missing/duplicate cases,
unknown execution, overlapping or incomplete runs, issues, known issues,
cancellation and skips. Aggregate success cannot replace a missing terminal.
Empty target runs count as zero and cannot satisfy any selected method.

`admit_observed_kit.py` checks the original manifest, commands/logs, actual host
receipt, unchanged source contract, and current Kit Git blobs before admitting
the ten methods. Git blobs avoid confusing Windows CRLF materialization with
source changes. The original post-qualification source guard was not reached
because the old parser threw; the derived receipt explicitly preserves that
fact. It does not invent a later source check for the old execution.

The next workflow executes only the five missing refresh functions, using their
actual method names. The Any mapping (three methods/four cases), shared session
(one method), and original R05 exact-one controller remain separate pending
steps. Their original skipped steps are not labelled as passes.

## Focused controller verification

Attempt 1 ran fifteen affected/new parser controls: fourteen passed and the
actual-original fixture exposed the additional empty simple-method message.
That failed original log is retained. After the narrowly scoped correction,
only the failed fixture and one new named-log rejection control ran; both
passed. Thus sixteen unique affected controls are covered without repeating
the fourteen unaffected passes. The unchanged host guard and five owned-process
controls retain their original source-bound evidence. No Swift product test,
App build or simulator was rerun for this diagnosis or requalification.

The original controller sources are under `before/`; their hashes bind them to
the previously archived control evidence. `parser-controls.json` binds the
corrected source and exact named results in both original control logs.

Sources: [original workflow](https://github.com/davidpovarsky/anytype-swift/actions/runs/44969141133),
[Swift Testing JSON ABI](https://github.com/swiftlang/swift-testing/blob/main/Documentation/ABI/JSON.md).
The observed underscored case fields are required for this fixed Swift 6.4
format; an unknown format fails for review rather than falling back to counts.
