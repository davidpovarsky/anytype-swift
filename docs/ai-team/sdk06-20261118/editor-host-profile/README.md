# Optional editor host component profile

This change adds one explicit `editor` profile to the existing SDK Apple runner.
The default remains `sdk06` and its four selected suites remain unchanged.
The new profile selects only `AnytypeTests/TorahQuoteInsertionTests` in
`Debug-Anytype`; it does not contribute to SDK06 acceptance.

## Exact execution contract

The reusable workflow `.github/workflows/pinkha-sdk06-tests.yml` accepts
`profile: editor`, together with the existing required
`expected_app_branch: codex/chatgpt-wave15-integration-20261118` and
`heart_source_run_id`. The CLI equivalent is `--profile editor`.
No arbitrary method, configuration, or source-branch input was added.

The source reviewed for the new suite is root commit
`fcdf0cb5e8800cb3b51fe92d29166e43ceae47a2`. Its Git blob SHA256 is
`c8d67f05a626e894ec82acf2b67382f08a2785f6d11f96b4d9df4b7fcc26944e`.
The exact ten method names are recorded in `source-contract.json`; the two
parameterized methods must retain their declarations `arguments: [false, true]`
and their original `dismiss: Bool` / `cancel: Bool` parameters. Thus there are
twelve distinct declared cases. This file was read from Git for verification;
no application source or duplicate test-suite copy is published by this change.

The runner retains actual run/attempt, branch/SHA, fresh simulator and
DerivedData, exact public Hanlin bootstrap, Heart provenance, resolved package
pins, product binaries, test-source hashes and post-execution source checks.
All ten full method signatures must occur once. Both actual Bool argument nodes
must pass in each parameterized method; missing, duplicate, skipped or failed
arguments cannot be replaced by an aggregate passing summary. Descendant
`Repetition` and `Test Case Run` results must also be `Passed`.

The raw summary may count ten methods or twelve distinct cases. Its count is
preserved unchanged; neither representation alone proves argument execution.
The result tree independently establishes the ten methods and twelve cases.

## Separate evidence and outcomes

Editor evidence is written to `build/editor-host-evidence`; the result bundle is
`EditorHost.xcresult`, with `editor-host-summary.json` and
`editor-host-tests.json`. The uploaded artifact is
`Pinkha-Editor-Host-<source SHA>-<run ID>-<attempt>`. Only this profile can produce
`EDITOR_COMPONENT_PASS`; `SDK06_COMPONENT_PASS` is reserved for the SDK profile.

If Apple returns an unrecognized Bool argument or execution-child representation, the command exits
nonzero with `EDITOR_EVIDENCE_REVIEW_PENDING`. The completed build/test exit,
raw summary/tree and their hashes, and post-execution source verification remain
available. The unchanged artifact can then be reviewed without repeating an
application run merely to adapt a parser. Cancellation handling and owned-process
cleanup are shared with the reviewed SDK runner.

## Evidence scope

Portable Python controls and source-contract inspection are controller evidence,
not Apple execution. The native editor suite uses controlled insertion and store
fixtures to exercise production session/repository lifetime and cancellation
logic. Passing it does not establish actual drag/drop UI, middleware writes,
provider networking, or SDK consent/create/read acceptance.

The recognized argument-tree shape was checked against the primary fastlane
fixture at commit `600714a2db5383e9e10fbfee271ba6d887c35c83`:
`trainer/spec/fixtures/Xcode26-Mixed-XCTest-SwiftTesting.json`, SHA256
`8c57cf16488633522f6923fbb14c047434606b52590f99d1795f44d4028eeac1`.
Its actual `Test Case` nodes contain `Arguments` children; argument children have
display names and results rather than unique node identifiers. This external
schema evidence is not a Pinkha test result. No third-party fixture or dependency
was copied into the application.

Independent review found and corrected a case where an unknown descendant with
a failure result could be ignored. Every descendant result must now be `Passed`,
regardless of its node type; an unknown structural child remains review-pending
even if it reports `Passed`. These are additional portable gate controls.

Native editor execution remains **NOT_RUN** until root dispatches the integrated
source through the existing Apple workflow.
