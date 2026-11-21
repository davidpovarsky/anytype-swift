# Shared editor input ownership — 21 November 2026

## Change and source boundary

Based on consolidated commit `8a7cc666c5d5f5719d6f94809069024262c05b69`,
which integrates the retained Heart application and the native Any consumer.

The two editors use `PinkhaTextInputRenderPolicy` from PinkhaKit. It protects a
composition, avoids replacing identical characters when only attributes change,
and preserves a native adapter's unacknowledged local input. Once that adapter
acknowledges the input, remote and undo changes replace text normally. It does
not infer acknowledgements from prefixes or record a permanent history of text
to ignore. Exact UTF-8 identity is required before applying attributes in place,
because canonical String equality does not guarantee equal storage offsets.

Heart's whole-text API needs sequential writes. Its former independent tasks
could all resume after one asynchronous empty-block fork with different text
snapshots; every task then emitted a whole-text local event. The content view
accepted any differing event even while later input was pending. The shared
serial queue dispatches one write at a time, coalesces only undispatched text,
and retains dirty ownership on failure or deliberate composition/search
deferral. It does not retry a dispatched write. Explicit identity reset
invalidates queued old work while preserving serialization with an in-flight
request. The Heart adapter rechecks its identity generation after asynchronous
materialization/fork and waits for text before keyboard structural actions.

The historical run44594932364 demonstrates input loss but did not retain the
callback interleaving. This change fixes the identified source race and adds
deterministic tests; the old run alone does not prove that race was its only
cause. Mounted editor and quote acceptance remain necessary.

## Narrow upstream integration hooks

The owner resumed implementation explicitly on21November2026; AGENTS.md's
standing authorization applies. Existing upstream-owned editor files receive
only hooks needed to connect their actual text callbacks/configuration to the
shared policy and serial queue:

- TextBlockActionHandler: ordered native input, composition/defocus, identity ownership.
- TextBlockActionHandlerProtocol: pending-input query, default false for other adapters.
- TextBlockContentConfiguration and TextBlockViewModel: live pending query.
- TextBlockContentView: shared rendering decision; existing explicit reset publisher remains authoritative.

Portable behavior lives in PinkhaKit. Heart/protobuf schemas and native API
contracts are unchanged. Any's conditional native transaction implementation
remains separate; it uses the same render policy through its UI adapter.

## Verification performed

The original two new shared production files and their original two test files
were copied byte-for-byte into a dependency-free package and run with Swift6.3.3
on Windows. Actual Swift Testing result: **9methods,11invocations,0failures**.
The raw `swift-test.log` contains each named result. The XCTest discovery
section reports zero because these tests use Swift Testing; it is not the test
result. Build86.81seconds; test execution0.006seconds.

The Swift subprocess exited0. The outer Python wrapper exited1 only while
printing the completed UTF-8 output through cp1252, after it had saved the raw
log and result. Both outcomes are preserved; no test was rerun to repair output
printing. `result.json` records pre/post source hashes and `sourceStable:true`.
`interpretation.json` records this limited interpretation and final source
hashes. The two shared production files and their tests were unchanged after
the run. Later adapter-only refinements (identity recheck, drain, UIKit fixture
initial ownership) are not claimed as runtime-tested on Windows.

Both shared production sources passed Swift6 typechecking. All ten changed
Swift files passed frontend parsing. UIKit/native storage runtime was not
exercised by this local check.

## Required focused Apple selection

Retained UIKit8methods/12invocations:

- pendingLocalTextSurvivesNativeReconfiguration()
- completedLocalTextAcceptsRemoteReplacement()
- initialFocusWaitsForAttachment()
- explicitHandoffDoesNotReplayInitialCaret()
- requestIdentityParticipatesInCellConfigurationEquality()
- staleFocusDoesNotSurviveRowLifetime(change:) —3arguments
- reusedCellUsesCurrentLockBeforeFocus(newLocked:) —2arguments
- insertedCellUsesCurrentEditingBeforeFocus(editing:) —2arguments

All are in TextBlockFocusLifecycleTests. Reuse the verified pure-test evidence
when its exact source hashes match. Run the Any renderer/marked-text/focus
selection and mounted old/new editor acceptance for their changed boundaries.
This checkpoint is not a product, device, release, or full parity approval.

## Rollback

Revert this dedicated editor commit on the integration branch, preserving the
raw test evidence. Do not reset or modify any earlier worktree or user Space.
