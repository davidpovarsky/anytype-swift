# Table editing shares the native text writer

Base: 21874a0d2bf0a5dac32f35fd2bbcc8fa0dfee2fa. Owner authorization:
the complete shared Heart/Any correction request and repository AGENTS.md.
The two retained app handlers are reviewed upstream integration changes;
the queue is the existing downstream PinkhaKit component.

## Corrected behavior

A table cell now freezes accepted UIKit text in the delegate turn, before a
reused view can supply another value. Its pending state comes from the same
PinkhaSerialTextEditQueue used by the page editor. Native rejection retains
dirty text, search-owned input is committed on defocus, and a structural key
waits for accepted text. Rebinding a table row explicitly retires its previous
owner generation; tables retain their nonforking identity policy.

Explicit link/programmatic replacements enter the queue before synchronous
reset publication. The regular page handler receives that same narrow ordering
fix: synchronous link callbacks capture and accept the value before launching
their awaiting task. Its existing materialization/fork semantics are retained,
and completion is fenced by the original fork generation.

Markdown styling uses the existing markup changer, analytics event and queued
replacement path. Markdown type changes and block additions enqueue one
mandatory transaction with captured text and owner. A mandatory item seals
the full-text coalescing segment on each side, so later text cannot cancel the
command or remove its preceding accepted text. The next full-text segment
still coalesces normally. Each resumed command checks the owner generation;
late results never publish stale text or a model reset. Each command's own
task is observed for failure, independently of later successful text saves.
The logger records only operation category and error type.

## Exact verification scope

- Five changed Swift source/test files passed Swift6.3.3 syntax parsing in
  job_c48254246ba0 before its separate pure-package build timed out.
- The declarative profile Tools/Hanlin/shared_table_profile.py exactly matches
  11 table test methods and 14 argument cases. Declaration validation passed.
  It delegates original xcresult argument checking to the existing strict
  wave15_core_profile validator; aggregate counts do not prove case execution.
- The table tests drive the actual table handler, UIKit text views, actual
  BlockActionHandler and controlled native-service responses. They cover
  capture, coalescing, rejection/retry, search defocus, row rebinding, keyboard
  ordering, synchronous publication, styling, both markdown structural commands,
  and ownership changes including returning to the original ID.
- The queue suite contains the four preserved original methods plus five new
  mandatory/barrier/reset/failure methods. The isolated Windows harness copies
  only its exact source and test files to a dependency-free package, jobs=2.
  First attempt stopped during compilation at the unchanged 240-second bound
  without producing a test executable. Its status is not a test pass.
  The same cached build then completed in job_f53ddeb2d2b9: all nine methods
  passed (0.032 seconds of actual execution), source hashes stayed stable, and
  no unrelated suite ran. The exact receipt/log are scoped-checks.json and
  queue-swift-test.log. A subsequent fixture-only initializer cleanup passes
  explicit locals rather than reading stored properties during initialization;
  its separate syntax/source receipt is fixture-parse.json. The queue source and
  test bytes remain the executed hashes; those nine methods were not repeated.
- Apple type checking and the 11/14 table-handler cases remain NOT_RUN at this
  source checkpoint. They are intended for the already required SDK06 Debug
  build, selected as one Swift Testing suite and verified by exact methods and
  literal argument cases. No separate application build is required.
- No unrelated UIKit, native library, Hanlin or full application suite was rerun.
  Existing receipts retain their original source identities and scope.

This slice does not claim real native table UI, copy/paste/undo, full editor,
cross-device synchronization or physical iPad acceptance. The source map pins
the two changed handler blobs and the exact shared queue dependency references;
it does not establish semantic equivalence by itself.
