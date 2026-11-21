# Qualified original results, 19 November 2026

These reports retain the exact original GitHub artifacts, hashes, source
bindings and limitations. Each result is scoped to its original source/run.

* Core `44602524261` at `c787745ad99348aa198b91be0c672f5a9ba2fbda` passed
  55 methods and 83 invocations, with no failures or skips. All 13 focus methods
  and 21 focus invocations passed. This closes the earlier diagnostic-fixture
  failures. It does not exercise the later direction additions (57/87) or the
  pending editor input-ownership correction.
* Quote `44594932364` at `40789dc97176bfa2a7166d2345e6b0dd3de9cada` built
  and passed preparation, then its actual UI test failed while typing the native
  anchor. The original screenshot and hierarchy show a partial anchor. The
  actual UI PID and earlier runtime-probe PID differ. Quote/drop/undo/redo stages
  were not reached; no Quote acceptance or same-process runtime claim follows.
* Native T5 attachment `44610974453` at
  `be6cc5d8b5e65ee78f46e09b3105e3360eec894f` passed both actual Linux native
  packages: 48 top-level tests, 250 test/subtest records, no skips. Restoring the
  exact original r14 `basic/details.go` through a one-file compile overlay made
  all four new ordinary-edit regressions fail for the expected attachment
  assertions, plus their parent test. All 91 source inputs and 37 applied native
  files remained unchanged. Explicit attachment behavior passed separately.

The T5 result does not build a corrected Apple runtime, prove unmodified old
client compatibility or complete T5. Editor, Quote, SDK06 and full release tasks
remain open until their own actual acceptance criteria pass.
